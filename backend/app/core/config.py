import os
from pathlib import Path

# 路径解析：backend/app/core/config.py
#   parents[0]=core, [1]=app, [2]=backend, [3]=项目根
BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
UPLOAD_ROOT = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "app.db"

# 确保数据目录存在（本地运行用；上云时由云存储替代）
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

# 数据库：本地 SQLite；上云切 CloudBase MySQL 仅改此环境变量，业务代码不变
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

# 安全
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-prod-9f2a7b3c")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 12 * 60

# 前端源（CORS）
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

# 存储后端：local（本地磁盘）/ cloud（云存储，阶段5实现 CloudStorageBackend）
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local")
