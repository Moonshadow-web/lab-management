from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import case, func, text
from sqlalchemy.orm import defer
import re

from ...core.crud_base import paginate, write_audit
from ...core.database import get_db
from ...core.security import get_current_user, require_roles
from ...core.storage import storage
from ...core.cos_storage import cos_storage
from ...core.docmeta import parse_doc_metadata
from ...models.document import Document, DocumentVersion, DOC_CATEGORIES
from ...models.file_change_log import FileChangeLog
from ...models.test_item import TestItem
from ...models.user import User
from ...schemas import DocumentRead, DocumentUpdate, DocumentVersionRead

router = APIRouter(prefix="/documents", tags=["documents"])


# ---- 项目说明书 → 项目查询 关联（卡片上预览用）----
def _norm(s: str) -> str:
    s = (s or "").strip().replace("（", "(").replace("）", ")").replace("　", " ").replace(" ", "")
    return s.lower()


# 厂商关键词（标题/文件名命中即推断品牌）；注意顺序靠前的优先
_BRAND_RULES = [
    ("贝克曼", ["贝克曼", "beekman", "beckman", "osr", "au生化", "au系列"]),
    ("罗氏", ["罗氏", "roche"]),
    ("安图", ["安图", "autobio"]),
    ("迈瑞", ["迈瑞", "mindray"]),
    ("西门子", ["西门子", "siemens"]),
    ("雅培", ["雅培", "abbott"]),
    ("积水", ["积水"]),
    ("九强", ["九强"]),
    ("美康", ["美康"]),
    ("利德曼", ["利德曼"]),
    ("透景", ["透景"]),
    ("基蛋", ["基蛋"]),
    ("奥森", ["奥森"]),
    ("东芝", ["东芝", "toshiba"]),
    ("日立", ["日立", "hitachi"]),
    ("沃芬", ["沃芬", "werfen", "il"]),
]


def _brand_heuristic(title: str, filename: str, project_brand: str = "") -> str:
    if project_brand:
        return project_brand
    hay = _norm((title or "") + " " + (filename or ""))
    for brand, keys in _BRAND_RULES:
        for k in keys:
            if _norm(k) in hay:
                return brand
    return ""


def _manual_core(title: str) -> str:
    """从「项目说明书」标题中提取核心项目名（去方法/试剂盒/说明书/编号等外壳）。"""
    t = title or ""
    t = re.sub(r"[（(][^（）()]*[)）]", "", t)        # 去括号及内容（方法学）
    t = re.sub(r"(测定|检测|定量)?试剂盒", "", t)
    t = re.sub(r"(产品|中文)?说明书", "", t)
    t = re.sub(r"投放版本", "", t)
    t = re.sub(r"rev[\d.]*", "", t, flags=re.I)
    t = re.sub(r"[A-Za-z]\d{3,}", "", t)              # 去货号（如 C22593 / A16369）
    t = re.sub(r"[—\-–\s/]+", "", t)
    t = re.sub(r"^[0-9]+", "", t)                     # 去开头序号
    return _norm(t)


@router.get("/project-manuals")
def project_manuals(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """返回全部「项目说明书」文档，并归一化匹配到项目查询(test_items)，
    供项目卡片点击预览。每项含 linked_project（关联项目名）与 brand（品牌）。"""
    items = db.query(TestItem.id, TestItem.name, TestItem.aliases, TestItem.brand).all()
    index = []
    for _tid, name, aliases, brand in items:
        keys = {_norm(name)}
        for part in re.split(r"[、,，/]", name):
            p = part.strip()
            if p:
                keys.add(_norm(p))
        if aliases:
            for seg in aliases.replace("，", ",").split(","):
                seg = seg.strip()
                if seg:
                    keys.add(_norm(seg))
        index.append({"oname": name or "", "nname": _norm(name), "brand": brand or "", "keys": keys})

    docs = (
        db.query(Document.id, Document.title, Document.original_filename)
        .filter(Document.category == "项目说明书")
        .all()
    )
    out = []
    for did, title, fn in docs:
        core = _manual_core(title)
        best = None
        if core:
            core_nh = core.replace("-", "")
            # 1) 精确命中 名称/别名（含拆分片段）：如「磷」「pct」「高敏肌钙蛋白I」
            for it in index:
                if core in it["keys"]:
                    best = it
                    break
            # 2) 子串匹配：仅允许较长 key，避免「钙/磷/pc」等过短别名被长词误含
            if not best:
                for it in index:
                    for k in it["keys"]:
                        if len(k) < 3 or len(core) < 3:
                            continue
                        k_nh = k.replace("-", "")
                        if core in k or k in core or core_nh in k_nh or k_nh in core_nh:
                            best = it
                            break
                    if best:
                        break
        linked = best["oname"] if best else None
        linked_brand = best["brand"] if best else ""
        brand = _brand_heuristic(title, fn, linked_brand)
        ext = (fn or title or "").split(".")[-1].lower()
        out.append({
            "id": did,
            "title": title,
            "brand": brand,
            "linked_project": linked,
            "ext": ext,
            "is_pdf": ext == "pdf",
        })
    out.sort(key=lambda x: (x["linked_project"] is None, x["linked_project"] or "", x["title"]))
    return out

# 文档头元数据字段（与 Document 模型属性一一对应）
META_FIELDS = [
    "doc_number", "doc_version", "revision", "author", "reviewer",
    "approver", "issued_date", "audit_date", "approve_date",
    "effective_date", "meta_raw",
]


def _strip_title_prefix(name: str) -> str:
    """去掉标题开头的文件编号前缀，仅保留正文标题：
    1) 体系编号前缀：BG-KS-GL-076- / MHZYY-JYK-SM-SOP-572-
    2) 文件序号前缀：101  / 001 / 2,A16369 / 011（数字+分隔符或正文）
    3) 文件扩展名：.docx / .pdf 等
    无前缀或纯中文时原样返回。"""
    if not name:
        return name
    # 去掉扩展名
    name = re.sub(r"\.[a-zA-Z0-9]+$", "", name)
    # 体系编号前缀（大写字母/数字，连字符分隔，以连字符结尾）
    name = re.sub(r"^[A-Z0-9]+(?:-[A-Z0-9]+)+-", "", name).strip()
    # 文件序号前缀（数字 + 可选分隔符 空格/逗号/点/连字符，或紧跟正文）
    name = re.sub(r"^\d+[\s,，.\-]*", "", name).strip()
    # 结尾残留分隔符
    name = re.sub(r"[\s\-–—]+$", "", name)
    return name or name


def _apply_meta(obj, meta: dict):
    """把解析到的文件头元数据写入对象（只写入非空字段，避免覆盖已有值）。"""
    for k in META_FIELDS:
        v = meta.get(k)
        if v:
            setattr(obj, k, v)


def _log_change(db: Session, doc, change_type: str, operator: str):
    """写入一条文件更改日志（新增 / 修改 / 作废）。doc 可为已删除对象（属性仍可读取）。"""
    db.add(
        FileChangeLog(
            doc_id=doc.id if doc else None,
            file_name=doc.title if doc else "",
            file_code=(doc.doc_number or "") if doc else "",
            change_type=change_type,
            operator=operator,
            change_date=datetime.now().date(),
        )
    )
    db.commit()


@router.get("")
def list_documents(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    q: str | None = None,
    hide_invalid: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    params = dict(request.query_params)
    query = db.query(Document).options(defer(Document.data))  # 列表不加载二进制字节（JSON 序列化会 UnicodeDecodeError）
    if q:
        query = query.filter(
            Document.title.ilike(f"%{q}%")
            | Document.original_filename.ilike(f"%{q}%")
            | Document.doc_number.ilike(f"%{q}%")
        )
    cat = params.get("category")
    if cat:
        query = query.filter(Document.category == cat)
    # 隐藏作废文件：仅保留非「作废」状态
    if hide_invalid:
        query = query.filter(Document.status != "作废")
    # 作废状态排到最后，其余按编号自然序（作废在末、同状态下仍按编号从小到大）
    query = query.order_by(
        case((Document.status == "作废", 1), else_=0),
        Document.doc_number,
    )
    return paginate(query, page, page_size)


@router.get("/{doc_id}", response_model=DocumentRead)
def get_document(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    d = db.query(Document).options(defer(Document.data)).filter(Document.id == doc_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="未找到文件")
    return d


@router.patch("/{doc_id}", response_model=DocumentRead, response_model_exclude={"data"})
def update_document(
    doc_id: int,
    payload: DocumentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "specialty_leader")),
):
    d = db.get(Document, doc_id)
    if not d:
        raise HTTPException(status_code=404, detail="未找到文件")
    if payload.category and payload.category not in DOC_CATEGORIES:
        raise HTTPException(status_code=400, detail="文件分类不合法")
    data = payload.model_dump(exclude_unset=True)
    skip = {"id", "created_at", "updated_at", "file_path", "original_filename", "uploader", "version", "parent_id", "meta_raw"}
    for k, v in data.items():
        if k in skip:
            continue
        setattr(d, k, v)
    d.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(d)
    write_audit(db, user, "update", "documents", d.id, {"fields": list(data.keys())})
    _log_change(db, d, "修改", user.full_name or user.username)
    return d


@router.post("/upload", response_model=DocumentRead, response_model_exclude={"data"}, status_code=201)
def upload_document(
    file: UploadFile = File(...),
    title: str = Form(""),
    category: str = Form("通用SOP"),
    note: str = Form(""),
    status: str = Form("生效"),
    description: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "specialty_leader")),
):
    if category not in DOC_CATEGORIES:
        raise HTTPException(status_code=400, detail="文件分类不合法")
    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空")
    rel = storage.save("docs", file.filename or title or "file", content)
    # 文件字节存 COS 云存储（不占 DB 内存），cloud_key 落库；磁盘仅兜底
    cloud_key = None
    if cos_storage.ready:
        try:
            cloud_key = cos_storage.save("documents", file.filename or title or "file", content)
        except Exception as e:
            pass  # COS 失败不阻塞上传，仍走磁盘 + LONGBLOB 兜底
    # 解析文件头元数据（.docx 解析表头；.doc 用文件名兜底提取编号）
    meta = parse_doc_metadata(str(storage.get_path(rel)), title or file.filename or "", category)
    version = "1.0"
    d = Document(
        title=title or _strip_title_prefix(file.filename or "未命名"),
        category=category,
        version=version,
        file_path=rel,
        cloud_key=cloud_key,
        data=content if not cloud_key else None,  # COS 成功后不再存 BLOB
        original_filename=file.filename or "",
        uploader=user.full_name or user.username,
        status=status,
        description=description,
    )
    _apply_meta(d, meta)
    db.add(d)
    db.commit()
    db.refresh(d)
    dv = DocumentVersion(document_id=d.id, version=version, file_path=rel, uploader=d.uploader, note=note or "初始版本")
    _apply_meta(dv, meta)
    db.add(dv)
    db.commit()
    write_audit(db, user, "create", "documents", d.id, {"title": d.title, "category": category})
    _log_change(db, d, "新增", user.full_name or user.username)
    return d


@router.post("/{doc_id}/new-version", response_model=DocumentRead, response_model_exclude={"data"})
def new_version(
    doc_id: int,
    file: UploadFile = File(...),
    note: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "specialty_leader")),
):
    d = db.get(Document, doc_id)
    if not d:
        raise HTTPException(status_code=404, detail="未找到文件")
    content = file.file.read()
    rel = storage.save("docs", file.filename or d.title, content)
    # COS 上传
    cloud_key = None
    if cos_storage.ready:
        try:
            cloud_key = cos_storage.save("documents", file.filename or d.title or "file", content)
        except Exception:
            pass
    # 解析新文件头元数据，覆盖文档当前元数据（空白字段保留旧值）
    meta = parse_doc_metadata(str(storage.get_path(rel)), d.title or d.original_filename or "", d.category)
    _apply_meta(d, meta)
    try:
        maj, minor = str(d.version).split(".")
        new_ver = f"{maj}.{int(minor) + 1}"
    except Exception:
        new_ver = f"{d.version}.1"
    d.version = new_ver
    d.file_path = rel
    d.cloud_key = cloud_key
    d.data = content if not cloud_key else None
    d.original_filename = file.filename or d.original_filename
    d.updated_at = datetime.utcnow()
    dv = DocumentVersion(document_id=d.id, version=new_ver, file_path=rel,
                         cloud_key=cloud_key, data=content if not cloud_key else None,
                         uploader=user.full_name or user.username, note=note)
    _apply_meta(dv, meta)
    db.add(dv)
    db.commit()
    db.refresh(d)
    write_audit(db, user, "update", "documents", d.id, {"version": new_ver})
    _log_change(db, d, "修改", user.full_name or user.username)
    return d


@router.get("/{doc_id}/versions", response_model=list[DocumentVersionRead], response_model_exclude={"data"})
def list_versions(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return (
        db.query(DocumentVersion)
        .options(defer(DocumentVersion.data))
        .filter(DocumentVersion.document_id == doc_id)
        .order_by(DocumentVersion.id.desc())
        .all()
    )


def _content_disposition(disposition: str, filename: str) -> str:
    """生成带 RFC5987 UTF-8 文件名的内容处置头（中文名安全）。
    
    旧版 filename="..." 仅支持 ASCII，非 ASCII 回退为 "download"；
    真实文件名通过 RFC 5987 filename*=UTF-8''... 传递。
    """
    ascii_name = filename.encode("ascii", "ignore").decode("ascii") or "download"
    return f'{disposition}; filename="{ascii_name}"; filename*=UTF-8\'\'{quote(filename)}'


def _get_file_bytes(d) -> bytes | None:
    """从 COS → MySQL BLOB → 磁盘  顺序获取文件字节。"""
    # 1) COS 云存储
    if d.cloud_key and cos_storage.ready:
        content = cos_storage.get_bytes(d.cloud_key)
        if content:
            return content
    # 2) 遗留 MySQL LONGBLOB
    if d.data:
        return d.data
    # 3) 本地磁盘兜底
    if d.file_path:
        p = storage.get_path(d.file_path)
        if p.exists():
            return p.read_bytes()
    return None


@router.get("/{doc_id}/download")
def download(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    d = db.get(Document, doc_id)
    if not d:
        raise HTTPException(status_code=404, detail="未找到文件")
    fname = d.original_filename or f"doc-{doc_id}"

    # COS/BLOB/磁盘 → 经服务器返回（302 重定向到 COS 域名有浏览器 CORS 问题）
    content = _get_file_bytes(d)
    if not content:
        raise HTTPException(status_code=404, detail="文件不存在")
    return Response(
        content, media_type="application/octet-stream",
        headers={
            "Content-Disposition": _content_disposition("attachment", fname),
            "Cache-Control": "no-store",
        },
    )


@router.get("/{doc_id}/preview")
def preview(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    d = db.get(Document, doc_id)
    if not d:
        raise HTTPException(status_code=404, detail="未找到文件")
    fname = d.original_filename or f"doc-{doc_id}"
    content = _get_file_bytes(d)
    if not content:
        raise HTTPException(status_code=404, detail="文件不存在")

    src = d.file_path or fname
    suffix = src.rsplit(".", 1)[-1].lower() if "." in src else ""
    media = {
        "pdf": "application/pdf",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xls": "application/vnd.ms-excel",
    }.get(suffix)
    return Response(
        content, media_type=media,
        headers={
            "Content-Disposition": _content_disposition("inline", fname),
            "Cache-Control": "no-store",
        },
    )


@router.post("/_backfill_data_from_disk")
def backfill_data_from_disk(db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    """一次性迁移：把磁盘上现存的文件字节读入 MySQL LONGBLOB（data 列）。

    用于「文档字节从本地盘迁移到数据库」的过渡：部署新代码（已加 data 列）后调用一次，
    把当前仍在磁盘上的文件固化进 DB，从此与容器生命周期解耦。幂等：已写过的不重复写。
    磁盘已丢失的文件（data 保持 NULL）需用户重新上传。
    分批小事务提交，规避 wait_timeout / 大 BLOB 单包超时（2013 Lost connection）。
    """
    try:
        # net_write_timeout 已由 engine connect 事件全局放宽（CloudBase 默认 60s 易 2013）；
        # 此处再补一次，双保险。
        try:
            db.execute(text("SET SESSION net_write_timeout=28800"))
            db.execute(text("SET SESSION net_read_timeout=28800"))
        except Exception:  # noqa: BLE001
            pass
        doc_done = 0
        doc_skipped = 0
        ver_done = 0
        ver_skipped = 0
        ver_failed = []

        # 单会话 + 逐条提交 + 失败跳过：既不冲垮连接池，又能隔离单条大 BLOB 触发的
        # 代理 60s 断连（2013）——失败仅跳过该记录，不影响其余。
        docs = db.query(Document).all()
        for d in docs:
            if d.data is None and d.file_path:
                p = storage.get_path(d.file_path)
                if p.exists():
                    try:
                        d.data = p.read_bytes()
                        db.commit()
                        doc_done += 1
                    except Exception:  # noqa: BLE001
                        db.rollback()
                        doc_skipped += 1
                else:
                    doc_skipped += 1
            else:
                doc_skipped += 1

        vers = db.query(DocumentVersion).all()
        for v in vers:
            if v.data is None and v.file_path:
                p = storage.get_path(v.file_path)
                if p.exists():
                    try:
                        v.data = p.read_bytes()
                        db.commit()
                        ver_done += 1
                    except Exception:  # noqa: BLE001
                        db.rollback()
                        ver_failed.append(v.id)
                        ver_skipped += 1
                else:
                    ver_skipped += 1
            else:
                ver_skipped += 1

        return {
            "ok": True,
            "documents_written": doc_done,
            "documents_skipped": doc_skipped,
            "versions_written": ver_done,
            "versions_skipped": ver_skipped,
            "versions_failed": ver_failed[:50],
        }
    except Exception as e:  # noqa: BLE001
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            pass
        return {"ok": False, "error": str(e)[:500]}


@router.post("/_migrate_to_cos")
def migrate_to_cos(db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    """把 MySQL LONGBLOB（data 列）中的文件字节迁移到 COS 云存储。

    成功后：cloud_key 记 COS 对象键，data 置 NULL（释放 DB 内存）。
    已迁移的不重复。分批小事务，单条失败跳过不影响其余。
    """
    if not cos_storage.ready:
        raise HTTPException(status_code=400, detail="COS 云存储未配置，请先设置环境变量")
    try:
        doc_migrated = 0
        doc_skipped = 0
        doc_failed = 0
        ver_migrated = 0
        ver_skipped = 0
        ver_failed = 0
        doc_errs = []
        ver_errs = []

        # 分批 yield 处理 documents（一次性 all() 会撑爆内存）
        BATCH = 20
        doc_q = db.query(Document).filter(Document.data.isnot(None), Document.cloud_key.is_(None))
        for d in doc_q.yield_per(BATCH):
            try:
                key = cos_storage.save("documents", d.original_filename or f"doc-{d.id}", d.data)
                d.cloud_key = key
                d.data = None
                db.commit()
                doc_migrated += 1
            except Exception as e:
                db.rollback()
                db.refresh(d)  # 重新 attach，避免后续循环 stale
                doc_failed += 1
                if len(doc_errs) < 5:
                    doc_errs.append(f"doc#{d.id}: {type(e).__name__}: {str(e)[:200]}")
        doc_skipped = db.query(Document).filter(Document.cloud_key.isnot(None)).count()

        # 分批 yield 处理 versions
        ver_q = db.query(DocumentVersion).filter(DocumentVersion.data.isnot(None), DocumentVersion.cloud_key.is_(None))
        for v in ver_q.yield_per(BATCH):
            try:
                key = cos_storage.save("document_versions", f"v{v.id}", v.data)
                v.cloud_key = key
                v.data = None
                db.commit()
                ver_migrated += 1
            except Exception as e:
                db.rollback()
                db.refresh(v)
                ver_failed += 1
                if len(ver_errs) < 5:
                    ver_errs.append(f"ver#{v.id}: {type(e).__name__}: {str(e)[:200]}")
        ver_skipped = db.query(DocumentVersion).filter(DocumentVersion.cloud_key.isnot(None)).count()

        return {
            "ok": True,
            "documents_migrated": doc_migrated,
            "documents_already_in_cos": doc_skipped,
            "documents_failed": doc_failed,
            "versions_migrated": ver_migrated,
            "versions_already_in_cos": ver_skipped,
            "versions_failed": ver_failed,
            "sample_errors": doc_errs + ver_errs,
        }
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        return {"ok": False, "error": str(e)[:500]}


@router.delete("/{doc_id}")
def delete_document(
    doc_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "specialty_leader")),
):
    d = db.get(Document, doc_id)
    if not d:
        raise HTTPException(status_code=404, detail="未找到文件")
    # 记录作废日志（删除前捕获名称/编码）
    _log_change(db, d, "作废", user.full_name or user.username)
    if d.file_path:
        storage.delete(d.file_path)
    db.delete(d)
    db.commit()
    write_audit(db, user, "delete", "documents", doc_id, "", request.client.host if request.client else None)
    return {"ok": True}
