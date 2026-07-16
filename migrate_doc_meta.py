"""为 documents / document_versions 表新增文件头元数据列。

create_all 只创建缺失的表、不会给已有表加列，故单独迁移。
已存在则跳过；执行前自动备份 data/app.db。
"""
import os
import shutil
import datetime
import sqlite3

from backend.app.core.database import engine, Base
from backend.app.models.document import Document, DocumentVersion

# 列定义：(表名, 列名, SQL 类型, 默认值)
NEW_COLUMNS = {
    "documents": [
        ("doc_number", "VARCHAR(100)", ""),
        ("doc_version", "VARCHAR(50)", ""),
        ("revision", "VARCHAR(20)", ""),
        ("author", "VARCHAR(100)", ""),
        ("reviewer", "VARCHAR(100)", ""),
        ("approver", "VARCHAR(100)", ""),
        ("issued_date", "VARCHAR(50)", ""),
        ("audit_date", "VARCHAR(50)", ""),
        ("approve_date", "VARCHAR(50)", ""),
        ("effective_date", "VARCHAR(50)", ""),
        ("meta_raw", "TEXT", ""),
    ],
    "document_versions": [
        ("doc_number", "VARCHAR(100)", ""),
        ("doc_version", "VARCHAR(50)", ""),
        ("revision", "VARCHAR(20)", ""),
        ("author", "VARCHAR(100)", ""),
        ("reviewer", "VARCHAR(100)", ""),
        ("approver", "VARCHAR(100)", ""),
        ("meta_raw", "TEXT", ""),
    ],
}


def main():
    db_path = "data/app.db"
    # 备份
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = f"data/app.db.bak_{ts}"
    shutil.copy2(db_path, bak)
    print(f"[备份] {bak}")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    for table, cols in NEW_COLUMNS.items():
        cur.execute(f"PRAGMA table_info({table})")
        existing = {r[1] for r in cur.fetchall()}
        for col, ctype, default in cols:
            if col in existing:
                print(f"  [跳过] {table}.{col} 已存在")
                continue
            ddl = f"ALTER TABLE {table} ADD COLUMN {col} {ctype} DEFAULT ''"
            cur.execute(ddl)
            print(f"  [新增] {table}.{col} ({ctype})")
    conn.commit()
    conn.close()
    print("[完成] 列迁移结束")


if __name__ == "__main__":
    # 确保 backend 包可被导入（脚本以项目根目录运行）
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    # 触发模型导入，确保表名解析一致
    _ = (Document, DocumentVersion)
    main()
