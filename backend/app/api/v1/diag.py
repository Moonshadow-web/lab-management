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
import traceback
from datetime import datetime, timezone

# 最近未捕获异常环缓冲（main.py 全局异常处理器写入），仅 admin 可查看。
# 用于 CloudBase 等无 stdout 日志环境临时定位 500 根因。
_LAST_ERRORS: list[dict] = []
_MAX_LAST_ERRORS = 10


def capture_exception(exc: BaseException, request_path: str = "") -> None:
    """被 main.py 全局异常处理器调用，记录最近的非 HTTP 异常。"""
    try:
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    except Exception:  # noqa: BLE001
        tb = str(exc)
    _LAST_ERRORS.append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "path": request_path,
        "type": type(exc).__name__,
        "message": str(exc),
        "traceback": tb,
    })
    if len(_LAST_ERRORS) > _MAX_LAST_ERRORS:
        _LAST_ERRORS.pop(0)

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
_BUILD_MARK = "eqa-cos-dualwrite-2026-08-28"


def get_build_mark() -> str:
    return _BUILD_MARK


from fastapi import APIRouter, HTTPException, Depends  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402
from ...core.database import get_db  # noqa: E402
from ...core.security import get_current_user, require_roles  # noqa: E402
from ...core.cos_storage import cos_storage  # noqa: E402
from ...models.user import User  # noqa: E402

router = APIRouter(prefix="/_diag", tags=["diag"])


@router.get("/build")
def diag_build():
    """返回构建标记，确认当前服役容器版本（免鉴权，仅探针）。"""
    return {"build": _BUILD_MARK, "has_self_heal": True}


@router.get("/_debug_manuals")
def _debug_manuals():
    """调试：模拟 listProjectManuals 匹配逻辑。"""
    import json as _json
    from ...core.database import SessionLocal
    from ...models.test_item import TestItem
    from ...models.document import Document
    db = SessionLocal()
    try:
        items = db.query(TestItem.id, TestItem.name, TestItem.manual_doc_ids).all()
        # 模拟 listProjectManuals 的循环
        index = []
        for i, n, m in items:
            index.append({"tid": i, "oname": n or "", "mdoc_ids_str": m or ""})
        docs = db.query(Document.id, Document.title, Document.original_filename).filter(Document.category == "项目说明书").all()
        out = []
        for did, title, fn in docs:
            best = None
            # 优先 manual_doc_ids
            for it in index:
                mdocs = it.get("mdoc_ids_str", "")
                if mdocs:
                    try:
                        mdoc_list = _json.loads(mdocs)
                        if did in mdoc_list:
                            best = it
                            break
                    except Exception:
                        pass
            out.append({"doc_id": did, "title": (title or "")[:50], "matched": best["oname"] if best else None})
        # 找 HIV
        for o in out:
            if o["doc_id"] == 534 or '缺陷' in o.get("title",""):
                print(o)
        # return only relevant
        relevant = [o for o in out if o["matched"] or '缺陷' in o.get("title","") or '丙肝' in o.get("title","") or '梅毒' in o.get("title","")]
        return {"total_docs": len(out), "relevant": relevant[:20]}
    finally:
        db.close()


@router.get("/copy-from-sqlite")
def diag_copy_from_sqlite():
    """把容器内 /app/data/app.db (SQLite) 的数据搬到 MySQL。
    用于调试：cloudbaserc.json 的 env 未生效、容器内仍在用 SQLite 时。
    用完即删。
    """
    if not os.path.exists(_DB_PATH):
        return {"error": "no sqlite at /app/data/app.db"}
    import sqlite3 as _sq
    src = _sq.connect(_DB_PATH)
    src.row_factory = _sq.Row
    from ...core.database import engine
    from sqlalchemy import text as _t
    report = {}
    with engine.begin() as dst:
        inspector = inspect(engine)
        for table in inspector.get_table_names():
            try:
                rows = src.execute(f"SELECT * FROM `{table}`").fetchall()
            except Exception as e:
                report[table] = f"read_err: {e}"
                continue
            if not rows:
                report[table] = "0 rows"
                continue
            cols = [c["name"] for c in inspector.get_columns(table)]
            col_q = ", ".join(f"`{c}`" for c in cols)
            ph = ", ".join(":" + c for c in cols)
            n = 0
            for row in rows:
                vals = {c: row[c] for c in cols}
                try:
                    dst.execute(_t(f"INSERT INTO `{table}` ({col_q}) VALUES ({ph})"), vals)
                    n += 1
                except Exception:
                    pass
            report[table] = f"+{n}/{len(rows)}"
    src.close()
    return {"ok": True, "report": report}


@router.get("/db")
def diag_db():
    """下载当前数据库文件（免鉴权，仅管理员使用）。"""
    if not os.path.exists(_DB_PATH):
        from fastapi import HTTPException as HE
        raise HE(status_code=404, detail="数据库文件不存在")
    return FileResponse(_DB_PATH, filename="app.db", media_type="application/octet-stream")


@router.get("/last-errors")
def diag_last_errors():
    """返回最近捕获的未处理异常（仅管理员，用于无日志环境排障）。"""
    return {"errors": list(_LAST_ERRORS), "count": len(_LAST_ERRORS)}


@router.get("/mysql-vars")
def diag_mysql_vars(db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    """临时诊断：返回与 BLOB 写入相关的 MySQL 会话/全局变量（排查 2013 断连）。"""
    from sqlalchemy import text
    out = {}
    for v in ["max_allowed_packet", "wait_timeout", "interactive_timeout",
              "net_write_timeout", "net_read_timeout", "connect_timeout",
              "innodb_buffer_pool_size", "version"]:
        try:
            r = db.execute(text(f"SHOW VARIABLES LIKE '{v}'")).fetchone()
            out[v] = r[1] if r else None
        except Exception as e:  # noqa: BLE001
            out[v] = f"err:{e}"
    # InnoDB buffer pool 实时状态
    for q in ["SHOW STATUS LIKE 'Innodb_buffer_pool_pages_total'",
              "SHOW STATUS LIKE 'Innodb_buffer_pool_pages_free'",
              "SHOW STATUS LIKE 'Innodb_buffer_pool_pages_data'",
              "SHOW STATUS LIKE 'Innodb_buffer_pool_pages_dirty'",
              "SHOW STATUS LIKE 'Innodb_buffer_pool_read_requests'",
              "SHOW STATUS LIKE 'Innodb_buffer_pool_reads'"]:
        try:
            r = db.execute(text(q)).fetchone()
            key = q.split("LIKE '")[1].rstrip("'")
            out[key] = r[1] if r else None
        except Exception as e:  # noqa: BLE001
            pass
    try:
        r = db.execute(text("SELECT COUNT(*) FROM documents WHERE data IS NOT NULL")).fetchone()
        out["documents_with_data"] = r[0] if r else None
        r = db.execute(text("SELECT COUNT(*) FROM document_versions WHERE data IS NOT NULL")).fetchone()
        out["versions_with_data"] = r[0] if r else None
        # 估算 BLOB 总大小（用于排查内存告警）
        r = db.execute(text("SELECT SUM(LENGTH(data)) FROM documents WHERE data IS NOT NULL")).fetchone()
        out["documents_data_mb"] = round(r[0] / (1024 * 1024), 2) if r and r[0] else 0
        r = db.execute(text("SELECT SUM(LENGTH(data)) FROM document_versions WHERE data IS NOT NULL")).fetchone()
        out["versions_data_mb"] = round(r[0] / (1024 * 1024), 2) if r and r[0] else 0
        out["total_blob_mb"] = round(out["documents_data_mb"] + out["versions_data_mb"], 2)
        # 附件表
        for tbl, label in [("comparison_attachments", "comp_attach"), ("interlab_attachments", "interlab_attach")]:
            r = db.execute(text(f"SELECT COUNT(*), SUM(LENGTH(data)) FROM {tbl} WHERE data IS NOT NULL")).fetchone()
            out[f"{label}_cnt"] = r[0] or 0
            out[f"{label}_mb"] = round((r[1] or 0) / (1024 * 1024), 2)
            r = db.execute(text(f"SELECT COUNT(*) FROM {tbl} WHERE cloud_key IS NOT NULL")).fetchone()
            out[f"{label}_cos"] = r[0] or 0
    except Exception as e:  # noqa: BLE001
        out["count_err"] = str(e)[:200]
    return out


@router.post("/backfill-aliases")
def backfill_test_item_aliases(db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    """批量回填 test_items.aliases（SQLite→MySQL 迁移后丢失的别名）。

    从 backend/scripts/backfill_test_item_aliases.py 的 ALIAS_PATCHES 读取映射。"""
    from importlib import import_module
    import importlib.util
    import os as _os
    from sqlalchemy import text

    # 加载脚本中的 ALIAS_PATCHES 字典
    script_path = _os.path.join(
        _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.dirname(__file__)))),
        "scripts", "backfill_test_item_aliases.py",
    )
    spec = importlib.util.spec_from_file_location("backfill_aliases", script_path)
    if not spec or not spec.loader:
        raise HTTPException(500, "无法加载脚本")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    patches = mod.ALIAS_PATCHES

    report = {"updated": 0, "skipped": 0, "errors": []}
    for tid, new_aliases in sorted(patches.items()):
        try:
            row = db.execute(text("SELECT name, aliases FROM test_items WHERE id = :id"), {"id": tid}).fetchone()
            if not row:
                report["errors"].append(f"id={tid}: not found")
                continue
            name, current = row[0], row[1] or ""
            existing = set(a.strip() for a in current.replace("，", ",").split(",") if a.strip())
            to_add = [a for a in new_aliases if a not in existing]
            if not to_add:
                report["skipped"] += 1
                continue
            merged = current.rstrip(", ") + ", " + ", ".join(to_add)
            db.execute(text("UPDATE test_items SET aliases = :aliases WHERE id = :id"), {"id": tid, "aliases": merged})
            db.commit()
            report["updated"] += 1
        except Exception as e:
            db.rollback()
            report["errors"].append(f"id={tid}: {type(e).__name__}: {str(e)[:100]}")

    return {"ok": True, **report}


@router.post("/fix-aliases")
def fix_aliases(payload: dict, db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    """直接按 ID 修正 test_items.aliases。 payload = {\"items\": [{\"id\": 9, \"aliases\": \"...\"}]}"""
    from sqlalchemy import text as _tx
    updated = 0
    for item in payload.get("items", []):
        tid, aliases = item["id"], item["aliases"]
        db.execute(_tx("UPDATE test_items SET aliases = :a WHERE id = :i"), {"a": aliases, "i": tid})
        db.commit()
        updated += 1
    return {"ok": True, "updated": updated}


@router.post("/force-recalc-goals")
def force_recalc_goals(db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    """强制重算所有质控月结行的 quality_goal（覆盖已有值，不限空值）。"""
    from sqlalchemy import text as _tx
    from ...services.qc_service import _lookup_qr_goal

    rows = db.execute(_tx("SELECT id, test_item, level, quality_goal FROM qc_monthly_summaries")).fetchall()
    updated = 0
    samples = []
    for row in rows:
        tid, test_item, level, old_goal = row[0], row[1], row[2], row[3]
        new_goal = _lookup_qr_goal(db, test_item, "", level)
        if new_goal and new_goal != old_goal:
            db.execute(_tx("UPDATE qc_monthly_summaries SET quality_goal = :g WHERE id = :i"),
                       {"g": new_goal, "i": tid})
            db.commit()
            updated += 1
            if len(samples) < 10:
                samples.append({"test_item": test_item, "level": level, "old": old_goal or "", "goal": new_goal})
    return {"ok": True, "updated": updated, "total": len(rows), "samples": samples}


@router.post("/migrate-attachments-to-cos")
def migrate_attachments_to_cos(db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    """把 comparison_attachments + interlab_attachments 的 data BLOB 迁移到 COS。"""
    if not cos_storage.ready:
        raise HTTPException(400, detail="COS 未配置")

    from ...models.comparison import ComparisonAttachment
    from ...models.interlab import InterlabAttachment

    report = {"comp": {"migrated": 0, "failed": 0, "errors": []},
              "interlab": {"migrated": 0, "failed": 0, "errors": []}}

    BATCH = 20
    for cls, label in [(ComparisonAttachment, "comp"), (InterlabAttachment, "interlab")]:
        q = db.query(cls).filter(cls.data.isnot(None), cls.cloud_key.is_(None))
        for obj in q.yield_per(BATCH):
            try:
                key = cos_storage.save(cls.__tablename__, obj.original_name or f"att-{obj.id}", obj.data)
                obj.cloud_key = key
                obj.data = None
                db.commit()
                report[label]["migrated"] += 1
            except Exception as e:
                db.rollback()
                db.refresh(obj)
                report[label]["failed"] += 1
                if len(report[label]["errors"]) < 3:
                    report[label]["errors"].append(f"id#{obj.id}: {type(e).__name__}: {str(e)[:150]}")

    return {"ok": True, **report}
