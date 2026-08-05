"""把 `D:\\民航总医院\\15189\\15189规范文件` 目录下的规范文件补充进系统 cnas_standards 模块，
并按内容归入三类：CNAS认可规范 / CNAS附件表 / 行标。

分类规则（按文件名）：
  - 含「附表」「附件」「认可合同」           → CNAS附件表
  - 含 WS/T（行标）                        → 行标
  - 其余（CNAS 准则/指南/规则/应用说明/申请书及填写指南）→ CNAS认可规范

文件代号(code)取文件名前导英文段；名称(name)取其后中文段。
按 original_filename 幂等（已存在则跳过）。

默认 DRY_RUN；APPLY=1 执行。
"""
import os
import re
import sys

import requests

BASE = "http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com/api/v1"
SRC_DIR = r"D:\民航总医院\15189\15189规范文件"

APPLY = os.environ.get("APPLY") == "1"

SKIP_NAMES = ("thumbs.db",)
CODE_HEAD = re.compile(r"^([A-Za-z0-9][A-Za-z0-9\-:]*)[　\s：:]*\d*")
NAME_TAIL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\-:]*[　\s：:]*\d*")


def classify(base: str):
    """返回 (category, code, name)。"""
    if ("ws" in base.lower()) and ("t" in base.lower()):
        category = "行标"
    elif any(k in base for k in ("附表", "附件", "认可合同")):
        category = "CNAS附件表"
    else:
        category = "CNAS认可规范"
    m = CODE_HEAD.match(base)
    code = m.group(1) if m else ""
    name = NAME_TAIL.sub("", base).strip() or base
    return category, code, name


def collect():
    items = []
    for root, _dirs, files in os.walk(SRC_DIR):
        for fn in files:
            low = fn.lower()
            if low in SKIP_NAMES or fn.startswith("~$"):
                continue
            if not low.endswith((".pdf", ".doc", ".docx")):
                continue
            base = os.path.splitext(fn)[0]
            category, code, name = classify(base)
            items.append({
                "path": os.path.join(root, fn),
                "filename": fn,
                "category": category,
                "code": code,
                "name": name,
            })
    # 稳定排序：同类按文件名
    items.sort(key=lambda x: (x["category"], x["filename"]))
    # 分配 sort_order：CNAS认可规范 100+，CNAS附件表 200+
    counters = {}
    for it in items:
        base_no = 100 if it["category"] == "CNAS认可规范" else 200
        counters[it["category"]] = counters.get(it["category"], base_no - 1) + 1
        it["sort_order"] = counters[it["category"]]
    return items


def main():
    items = collect()
    if not items:
        print("[ERROR] 未找到任何文件")
        sys.exit(1)

    r = requests.post(BASE + "/auth/login", data={"username": "jinzizheng", "password": "Jzz6827556"}, timeout=120)
    tok = r.json()["access_token"]
    H = {"Authorization": f"Bearer {tok}"}
    existing = requests.get(BASE + "/cnas-standards", headers=H, timeout=120).json()
    existing_names = {os.path.basename(e["original_filename"]) for e in existing}

    added, skipped, failed = [], [], []
    for it in items:
        print(f"[{it['category']:>10}] {it['filename']}  code={it['code']!r} name={it['name'][:24]!r}")
        if it["filename"] in existing_names:
            skipped.append(it["filename"])
            print("      -> 已存在，跳过")
            continue
        if not APPLY:
            continue
        with open(it["path"], "rb") as f:
            files = {"file": (it["filename"], f, "application/octet-stream")}
            data = {
                "code": it["code"], "name": it["name"],
                "category": it["category"], "sort_order": it["sort_order"],
            }
            rr = requests.post(BASE + "/cnas-standards/upload", files=files, data=data, headers=H, timeout=300)
        if rr.status_code >= 300:
            failed.append((it["filename"], rr.status_code, rr.text[:120]))
            print(f"      -> 失败 {rr.status_code} {rr.text[:120]}")
        else:
            added.append(it["filename"])
            print("      -> 已上传")

    print(f"\n统计: 新增={len(added)}  跳过(已存在)={len(skipped)}  失败={len(failed)}")
    if failed:
        print("失败明细:")
        for fn, st, msg in failed:
            print(f"  {fn} [{st}] {msg}")
    if not APPLY:
        print("\n[DRY_RUN] 未实际写入。APPLY=1 以执行。")


if __name__ == "__main__":
    main()
