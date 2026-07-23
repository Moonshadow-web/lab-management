import os
from pathlib import Path

# 路径解析：backend/app/core/config.py
#   parents[0]=core, [1]=app, [2]=backend, [3]=项目根
BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent

# 数据目录与上传目录：支持环境变量覆盖（容器/云环境）
# 本地默认在项目根 data/；Docker 中通过 ENV DATA_DIR=/app/data 覆盖
_data_dir_env = os.getenv("DATA_DIR")
DATA_DIR = Path(_data_dir_env) if _data_dir_env else PROJECT_ROOT / "data"
_upload_env = os.getenv("UPLOAD_ROOT")
UPLOAD_ROOT = Path(_upload_env) if _upload_env else DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "app.db"

# 确保数据目录存在（本地运行用；上云时由云存储替代）
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

# 数据库：本地 SQLite；上云切 CloudBase MySQL 仅改此环境变量，业务代码不变
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

# 安全
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-prod-9f2a7b3c")
ALGORITHM = "HS256"
# access token 短效，过期由 refresh token 静默续期，避免频繁登录
ACCESS_TOKEN_EXPIRE_MINUTES = 30
# refresh token 长效 = 「保持登录」时长；可经环境变量覆盖
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# 前端源（CORS）
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

# 存储后端：local（本地磁盘）/ cloud（云存储，阶段5实现 CloudStorageBackend）
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local")

# 邮件发送（SMTP）：配置后真正发信；未配置时降级为本地日志（便于开发/上云前验证流程）。
# 例如 QQ 邮箱：SMTP_HOST=smtp.qq.com SMTP_PORT=465 SMTP_USER=你的邮箱 SMTP_PASS=授权码（非登录密码）
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_TLS = os.getenv("SMTP_TLS", "true").lower() in ("1", "true", "yes", "y")
MAIL_FROM = os.getenv("MAIL_FROM", SMTP_USER or "noreply@localhost")
SYSTEM_NAME = os.getenv("SYSTEM_NAME", "检验科生免组实验室管理系统")

# 微信推送（WxPusher）：配置 appToken 后按人向用户微信发提醒；未配置时降级为本地日志。
# 注册/登录：wxpusher.zjiecode.com/admin 用微信扫码，无账号自动注册；创建应用拿 appToken。
# 官方文档：https://wxpusher.zjiecode.com/docs/
WXPUSHER_ENABLED = os.getenv("WXPUSHER_ENABLED", "false").lower() in ("1", "true", "yes", "y")
WXPUSHER_APP_TOKEN = os.getenv("WXPUSHER_APP_TOKEN", "")
