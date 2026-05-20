"""调班管理 API 路由（异步）"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models import SysUser
from app.schemas.swap import SwapRequestCreate, SwapApproveRequest, SwapRequestResponse, SwapListResponse
from app.services.swap_service import SwapService

router = APIRouter(prefix="/swaps", tags=["调班管理"])


@router.get("", response_model=SwapListResponse, summary="获取调班申请列表")
async def list_swaps(
    role: str = Query("requester", description="视角：requester/target/approver"),
    status: str | None = Query(None, description="状态筛选"),
    swap_type: str | None = Query(None, description="类型筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    role_codes = [r.code for r in current_user.roles]
    result = await SwapService.get_list(
        db, user_id=current_user.id, role=role,
        status=status, swap_type=swap_type, page=page, page_size=page_size,
        user_roles=role_codes,
    )
    return SwapListResponse(items=result["items"], total=result["total"])


@router.get("/all", response_model=SwapListResponse, summary="获取全部调班记录（管理员）")
async def list_all_swaps(
    status: str | None = Query(None),
    swap_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    role_codes = [r.code for r in current_user.roles]
    if "admin" not in role_codes and "scheduler" not in role_codes and "leader" not in role_codes:
        raise HTTPException(status_code=403, detail="无权查看全部记录")

    result = await SwapService.get_list(
        db, user_id=None, role="all",
        status=status, swap_type=swap_type, page=page, page_size=page_size,
    )
    return SwapListResponse(items=result["items"], total=result["total"])


@router.get("/{request_id}", response_model=SwapRequestResponse, summary="获取调班申请详情")
async def get_swap(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    try:
        return await SwapService.get_by_id(db, request_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("", response_model=SwapRequestResponse, status_code=201, summary="发起调班申请")
async def create_swap(
    data: SwapRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    try:
        return await SwapService.create(db, current_user.id, data.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{request_id}/confirm", summary="对方确认换班")
async def confirm_swap(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    try:
        result = await SwapService.confirm(db, request_id, current_user.id)
        return {"code": 200, "data": result, "message": "确认成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{request_id}/claim", summary="认领开放换班")
async def claim_swap(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    try:
        result = await SwapService.claim(db, request_id, current_user.id)
        return {"code": 200, "data": result, "message": "认领成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{request_id}/approve", summary="审批通过")
async def approve_swap(
    request_id: int,
    data: SwapApproveRequest = SwapApproveRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    role_codes = [r.code for r in current_user.roles]
    if "admin" not in role_codes and "scheduler" not in role_codes:
        raise HTTPException(status_code=403, detail="仅管理员或排班管理员可审批")
    try:
        result = await SwapService.approve(db, request_id, current_user.id, data.approve_comment)
        return {"code": 200, "data": result, "message": "审批通过"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{request_id}/reject", summary="审批拒绝")
async def reject_swap(
    request_id: int,
    data: SwapApproveRequest = SwapApproveRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    role_codes = [r.code for r in current_user.roles]
    if "admin" not in role_codes and "scheduler" not in role_codes:
        raise HTTPException(status_code=403, detail="仅管理员或排班管理员可审批")
    try:
        result = await SwapService.reject(db, request_id, current_user.id, data.approve_comment)
        return {"code": 200, "data": result, "message": "已拒绝"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{request_id}/refuse", summary="对方拒绝换班")
async def refuse_swap(
    request_id: int,
    data: SwapApproveRequest = SwapApproveRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    try:
        result = await SwapService.refuse(db, request_id, current_user.id, data.approve_comment)
        return {"code": 200, "data": result, "message": "已拒绝"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{request_id}/cancel", summary="撤回申请")
async def cancel_swap(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    try:
        result = await SwapService.cancel(db, request_id, current_user.id)
        return {"code": 200, "data": result, "message": "已撤回"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
