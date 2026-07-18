"""临时诊断/修复路由（排查线上 SQLite 损坏，修复后删除）。

路径前缀 /_diag，避免与 instruments 的 /{id} 抢匹配。
"""
import os
import shutil
import sqlite3
import datetime as _dt

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ...core.database import engine, get_db
from ...core.security import get_current_user
from ...models.user import User

router = APIRouter(prefix="/_diag", tags=["diag"])

_DB_PATH = "/app/data/app.db"
_RECOVERED = "/tmp/recovered_app.db"


def _swap_in(report: dict, new_path: str, label: str):
    """用新文件原子替换损坏库，并清理 WAL/SHM、强制连接池重连。"""
    for ext in ("-wal", "-shm"):
        p = _DB_PATH + ext
        if os.path.exists(p):
            os.remove(p)
    os.replace(new_path, _DB_PATH)
    try:
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


@router.post("/db-recover")
def diag_db_recover(user: User = Depends(get_current_user)):
    """恢复损坏的 SQLite：先 REINDEX 重建索引页，干净则 VACUUM 替换；
    否则走逐表 dump 重建兜底。替换前先备份损坏文件，可回滚。"""
    report: dict = {"db_path": _DB_PATH}
    try:
        engine.dispose()
    except Exception as e:  # noqa: BLE001
        report["engine_dispose_warn"] = repr(e)

    ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = f"{_DB_PATH}.corrupt-bak-{ts}"
    try:
        shutil.copy2(_DB_PATH, bak)
        report["backup"] = bak
    except Exception as e:  # noqa: BLE001
        report["backup_error"] = repr(e)

    # ---- 第一步：REINDEX 全部索引（从完好表数据重建索引页）----
    try:
        con = sqlite3.connect(_DB_PATH)
        con.execute("PRAGMA writable_schema=ON")
        try:
            con.execute("REINDEX")
            report["reindex"] = "ok"
        except Exception as e:  # noqa: BLE001
            report["reindex_error"] = repr(e)
            idxs = [r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()]
            per = {}
            for ix in idxs:
                try:
                    con.execute(f'REINDEX "{ix}"')
                    per[ix] = "ok"
                except Exception as ex:  # noqa: BLE001
                    per[ix] = f"fail: {ex}"
            report["reindex_per_index"] = per
        con.commit()
        report["integrity_after_reindex"] = [r[0] for r in con.execute("PRAGMA integrity_check").fetchall()]
        con.close()
    except Exception as e:  # noqa: BLE001
        report["reindex_stage_error"] = repr(e)

    # ---- 第二步：若已干净，VACUUM 压缩并原子替换 ----
    if report.get("integrity_after_reindex") == ["ok"]:
        try:
            if os.path.exists(_RECOVERED):
                os.remove(_RECOVERED)
            c2 = sqlite3.connect(_DB_PATH)
            c2.execute(f"VACUUM INTO '{_RECOVERED}'")
            c2.close()
            v = sqlite3.connect(_RECOVERED)
            ic2 = [r[0] for r in v.execute("PRAGMA integrity_check").fetchall()]
            v.close()
            if ic2 == ["ok"]:
                _swap_in(report, _RECOVERED, "ok (reindex+vacuum)")
                report["final_integrity"] = ic2
                return report
            report["vacuum_verify"] = ic2
        except Exception as e:  # noqa: BLE001
            report["vacuum_error"] = repr(e)

    # ---- 兜底：逐表 dump 重建 ----
    dump_path = "/tmp/recover_dump.db"
    try:
        _generic_dump_recover(_DB_PATH, dump_path, report)
        if report.get("recovered_integrity") == ["ok"]:
            _swap_in(report, dump_path, "ok (dump-recover)")
        else:
            report["swap"] = "skipped: dump 后仍不干净，保留损坏文件，请用 backup 回滚"
    except Exception as e:  # noqa: BLE001
        report["dump_stage_error"] = repr(e)
    return report



@router.get("/db")
def diag_db(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """评估数据库损坏范围，并尝试 VACUUM 出干净副本。"""
    out: dict = {"db_path": _DB_PATH}

    # 1. 完整性检查
    try:
        rows = db.execute(text("PRAGMA integrity_check")).fetchall()
        out["integrity_check"] = [r[0] for r in rows]
    except Exception as e:
        out["integrity_check_error"] = repr(e)

    # 2. 外键检查
    try:
        rows = db.execute(text("PRAGMA foreign_key_check")).fetchall()
        out["foreign_key_check"] = [list(r) for r in rows]
    except Exception as e:
        out["foreign_key_check_error"] = repr(e)

    # 3. WAL 检查点（清理可能不一致的 WAL）
    try:
        r = db.execute(text("PRAGMA wal_checkpoint(TRUNCATE)")).fetchall()
        out["wal_checkpoint"] = [list(x) for x in r]
    except Exception as e:
        out["wal_checkpoint_error"] = repr(e)

    # 4. 逐表计数（看哪些表能正常读）
    try:
        names = [n[0] for n in db.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        ).fetchall()]
        counts = {}
        for n in names:
            try:
                c = db.execute(text(f'SELECT COUNT(*) FROM "{n}"')).fetchone()[0]
                counts[n] = c
            except Exception as e:
                counts[n] = f"ERR:{e}"
        out["table_counts"] = counts
    except Exception as e:
        out["table_counts_error"] = repr(e)

    # 5. 尝试 VACUUM 出干净副本（可恢复则能用于替换）
    try:
        if os.path.exists(_RECOVERED):
            os.remove(_RECOVERED)
        db.execute(text(f"VACUUM INTO '{_RECOVERED}'"))
        db.commit()
        out["vacuum_into"] = "ok"
        out["recovered_size"] = os.path.getsize(_RECOVERED)
    except Exception as e:
        out["vacuum_into_error"] = repr(e)

    return out


@router.post("/db-repair-swap")
def diag_db_repair_swap(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """用 VACUUM 出的干净副本替换损坏文件（先备份损坏文件，绝不删除）。"""
    if not os.path.exists(_RECOVERED):
        try:
            if os.path.exists(_RECOVERED):
                os.remove(_RECOVERED)
            db.execute(text(f"VACUUM INTO '{_RECOVERED}'"))
            db.commit()
        except Exception as e:
            return {"ok": False, "step": "vacuum", "error": repr(e)}

    if not os.path.exists(_RECOVERED):
        return {"ok": False, "step": "vacuum", "error": "recovered file missing"}

    # 备份损坏文件（不删除，留作回滚）
    bak = _DB_PATH + ".corrupt-bak"
    if os.path.exists(_DB_PATH):
        shutil.copy2(_DB_PATH, bak)

    # 删除旧的 WAL/SHM，避免与新文件冲突
    for ext in ("-wal", "-shm"):
        p = _DB_PATH + ext
        if os.path.exists(p):
            os.remove(p)

    # 原子替换
    os.replace(_RECOVERED, _DB_PATH)

    # 强制连接池重连到新文件
    try:
        engine.dispose()
    except Exception:
        pass

    return {"ok": True, "swapped": True, "backup": bak}
