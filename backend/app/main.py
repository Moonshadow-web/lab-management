from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .core.config import FRONTEND_ORIGIN, UPLOAD_ROOT
from .core.database import Base, SessionLocal, engine
from .models import *  # noqa: F401,F403 注册全部表
from .api.v1.router import api_router
from .seed.seed import run_seed
from .services.notification_service import refresh_calibration_notifications


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        run_seed(db)
        refresh_calibration_notifications(db)
    yield


app = FastAPI(title="检验科生免组实验室管理系统", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# 本地磁盘文件预览（上云由云存储 SDK 的临时 URL 替代）
if UPLOAD_ROOT.exists():
    app.mount("/uploads", StaticFiles(directory=str(UPLOAD_ROOT)), name="uploads")


@app.get("/health")
def health():
    return {"status": "ok"}
