"""调班管理服务（全异步）"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SysUser, OrgStaff
from app.models.swap import SchSwapRequest
from app.models.schedule import SchSchedule, SchScheduleDetail
from app.models.shift_template import SchShiftTemplate
from app.models.audit_log import SysAuditLog, SysConfig
from app.services.message_service import MessageService, notify_admins_extra
from app.utils.time_helper import to_local_str as _to_local_str

# 调班状态常量
STATUS_PENDING_CONFIRM = "pending_confirm"
STATUS_PENDING_CLAIM = "pending_claim"
STATUS_PENDING_APPROVE = "pending_approve"
STATUS_APPROVED = "approved"
STATUS_COMPLETED = "completed"
STATUS_CANCELLED = "cancelled"
STATUS_REJECTED = "rejected"
STATUS_TARGET_REFUSED = "target_refused"


class SwapService:
    """调班管理服务"""

    # ==================== 列表查询 ====================

    @staticmethod
    async def get_list(
        db: AsyncSession,
        *,
        user_id: Optional[int] = None,
        role: str = "requester",
        status: Optional[str] = None,
        swap_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        user_roles: Optional[list[str]] = None,
    ) -> dict:
        """获取调班申请列表"""
        query = select(SchSwapRequest)
        is_manager = user_roles and any(r in user_roles for r in ("admin", "scheduler", "leader"))

        if user_id is not None:
            if role == "requester":
                query = query.where(SchSwapRequest.requester_id == user_id)
            elif role == "target":
                from sqlalchemy import or_
                conditions = [
                    SchSwapRequest.target_id == user_id,
                    SchSwapRequest.claimer_id == user_id,
                    (
                        (SchSwapRequest.swap_type == "open") &
                        (SchSwapRequest.status == STATUS_PENDING_CLAIM) &
                        (SchSwapRequest.requester_id != user_id)
                    ),
                ]
                # 管理员/排班管理员/组长额外包含待审批的申请
                if is_manager:
                    conditions.append(
                        (SchSwapRequest.status == STATUS_PENDING_APPROVE)
                    )
                query = query.where(or_(*conditions))
            elif role == "approver":
                query = query.where(SchSwapRequest.status == STATUS_PENDING_APPROVE)

        if status:
            query = query.where(SchSwapRequest.status == status)
        if swap_type:
            query = query.where(SchSwapRequest.swap_type == swap_type)

        total = (await db.execute(
            select(func.count()).select_from(query.subquery())
        )).scalar() or 0

        query = query.order_by(SchSwapRequest.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        requests = list((await db.execute(query)).scalars().all())
        items = await _serialize_swap_list(db, requests)

        return {"items": items, "total": total}

    # ==================== 单条查询 ====================

    @staticmethod
    async def get_by_id(db: AsyncSession, request_id: int) -> dict:
        """获取调班申请详情"""
        swap = (await db.execute(
            select(SchSwapRequest).where(SchSwapRequest.id == request_id)
        )).scalars().first()
        if not swap:
            raise ValueError("调班申请不存在")

        items = await _serialize_swap_list(db, [swap])
        return items[0] if items else {}

    # ==================== 发起申请 ====================

    @staticmethod
    async def create(db: AsyncSession, user_id: int, data: dict) -> dict:
        """发起调班申请"""
        # 校验发起人排班
        req_schedule = await _get_schedule_or_raise(db, data["requester_schedule_id"])
        if req_schedule.status != SchSchedule.STATUS_PUBLISHED:
            raise ValueError("只能对已发布的排班发起调班申请")

        # 生成申请编号
        request_no = await _generate_request_no(db)

        swap_type = data["swap_type"]

        if swap_type == "specified":
            # 指定换班：前端传入的是 staff_id，需要转换为 user_id
            target_id = data.get("target_id")
            target_schedule_id = data.get("target_schedule_id")
            if not target_id or not target_schedule_id:
                raise ValueError("指定换班必须提供被换人和对方排班记录")

            # 将 staff_id 转换为 user_id
            target_user = (await db.execute(
                select(SysUser).where(SysUser.staff_id == target_id)
            )).scalars().first()
            if not target_user:
                raise ValueError("换班对象暂无登录账号，无法发起换班")
            target_id = target_user.id

            target_schedule = await _get_schedule_or_raise(db, target_schedule_id)
            if target_schedule.status != SchSchedule.STATUS_PUBLISHED:
                raise ValueError("对方排班未发布，无法换班")

            initial_status = STATUS_PENDING_CONFIRM

        elif swap_type == "open":
            # 开放换班
            initial_status = STATUS_PENDING_CLAIM
            target_id = None
            target_schedule_id = None

        else:
            raise ValueError("调班类型必须为 specified 或 open")

        # 检查是否已存在未完成的申请
        existing = (await db.execute(
            select(SchSwapRequest).where(
                SchSwapRequest.requester_schedule_id == data["requester_schedule_id"],
                SchSwapRequest.status.in_([
                    STATUS_PENDING_CONFIRM, STATUS_PENDING_CLAIM, STATUS_PENDING_APPROVE
                ]),
            )
        )).scalars().first()
        if existing:
            raise ValueError("该排班已存在未完成的调班申请，请勿重复提交")

        swap = SchSwapRequest(
            request_no=request_no,
            swap_type=swap_type,
            requester_id=user_id,
            requester_schedule_id=data["requester_schedule_id"],
            target_id=target_id,
            target_schedule_id=target_schedule_id,
            reason=data.get("reason"),
            status=initial_status,
        )
        db.add(swap)
        await db.flush()
        await db.refresh(swap)

        # 记录操作日志
        await _log_action(db, user_id, "swap_create", "swap_request", swap.id, {
            "swap_type": swap_type, "request_no": request_no,
        })

        # 发送通知
        if swap_type == "specified" and target_id:
            await _notify_swap_created(db, swap, target_id)
        elif swap_type == "open":
            await _notify_open_swap_created(db, swap)

        items = await _serialize_swap_list(db, [swap])
        return items[0] if items else {}

    # ==================== 对方确认（指定换班） ====================

    @staticmethod
    async def confirm(db: AsyncSession, request_id: int, user_id: int) -> dict:
        """对方确认换班"""
        swap = await _get_swap_or_raise(db, request_id)

        if swap.swap_type != "specified":
            raise ValueError("仅指定换班需要对方确认")
        if swap.status != STATUS_PENDING_CONFIRM:
            raise ValueError(f"当前状态 {swap.status} 不允许确认")
        if swap.target_id != user_id:
            raise ValueError("只有被换人才能确认")

        # 冲突检测
        await _check_swap_conflicts(db, swap)

        # 检查审批开关
        approval_required = await _is_approval_required(db)

        swap.confirmed_at = datetime.now()

        if approval_required:
            swap.status = STATUS_PENDING_APPROVE
            # 通知审批人
            await _notify_pending_approval(db, swap)
        else:
            swap.status = STATUS_COMPLETED
            await _execute_swap(db, swap)

        await db.flush()
        await db.refresh(swap)

        await _log_action(db, user_id, "swap_confirm", "swap_request", swap.id, {
            "confirmed_at": str(swap.confirmed_at),
        })

        # 通知发起人
        confirmer_name = await _get_staff_name_by_user_id(db, user_id)
        await MessageService.create_message(
            db, receiver_id=swap.requester_id,
            title="您的调班申请对方已确认",
            content=f"申请编号 {swap.request_no} 已被 {confirmer_name} 确认{'，等待管理员审批' if approval_required else '并生效'}。",
            msg_type="swap", sender_id=user_id,
            relation_type="swap_request", relation_id=swap.id,
        )

        items = await _serialize_swap_list(db, [swap])
        return items[0] if items else {}

    # ==================== 认领开放换班 ====================

    @staticmethod
    async def claim(db: AsyncSession, request_id: int, user_id: int) -> dict:
        """认领开放换班"""
        swap = await _get_swap_or_raise(db, request_id)

        if swap.swap_type != "open":
            raise ValueError("仅开放换班可认领")
        if swap.status != STATUS_PENDING_CLAIM:
            raise ValueError(f"当前状态 {swap.status} 不允许认领")
        if swap.requester_id == user_id:
            raise ValueError("不能认领自己发起的换班申请")

        swap.claimer_id = user_id

        approval_required = await _is_approval_required(db)

        if approval_required:
            swap.status = STATUS_PENDING_APPROVE
            await _notify_pending_approval(db, swap)
        else:
            swap.status = STATUS_COMPLETED
            await _execute_swap(db, swap)

        await db.flush()
        await db.refresh(swap)

        await _log_action(db, user_id, "swap_claim", "swap_request", swap.id, {})

        # 通知发起人
        claimer_name = await _get_staff_name_by_user_id(db, user_id)
        await MessageService.create_message(
            db, receiver_id=swap.requester_id,
            title="您的开放换班申请已被认领",
            content=f"申请编号 {swap.request_no} 已被 {claimer_name} 认领{'，等待管理员审批' if approval_required else '并生效'}。",
            msg_type="swap", sender_id=user_id,
            relation_type="swap_request", relation_id=swap.id,
        )

        items = await _serialize_swap_list(db, [swap])
        return items[0] if items else {}

    # ==================== 审批 ====================

    @staticmethod
    async def approve(db: AsyncSession, request_id: int, user_id: int, comment: str = None) -> dict:
        """审批通过"""
        swap = await _get_swap_or_raise(db, request_id)

        if swap.status != STATUS_PENDING_APPROVE:
            raise ValueError(f"当前状态 {swap.status} 不允许审批")

        swap.status = STATUS_APPROVED
        swap.approved_by = user_id
        swap.approved_at = datetime.now()
        swap.approve_comment = comment

        # 执行换班
        await _execute_swap(db, swap)
        swap.status = STATUS_COMPLETED

        await db.flush()
        await db.refresh(swap)

        await _log_action(db, user_id, "swap_approve", "swap_request", swap.id, {})

        # 通知相关人员
        approver_name = await _get_staff_name_by_user_id(db, user_id)
        notify_ids = [swap.requester_id]
        if swap.target_id:
            notify_ids.append(swap.target_id)
        if swap.claimer_id:
            notify_ids.append(swap.claimer_id)

        for uid in set(notify_ids):
            await MessageService.create_message(
                db, receiver_id=uid,
                title="调班申请已审批通过",
                content=f"申请编号 {swap.request_no} 已由 {approver_name} 审批通过并生效。",
                msg_type="approve", sender_id=user_id,
                relation_type="swap_request", relation_id=swap.id,
            )

        items = await _serialize_swap_list(db, [swap])
        return items[0] if items else {}

    # ==================== 审批拒绝 ====================

    @staticmethod
    async def reject(db: AsyncSession, request_id: int, user_id: int, comment: str = None) -> dict:
        """审批拒绝"""
        swap = await _get_swap_or_raise(db, request_id)

        if swap.status != STATUS_PENDING_APPROVE:
            raise ValueError(f"当前状态 {swap.status} 不允许审批")

        swap.status = STATUS_REJECTED
        swap.approved_by = user_id
        swap.approved_at = datetime.now()
        swap.approve_comment = comment

        await db.flush()
        await db.refresh(swap)

        await _log_action(db, user_id, "swap_reject", "swap_request", swap.id, {})

        # 通知发起人
        rejector_name = await _get_staff_name_by_user_id(db, user_id)
        await MessageService.create_message(
            db, receiver_id=swap.requester_id,
            title="调班申请已被拒绝",
            content=f"申请编号 {swap.request_no} 已被 {rejector_name} 审批拒绝。{('原因：' + comment) if comment else ''}",
            msg_type="approve", sender_id=user_id,
            relation_type="swap_request", relation_id=swap.id,
        )

        items = await _serialize_swap_list(db, [swap])
        return items[0] if items else {}

    # ==================== 对方拒绝（指定换班） ====================

    @staticmethod
    async def refuse(db: AsyncSession, request_id: int, user_id: int, reason: str = None) -> dict:
        """对方拒绝换班（仅指定换班，pending_confirm 状态）"""
        swap = await _get_swap_or_raise(db, request_id)

        if swap.swap_type != "specified":
            raise ValueError("仅指定换班可被拒绝")
        if swap.status != STATUS_PENDING_CONFIRM:
            raise ValueError(f"当前状态 {swap.status} 不允许拒绝")
        if swap.target_id != user_id:
            raise ValueError("只有被换人才能拒绝")

        swap.status = STATUS_TARGET_REFUSED
        swap.refused_at = datetime.now()
        swap.refuse_comment = reason
        await db.flush()
        await db.refresh(swap)

        await _log_action(db, user_id, "swap_refuse", "swap_request", swap.id, {
            "refused_at": str(swap.refused_at), "reason": reason,
        })

        # 通知发起人
        refuser_name = await _get_staff_name_by_user_id(db, user_id)
        msg = f"申请编号 {swap.request_no} 已被 {refuser_name} 拒绝。"
        if reason:
            msg += f"原因：{reason}"
        await MessageService.create_message(
            db, receiver_id=swap.requester_id,
            title="您的调班申请已被对方拒绝",
            content=msg,
            msg_type="swap", sender_id=user_id,
            relation_type="swap_request", relation_id=swap.id,
        )

        items = await _serialize_swap_list(db, [swap])
        return items[0] if items else {}

    # ==================== 撤回申请 ====================

    @staticmethod
    async def cancel(db: AsyncSession, request_id: int, user_id: int) -> dict:
        """撤回调班申请"""
        swap = await _get_swap_or_raise(db, request_id)

        if swap.requester_id != user_id:
            raise ValueError("只有发起人才能撤回")
        if swap.status in (STATUS_COMPLETED, STATUS_CANCELLED, STATUS_REJECTED, STATUS_TARGET_REFUSED):
            raise ValueError(f"当前状态 {swap.status} 不允许撤回")

        swap.status = STATUS_CANCELLED
        await db.flush()
        await db.refresh(swap)

        await _log_action(db, user_id, "swap_cancel", "swap_request", swap.id, {})

        # 通知相关人员
        canceller_name = await _get_staff_name_by_user_id(db, user_id)
        notify_ids = []
        if swap.target_id:
            notify_ids.append(swap.target_id)
        if swap.claimer_id:
            notify_ids.append(swap.claimer_id)
        for uid in set(notify_ids):
            await MessageService.create_message(
                db, receiver_id=uid,
                title="调班申请已被撤回",
                content=f"申请编号 {swap.request_no} 已被 {canceller_name} 撤回。",
                msg_type="swap", relation_type="swap_request", relation_id=swap.id,
            )

        items = await _serialize_swap_list(db, [swap])
        return items[0] if items else {}


# ====================================================================== #
#  私有辅助函数
# ====================================================================== #

async def _get_staff_name_by_user_id(db: AsyncSession, user_id: int) -> str:
    """根据 user_id 获取人员姓名（优先 staff.name，其次 username）"""
    user = (await db.execute(
        select(SysUser).where(SysUser.id == user_id)
    )).scalars().first()
    if user and user.staff_id:
        staff = (await db.execute(
            select(OrgStaff).where(OrgStaff.id == user.staff_id)
        )).scalars().first()
        if staff:
            return staff.name
    return user.username if user else "未知用户"


async def _get_swap_or_raise(db: AsyncSession, request_id: int) -> SchSwapRequest:
    swap = (await db.execute(
        select(SchSwapRequest).where(SchSwapRequest.id == request_id)
    )).scalars().first()
    if not swap:
        raise ValueError("调班申请不存在")
    return swap


async def _get_schedule_or_raise(db: AsyncSession, schedule_id: int) -> SchSchedule:
    schedule = (await db.execute(
        select(SchSchedule).where(SchSchedule.id == schedule_id)
    )).scalars().first()
    if not schedule:
        raise ValueError(f"排班记录不存在（id={schedule_id}）")
    return schedule


async def _generate_request_no(db: AsyncSession) -> str:
    """生成申请编号：SWAP + 日期 + 序号"""
    from datetime import date
    today = date.today().strftime("%Y%m%d")
    prefix = f"SWAP{today}"

    count = (await db.execute(
        select(func.count(SchSwapRequest.id))
        .where(SchSwapRequest.request_no.like(f"{prefix}%"))
    )).scalar() or 0

    return f"{prefix}{count + 1:03d}"


async def _is_approval_required(db: AsyncSession) -> bool:
    """检查调班审批开关"""
    config = (await db.execute(
        select(SysConfig).where(SysConfig.config_key == "swap_approval_enabled")
    )).scalars().first()
    return config and config.config_value == "true"


async def _check_swap_conflicts(db: AsyncSession, swap: SchSwapRequest):
    """调班冲突检测（简化版：检查约束规则）"""
    from app.models.constraint import SchConstraint
    from app.models.special_rule import SchSpecialRule

    # 基础检测：排班是否存在且已发布
    req_schedule = await _get_schedule_or_raise(db, swap.requester_schedule_id)
    if req_schedule.status != SchSchedule.STATUS_PUBLISHED:
        raise ValueError("发起人排班已变更，请刷新后重试")

    if swap.target_schedule_id:
        target_schedule = await _get_schedule_or_raise(db, swap.target_schedule_id)
        if target_schedule.status != SchSchedule.STATUS_PUBLISHED:
            raise ValueError("对方排班已变更，请刷新后重试")

    # TODO: 可扩展完整约束校验引擎


async def _execute_swap(db: AsyncSession, swap: SchSwapRequest):
    """执行换班操作：交换排班明细中的人员"""
    req_schedule = await _get_schedule_or_raise(db, swap.requester_schedule_id)

    if swap.swap_type == "specified" and swap.target_schedule_id:
        target_schedule = await _get_schedule_or_raise(db, swap.target_schedule_id)

        # 交换两个排班记录的人员明细
        req_details = (await db.execute(
            select(SchScheduleDetail).where(SchScheduleDetail.schedule_id == req_schedule.id)
        )).scalars().all()

        target_details = (await db.execute(
            select(SchScheduleDetail).where(SchScheduleDetail.schedule_id == target_schedule.id)
        )).scalars().all()

        # 将发起人从自己的排班中移除，添加到对方排班
        for d in req_details:
            if d.staff_id and (await _is_user_staff(db, swap.requester_id, d.staff_id)):
                d.schedule_id = target_schedule.id
                break

        # 将被换人从对方排班中移除，添加到发起人排班
        if swap.target_id:
            for d in target_details:
                if d.staff_id and (await _is_user_staff(db, swap.target_id, d.staff_id)):
                    d.schedule_id = req_schedule.id
                    break

    elif swap.swap_type == "open" and swap.claimer_id:
        # 开放换班：认领人替换发起人
        req_details = (await db.execute(
            select(SchScheduleDetail).where(SchScheduleDetail.schedule_id == req_schedule.id)
        )).scalars().all()

        # 反向查询：通过 SysUser.staff_id 获取认领人的 staff_id
        claimer_user = (await db.execute(
            select(SysUser).where(SysUser.id == swap.claimer_id)
        )).scalars().first()
        claimer_staff_id = claimer_user.staff_id if claimer_user else None

        for d in req_details:
            if d.staff_id and (await _is_user_staff(db, swap.requester_id, d.staff_id)):
                if claimer_staff_id:
                    d.staff_id = claimer_staff_id
                    d.is_substitute = True
                    d.note = f"替班（调班申请 {swap.request_no}）"
                break

    await db.flush()


async def _is_user_staff(db: AsyncSession, user_id: int, staff_id: int) -> bool:
    """判断 staff_id 是否属于该 user"""
    user = (await db.execute(
        select(SysUser).where(SysUser.id == user_id)
    )).scalars().first()
    return user and user.staff_id == staff_id


async def _log_action(db: AsyncSession, user_id: int, action: str, target_type: str, target_id: int, detail: dict):
    """记录操作日志"""
    log = SysAuditLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail,
    )
    db.add(log)


# ==================== 通知函数 ====================

async def _notify_swap_created(db: AsyncSession, swap: SchSwapRequest, target_user_id: int):
    """通知被换人"""
    req_user = (await db.execute(
        select(SysUser).where(SysUser.id == swap.requester_id)
    )).scalars().first()
    req_name = "未知用户"
    if req_user and req_user.staff_id:
        req_staff = (await db.execute(
            select(OrgStaff).where(OrgStaff.id == req_user.staff_id)
        )).scalars().first()
        if req_staff:
            req_name = req_staff.name

    schedule = (await db.execute(
        select(SchSchedule).where(SchSchedule.id == swap.requester_schedule_id)
    )).scalars().first()

    shift = None
    if schedule:
        shift = (await db.execute(
            select(SchShiftTemplate).where(SchShiftTemplate.id == schedule.shift_id)
        )).scalars().first()

    shift_name = shift.name if shift else "未知班次"
    date_str = str(schedule.date) if schedule else "未知日期"

    await MessageService.create_message(
        db, receiver_id=target_user_id,
        title=f"{req_name} 申请与您换班",
        content=f"申请编号：{swap.request_no}\n日期：{date_str}\n班次：{shift_name}\n原因：{swap.reason or '无'}",
        msg_type="swap", sender_id=swap.requester_id,
        relation_type="swap_request", relation_id=swap.id,
    )

    # 管理员补发
    await notify_admins_extra(
        db,
        title=f"新调班申请：{swap.request_no}",
        content=f"{req_name} 发起了换班申请。",
        msg_type="swap", sender_id=swap.requester_id,
        relation_type="swap_request", relation_id=swap.id,
        exclude_user_ids={swap.requester_id, target_user_id},
    )


async def _notify_open_swap_created(db: AsyncSession, swap: SchSwapRequest):
    """通知同组织人员有新的开放换班申请"""
    req_schedule = (await db.execute(
        select(SchSchedule).where(SchSchedule.id == swap.requester_schedule_id)
    )).scalars().first()

    if not req_schedule:
        return

    # 查找同组织的活跃人员（排除发起人自己）
    staff_list = (await db.execute(
        select(OrgStaff).where(
            OrgStaff.org_id == req_schedule.org_id,
            OrgStaff.status == 1,
        )
    )).scalars().all()

    # 获取发起人姓名
    req_user = (await db.execute(
        select(SysUser).where(SysUser.id == swap.requester_id)
    )).scalars().first()
    req_name = "未知用户"
    if req_user and req_user.staff_id:
        req_staff = (await db.execute(
            select(OrgStaff).where(OrgStaff.id == req_user.staff_id)
        )).scalars().first()
        if req_staff:
            req_name = req_staff.name

    # 获取班次信息
    shift = (await db.execute(
        select(SchShiftTemplate).where(SchShiftTemplate.id == req_schedule.shift_id)
    )).scalars().first()
    shift_name = getattr(shift, "name", "未知班次") if shift else "未知班次"
    date_str = str(req_schedule.date)

    # 查找人员对应的用户ID
    staff_ids = [s.id for s in staff_list if s.id]
    user_rows = (await db.execute(
        select(SysUser.staff_id, SysUser.id)
        .where(SysUser.staff_id.in_(staff_ids), SysUser.status == 1)
    )).all()
    staff_to_user: dict[int, int] = {row[0]: row[1] for row in user_rows if row[0]}

    # 向同组织所有人发送通知（排除发起人）
    for staff in staff_list:
        uid = staff_to_user.get(staff.id)
        if not uid or uid == swap.requester_id:
            continue
        await MessageService.create_message(
            db, receiver_id=uid,
            title=f"{req_name}发布了一个替班申请",
            content=f"申请编号：{swap.request_no}\n日期：{date_str}\n班次：{shift_name}\n快来认领！",
            msg_type="swap", sender_id=swap.requester_id,
            relation_type="swap_request", relation_id=swap.id,
        )

    # 管理员补发
    await notify_admins_extra(
        db,
        title=f"新开放换班申请：{swap.request_no}",
        content=f"{req_name} 发布了 {date_str} {shift_name} 的替班申请。",
        msg_type="swap", sender_id=swap.requester_id,
        relation_type="swap_request", relation_id=swap.id,
        exclude_user_ids={swap.requester_id},
    )


async def _notify_pending_approval(db: AsyncSession, swap: SchSwapRequest):
    """通知审批人"""
    from app.models import SysRole, SysUserRole

    roles = (await db.execute(
        select(SysRole).where(SysRole.code.in_(["admin", "scheduler"]))
    )).scalars().all()
    if not roles:
        return

    role_ids = [r.id for r in roles]
    user_roles = (await db.execute(
        select(SysUserRole.user_id).where(SysUserRole.role_id.in_(role_ids)).distinct()
    )).all()

    approver_ids = list({row[0] for row in user_roles if row[0]})

    for uid in approver_ids:
        await MessageService.create_message(
            db, receiver_id=uid,
            title="新的调班申请待审批",
            content=f"申请编号 {swap.request_no} 等待审批。",
            msg_type="approve", relation_type="swap_request", relation_id=swap.id,
        )


# ==================== 序列化 ====================

async def _serialize_swap_list(db: AsyncSession, swaps: list[SchSwapRequest]) -> list[dict]:
    """将调班申请列表序列化为字典"""
    if not swaps:
        return []

    # 收集关联数据
    all_user_ids: set[int] = set()
    all_schedule_ids: set[int] = set()

    for s in swaps:
        all_user_ids.add(s.requester_id)
        if s.target_id:
            all_user_ids.add(s.target_id)
        if s.claimer_id:
            all_user_ids.add(s.claimer_id)
        if s.approved_by:
            all_user_ids.add(s.approved_by)
        all_schedule_ids.add(s.requester_schedule_id)
        if s.target_schedule_id:
            all_schedule_ids.add(s.target_schedule_id)

    # 用户名映射
    users = (await db.execute(
        select(SysUser).where(SysUser.id.in_(list(all_user_ids)))
    )).scalars().all()
    staff_ids = [u.staff_id for u in users if u.staff_id]
    staff_map: dict[int, str] = {}
    if staff_ids:
        rows = (await db.execute(
            select(OrgStaff.id, OrgStaff.name).where(OrgStaff.id.in_(staff_ids))
        )).all()
        staff_map = {row[0]: row[1] for row in rows}

    user_map: dict[int, str] = {}
    for u in users:
        if u.staff_id and u.staff_id in staff_map:
            user_map[u.id] = staff_map[u.staff_id]
        else:
            user_map[u.id] = u.username

    # 排班信息映射
    schedules = (await db.execute(
        select(SchSchedule).where(SchSchedule.id.in_(list(all_schedule_ids)))
    )).scalars().all()
    schedule_map = {s.id: s for s in schedules}

    shift_ids = list({s.shift_id for s in schedules})
    shifts: dict = {}
    if shift_ids:
        shift_rows = (await db.execute(
            select(SchShiftTemplate).where(SchShiftTemplate.id.in_(shift_ids))
        )).scalars().all()
        shifts = {s.id: s for s in shift_rows}

    items = []
    for s in swaps:
        req_schedule = schedule_map.get(s.requester_schedule_id)
        req_shift = shifts.get(req_schedule.shift_id) if req_schedule else None

        tgt_schedule = schedule_map.get(s.target_schedule_id) if s.target_schedule_id else None
        tgt_shift = shifts.get(tgt_schedule.shift_id) if tgt_schedule else None

        items.append({
            "id": s.id,
            "request_no": s.request_no,
            "swap_type": s.swap_type,
            "requester_id": s.requester_id,
            "requester_name": user_map.get(s.requester_id),
            "requester_schedule_id": s.requester_schedule_id,
            "requester_schedule_date": req_schedule.date if req_schedule else None,
            "requester_shift_name": req_shift.name if req_shift else None,
            "target_id": s.target_id,
            "target_name": user_map.get(s.target_id) if s.target_id else None,
            "target_schedule_id": s.target_schedule_id,
            "target_schedule_date": tgt_schedule.date if tgt_schedule else None,
            "target_shift_name": tgt_shift.name if tgt_shift else None,
            "claimer_id": s.claimer_id,
            "claimer_name": user_map.get(s.claimer_id) if s.claimer_id else None,
            "reason": s.reason,
            "status": s.status,
            "confirmed_at": _to_local_str(s.confirmed_at),
            "refused_at": _to_local_str(s.refused_at),
            "refuse_comment": s.refuse_comment,
            "approved_by": s.approved_by,
            "approver_name": user_map.get(s.approved_by) if s.approved_by else None,
            "approved_at": _to_local_str(s.approved_at),
            "approve_comment": s.approve_comment,
            "created_at": _to_local_str(s.created_at),
            "updated_at": _to_local_str(s.updated_at),
        })

    return items
