"""SQLite → MySQL 迁移脚本。

用法（在 backend/ 目录下运行）：
  python -m app.scripts.migrate --mysql-url mysql+pymysql://user:pass@10.0.1.18:3306/cloud1-0gjhamv53ff2298d

也可以直接指定 SQLite 路径：
  python scripts/migrate_to_mysql.py --sqlite /tmp/online.db --mysql mysql+pymysql://...
"""

import os
import sys
import argparse
import urllib.request
from pathlib import Path

# 添加 backend 到路径
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from app.core.database import Base


def transfer_tables(src_session: Session, dst_session: Session, exclude: list[str] | None = None):
    """将 src_session 中所有表的数据拷贝到 dst_session。"""
    exclude = exclude or []
    inspector = inspect(src_session.bind)
    tables = [t for t in inspector.get_table_names() if t not in exclude]

    for table_name in tables:
        # 读所有行
        rows = src_session.execute(text(f"SELECT * FROM `{table_name}`")).fetchall()
        if not rows:
            print(f"  {table_name}: 0 rows (skip)")
            continue

        columns = [col["name"] for col in inspector.get_columns(table_name)]
        col_quoted = ", ".join(f"`{c}`" for c in columns)
        placeholders = ", ".join(":" + c for c in columns)

        inserted = 0
        for row in rows:
            values = {c: getattr(row, c) for c in columns}
            try:
                dst_session.execute(
                    text(f"INSERT INTO `{table_name}` ({col_quoted}) VALUES ({placeholders})"),
                    values,
                )
                inserted += 1
            except Exception as e:
                # 跳过重复键等约束错误
                print(f"    skip row in {table_name}: {e}")
        dst_session.commit()
        print(f"  {table_name}: {inserted}/{len(rows)} rows")


def main():
    parser = argparse.ArgumentParser(description="SQLite → MySQL migration")
    parser.add_argument("--mysql-url", required=True, help="MySQL connection string, e.g. mysql+pymysql://user:pass@host:3306/db")
    parser.add_argument("--sqlite", default="", help="Path to SQLite DB file. If empty, download from online /_diag/db")
    parser.add_argument("--api-base", default="https://lab-management-282724-9-1408547492.sh.run.tcloudbase.com", help="API base URL for downloading DB")
    args = parser.parse_args()

    # Download online SQLite DB if no local path given
    sqlite_path = args.sqlite
    if not sqlite_path:
        print(f"Downloading DB from {args.api_base}/api/v1/_diag/db ...")
        tmp = Path("/tmp/online_sqlite.db")
        urllib.request.urlretrieve(f"{args.api_base}/api/v1/_diag/db", tmp)
        sqlite_path = str(tmp)

    # 引擎
    src_engine = create_engine(f"sqlite:///{sqlite_path}", future=True)
    dst_engine = create_engine(args.mysql_url, future=True)

    # 在 MySQL 建表（这里把创建表放在独立的连接中，如果表已经存在就跳过）
    Base.metadata.create_all(dst_engine)

    # 传输数据
    with Session(src_engine) as src_s, Session(dst_engine) as dst_s:
        transfer_tables(src_s, dst_s)

    print("\n✓ Migration complete!")
    print(f"  Source: {sqlite_path}")
    print(f"  Target: {args.mysql_url}")


if __name__ == "__main__":
    main()
