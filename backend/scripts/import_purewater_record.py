# -*- coding: utf-8 -*-
"""将纯水机的「操作+保养记录」BG-SM-CZ-001(.doc) 导入文件管理，并关联到纯水机仪器。

- 源文件为 OLE2 .doc，经 doc_convert 转成 .docx 以便浏览器内预览；
- doc_number 不存在 → 新增到「记录表格」；存在 → 走新版本更新；
- 建立 document_instruments 关联（仅关联纯水机 id=27，幂等：先清再加）。

在 backend 目录用 venv python 运行：
    venv/Scripts/python -m scripts.import_purewater_record
"""
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.storage import storage  # noqa: E402
from app.core.doc_convert import convert_doc_bytes_to_docx  # noqa: E402
from app.models import (  # noqa: E402
    Document,
    DocumentVersion,
    DocumentInstrument,
    FileChangeLog,
)

SRC = r"D:/民航总医院/生免组管理体系文件/（新）质控总结+仪器操作+保养记录/（新）质控总结+仪器操作+保养记录/BG-SM-CZ-001-生化免疫组纯水机使用监测记录表.doc"
DOC_NUMBER = "BG-SM-CZ-001"
INSTRUMENT_ID = 27  # 纯水机A/B/C


def title_from_filename(fn: str) -> str:
    stem = re.sub(r"\.[a-zA-Z0-9]+$", "", fn)
    stem = re.sub(r"^BG-SM-CZ-\d+-", "", stem).strip()
    return stem


def bump_version(v: str) -> str:
    try:
        maj, minor = str(v).split(".")
        return f"{maj}.{int(minor) + 1}"
    except Exception:
        return f"{v}.1"


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    now = datetime.now()
    try:
        with open(SRC, "rb") as f:
            content = f.read()

        # 转 docx（OLE2 -> 真 docx），失败则保留原 .doc
        converted = convert_doc_bytes_to_docx(content)
        if converted:
            content = converted
            ext = ".docx"
            print("[ok] .doc 已转换为 .docx")
        else:
            ext = ".doc"
            print("[WARN] .doc 转换失败，按原格式写入（预览将回退下载）")

        fn = f"BG-SM-CZ-001-生化免疫组纯水机使用监测记录表{ext}"
        title = title_from_filename(fn)
        rel = storage.save("docs", fn, content)

        d = db.query(Document).filter(Document.doc_number == DOC_NUMBER).first()
        if d:  # 已存在 → 新版本
            new_ver = bump_version(d.version or "1.0")
            d.version = new_ver
            d.file_path = rel
            d.original_filename = fn
            d.title = title
            d.status = d.status or "生效"
            d.updated_at = now
            db.add(DocumentVersion(
                document_id=d.id, version=new_ver, file_path=rel,
                uploader="系统导入", note="更新操作+保养记录",
            ))
            db.add(FileChangeLog(
                doc_id=d.id, file_name=d.title, file_code=DOC_NUMBER,
                change_type="修改", operator="系统导入", change_date=now.date(),
            ))
            db.commit()
            db.refresh(d)
            print("新版本:", d.id, new_ver, title)
        else:  # 新增
            d = Document(
                title=title, category="记录表格", version="1.0",
                file_path=rel, original_filename=fn, uploader="系统导入",
                status="生效", description="", doc_number=DOC_NUMBER,
            )
            db.add(d)
            db.commit()
            db.refresh(d)
            db.add(DocumentVersion(
                document_id=d.id, version="1.0", file_path=rel,
                uploader="系统导入", note="初始版本",
            ))
            db.add(FileChangeLog(
                doc_id=d.id, file_name=d.title, file_code=DOC_NUMBER,
                change_type="新增", operator="系统导入", change_date=now.date(),
            ))
            db.commit()
            db.refresh(d)
            print("新增:", d.id, title)

        # 关联纯水机（幂等）
        db.query(DocumentInstrument).filter(
            DocumentInstrument.document_id == d.id
        ).delete()
        db.add(DocumentInstrument(document_id=d.id, instrument_id=INSTRUMENT_ID))
        db.commit()
        print(f"已关联仪器 id={INSTRUMENT_ID}（纯水机A/B/C）")
    finally:
        db.close()


if __name__ == "__main__":
    main()
