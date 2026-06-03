from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings
from typing import AsyncGenerator

# 创建异步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)

# 创建异步Session工厂
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# 基础模型类
class Base(DeclarativeBase):
    pass


# 获取数据库Session的依赖
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# 初始化数据库（创建表）
async def init_db():
    from sqlalchemy import inspect as sa_inspect, text as sa_text

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 自动检测并补充缺失字段
    await _auto_migrate_columns()

    # 为历史人员自动创建用户账号
    await _auto_create_accounts_for_existing_staff()


# ========== 动态列迁移 ==========

# 声明式定义：需要确保存在的字段（表名, 列名, DDL 类型, 默认值）
_COLUMN_MIGRATIONS: list[tuple[str, str, str, str | None]] = [
    ("sys_user", "must_change_password", "BOOLEAN NOT NULL DEFAULT FALSE", "false"),
]


async def _auto_migrate_columns():
    """动态检查并补充缺失字段（基于模型定义自动对比）"""
    from sqlalchemy import inspect as sa_inspect

    async with engine.begin() as conn:
        def _check_and_add(sync_conn):
            inspector = sa_inspect(sync_conn)
            existing_tables = set(inspector.get_table_names())
            for table_name, table in Base.metadata.tables.items():
                if table_name not in existing_tables:
                    continue
                existing_cols = {col['name'] for col in inspector.get_columns(table_name)}
                for column in table.columns:
                    if column.name not in existing_cols:
                        col_type = column.type.compile(dialect=sync_conn.dialect)
                        nullable = "" if column.nullable else " NOT NULL"
                        default = ""
                        if column.default is not None:
                            default_val = column.default.arg if hasattr(column.default, 'arg') else None
                            if default_val is not None:
                                if isinstance(default_val, bool):
                                    default = f" DEFAULT {'TRUE' if default_val else 'FALSE'}"
                                elif isinstance(default_val, str):
                                    default = f" DEFAULT '{default_val}'"
                                else:
                                    default = f" DEFAULT {default_val}"
                        sql = f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column.name} {col_type}{nullable}{default}"
                        try:
                            sync_conn.execute(text(sql))
                        except Exception:
                            pass

        await conn.run_sync(_check_and_add)

# ========== 自动创建账号 ==========


async def _auto_create_accounts_for_existing_staff():
    """为没有账号的历史人员自动创建用户账号（ORM 方式，幂等执行）"""
    from sqlalchemy import select
    from app.models import SysUser, OrgStaff, SysRole, SysUserRole
    from app.utils.security import hash_password

    default_password = hash_password("123456")

    async with async_session_factory() as session:
        # 查找所有没有关联用户的在职人员
        all_staff = (await session.execute(
            select(OrgStaff).where(OrgStaff.status == 1)
        )).scalars().all()

        existing_staff_ids = set()
        if all_staff:
            all_staff_ids = [s.id for s in all_staff]
            bound_users = (await session.execute(
                select(SysUser.staff_id).where(SysUser.staff_id.in_(all_staff_ids))
            )).scalars().all()
            existing_staff_ids = {sid for sid in bound_users if sid is not None}

        # 查找默认角色
        default_role = (await session.execute(
            select(SysRole).where(SysRole.code == "member")
        )).scalars().first()

        created_count = 0
        for staff in all_staff:
            if staff.id in existing_staff_ids:
                continue

            username = staff.employee_no
            # 检查用户名是否已存在
            exists = (await session.execute(
                select(SysUser).where(SysUser.username == username)
            )).scalars().first()
            if exists:
                continue

            user = SysUser(
                username=username,
                password_hash=default_password,
                staff_id=staff.id,
                status=1,
                must_change_password=True,
            )
            session.add(user)
            await session.flush()

            if default_role:
                session.add(SysUserRole(user_id=user.id, role_id=default_role.id))

            created_count += 1

        if created_count > 0:
            await session.commit()
            print(f"[init_db] 已为 {created_count} 位历史人员自动创建用户账号（密码: 123456）")
