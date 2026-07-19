from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
import re

from .config import DATABASE_URL

# SQLite 需要关闭同线程检查以在 FastAPI 异步事件循环中使用；
# MySQL 不需要这个参数（会报错）
IS_SQLITE = DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if IS_SQLITE else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def _doc_number_sort(s):
    """用于按编号自然排序：把编号中的数字段零填充到 6 位，使 076<901；
    空值返回大字符串，排在末尾。"""
    if not s:
        return "zzzzzz"
    return re.sub(r"(\d+)", lambda m: m.group(1).zfill(6), s)


@event.listens_for(engine, "connect")
def _register_sqlite_functions(dbapi_conn, conn_record):
    if not IS_SQLITE:
        return
    # 注册自定义排序函数
    dbapi_conn.create_function("doc_number_sort", 1, _doc_number_sort)
    # 以下 PRAGMA 优化 SQLite 在 CFS（网络文件系统）上的并发与稳定性：
    #
    # 1. WAL（Write-Ahead Logging）：读不阻塞写、写不阻塞读，大幅减少锁冲突。
    #    在 CFS 上 rollback journal 的锁经常超时卡死，WAL 模式显著改善。
    # 2. busy_timeout=5000：数据库被锁时最多等 5 秒再报错，避免瞬间 500。
    # 3. synchronous=NORMAL：WAL 模式下 crash-safe，比 FULL 少一次 fsync，
    #    对 CFS 网络盘性能有明显改善（且安全性足够）。
    try:
        dbapi_conn.execute("PRAGMA journal_mode=WAL")
        dbapi_conn.execute("PRAGMA busy_timeout=5000")
        dbapi_conn.execute("PRAGMA synchronous=NORMAL")
    except Exception:
        pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
