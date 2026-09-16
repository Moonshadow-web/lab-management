"""清理「试剂验收」里同一支试剂因目录重复条目而产生的重复记录。

按 (归一化名称, 类型) 分组，保留「名称带货号前缀」或 id 最小的一条，其余删除。

用法：python scripts/dedupe_lot_verifications.py [--apply]
"""
import json
import sys
import urllib.parse
import urllib.request
from collections import defaultdict

sys.path.insert(0, "scripts")
from apply_shipment import norm_name  # noqa: E402

H = "http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com"


def login():
    data = urllib.parse.urlencode(
        {"username": "jinzizheng", "password": "Jzz6827556"}).encode()
    r = urllib.request.Request(H + "/api/v1/auth/login", data=data)
    return json.load(urllib.request.urlopen(r, timeout=60))["access_token"]


def call(tok, path, method="GET"):
    r = urllib.request.Request(H + path, method=method,
                               headers={"Authorization": "Bearer " + tok})
    try:
        return 200, json.load(urllib.request.urlopen(r, timeout=180))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}


def main():
    apply_changes = "--apply" in sys.argv
    tok = login()
    rows, page = [], 1
    while True:
        c, d = call(tok, f"/api/v1/reagent/lot-verifications?page={page}&page_size=200")
        rows += d["items"]
        if len(rows) >= d["total"] or not d["items"]:
            break
        page += 1

    groups = defaultdict(list)
    for x in rows:
        key = (norm_name(x["reagent_name"]), x["item_type"],
               x["old_batch_no"], x["new_batch_no"])
        groups[key].append(x)

    dup_groups = {k: v for k, v in groups.items() if len(v) > 1}
    print(f"共 {len(rows)} 条，归并为 {len(groups)} 组；其中重复组 {len(dup_groups)} 个")

    to_delete = []
    for (nm, ty, ob, nb), lst in dup_groups.items():
        # 优先保留：名称带货号前缀（含 '/'） → id 最小
        lst.sort(key=lambda z: ("/" not in (z["reagent_name"] or ""), z["id"]))
        keep, drop = lst[0], lst[1:]
        print(f"  [{nm} / {ty} / {ob}→{nb}] 保留 #{keep['id']} "
              f"{keep['reagent_name'][:26]}；删除 {[d['id'] for d in drop]}")
        to_delete += drop

    if not to_delete:
        print("无需清理。")
        return
    if not apply_changes:
        print(f"\n模式：仅预演（共需删除 {len(to_delete)} 条）。加 --apply 才真正删除。")
        return

    ok, fail = 0, []
    for d in to_delete:
        c, _ = call(tok, f"/api/v1/reagent/lot-verifications/{d['id']}", method="DELETE")
        if c == 200:
            ok += 1
        else:
            fail.append((d["id"], c))
    print(f"已删除 {ok} 条；失败 {len(fail)} 条 {fail[:5]}")


if __name__ == "__main__":
    main()
