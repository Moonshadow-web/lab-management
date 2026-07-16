"""回填已有文档的文件头元数据。

遍历 data/uploads/docs 下所有 .docx，解析表头元数据，写回 documents 表
（及该文档最新一条 document_versions 记录），便于前端展示与版本追溯。

仅写入解析到的非空字段；不解析的文档（记录表格/PDF/旧版 .doc）保持不变。
可重复执行（幂等）。
"""
import os
import sys

sys.path.insert(0, "backend")

from app.core.database import SessionLocal
from app.core.storage import storage
from app.core.docmeta import parse_doc_metadata
from app.models.document import Document, DocumentVersion

META_FIELDS = [
    "doc_number", "doc_version", "revision", "author", "reviewer",
    "approver", "issued_date", "audit_date", "approve_date",
    "effective_date", "meta_raw",
]


def _clear_meta(d, db) -> bool:
    """清空文档及其最新版本记录的全部元数据字段（仅在有残留时返回 True）。"""
    changed = False
    for k in META_FIELDS:
        if getattr(d, k, ""):
            setattr(d, k, "")
            changed = True
    if changed:
        latest = (
            db.query(DocumentVersion)
            .filter(DocumentVersion.document_id == d.id)
            .order_by(DocumentVersion.id.desc())
            .first()
        )
        if latest:
            for k in META_FIELDS:
                if getattr(latest, k, ""):
                    setattr(latest, k, "")
    return changed


def main():
    db = SessionLocal()
    docs = db.query(Document).all()
    updated = 0
    cleared = 0
    skipped = 0
    for d in docs:
        if not d.file_path:
            skipped += 1
            continue
        # 对 .doc/.docx 都走 parse_doc_metadata：
        # - .docx：解析表头；无编号时用文件名兜底
        # - .doc：python-docx 无法读内容，文件名兜底提取编号
        # - .xlsx/.pdf 等：解析器会返回 {}，触发清空
        path = storage.get_path(d.file_path)
        if not path.exists():
            skipped += 1
            continue
        meta = parse_doc_metadata(str(path), d.title or "", d.category)
        if not meta:
            # 无元数据：清空可能残留的弱字段（保持干净）
            if _clear_meta(d, db):
                cleared += 1
            continue
        changed = False
        for k in META_FIELDS:
            v = meta.get(k)
            if v and getattr(d, k, "") != v:
                setattr(d, k, v)
                changed = True
        if changed:
            latest = (
                db.query(DocumentVersion)
                .filter(DocumentVersion.document_id == d.id)
                .order_by(DocumentVersion.id.desc())
                .first()
            )
            if latest:
                for k in META_FIELDS:
                    v = meta.get(k)
                    if v:
                        setattr(latest, k, v)
            updated += 1
    db.commit()
    db.close()
    print(f"[完成] 更新文档数={updated} | 跳过(无docx/无元数据)={skipped}")


if __name__ == "__main__":
    main()
