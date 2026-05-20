from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import SysUser, SysRole, SysUserRole, OrgOrganization, SysConfig
from app.utils.security import hash_password
from app.config import settings
from app.services.constraint_service import ConstraintService


async def init_default_data(db: AsyncSession):
    """初始化系统默认数据"""

    # 1. 初始化默认角色
    roles = [
        {"name": "系统管理员", "code": "admin", "is_system": True,
         "permissions": {"all": True}},
        {"name": "排班管理员", "code": "scheduler", "is_system": True,
         "permissions": {
             "schedule": ["read", "create", "update", "delete", "publish"],
             "staff": ["read", "create", "update"],
             "shift_template": ["read", "create", "update"],
             "constraint": ["read", "create", "update"],
             "swap": ["read", "approve"],
             "message": ["read", "create"],
             "export": ["read"],
         }},
        {"name": "组长", "code": "leader", "is_system": True,
         "permissions": {
             "schedule": ["read"],
             "swap": ["read", "create"],
             "message": ["read"],
             "export": ["read"],
         }},
        {"name": "普通队员", "code": "member", "is_system": True,
         "permissions": {
             "schedule": ["read"],
             "swap": ["read", "create"],
             "message": ["read"],
         }},
    ]

    for role_data in roles:
        result = await db.execute(select(SysRole).where(SysRole.code == role_data["code"]))
        if not result.scalar_one_or_none():
            db.add(SysRole(**role_data))

    await db.flush()

    # 2. 初始化默认管理员账号
    result = await db.execute(select(SysUser).where(SysUser.username == settings.DEFAULT_ADMIN_USERNAME))
    if not result.scalar_one_or_none():
        admin_user = SysUser(
            username=settings.DEFAULT_ADMIN_USERNAME,
            password_hash=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
            status=1,
        )
        db.add(admin_user)
        await db.flush()

        # 分配管理员角色
        result = await db.execute(select(SysRole).where(SysRole.code == "admin"))
        admin_role = result.scalar_one_or_none()
        if admin_role:
            db.add(SysUserRole(user_id=admin_user.id, role_id=admin_role.id))

    # 3. 初始化默认系统配置
    default_configs = [
        {"config_key": "swap_approval_enabled", "config_value": "true", "description": "调班审批开关"},
        {"config_key": "schedule_approval_enabled", "config_value": "true", "description": "排班审批开关"},
        {"config_key": "system_name", "config_value": "排班管理系统", "description": "系统名称"},
        {"config_key": "org_name", "config_value": "应急涉安部门", "description": "单位名称"},
        {"config_key": "admin_receive_all_notifications", "config_value": "true", "description": "管理员接收全部通知开关"},
    ]

    for config_data in default_configs:
        result = await db.execute(select(SysConfig).where(SysConfig.config_key == config_data["config_key"]))
        if not result.scalar_one_or_none():
            db.add(SysConfig(**config_data))

    # 4. 初始化预置约束规则
    await ConstraintService.init_preset_rules(db)

    await db.commit()
    print("默认数据初始化完成")
