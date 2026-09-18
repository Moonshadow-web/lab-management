"""核对「人工确认映射」的表侧/系统侧归一化名，以及相关试剂的库存批号现状。

用法：python scripts/check_alias_map.py
"""
import json
import sys
import urllib.parse
import urllib.request
from collections import defaultdict

sys.path.insert(0, "scripts")
from analyze_shipments_multi import norm_name  # noqa: E402

H = "http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com"

# 用户 2026-09-18 确认的映射：表内商品名 → 系统试剂名
CONFIRMED = [
    ("皮质醇", "人皮质醇检测试剂盒（磁微粒化学发光法）"),
    ("载脂蛋白A1", "载脂蛋白A1测定试剂合"),
    ("癌胚抗原", "癌胚抗原定量测定试剂盒（电化学发光法）"),
    ("微量白蛋白", "微量白蛋白液体试剂盒（尿）"),
    ("免疫球蛋白G", "尿免疫球蛋白G测定试剂盒"),
    ("转铁蛋白", "尿转铁蛋白测定试剂盒（胶乳免疫比浊法）"),
]


def login():
    data = urllib.parse.urlencode(
        {"username": "jinzizheng", "password": "Jzz6827556"}).encode()
    r = urllib.request.Request(H + "/api/v1/auth/login", data=data)
    return json.load(urllib.request.urlopen(r, timeout=60))["access_token"]


def get(tok, p):
    r = urllib.request.Request(H + p, headers={"Authorization": "Bearer " + tok})
    return json.load(urllib.request.urlopen(r, timeout=300))


def paged(tok, p, size=200):
    out, page = [], 1
    while True:
        d = get(tok, f"{p}&page={page}&page_size={size}")
        out += d["items"]
        if len(out) >= d["total"] or not d["items"]:
            break
        page += 1
    return out


def main():
    tok = login()
    items = paged(tok, "/api/v1/reagent/items?page=1")
    by_name = {i["name"]: i for i in items}
    st = paged(tok, "/api/v1/reagent/stock?page=1")
    by_item = defaultdict(list)
    for s in st:
        by_item[s["item_id"]].append(s)

    print("用户确认的映射核对：")
    for src_kw, sys_name in CONFIRMED:
        it = by_name.get(sys_name)
        if not it:
            print(f"  ❌ 系统里找不到「{sys_name}」")
            continue
        rows = by_item.get(it["id"], [])
        info = [(r.get("batch_no") or "(空)", str(r.get("expiry_date") or "")) for r in rows]
        print(f"  表侧「{src_kw}」 → id={it['id']} {sys_name}")
        print(f"      norm(系统)={norm_name(sys_name)!r}  norm(表侧)={norm_name(src_kw)!r}")
        print(f"      类型={it.get('type')}  库存={info if info else '（无库存行）'}")


if __name__ == "__main__":
    main()
