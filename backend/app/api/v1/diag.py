"""启动自愈所需的 SQLite 修复工具 + 版本探针。

仅保留 main.py 启动自愈(_self_heal_db)真正依赖的辅助函数
(_integrity_ok / _generic_dump_recover / _swap_in) 与无害的 /build 版本探针。
曾用于 CFS 损坏后数据恢复的临时诊断/恢复路由(audit-missing / diff-table /
recover-table 等) 已移除，收敛攻击面。

路径前缀 /_diag，避免与 instruments 的 /{id} 抢匹配。
"""
import os
import shutil
import sqlite3

_DB_PATH = "/app/data/app.db"
# CFS 持久卷 /app/data 与本机 /tmp 是不同设备，临时文件放在同设备内，
# 且 _swap_in 用 shutil.move 兜底跨设备替换，避免 OSError(18, Invalid cross-device link)。
_TMP_DIR = "/app/data"


def _integrity_ok(path: str) -> bool:
    try:
        c = sqlite3.connect(path)
        ok = [r[0] for r in c.execute("PRAGMA integrity_check").fetchall()] == ["ok"]
        c.close()
        return ok
    except Exception:
        return False


def _swap_in(report: dict, new_path: str, label: str):
    """用新文件替换损坏库（同设备用 os.replace 原子替换；跨设备 shutil.move 兜底），
    并清理 WAL/SHM、强制连接池重连。"""
    for ext in ("-wal", "-shm"):
        p = _DB_PATH + ext
        if os.path.exists(p):
            os.remove(p)
    try:
        os.replace(new_path, _DB_PATH)
    except OSError as e:  # noqa: BLE001
        if getattr(e, "errno", None) == 18:  # Invalid cross-device link
            shutil.move(new_path, _DB_PATH)
        else:
            raise
    try:
        from ...core.database import engine

        engine.dispose()
    except Exception as e:  # noqa: BLE001
        report["engine_dispose_warn"] = repr(e)
    report["swap"] = label


def _generic_dump_recover(src_path: str, new_path: str, report: dict):
    """从损坏库逐表导出：用 sqlite_master 里存的 CREATE 语句原样重建表+索引，
    再拷行。表数据页完好即可零丢失恢复（含模型外的表）。"""
    if os.path.exists(new_path):
        os.remove(new_path)
    src = sqlite3.connect(src_path)
    src.text_factory = str
    new = sqlite3.connect(new_path)
    cur = src.cursor()
    tbls = cur.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    idxs = cur.execute(
        "SELECT sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    for name, sql in tbls:
        if sql:
            new.execute(sql)
    for (sql,) in idxs:
        if sql:
            try:
                new.execute(sql)
            except Exception as e:  # noqa: BLE001
                report.setdefault("index_create_errors", []).append(str(e))
    new.commit()
    per = {}
    for name, _ in tbls:
        cols = [r[1] for r in cur.execute(f'PRAGMA table_info("{name}")').fetchall()]
        if not cols:
            continue
        col_sql = ", ".join(f'"{c}"' for c in cols)
        qmarks = ", ".join("?" * len(cols))
        try:
            rows = cur.execute(f'SELECT {col_sql} FROM "{name}"').fetchall()
        except Exception as e:  # noqa: BLE001
            per[name] = f"read_err: {e}"
            rows = []
        n = 0
        try:
            nc = new.cursor()
            for r in rows:
                nc.execute(f'INSERT INTO "{name}" ({col_sql}) VALUES ({qmarks})', r)
                n += 1
            new.commit()
            if name not in per:
                per[name] = n
        except Exception as e:  # noqa: BLE001
            per[name] = f"write_err after {n}: {e}"
    src.close()
    new.close()
    report["recover_tables"] = per
    v = sqlite3.connect(new_path)
    report["recovered_integrity"] = [r[0] for r in v.execute("PRAGMA integrity_check").fetchall()]
    v.close()


# 构建标记：用于线上确认当前服役容器版本（免鉴权，仅返回字符串，无副作用）。
_BUILD_MARK = "nodrop-relaxnotnull-2026-07-18"


def get_build_mark() -> str:
    return _BUILD_MARK


from fastapi import APIRouter  # noqa: E402

router = APIRouter(prefix="/_diag", tags=["diag"])


@router.get("/build")
def diag_build():
    """返回构建标记，确认当前服役容器版本（免鉴权，仅探针）。"""
    return {"build": _BUILD_MARK, "has_self_heal": True}
