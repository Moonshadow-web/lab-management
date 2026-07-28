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
    if IS_SQLITE:
        # 注册自定义排序函数
        dbapi_conn.create_function("doc_number_sort", 1, _doc_number_sort)
        # 以下 PRAGMA 优化 SQLite 在 CFS（网络文件系统）上的并发与稳定性：
        try:
            dbapi_conn.execute("PRAGMA journal_mode=WAL")
            dbapi_conn.execute("PRAGMA busy_timeout=5000")
            dbapi_conn.execute("PRAGMA synchronous=NORMAL")
        except Exception:
            pass
    else:
        # MySQL/CloudBase：放宽单语句网络写超时（默认 net_write_timeout=60s，
        # 大 BLOB 写入易 2013 Lost connection）。对所有连接生效，覆盖上传与回填。
        try:
            cur = dbapi_conn.cursor()
            cur.execute("SET SESSION net_write_timeout=28800")
            cur.execute("SET SESSION net_read_timeout=28800")
            cur.close()
        except Exception:
            pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
