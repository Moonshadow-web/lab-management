# -*- coding: utf-8 -*-
"""一次性导入「操作+保养记录」docx 到文件管理，并建立文档↔仪器关联。

规则：
- 编号已存在(BG-SM-CZ-051~070) → 走「新版本」保留历史，更新 file_path/version/
  original_filename/title；
- 编号不存在(078/079/080) → 新增到「记录表格」分类；
- 按 curated 映射写入 document_instruments（幂等：先清掉这些文档的旧关联再插）。

在 backend 目录用 venv python 运行：
    venv/Scripts/python -m scripts.import_operation_records
"""
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.storage import storage  # noqa: E402
from app.models import (  # noqa: E402
    Document,
    DocumentVersion,
    DocumentInstrument,
    FileChangeLog,
)

SRC_DIR = r"D:/民航总医院/生免组管理体系文件/（新）质控总结+仪器操作+保养记录/（新）质控总结+仪器操作+保养记录"

# 编号 -> (源文件名, [关联仪器 id...])  —— 仪器 id 依据真实库 instruments 表
PLAN = {
    "BG-SM-CZ-051": ("BG-SM-CZ-051-贝克曼流水线+贝克曼AU5822A 操作记录.docx", [66, 67]),
    "BG-SM-CZ-052": ("BG-SM-CZ-052-贝克曼DXI800 1+2操作记录+保养.docx", [69, 70]),
    "BG-SM-CZ-053": ("BG-SM-CZ-053-贝克曼AU5800急诊保养+操作记录.docx", [5]),
    "BG-SM-CZ-054": ("BG-SM-CZ-054-贝克曼DXI800急诊操作记录+保养.docx", [73]),
    "BG-SM-CZ-055": ("BG-SM-CZ-055-贝克曼DXI800唐筛操作记录+保养.docx", [74]),
    "BG-SM-CZ-056": ("BG-SM-CZ-056-凝血流水线+TOP700A+B操作记录 +保养.docx", [8, 9, 10]),
    "BG-SM-CZ-057": ("BG-SM-CZ-057-沃芬TOP700C操作记录 +保养.docx", [11]),
    "BG-SM-CZ-058": ("BG-SM-CZ-058-日立HT7600操作+保养记录.docx", [12]),
    "BG-SM-CZ-059": ("BG-SM-CZ-059-西门子Rapidpoint1+2操作记录+保养.docx", [13, 21]),
    "BG-SM-CZ-060": ("BG-SM-CZ-060-罗氏e601操作记录+保养.docx", [14]),
    "BG-SM-CZ-061": ("BG-SM-CZ-061-罗氏e602操作记录+保养.docx", [15]),
    "BG-SM-CZ-062": ("BG-SM-CZ-062-罗氏e411操作记录+保养.docx", [16]),
    "BG-SM-CZ-063": ("BG-SM-CZ-063-安图A6200+A2000操作+保养记录.docx", [75, 17, 22]),
    "BG-SM-CZ-064": ("BG-SM-CZ-064-爱康酶标仪操作+保养记录.docx", [23]),
    "BG-SM-CZ-065": ("BG-SM-CZ-065-迈瑞CL-6000i操作+保养记录.docx", [18]),
    "BG-SM-CZ-066": ("BG-SM-CZ-066-糖化G8操作+保养记录.docx", [19]),
    "BG-SM-CZ-067": ("BG-SM-CZ-067-血氨操作记录+保养.docx", [20]),
    "BG-SM-CZ-068": ("BG-SM-CZ-068-Sebia毛细管电泳仪操作+保养记录.docx", [24]),
    "BG-SM-CZ-069": ("BG-SM-CZ-069-Sebia凝胶电泳仪操作+保养记录.docx", [25]),
    "BG-SM-CZ-070": ("BG-SM-CZ-070-Stago操作记录 +保养.docx", [26]),
    "BG-SM-CZ-078": ("BG-SM-CZ-078-贝克曼流水线+贝克曼AU5822B操作记录.docx", [66, 68]),
    "BG-SM-CZ-079": ("BG-SM-CZ-079-贝克曼DXI800 3操作记录+保养.docx", [71]),
    "BG-SM-CZ-080": ("BG-SM-CZ-080-贝克曼DXI800 4操作记录+保养.docx", [72]),
}


def title_from_filename(fn: str) -> str:
    """BG-SM-CZ-058-日立HT7600操作+保养记录.docx -> 日立HT7600操作+保养记录"""
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
    Base.metadata.create_all(bind=engine)  # 建 document_instruments 等缺失表
    db = SessionLocal()
    now = datetime.now()
    added, versioned, skipped_missing = [], [], []
    doc_id_by_number = {}
    try:
        for number, (fn, inst_ids) in PLAN.items():
            src = os.path.join(SRC_DIR, fn)
            if not os.path.exists(src):
                skipped_missing.append((number, fn))
                continue
            with open(src, "rb") as f:
                content = f.read()
            if content[:2] != b"PK":
                # 非真 docx（可能是伪 docx/OLE2），本批已确认全为 PK，此处仅保护
                print(f"[WARN] {number} 非真docx(magic={content[:4]!r})，仍原样写入")
            title = title_from_filename(fn)
            rel = storage.save("docs", fn, content)

            d = db.query(Document).filter(Document.doc_number == number).first()
            if d:  # 已存在 → 新版本
                new_ver = bump_version(d.version or "1.0")
                d.version = new_ver
                d.file_path = rel
                d.original_filename = fn
                d.title = title
                d.status = d.status or "生效"
                d.updated_at = now
                dv = DocumentVersion(
                    document_id=d.id, version=new_ver, file_path=rel,
                    uploader="系统导入", note="更新操作+保养记录",
                )
                db.add(dv)
                db.add(FileChangeLog(
                    doc_id=d.id, file_name=d.title, file_code=number,
                    change_type="修改", operator="系统导入", change_date=now.date(),
                ))
                db.commit()
                db.refresh(d)
                versioned.append((number, d.id, title))
            else:  # 新增
                d = Document(
                    title=title, category="记录表格", version="1.0",
                    file_path=rel, original_filename=fn, uploader="系统导入",
                    status="生效", description="", doc_number=number,
                )
                db.add(d)
                db.commit()
                db.refresh(d)
                dv = DocumentVersion(
                    document_id=d.id, version="1.0", file_path=rel,
                    uploader="系统导入", note="初始版本",
                )
                db.add(dv)
                db.add(FileChangeLog(
                    doc_id=d.id, file_name=d.title, file_code=number,
                    change_type="新增", operator="系统导入", change_date=now.date(),
                ))
                db.commit()
                db.refresh(d)
                added.append((number, d.id, title))

            doc_id_by_number[number] = d.id

            # 重建关联（幂等）
            db.query(DocumentInstrument).filter(
                DocumentInstrument.document_id == d.id
            ).delete()
            for iid in inst_ids:
                db.add(DocumentInstrument(document_id=d.id, instrument_id=iid))
            db.commit()

        print("=== 新增(new) ===")
        for x in added:
            print("  ", x)
        print("=== 新版本(versioned) ===")
        for x in versioned:
            print("  ", x)
        if skipped_missing:
            print("=== 源文件缺失(skipped) ===")
            for x in skipped_missing:
                print("  ", x)

        # 汇总关联
        print("=== document_instruments 关联汇总 ===")
        rows = db.execute(
            __import__("sqlalchemy").text(
                "SELECT di.instrument_id, COUNT(*) FROM document_instruments di GROUP BY di.instrument_id ORDER BY di.instrument_id"
            )
        ).fetchall()
        total = db.query(DocumentInstrument).count()
        print("  关联行总数:", total, " 涉及仪器数:", len(rows))
    finally:
        db.close()


if __name__ == "__main__":
    main()
