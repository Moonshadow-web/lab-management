"""启动自愈所需的 SQLite 修复工具 + 版本探针。

仅保留 main.py 启动自愈(_self_heal_db)真正依赖的辅助函数
(_integrity_ok / _generic_dump_recover / _swap_in) 与无害的 /build 版本探针。
曾用于 CFS 损坏后数据恢复的临时诊断/恢复路由(db-recover / inspect-* /
recover-*-from-backup 等) 已移除，收敛攻击面。

路径前缀 /_diag，避免与 instruments 的 /{id} 抢匹配。
"""
import os
import shutil
import sqlite3
import datetime as _dt

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
_BUILD_MARK = "4da3a52-selfheal-2026-07-18-diffrec3"


def get_build_mark() -> str:
    return _BUILD_MARK


from fastapi import APIRouter, Depends  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402
from ...core.security import require_roles  # noqa: E402
from ...models.user import User  # noqa: E402
from ...core.database import get_db, engine  # noqa: E402

router = APIRouter(prefix="/_diag", tags=["diag"])


@router.get("/build")
def diag_build():
    """返回构建标记，确认当前服役容器版本（免鉴权，仅探针）。"""
    return {"build": _BUILD_MARK, "has_self_heal": True}


@router.get("/audit-missing")
def diag_audit_missing(db: Session = Depends(get_db),
                       _u: User = Depends(require_roles("admin"))):
    """只读审计：逐表比较线上库行数与所有损坏前副本(corrupt-bak/lastgood/manual-bak)的
    可读行数，找出任何「副本里有、线上漏了」的数据。无写操作。"""
    import glob

    d = os.path.dirname(_DB_PATH)
    pats = ["app.db.corrupt-bak-*", "app.db.lastgood", "app.db.manual-bak-*"]
    copies = sorted(
        set(sum((glob.glob(os.path.join(d, p)) for p in pats), [])),
        key=lambda f: os.path.getmtime(f),
    )
    live_tables = [
        r[0] for r in db.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        ).fetchall()
    ]
    live_counts = {}
    for t in live_tables:
        try:
            live_counts[t] = db.execute(text(f'SELECT COUNT(*) FROM "{t}"')).fetchone()[0]
        except Exception:  # noqa: BLE001
            live_counts[t] = None
    copy_rows = {}
    copy_integrity = {}
    for cp in copies:
        base = os.path.basename(cp)
        try:
            c = sqlite3.connect(cp)
            c.text_factory = str
            copy_integrity[base] = [r[0] for r in c.execute("PRAGMA integrity_check").fetchall()]
            tbls = [
                r[0] for r in c.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                ).fetchall()
            ]
            rows = {}
            for t in tbls:
                try:
                    rows[t] = c.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
                except Exception as e:  # noqa: BLE001
                    rows[t] = f"err:{e}"
            copy_rows[base] = rows
            c.close()
        except Exception as e:  # noqa: BLE001
            copy_rows[base] = {"__open_err__": str(e)}
            copy_integrity[base] = ["open_err"]
    missing = []
    for t in live_tables:
        best = None
        best_src = None
        for base, rows in copy_rows.items():
            if t in rows and isinstance(rows[t], int):
                if best is None or rows[t] > best:
                    best = rows[t]
                    best_src = base
        live = live_counts.get(t)
        if isinstance(live, int) and best is not None and best > live:
            missing.append(
                {"table": t, "live": live, "best_copy": best,
                 "missing_rows": best - live, "source": best_src}
            )
    return {
        "live_table_count": len(live_tables),
        "live_counts": live_counts,
        "copies_integrity": copy_integrity,
        "missing": missing,
        "copy_table_counts": copy_rows,
    }


def _list_copies():
    import glob

    d = os.path.dirname(_DB_PATH)
    pats = ["app.db.corrupt-bak-*", "app.db.lastgood", "app.db.manual-bak-*"]
    return sorted(
        set(sum((glob.glob(os.path.join(d, p)) for p in pats), [])),
        key=lambda f: os.path.getmtime(f),
    )


def _best_copy_for(table: str):
    """返回 (副本路径, 可读行数) —— 选该表可读行数最多、且修改时间最新的副本。"""
    best_cp, best_n, best_mt = None, -1, 0
    for cp in _list_copies():
        try:
            c = sqlite3.connect(cp)
            c.text_factory = str
            n = c.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            c.close()
            mt = os.path.getmtime(cp)
            if n > best_n or (n == best_n and mt > best_mt):
                best_n, best_cp, best_mt = n, cp, mt
        except Exception:  # noqa: BLE001
            pass
    return best_cp, best_n


@router.get("/diff-table")
def diag_diff_table(table: str, db: Session = Depends(get_db),
                    _u: User = Depends(require_roles("admin"))):
    """逐行对比线上表与最佳可读副本（按首列即主键），找出缺失/多余/值不一致。只读。"""
    best_cp, best_n = _best_copy_for(table)
    if best_cp is None or best_n <= 0:
        return {"table": table, "status": "no_source", "best_copy": best_cp}
    c = sqlite3.connect(best_cp)
    c.text_factory = str
    cols = [r[1] for r in c.execute(f'PRAGMA table_info("{table}")').fetchall()]
    if not cols:
        c.close()
        return {"table": table, "status": "no_cols"}
    col_sql = ", ".join(f'"{x}"' for x in cols)
    try:
        rows = c.execute(f'SELECT {col_sql} FROM "{table}"').fetchall()
    except Exception as e:  # noqa: BLE001
        c.close()
        return {"table": table, "status": "read_err", "error": str(e)}
    c.close()
    src = {r[0]: r for r in rows}
    live_rows = db.execute(text(f'SELECT {col_sql} FROM "{table}"')).fetchall()
    live = {r[0]: r for r in live_rows}
    missing_in_live = [k for k in src if k not in live]
    extra_in_live = [k for k in live if k not in src]
    mismatched = []
    for k in src:
        if k in live and src[k] != live[k]:
            diff_cols = [cols[i] for i in range(1, len(cols)) if src[k][i] != live[k][i]]
            mismatched.append({"id": k, "diff_cols": diff_cols[:8]})
            if len(mismatched) >= 20:
                break
    return {
        "table": table,
        "best_copy": os.path.basename(best_cp),
        "source_rows": len(rows),
        "live_rows": len(live_rows),
        "missing_in_live": missing_in_live[:50],
        "missing_in_live_count": len(missing_in_live),
        "extra_in_live_count": len(extra_in_live),
        "mismatched_count": len(mismatched),
        "mismatched_sample": mismatched,
    }


@router.post("/recover-table")
def diag_recover_table(payload: dict, db: Session = Depends(get_db),
                        _u: User = Depends(require_roles("admin"))):
    """用最佳可读副本对指定表做 INSERT OR REPLACE 整表修复：
    - 副本有、线上漏的 → 新增
    - 两边都有(同主键) → 用副本值覆盖线上(修正损坏/错误值)
    - 线上独有(副本无) → 保留，不删除
    不触发 DELETE，避免外键级联问题。仅处理用户数据表，跳过系统表。
    """
    BLOCK = {"alembic_version", "sqlite_sequence", "refresh_tokens"}
    tables = payload.get("tables", [])
    mode = payload.get("mode", "replace")  # replace | insert_missing
    report = []
    for t in tables:
        if t in BLOCK:
            report.append({"table": t, "status": "skipped_system"})
            continue
        best_cp, best_n = _best_copy_for(t)
        if best_cp is None or best_n <= 0:
            report.append({"table": t, "status": "no_source", "best_copy": best_cp})
            continue
        c = sqlite3.connect(best_cp)
        c.text_factory = str
        cols = [r[1] for r in c.execute(f'PRAGMA table_info("{t}")').fetchall()]
        if not cols:
            c.close()
            report.append({"table": t, "status": "no_cols"})
            continue
        col_sql = ", ".join(f'"{x}"' for x in cols)
        qmarks = ", ".join("?" * len(cols))
        try:
            rows = c.execute(f'SELECT {col_sql} FROM "{t}"').fetchall()
        except Exception as e:  # noqa: BLE001
            c.close()
            report.append({"table": t, "status": "read_err", "error": str(e)})
            continue
        c.close()
        # 从 SQLAlchemy 连接池取原生连接写回（支持 ? 占位符，且不会与池抢锁）
        conn = engine.raw_connection()
        try:
            cur = conn.cursor()
            replaced = 0
            added = 0
            live_ids = set(r[0] for r in cur.execute(f'SELECT "{cols[0]}" FROM "{t}"').fetchall())
            for r in rows:
                if mode == "insert_missing" and r[0] in live_ids:
                    continue  # 仅补缺失，不覆盖现有行（保护 password_hash 等）
                try:
                    cur.execute(
                        f'INSERT OR REPLACE INTO "{t}" ({col_sql}) VALUES ({qmarks})', r
                    )
                    if r[0] in live_ids:
                        replaced += 1
                    else:
                        added += 1
                except Exception:  # noqa: BLE001
                    pass
            conn.commit()
            # 同步 sqlite_sequence，避免后续自增主键冲突
            try:
                maxid = cur.execute(f'SELECT MAX("{cols[0]}") FROM "{t}"').fetchone()[0]
                if maxid is not None:
                    cur.execute(
                        "INSERT OR REPLACE INTO sqlite_sequence(name, seq) VALUES (?, ?)",
                        (t, maxid),
                    )
                    conn.commit()
            except Exception:  # noqa: BLE001
                pass
        finally:
            conn.close()
        report.append(
            {
                "table": t,
                "status": "ok",
                "best_copy": os.path.basename(best_cp),
                "source_rows": len(rows),
                "replaced": replaced,
                "added": added,
            }
        )
    return {"report": report}

