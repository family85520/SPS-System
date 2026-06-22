import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db, async_session_factory
from app.utils.init_data import init_default_data

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
from app.api.message import router as message_router
from app.api.dashboard import router as dashboard_router
from app.api.export import router as export_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"启动 {settings.APP_NAME} v{settings.APP_VERSION}")

    await init_db()

    async with async_session_factory() as db:
        await init_default_data(db)

    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from app.services.auto_schedule_job import run_monthly_auto_schedule
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        lambda: asyncio.create_task(run_monthly_auto_schedule(async_session_factory)),
        'interval', minutes=30,
        id='auto_schedule_monthly',
    )
    scheduler.start()
    print("自动排班调度器已启动（每 30 分钟检查一次）")

    print("系统初始化完成")

    yield

    scheduler.shutdown(wait=False)
    print("系统关闭")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="排班管理系统API",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api"
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(org_router, prefix=API_PREFIX)
app.include_router(staff_router, prefix=API_PREFIX)
app.include_router(shift_template_router, prefix=API_PREFIX)
app.include_router(special_rule_router, prefix=API_PREFIX)
app.include_router(constraint_router, prefix=API_PREFIX)
app.include_router(role_router, prefix=API_PREFIX)
app.include_router(system_router, prefix=API_PREFIX)
app.include_router(schedule_router, prefix=API_PREFIX)
app.include_router(swap_router, prefix=API_PREFIX)
app.include_router(message_router, prefix=API_PREFIX)
app.include_router(dashboard_router, prefix=API_PREFIX)
app.include_router(export_router, prefix=API_PREFIX)


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
