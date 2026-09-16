"""清空 / 批量删除试剂验收记录（管理员）。

用法：
  python scripts/clear_lot_verifications.py            # 只列出，不删
  python scripts/clear_lot_verifications.py --apply    # 全删
  python scripts/clear_lot_verifications.py --apply --ids 1,2,3   # 只删指定 id
"""
import json
import sys
import urllib.parse
import urllib.request

H = "http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com"


def login():
    data = urllib.parse.urlencode(
        {"username": "jinzizheng", "password": "Jzz6827556"}).encode()
    req = urllib.request.Request(H + "/api/v1/auth/login", data=data)
    return json.load(urllib.request.urlopen(req, timeout=60))["access_token"]


def req(tok, path, method="GET"):
    r = urllib.request.Request(H + path, method=method,
                               headers={"Authorization": "Bearer " + tok})
    try:
        return 200, json.load(urllib.request.urlopen(r, timeout=120))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}


def main():
    apply_changes = "--apply" in sys.argv
    only_ids = None
    if "--ids" in sys.argv:
        only_ids = [int(x) for x in sys.argv[sys.argv.index("--ids") + 1].split(",")]

    tok = login()
    rows = []
    page = 1
    while True:
        code, d = req(tok, f"/api/v1/reagent/lot-verifications?page={page}&page_size=200")
        if code != 200:
            print("查询失败 HTTP", code, d)
            return
        rows += d["items"]
        if len(rows) >= d["total"] or not d["items"]:
            break
        page += 1

    targets = [r for r in rows if (only_ids is None or r["id"] in only_ids)]
    print(f"当前验收记录 {len(rows)} 条；本次将删除 {len(targets)} 条")
    if not apply_changes:
        for r in targets[:10]:
            print(f"  #{r['id']} {str(r['reagent_name'])[:28]:<30} "
                  f"{r['old_batch_no']}→{r['new_batch_no']} {r['conclusion']}")
        if len(targets) > 10:
            print(f"  ... 共 {len(targets)} 条")
        print("\n模式：仅列出（未删除）。加 --apply 才真正删除。")
        return

    ok, fail = 0, []
    for r in targets:
        code, _ = req(tok, f"/api/v1/reagent/lot-verifications/{r['id']}", method="DELETE")
        if code == 200:
            ok += 1
        else:
            fail.append((r["id"], code))
    print(f"已删除 {ok} 条；失败 {len(fail)} 条")
    if fail:
        print("  失败明细:", fail[:10])


if __name__ == "__main__":
    main()
