from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ...core.crud_base import paginate, write_audit
from ...core.database import get_db
from ...core.security import get_current_user
from ...core.storage import storage
from ...models.document import Document, DocumentVersion, DOC_CATEGORIES
from ...models.user import User
from ...schemas import DocumentRead, DocumentVersionRead

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("")
def list_documents(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    q: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    params = dict(request.query_params)
    query = db.query(Document)
    if q:
        query = query.filter(Document.title.ilike(f"%{q}%") | Document.original_filename.ilike(f"%{q}%"))
    cat = params.get("category")
    if cat:
        query = query.filter(Document.category == cat)
    query = query.order_by(Document.id.desc())
    return paginate(query, page, page_size)


@router.get("/{doc_id}", response_model=DocumentRead)
def get_document(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    d = db.get(Document, doc_id)
    if not d:
        raise HTTPException(status_code=404, detail="未找到文件")
    return d


@router.post("/upload", response_model=DocumentRead, status_code=201)
def upload_document(
    file: UploadFile = File(...),
    title: str = Form(""),
    category: str = Form("通用SOP"),
    note: str = Form(""),
    status: str = Form("生效"),
    description: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if category not in DOC_CATEGORIES:
        raise HTTPException(status_code=400, detail="文件分类不合法")
    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空")
    rel = storage.save("docs", file.filename or title or "file", content)
    version = "1.0"
    d = Document(
        title=title or (file.filename or "未命名"),
        category=category,
        version=version,
        file_path=rel,
        original_filename=file.filename or "",
        uploader=user.full_name or user.username,
        status=status,
        description=description,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    db.add(DocumentVersion(document_id=d.id, version=version, file_path=rel, uploader=d.uploader, note=note or "初始版本"))
    db.commit()
    write_audit(db, user, "create", "documents", d.id, {"title": d.title, "category": category})
    return d


@router.post("/{doc_id}/new-version", response_model=DocumentRead)
def new_version(
    doc_id: int,
    file: UploadFile = File(...),
    note: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    d = db.get(Document, doc_id)
    if not d:
        raise HTTPException(status_code=404, detail="未找到文件")
    content = file.file.read()
    rel = storage.save("docs", file.filename or d.title, content)
    try:
        maj, minor = str(d.version).split(".")
        new_ver = f"{maj}.{int(minor) + 1}"
    except Exception:
        new_ver = f"{d.version}.1"
    d.version = new_ver
    d.file_path = rel
    d.original_filename = file.filename or d.original_filename
    d.updated_at = datetime.utcnow()
    db.add(DocumentVersion(document_id=d.id, version=new_ver, file_path=rel, uploader=user.full_name or user.username, note=note))
    db.commit()
    db.refresh(d)
    write_audit(db, user, "update", "documents", d.id, {"version": new_ver})
    return d


@router.get("/{doc_id}/versions", response_model=list[DocumentVersionRead])
def list_versions(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return (
        db.query(DocumentVersion)
        .filter(DocumentVersion.document_id == doc_id)
        .order_by(DocumentVersion.id.desc())
        .all()
    )


@router.get("/{doc_id}/download")
def download(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    d = db.get(Document, doc_id)
    if not d or not d.file_path:
        raise HTTPException(status_code=404, detail="未找到文件")
    p = storage.get_path(d.file_path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(p, filename=d.original_filename or p.name)


@router.get("/{doc_id}/preview")
def preview(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    d = db.get(Document, doc_id)
    if not d or not d.file_path:
        raise HTTPException(status_code=404, detail="未找到文件")
    p = storage.get_path(d.file_path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    media = "application/pdf" if p.suffix.lower() == ".pdf" else None
    return FileResponse(p, media_type=media, filename=d.original_filename or p.name)


@router.delete("/{doc_id}")
def delete_document(
    doc_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    d = db.get(Document, doc_id)
    if not d:
        raise HTTPException(status_code=404, detail="未找到文件")
    if d.file_path:
        storage.delete(d.file_path)
    db.delete(d)
    db.commit()
    write_audit(db, user, "delete", "documents", doc_id, "", request.client.host if request.client else None)
    return {"ok": True}
