"""首页看板 API（异步）"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.auth import get_current_user
from app.models import SysUser
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["首页看板"])


@router.get("/overview", summary="获取首页看板数据")
async def get_dashboard_overview(
    db: AsyncSession = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    org_id = None
    if current_user.staff:
        org_id = getattr(current_user.staff, "org_id", None)

    data = await DashboardService.get_overview(db, user_id=current_user.id, org_id=org_id)
    return {"code": 200, "data": data, "message": "success"}
