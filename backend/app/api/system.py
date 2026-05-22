from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, require_roles
from app.models import SysUser, SysConfig
from app.schemas.system import SystemConfigResponse, SystemConfigUpdate

router = APIRouter(prefix="/system", tags=["系统配置"])


async def get_config_value(db: AsyncSession, key: str, default: str = "") -> str:
    """获取单个配置值"""
    stmt = select(SysConfig.config_value).where(SysConfig.config_key == key)
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    return row if row is not None else default

@router.get("/config/public")
async def get_public_config(
    db: AsyncSession = Depends(get_db),
):
    """获取公开系统配置（无需登录）"""
    system_name = await get_config_value(db, "system_name", "排班管理系统")
    org_name = await get_config_value(db, "org_name", "")

    return {
        "system_name": system_name,
        "org_name": org_name,
    }

@router.get("/config/overview")
async def get_config_overview(
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """获取系统概要配置（登录即可，用于页面标题/侧边栏等场景）"""
    system_name = await get_config_value(db, "system_name", "排班管理系统")
    org_name = await get_config_value(db, "org_name", "")
    swap_approval = await get_config_value(db, "swap_approval_enabled", "true")

    return {
        "system_name": system_name,
        "org_name": org_name,
        "swap_approval_enabled": swap_approval.lower() == "true",
    }


@router.get("/config", response_model=SystemConfigResponse)
async def get_system_config(
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_roles("admin")),
):
    """获取所有系统配置"""
    system_name = await get_config_value(db, "system_name", "排班管理系统")
    org_name = await get_config_value(db, "org_name", "")
    swap_approval = await get_config_value(db, "swap_approval_enabled", "true")
    schedule_approval = await get_config_value(db, "schedule_approval_enabled", "false")
    admin_receive_all = await get_config_value(db, "admin_receive_all_notifications", "true")

    return SystemConfigResponse(
        system_name=system_name,
        org_name=org_name,
        swap_approval_enabled=swap_approval.lower() == "true",
        schedule_approval_enabled=schedule_approval.lower() == "true",
        admin_receive_all_notifications=admin_receive_all,
    )


@router.put("/config", response_model=SystemConfigResponse)
async def update_system_config(
    data: SystemConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(require_roles("admin")),
):
    """更新系统配置"""
    try:
        # 先查询所有相关配置
        config_keys = [
            "system_name", "org_name", "swap_approval_enabled",
            "schedule_approval_enabled", "admin_receive_all_notifications",
        ]
        stmt = select(SysConfig).where(SysConfig.config_key.in_(config_keys))
        result = await db.execute(stmt)
        config_map = {c.config_key: c for c in result.scalars().all()}

        # 更新
        update_map = {
            "system_name": data.system_name,
            "org_name": data.org_name,
            "swap_approval_enabled": str(data.swap_approval_enabled).lower() if data.swap_approval_enabled is not None else None,
            "schedule_approval_enabled": str(data.schedule_approval_enabled).lower() if data.schedule_approval_enabled is not None else None,
            "admin_receive_all_notifications": data.admin_receive_all_notifications if getattr(data, "admin_receive_all_notifications", None) is not None else None,
        }

        for key, value in update_map.items():
            if value is not None:
                if key in config_map:
                    config_map[key].config_value = value
                else:
                    db.add(SysConfig(config_key=key, config_value=value))

        await db.commit()

        # 从已修改的对象构建返回值
        system_name = config_map.get("system_name")
        org_name = config_map.get("org_name")
        swap_approval = config_map.get("swap_approval_enabled")
        schedule_approval = config_map.get("schedule_approval_enabled")
        admin_receive_all = config_map.get("admin_receive_all_notifications")

        return SystemConfigResponse(
            system_name=system_name.config_value if system_name else "排班管理系统",
            org_name=org_name.config_value if org_name else "",
            swap_approval_enabled=(swap_approval.config_value.lower() == "true") if swap_approval else True,
            schedule_approval_enabled=(schedule_approval.config_value.lower() == "true") if schedule_approval else False,
            admin_receive_all_notifications=admin_receive_all.config_value if admin_receive_all else "true",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")
