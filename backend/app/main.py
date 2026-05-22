from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db, async_session_factory
from app.utils.init_data import init_default_data

# 导入路由
from app.api.auth import router as auth_router
from app.api.organization import router as org_router
from app.api.staff import router as staff_router
from app.api.shift_template import router as shift_template_router
from app.api.constraint import router as constraint_router
from app.api.special_rule import router as special_rule_router
from app.api.role import router as role_router
from app.api.system import router as system_router
from app.api.schedule import router as schedule_router
from app.api.swap import router as swap_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print(f"启动 {settings.APP_NAME} v{settings.APP_VERSION}")

    # 初始化数据库表
    await init_db()

    # 初始化默认数据
    async with async_session_factory() as db:
        await init_default_data(db)

    print("系统初始化完成")

    yield

    # 关闭时执行
    print("系统关闭")


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="排班管理系统API",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# 跨域中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth_router, prefix="/api")
app.include_router(org_router, prefix="/api")
app.include_router(staff_router, prefix="/api")
app.include_router(shift_template_router, prefix="/api")
app.include_router(special_rule_router, prefix="/api")
app.include_router(constraint_router, prefix="/api")
app.include_router(role_router, prefix="/api")
app.include_router(system_router, prefix="/api")
app.include_router(schedule_router, prefix="/api")
app.include_router(swap_router, prefix="/api")
# 新增：消息系统路由
from app.api.message import router as message_router
app.include_router(message_router, prefix="/api")

# 新增：首页看板路由
from app.api.dashboard import router as dashboard_router
app.include_router(dashboard_router, prefix="/api")

# 新增：导出路由
from app.api.export import router as export_router
app.include_router(export_router, prefix="/api")

@app.get("/", tags=["健康检查"])
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }


@app.get("/health", tags=["健康检查"])
async def health_check():
    return {"status": "healthy"}
