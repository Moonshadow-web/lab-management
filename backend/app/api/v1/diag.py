"""临时诊断/修复路由（排查线上 SQLite 损坏，修复后删除）。

路径前缀 /_diag，避免与 instruments 的 /{id} 抢匹配。
"""
import os
import shutil

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ...core.database import engine, get_db
from ...core.security import get_current_user
from ...models.user import User

router = APIRouter(prefix="/_diag", tags=["diag"])

_DB_PATH = "/app/data/app.db"
_RECOVERED = "/tmp/recovered_app.db"


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
