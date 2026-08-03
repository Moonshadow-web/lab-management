"""把 3 个本地文件夹的 SOP 终版写入系统文件档案（/api/v1/documents）。

匹配策略（解决系统里 doc_number 标错的问题）：
  1) 本地文件名提取编号 N = SM-SOP-XXX。
  2) 系统 doc_number 去掉前缀 MHZYY-JYK- / HZYY-JYK- 后 = 规范化编号。
  3) 优先按 规范化编号 精确相等匹配；若 0 或 >1 命中，则用“标题核心名”
     （去掉编号前缀、仪器检测系统前缀、测定标准操作程序后缀，归一化）匹配。
动作：
  - 命中已存在记录 -> POST /{id}/new-version 传新文件（版本号 +1），
    再 PATCH 修正 doc_number=MHZYY-JYK-SM-SOP-N（一并纠正系统标错）、title=新标题。
  - 未命中 -> POST /upload 新增（category=项目SOP, status=生效），
    再 PATCH doc_number=MHZYY-JYK-SM-SOP-N。
默认 DRY_RUN（打印方案不写入）；APPLY=1 执行。
"""
import os, re, sys, json
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


def title_core(t):
    t = re.sub(r"^SM-SOP-\d+\s*[-—]?\s*", "", t or "")
    for p in INSTR:
        t = t.replace(p, "")
    t = t.replace(" 沃文特", "").strip()
    t = re.sub(r"(测定标准操作程序|标准操作程序|操作程序)$", "", t).strip()
    return t.replace("（", "(").replace("）", ")").replace(" ", "").lower()


def first_title(path):
    try:
        doc = Document(path)
        for p in doc.paragraphs:
            if p.text.strip():
                return p.text.strip()
    except Exception:
        pass
    return ""


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

    # 规范化编号索引 + 标题核心索引
    by_norm = {}
    by_core = {}
    for it in docs:
        dn = (it.get("doc_number") or "").strip()
        norm = PREFIX_RE.sub("", dn).strip()
        if norm:
            by_norm.setdefault(norm, []).append(it)
        core = title_core(it.get("title") or "")
        if core:
            by_core.setdefault(core, []).append(it)

    # 本地文件
    local = []
    for folder in FOLDERS:
        for fn in sorted(os.listdir(folder)):
            if not fn.lower().endswith(".docx") or fn.startswith("~$"):
                continue
            m = NUM_RE.search(fn)
            if not m:
                print(f"[WARN] 无法提取编号: {fn}")
                continue
            num = "SM-SOP-" + m.group(1)
            path = os.path.join(folder, fn)
            title = first_title(path) or re.sub(r"^SM-SOP-\d+\s*[-—]?\s*", "", fn)
            # 核心名从文件名推导（与系统标题来源一致；正文第一段可能有"血清"等差异）
            stem = os.path.splitext(re.sub(r"^SM-SOP-\d+\s*[-—]?\s*", "", fn))[0]
            local.append({"num": num, "fn": fn, "path": path,
                          "title": title, "core": title_core(stem)})

    plan = []  # (num, action, target_id_or_None, title, status, note)
    collisions = []
    for e in local:
        N = e["num"]
        cands = by_norm.get(N, [])
        target = None
        method = ""
        if len(cands) == 1:
            target = cands[0]; method = "编号精确"
        elif len(cands) == 0:
            core_hits = by_core.get(e["core"], [])
            core_hits = [c for c in core_hits if c.get("doc_number", "").strip() != ""]
            if len(core_hits) == 1:
                target = core_hits[0]; method = "标题核心(系统编号标错已纠正)"
            elif len(core_hits) == 0:
                target = None; method = "新增"
            else:
                collisions.append((e, core_hits, "标题核心多命中")); method = "冲突"
        else:
            # >1 规范化编号命中：用标题核心在候选中挑
            pick = [c for c in cands if title_core(c.get("title") or "") == e["core"]]
            if len(pick) == 1:
                target = pick[0]; method = "编号精确(多命中按标题核心)"
            else:
                collisions.append((e, cands, "编号多命中")); method = "冲突"

        if method == "冲突":
            plan.append((N, "冲突", None, e["title"], "", "见冲突列表"))
        elif target is None:
            plan.append((N, "新增", None, e["title"], "生效", method))
        else:
            plan.append((N, "新版本", target["id"], e["title"], target.get("status"),
                         f"{method}; 原doc_number={target.get('doc_number')}"))

    # 输出方案
    print(f"=== DRY_RUN={not apply}  本地文件数={len(local)}  系统文档总数={len(docs)} ===\n")
    new_n = sum(1 for p in plan if p[1] == "新增")
    ver_n = sum(1 for p in plan if p[1] == "新版本")
    col_n = sum(1 for p in plan if p[1] == "冲突")
    for N, act, tid, title, status, note in sorted(plan, key=lambda x: x[0]):
        if act == "新增":
            print(f"[新增]   {N}  标题={title[:40]}")
        elif act == "新版本":
            print(f"[新版本] {N}  id={tid:<4} status={status:<4} {note}")
        else:
            print(f"[冲突]   {N}  标题={title[:40]}  -> {note}")
    print(f"\n统计: 新增={new_n}  新版本={ver_n}  冲突={col_n}")
    if collisions:
        print("\n===== 冲突明细 =====")
        for e, hits, why in collisions:
            print(f"  {e['num']} ({why}):")
            for c in hits:
                print(f"      id={c['id']} doc_number={c.get('doc_number')!r} title={c.get('title','')[:34]!r}")

    if not apply:
        print("\n(DRY_RUN 完成，未写入。APPLY=1 执行)")
        return

    # 执行
    print("\n===== 执行写入 =====")
    ok_new = ok_ver = fail = 0
    fails = []
    for N, act, tid, title, status, note in sorted(plan, key=lambda x: x[0]):
        if act == "冲突":
            continue
        full_code = "MHZYY-JYK-" + N
        with open(e_path := next(x["path"] for x in local if x["num"] == N), "rb") as fh:
            content = fh.read()
        fname = next(x["fn"] for x in local if x["num"] == N)
        headers = {"Authorization": f"Bearer {tok}"}
        try:
            if act == "新增":
                r = requests.post(BASE + "/documents/upload",
                                  files={"file": (fname, content,
                                          "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
                                  data={"title": title, "category": "项目SOP",
                                        "status": "生效", "note": "批量导入终版"},
                                  headers=headers, timeout=300)
                r.raise_for_status()
                did = r.json()["id"]
            else:
                r = requests.post(BASE + f"/documents/{tid}/new-version",
                                  files={"file": (fname, content,
                                          "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
                                  data={"note": "SOP内容更新：仪器/型号引用同步修订"},
                                  headers=headers, timeout=300)
                r.raise_for_status()
                did = tid
            # 修正 doc_number + 标题
            p = requests.patch(BASE + f"/documents/{did}",
                               json={"title": title, "doc_number": full_code},
                               headers=headers, timeout=120)
            p.raise_for_status()
            if act == "新增":
                ok_new += 1
            else:
                ok_ver += 1
            print(f"  ✓ {N} {act} id={did}")
        except Exception as ex:
            fail += 1
            fails.append((N, act, str(ex)[:120]))
            print(f"  ✗ {N} {act} 失败: {ex}")

    print(f"\n执行结果: 新增成功={ok_new}  新版本成功={ok_ver}  失败={fail}")
    if fails:
        print("失败明细:")
        for N, act, msg in fails:
            print(f"  {N} {act}: {msg}")


if __name__ == "__main__":
    main()
