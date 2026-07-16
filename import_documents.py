"""
把本地四个文件夹的文档批量导入新系统"文件管理"模块。
- 只读取源文件、复制到 data/uploads/docs/，绝不修改源文件。
- 复刻 backend/app/core/storage.py 的 save 逻辑（文件名安全化 + 同名加 _n）。
- 写 documents + document_versions 两表；同 (category, original_filename) 已存在则跳过（可重跑）。
- 分类映射：仪器作业指导书->仪器SOP，记录表格->记录表格，通用作业指导书->通用SOP，项目作业指导书->项目SOP。
"""
import os, re, sqlite3, shutil, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(ROOT, "data", "app.db")
UPLOADS = os.path.join(ROOT, "data", "uploads", "docs")

FOLDERS = {
    "仪器SOP": r"D:\民航总医院\生免组管理体系文件\生免组仪器作业指导书",
    "记录表格": r"D:\民航总医院\生免组管理体系文件\生免组记录表格",
    "通用SOP": r"D:\民航总医院\生免组管理体系文件\生免组通用作业指导书",
    "项目SOP": r"D:\民航总医院\生免组管理体系文件\生免组项目作业指导书",
}
VALID = {"通用SOP", "项目SOP", "仪器SOP", "记录表格", "项目说明书"}


def safe_filename(name):
    name = (name or "file").strip()
    name = re.sub(r'[^\w\u4e00-\u9fff\.\-]', '_', name)
    return name or "file"


def unique_path(directory, safe_name):
    os.makedirs(directory, exist_ok=True)
    stem, ext = os.path.splitext(safe_name)
    target = os.path.join(directory, safe_name)
    n = 1
    while os.path.exists(target):
        target = os.path.join(directory, f"{stem}_{n}{ext}")
        n += 1
    return target


def main():
    # 备份
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(DB, DB + f".bak_{ts}")
    print(f"[备份] {os.path.basename(DB)} -> .bak_{ts}")

    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys=OFF")
    cur = con.cursor()

    stats = {c: {"ok": 0, "skip": 0, "err": 0} for c in FOLDERS}
    for cat, root in FOLDERS.items():
        if cat not in VALID:
            print("!! 非法分类跳过:", cat); continue
        if not os.path.isdir(root):
            print("!! 源文件夹不存在:", root); continue
        print(f"\n=== 处理 {cat}: {root} ===")
        for dp, dn, fns in os.walk(root):
            for fn in fns:
                src = os.path.join(dp, fn)
                rel = os.path.relpath(src, root)
                try:
                    with open(src, "rb") as fh:
                        content = fh.read()
                    if not content:
                        stats[cat]["err"] += 1
                        print("  跳过(空文件):", rel)
                        continue
                    # 去重检查：同分类+同名+磁盘文件大小一致 才视为重复（同名不同内容的两份都保留）
                    cur.execute(
                        "SELECT file_path FROM documents WHERE category=? AND original_filename=?",
                        (cat, fn),
                    )
                    dup = False
                    for (fp,) in cur.fetchall():
                        disk = os.path.join(ROOT, "data", "uploads", fp)
                        if os.path.exists(disk) and os.path.getsize(disk) == len(content):
                            dup = True
                            break
                    if dup:
                        stats[cat]["skip"] += 1
                        continue
                    # 复刻 storage.save("docs", fn, content)
                    target = unique_path(UPLOADS, safe_filename(fn))
                    with open(target, "wb") as out:
                        out.write(content)
                    rel_path = "docs/" + os.path.basename(target)
                    cur.execute(
                        """INSERT INTO documents
                           (title, category, version, file_path, original_filename, uploader, status, description, parent_id, created_at, updated_at)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                        (fn, cat, "1.0", rel_path, fn, "系统导入", "生效",
                         f"{os.path.basename(root)}/{rel}", None,
                         datetime.datetime.utcnow(), datetime.datetime.utcnow()),
                    )
                    did = cur.lastrowid
                    cur.execute(
                        """INSERT INTO document_versions
                           (document_id, version, file_path, uploader, note, created_at)
                           VALUES (?,?,?,?,?,?)""",
                        (did, "1.0", rel_path, "系统导入", "批量导入初始版本", datetime.datetime.utcnow()),
                    )
                    stats[cat]["ok"] += 1
                except Exception as e:
                    stats[cat]["err"] += 1
                    print(f"  !! 错误 {rel}: {e}")
    con.commit()
    con.close()
    print("\n===== 导入汇总 =====")
    tot_ok = tot_skip = tot_err = 0
    for c, s in stats.items():
        print(f"  {c}: 新增 {s['ok']} | 跳过(已存在) {s['skip']} | 错误 {s['err']}")
        tot_ok += s["ok"]; tot_skip += s["skip"]; tot_err += s["err"]
    print(f"  合计: 新增 {tot_ok} | 跳过 {tot_skip} | 错误 {tot_err}")


if __name__ == "__main__":
    main()
