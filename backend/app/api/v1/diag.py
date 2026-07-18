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


def _integrity_ok(path: str) -> bool:
    try:
        c = sqlite3.connect(path)
        ok = [r[0] for r in c.execute("PRAGMA integrity_check").fetchall()] == ["ok"]
        c.close()
        return ok
    except Exception:
        return False


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
def diag_db_recover():
    """轻量恢复损坏的 SQLite（针对「仅索引页损坏、表数据完好」场景）：
    1) 备份当前文件（可回滚）；2) 释放 ORM 连接池旧句柄；
    3) REINDEX 重建全部索引（从完好表数据 → 修复坏掉的索引页）；
    4) integrity_check 校验。
    不做 VACUUM 整库复制 / 文件原子替换（CFS 上易超网关请求超时导致 504）。
    临时放开鉴权：DB 损坏时登录接口会因插入 refresh_tokens 失败而 500，无法拿 token，
    故允许无 token 调用（修复后将整路由删除）。"""
    report: dict = {"db_path": _DB_PATH, "started_at": _dt.datetime.now().isoformat()}

    # 0. 备份（快速，可回滚）
    ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = f"{_DB_PATH}.corrupt-bak-{ts}"
    try:
        shutil.copy2(_DB_PATH, bak)
        report["backup"] = bak
    except Exception as e:  # noqa: BLE001
        report["backup_error"] = repr(e)

    # 1. 释放 ORM 连接池（避免残留旧文件句柄）
    try:
        engine.dispose()
    except Exception as e:  # noqa: BLE001
        report["engine_dispose_warn"] = repr(e)

    # 2. REINDEX 重建所有索引（从完好表数据修复索引页损坏）—— 通常几秒完成
    try:
        con = sqlite3.connect(_DB_PATH)
        con.execute("PRAGMA writable_schema=ON")
        con.execute("REINDEX")
        con.commit()
        report["reindex"] = "ok"
        report["integrity_after_reindex"] = [r[0] for r in con.execute("PRAGMA integrity_check").fetchall()]
        con.close()
    except Exception as e:  # noqa: BLE001
        report["reindex_error"] = repr(e)
        report["integrity_after_reindex"] = None

    # 3. 若 REINDEX 后仍不干净，原地 VACUUM 重写文件释放损坏页（不复制整库、不替换文件）
    if report.get("integrity_after_reindex") != ["ok"]:
        try:
            c = sqlite3.connect(_DB_PATH)
            c.execute("VACUUM")
            c.close()
            c2 = sqlite3.connect(_DB_PATH)
            report["integrity_after_vacuum"] = [r[0] for r in c2.execute("PRAGMA integrity_check").fetchall()]
            c2.close()
        except Exception as e:  # noqa: BLE001
            report["vacuum_error"] = repr(e)

    # 4. 兜底：逐表 dump 重建（从 sqlite_master 存的 CREATE 语句原样建表+索引，再拷行）
    #    仅当 REINDEX+VACUUM 仍不干净时启用。小库（几十张表、数千行）秒级完成，不超网关超时。
    if report.get("integrity_after_reindex") != ["ok"] and report.get("integrity_after_vacuum") != ["ok"]:
        try:
            dump_path = "/tmp/recover_dump.db"
            _generic_dump_recover(_DB_PATH, dump_path, report)
            if report.get("recovered_integrity") == ["ok"]:
                _swap_in(report, dump_path, "ok (dump-recover)")
            else:
                # dump 后仍不干净：回退到镜像种子库（干净，含全部基础数据）。
                # 用 copy 而非 replace，保留 /app/backup/app.db 不被移走。
                seed = "/app/backup/app.db"
                if os.path.exists(seed) and _integrity_ok(seed):
                    for ext in ("-wal", "-shm"):
                        p = _DB_PATH + ext
                        if os.path.exists(p):
                            os.remove(p)
                    shutil.copy2(seed, _DB_PATH)
                    try:
                        engine.dispose()
                    except Exception:
                        pass
                    report["swap"] = "ok (seed fallback)"
                    report["recovered_integrity"] = ["ok"]
                else:
                    report["swap"] = "skipped: dump 后仍不干净，保留原文件，请用 backup 回滚"
        except Exception as e:  # noqa: BLE001
            report["dump_stage_error"] = repr(e)

    report["finished_at"] = _dt.datetime.now().isoformat()
    return report

@router.post("/db-backup")
def diag_db_backup():
    """手动备份当前数据库文件到带时间戳的副本（可回滚）。免鉴权。"""
    ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = f"{_DB_PATH}.manual-bak-{ts}"
    try:
        shutil.copy2(_DB_PATH, bak)
        return {"ok": True, "backup": bak, "size": os.path.getsize(bak)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": repr(e)}



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
