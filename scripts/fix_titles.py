"""修复系统文件档案里被截断的 SOP 标题。

根因：上传时标题取自 docx 正文"第一段"(first_title)，但这些 SOP 的大标题
是分多段写的（如「AU5800检测系统免疫透射比浊法」+「血清载脂蛋白B测定标准
操作程序」），python-docx 只读了第一段，导致标题被截断。

修复：从 docx 重新拼接完整标题——收集开头连续段落，直到遇到「1 承担部门」
或数字开头的段落（正文起始）为止，拼接即为完整标题。按 doc_number 匹配系统
记录后 PATCH 标题。默认 DRY_RUN；APPLY=1 执行。
"""
import os, re, sys
import requests
from docx import Document

BASE = "http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com/api/v1"
FOLDERS = [
    r"C:/Users/81526/Desktop/待办/AU5800",
    r"C:/Users/81526/Desktop/待办/DXI",
    r"C:/Users/81526/Desktop/待办/安图",
]
NUM_RE = re.compile(r"SM-SOP-(\d+)")
PREFIX_RE = re.compile(r"^(MHZYY-JYK-|HZYY-JYK-)")
INSTR = [
    "安图AutoLumoA6200检测系统", "安图AutolumoA2000检测系统",
    "贝克曼DXI800检测系统", "AU5800检测系统",
    "迈瑞CL-6000i检测系统", "罗氏Cobas检测系统",
]

TITLE_SUFFIXES = ("测定标准操作程序", "标准操作程序", "操作作业指导书", "操作程序")
BODY_KEYWORDS = ("原理", "性能参数", "标本", "样本", "试剂", "校准", "质控", "分析原",
                 "检验目的", "检测目的", "检查目的", "承担部门")


def doc_full_title(path):
    """拼接 docx 开头的完整大标题：收集开头连续段落，直到遇到正文起始
    （以数字开头，或「检验目的/检测目的/检查目的/承担部门」）为止。"""
    try:
        doc = Document(path)
    except Exception:
        return ""
    parts = []
    for p in doc.paragraphs:
        t = p.text.strip()
        if not t:
            if parts:
                break  # 标题与正文之间的空行
            continue
        if re.match(r"^\d", t) or t.startswith(("检验目的", "检测目的", "检查目的", "承担部门")):
            break
        parts.append(t)
    return "".join(parts)


def best_title(path, stem):
    """优先用 docx 拼接的完整标题（保留正文具体方法写法）；若拼接结果
    被截断或吞入正文，则回退到文件名（保证完整）。"""
    r = doc_full_title(path)
    clean = r.endswith(TITLE_SUFFIXES) and not any(k in r for k in BODY_KEYWORDS)
    return r if clean else stem


def stem_title(fn):
    base = os.path.splitext(fn)[0]
    return re.sub(r"^SM-SOP-\d+\s*[-—]?\s*", "", base).strip().rstrip("- ").strip()


def title_core(t):
    t = re.sub(r"^SM-SOP-\d+\s*[-—]?\s*", "", t or "")
    for p in INSTR:
        t = t.replace(p, "")
    t = t.replace(" 沃文特", "").strip()
    t = re.sub(r"(测定标准操作程序|标准操作程序|操作程序)$", "", t).strip()
    return t.replace("（", "(").replace("）", ")").replace(" ", "").lower()


def login():
    r = requests.post(BASE + "/auth/login",
                      data={"username": "jinzizheng", "password": "Jzz6827556"},
                      timeout=120)
    r.raise_for_status()
    return r.json()["access_token"]


def fetch_all_docs(tok):
    out, page = [], 1
    while True:
        r = requests.get(BASE + "/documents", params={"page": page, "page_size": 200},
                         headers={"Authorization": f"Bearer {tok}"}, timeout=120)
        r.raise_for_status()
        j = r.json()
        items = j.get("items", [])
        out.extend(items)
        if page * 200 >= j.get("total", 0) or not items:
            break
        page += 1
    return out


def main():
    apply = os.environ.get("APPLY") == "1"
    tok = login()
    docs = fetch_all_docs(tok)
    by_norm, by_core = {}, {}
    for it in docs:
        dn = (it.get("doc_number") or "").strip()
        norm = PREFIX_RE.sub("", dn).strip()
        if norm:
            by_norm.setdefault(norm, []).append(it)
        core = title_core(it.get("title") or "")
        if core:
            by_core.setdefault(core, []).append(it)

    plan = []
    for folder in FOLDERS:
        for fn in sorted(os.listdir(folder)):
            if not fn.lower().endswith(".docx") or fn.startswith("~$"):
                continue
            m = NUM_RE.search(fn)
            if not m:
                continue
            N = "SM-SOP-" + m.group(1)
            full = "MHZYY-JYK-" + N
            new_title = best_title(os.path.join(folder, fn), stem_title(fn))
            cands = by_norm.get(N, [])
            target = None
            if len(cands) == 1:
                target = cands[0]
            elif len(cands) == 0:
                ch = [c for c in by_core.get(title_core(stem_title(fn)), []) if c.get("doc_number", "").strip()]
                if len(ch) == 1:
                    target = ch[0]
            else:
                pick = [c for c in cands if title_core(c.get("title") or "") == title_core(stem_title(fn))]
                if len(pick) == 1:
                    target = pick[0]
            plan.append((N, full, new_title, target))

    print(f"=== DRY_RUN={not apply}  本地={len(plan)}  系统={len(docs)} ===\n")
    changes, skipped, nomatch = [], [], []
    for N, full, new_title, target in sorted(plan, key=lambda x: x[0]):
        if target is None:
            nomatch.append(N)
            print(f"[无匹配] {N}  {new_title[:40]}")
            continue
        cur = target.get("title") or ""
        if cur == new_title:
            skipped.append(N)
            continue
        changes.append((N, target["id"], cur, new_title))
        print(f"[改] {N}  id={target['id']}")
        print(f"     原={cur!r}")
        print(f"     新={new_title!r}")
    print(f"\n统计: 需修改={len(changes)}  无需改={len(skipped)}  无匹配={len(nomatch)}")

    # 校验：所有新标题必须以标准后缀结尾、且不含正文关键词、且不应明显短于文件名
    local_map = {}
    for folder in FOLDERS:
        for fn in sorted(os.listdir(folder)):
            if not fn.lower().endswith(".docx") or fn.startswith("~$"):
                continue
            m = NUM_RE.search(fn)
            if not m:
                continue
            N = "SM-SOP-" + m.group(1)
            local_map[N] = stem_title(fn)
    bad = []
    for N, full, new_title, target in plan:
        if not new_title.endswith(TITLE_SUFFIXES):
            bad.append((N, "后缀异常", new_title))
        elif any(k in new_title for k in BODY_KEYWORDS):
            bad.append((N, "含正文关键词", new_title))
    if bad:
        print("\n!!! 校验未通过（以下新标题仍异常，需人工核查）:")
        for N, why, t in bad:
            print(f"    {N} [{why}] {t[:60]}")
    else:
        print("校验通过：所有新标题均以标准后缀结尾、无正文残留、且未短于文件名。")

    if nomatch:
        print("无匹配编号:", nomatch)

    if not apply:
        print("\n(DRY_RUN 完成，未写入。APPLY=1 执行)")
        return

    ok = fail = 0
    for N, full, new_title, target in sorted(plan, key=lambda x: x[0]):
        if target is None or (target.get("title") or "") == new_title:
            continue
        try:
            r = requests.patch(BASE + f"/documents/{target['id']}",
                               json={"title": new_title, "doc_number": full},
                               headers={"Authorization": f"Bearer {tok}"}, timeout=120)
            r.raise_for_status()
            ok += 1
            print(f"  ✓ {N} id={target['id']}")
        except Exception as e:
            fail += 1
            print(f"  ✗ {N}: {e}")
    print(f"\n完成: 成功={ok} 失败={fail}")


if __name__ == "__main__":
    main()
