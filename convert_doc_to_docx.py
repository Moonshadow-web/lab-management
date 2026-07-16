"""批量把 uploads/docs 下的 .doc 文件转换为 .docx（Word COM 驱动）。

- 转换成功后删除原 .doc
- 同步更新数据库 documents 表的 file_path / original_filename（扩展名 .doc -> .docx）
- 每个文件转换前检查磁盘存在性；转换失败保留原文件并记录
- 数据库已先行备份（data/app.db.bak_20260711_042530）
"""
import os
import sqlite3
import win32com.client

BASE = r"D:\workbuddyprojects\网页版-生免速查工具"
UPLOAD_ROOT = os.path.join(BASE, "data", "uploads")
DB = os.path.join(BASE, "data", "app.db")

WD_FORMAT_XML = 16  # wdFormatXMLDocument


def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, file_path, original_filename FROM documents "
        "WHERE file_path LIKE '%.doc' AND file_path NOT LIKE '%.docx'"
    ).fetchall()
    print(f"待转换 .doc 文件数: {len(rows)}")

    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0

    ok = 0
    fail = 0
    try:
        for r in rows:
            src = os.path.join(UPLOAD_ROOT, r["file_path"])
            if not os.path.exists(src):
                print(f"  [跳过] 磁盘文件不存在: {r['file_path']}")
                fail += 1
                continue
            dst = src[:-4] + ".docx"
            try:
                doc = word.Documents.Open(src)
                doc.SaveAs(dst, WD_FORMAT_XML)
                doc.Close()
                # 转换成功再删原文件
                os.remove(src)
                new_fp = r["file_path"][:-4] + ".docx"
                new_of = (r["original_filename"] or "")[:-4] + ".docx"
                conn.execute(
                    "UPDATE documents SET file_path=?, original_filename=? WHERE id=?",
                    (new_fp, new_of, r["id"]),
                )
                ok += 1
                print(f"  [OK] {os.path.basename(src)} -> {os.path.basename(dst)}")
            except Exception as e:
                print(f"  [失败] {r['file_path']}: {e}")
                fail += 1
    finally:
        word.Quit()
        conn.commit()
        conn.close()

    print(f"转换完成：成功 {ok}，失败 {fail}")


if __name__ == "__main__":
    main()
