"""回填试剂验收记录的「检验项目」与「新批号效期」。

背景：批量生成（`_generate`）此前漏了自动关联检验项目，导致 95 条记录的项目列全空；
另有部分记录（安图销售表无有效期列）新批号效期为空。

数据来源：`/reagent/lot-verifications/_prepare?item_id=` 返回的
  - `test_items`            该试剂关联的检验项目
  - `new_batch_candidates`  已确认/未确认收货单里的批号（含效期）

用法：
  python scripts/backfill_lot_item_expiry.py           # 预演
  python scripts/backfill_lot_item_expiry.py --apply   # 写入
"""
import json
import sys
import urllib.parse
import urllib.request

H = "http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com"


def login():
    data = urllib.parse.urlencode(
        {"username": "jinzizheng", "password": "Jzz6827556"}).encode()
    r = urllib.request.Request(H + "/api/v1/auth/login", data=data)
    return json.load(urllib.request.urlopen(r, timeout=60))["access_token"]


def call(tok, path, method="GET", body=None):
    hdr = {"Authorization": "Bearer " + tok, "Content-Type": "application/json"}
    r = urllib.request.Request(H + path, method=method,
                               data=json.dumps(body).encode() if body else None,
                               headers=hdr)
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
    print(f"验收记录 {len(rows)} 条\n")

    prep_cache = {}
    item_fix, exp_fix, item_miss, exp_miss = [], [], [], []

    for x in rows:
        iid = x["item_id"]
        if iid not in prep_cache:
            c, d = call(tok, f"/api/v1/reagent/lot-verifications/_prepare?item_id={iid}")
            prep_cache[iid] = d if c == 200 else {}
        p = prep_cache[iid]

        # ① 检验项目
        if not str(x.get("test_item_name") or "").strip():
            tis = p.get("test_items") or []
            if tis:
                item_fix.append((x, tis[0]))
            else:
                item_miss.append(x)

        # ② 新批号效期（优先用收货单里同批号的效期）
        if not x.get("new_expiry_date"):
            nb = (x.get("new_batch_no") or "").strip()
            hit = next((c for c in (p.get("new_batch_candidates") or [])
                        if (c.get("batch_no") or "").strip() == nb
                        and c.get("expiry_date")), None)
            if hit:
                exp_fix.append((x, hit["expiry_date"]))
            else:
                # 退一步：库存里同批号的效期
                hit2 = next((b for b in (p.get("stock_batches") or [])
                             if (b.get("batch_no") or "").strip() == nb
                             and b.get("expiry_date")), None)
                if hit2:
                    exp_fix.append((x, hit2["expiry_date"]))
                else:
                    exp_miss.append(x)

    print(f"【检验项目】可回填 {len(item_fix)} 条；无关联项目 {len(item_miss)} 条")
    for x, ti in item_fix[:10]:
        print(f"  #{x['id']:<4}{str(x['reagent_name'])[:32]:<34}→ {ti['name']}")
    if len(item_fix) > 10:
        print(f"  ... 共 {len(item_fix)} 条")

    print(f"\n【新批号效期】可回填 {len(exp_fix)} 条；仍无法获取 {len(exp_miss)} 条")
    for x, e in exp_fix:
        print(f"  #{x['id']:<4}{str(x['reagent_name'])[:32]:<34}{x['new_batch_no']} → {e}")
    for x in exp_miss[:20]:
        print(f"  ✗ #{x['id']:<4}{str(x['reagent_name'])[:32]:<34}{x['new_batch_no']}（需手工填）")

    print(f"\n【无关联项目的试剂】{len(item_miss)} 条 —— 需在「项目与仪器关联」里补建关联：")
    for x in item_miss:
        print(f"  #{x['id']:<4}{str(x['reagent_name'])[:40]}")

    if not apply_changes:
        print("\n模式：仅预演。加 --apply 写入。")
        return

    ok = 0
    for x, ti in item_fix:
        c, _ = call(tok, f"/api/v1/reagent/lot-verifications/{x['id']}", "PUT",
                    {"test_item_id": ti["id"], "test_item_name": ti["name"]})
        if c == 200:
            ok += 1
    print(f"\n检验项目已回填 {ok}/{len(item_fix)} 条")

    ok2 = 0
    for x, e in exp_fix:
        c, _ = call(tok, f"/api/v1/reagent/lot-verifications/{x['id']}", "PUT",
                    {"new_expiry_date": e})
        if c == 200:
            ok2 += 1
    print(f"新批号效期已回填 {ok2}/{len(exp_fix)} 条")


if __name__ == "__main__":
    main()
