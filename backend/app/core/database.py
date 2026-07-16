from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
import re

from .config import DATABASE_URL

# SQLite 需要关闭同线程检查以在 FastAPI 异步事件循环中使用
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

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
    dbapi_conn.create_function("doc_number_sort", 1, _doc_number_sort)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
