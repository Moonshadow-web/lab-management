"""精确探测：按 doc_number 精确相等匹配，避免 title/filename 模糊误关联。
输出每个本地 SOP 编号 -> 精确 doc_number==编号 的现存记录(含original_filename)。
"""
import os, re, json, urllib.request, urllib.parse

BASE = "http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com/api/v1"
FOLDERS = [
    r"C:/Users/81526/Desktop/待办/AU5800",
    r"C:/Users/81526/Desktop/待办/DXI",
    r"C:/Users/81526/Desktop/待办/安图",
]
NUM_RE = re.compile(r"SM-SOP-(\d+)")


def req(m, p, data=None, tok=""):
    h = {"Accept": "application/json"}
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    body = None
    if data is not None:
        if m == "POST" and p == "/auth/login":
            body = urllib.parse.urlencode(data).encode()
            h["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            body = json.dumps(data, ensure_ascii=False).encode()
            h["Content-Type"] = "application/json"
    r = urllib.request.Request(BASE + p, data=body, headers=h, method=m)
    try:
        resp = urllib.request.urlopen(r, timeout=120)
        return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]


def main():
    st, l = req("POST", "/auth/login", {"username": "jinzizheng", "password": "Jzz6827556"})
    assert st == 200, f"login failed {st} {l}"
    tok = l["access_token"]

    # 本地文件：编号 -> [(folder, filename, path)]
    local = {}
    for folder in FOLDERS:
        for fn in sorted(os.listdir(folder)):
            if not fn.lower().endswith(".docx") or fn.startswith("~$"):
                continue
            m = NUM_RE.search(fn)
            if not m:
                print(f"[WARN] 无法提取编号: {fn}")
                continue
            num = "SM-SOP-" + m.group(1)
            local.setdefault(num, []).append((os.path.basename(folder), fn, os.path.join(folder, fn)))

    # 去重编号
    nums = sorted(local.keys())

    # 一次性拉取全部文档(大页)，建立 doc_number -> [records]
    all_docs = []
    page = 1
    while True:
        st, r = req("GET", f"/documents?page={page}&page_size=200", tok=tok)
        if not isinstance(r, dict):
            break
        items = r.get("items", [])
        all_docs.extend(items)
        tot = r.get("total", 0)
        if page * 200 >= tot or not items:
            break
        page += 1
    print(f"系统文档总数(拉取): {len(all_docs)}")

    by_num = {}
    for it in all_docs:
        dn = (it.get("doc_number") or "").strip()
        by_num.setdefault(dn, []).append(it)

    new_count = 0
    ver_count = 0
    collision = 0
    for num in nums:
        recs = by_num.get(num, [])
        sources = local[num]
        if not recs:
            new_count += 1
            print(f"[新增]     {num}  本地源({len(sources)}): {sources[0][1][:46]}")
        elif len(recs) == 1:
            it = recs[0]
            ver_count += 1
            flag = "" if (num in (it.get("title") or "") or num in (it.get("original_filename") or "")) else "  (doc_number匹配但title/filename不含编号)"
            print(f"[新版本]   {num}  id={it['id']} ver={it.get('version')} status={it.get('status')} "
                  f"cat={it.get('category')} title={it.get('title','')[:34]!r}{flag}")
        else:
            collision += 1
            print(f"[冲突!!]   {num}  精确doc_number命中 {len(recs)} 条:")
            for it in recs:
                print(f"            id={it['id']} ver={it.get('version')} status={it.get('status')} "
                      f"title={it.get('title','')[:30]!r} file={it.get('original_filename','')[:40]!r}")
    print(f"\n===== 统计: 新增={new_count}  精确新版本={ver_count}  编号冲突={collision}  编号总数={len(nums)} =====")


if __name__ == "__main__":
    main()
