from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.database import get_db
from app.models import SysUser, SysUserRole, SysRole
from app.schemas.auth import LoginRequest, TokenResponse, UserInfo, ChangePasswordRequest, ForceChangePasswordRequest
from app.utils.security import verify_password, hash_password, create_access_token
from app.api.deps import get_current_user
from app.utils.time_helper import to_local_str as _to_local_str

router = APIRouter(prefix="/auth", tags=["认证管理"])


@router.post("/login", response_model=TokenResponse, summary="用户登录")
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录，返回JWT Token"""
    # 查询用户
    result = await db.execute(select(SysUser).where(SysUser.username == request.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    if user.status != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )

    # 更新最后登录时间
    await db.execute(
        update(SysUser).where(SysUser.id == user.id).values(last_login_at=datetime.utcnow())
    )

    # 获取用户角色
    role_codes = [role.code for role in user.roles]

    # 创建Token
    access_token = create_access_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=480 * 60,  # 秒
        user_id=user.id,
        username=user.username,
        roles=role_codes,
        must_change_password=user.must_change_password,
    )


@router.get("/me", response_model=UserInfo, summary="获取当前用户信息")
async def get_me(current_user: SysUser = Depends(get_current_user)):
    """获取当前登录用户的详细信息"""
    role_codes = [role.code for role in current_user.roles]

    # 合并权限
    permissions = {}
    for role in current_user.roles:
        if role.permissions:
            if role.permissions.get("all"):
                permissions = {"all": True}
                break
            for resource, actions in role.permissions.items():
                if resource not in permissions:
                    permissions[resource] = []
                if isinstance(actions, list):
                    permissions[resource].extend(actions)
                    permissions[resource] = list(set(permissions[resource]))

    return UserInfo(
        id=current_user.id,
        username=current_user.username,
        staff_id=current_user.staff_id,
        staff_name=current_user.staff.name if current_user.staff else None,
        status=current_user.status,
        roles=role_codes,
        permissions=permissions,
        last_login_at=_to_local_str(current_user.last_login_at),
        must_change_password=current_user.must_change_password,
    )


@router.post("/change-password", summary="修改密码")
async def change_password(
    request: ChangePasswordRequest,
    current_user: SysUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改当前用户密码"""
    if not verify_password(request.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="原密码错误",
        )

    new_password_hash = hash_password(request.new_password)
    await db.execute(
        update(SysUser).where(SysUser.id == current_user.id).values(
            password_hash=new_password_hash,
            must_change_password=False,
        )
    )

    return {"message": "密码修改成功"}


@router.post("/force-change-password", summary="首次登录强制修改密码")
async def force_change_password(
    request: ForceChangePasswordRequest,
    current_user: SysUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """首次登录强制修改密码（不需要旧密码）"""
    if not current_user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前无需强制修改密码",
        )

    new_password_hash = hash_password(request.new_password)
    await db.execute(
        update(SysUser).where(SysUser.id == current_user.id).values(
            password_hash=new_password_hash,
            must_change_password=False,
        )
    )

    return {"message": "密码修改成功，请重新登录"}
