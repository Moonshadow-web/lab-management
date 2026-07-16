"""一次性脚本：把现有仪器档案中的 .doc 文件转换为 .docx（Word COM）。

- 转换成功后删除原 .doc，写入 .docx，并更新数据库 filename / file_ext / original_filename
- 转换失败则保留原文件并在末尾列出
- 运行前请先备份 data/app.db（脚本不自动备份）

用法（后端 venv）：
    backend/venv/Scripts/python.exe backend/scripts/convert_archives_doc_to_docx.py
"""
import os
import sys

BACKEND = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.abspath(BACKEND))

from app.core.database import SessionLocal  # noqa: E402
from app.core.storage import storage  # noqa: E402
from app.models.instrument_archive import InstrumentArchive  # noqa: E402
from app.core.doc_convert import convert_doc_bytes_to_docx  # noqa: E402


def main():
    db = SessionLocal()
    recs = db.query(InstrumentArchive).filter(InstrumentArchive.file_ext == ".doc").all()
    print(f"待转换 .doc 档案: {len(recs)}")
    ok = 0
    fail = []
    for rec in recs:
        p = storage.get_path(rec.filename)
        if not p.exists():
            print(f"  [跳过] 文件缺失: {rec.filename}")
            fail.append(rec.filename)
            continue
        content = p.read_bytes()
        converted = convert_doc_bytes_to_docx(content)
        if not converted:
            print(f"  [失败] 转换错误: {rec.filename}")
            fail.append(rec.filename)
            continue
        storage.delete(rec.filename)
        stem = os.path.splitext(os.path.basename(rec.filename))[0]
        new_rel = storage.save("instrument_archives", stem + ".docx", converted)
        rec.filename = new_rel
        rec.file_ext = ".docx"
        if rec.original_filename:
            rec.original_filename = os.path.splitext(rec.original_filename)[0] + ".docx"
        db.commit()
        ok += 1
        print(f"  [完成] {new_rel} ({len(converted)} bytes)")
    print(f"\n转换完成：成功 {ok}，失败 {len(fail)}")
    for f in fail:
        print(f"  失败: {f}")
    db.close()


if __name__ == "__main__":
    main()
