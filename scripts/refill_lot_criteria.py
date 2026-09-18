"""对「未设允许偏倚」的验收记录重新调用标准解析接口，能解析到的就自动补上。

用于匹配逻辑修复后回填（如 _core 去后缀修复）。

用法：
  python scripts/refill_lot_criteria.py            # 只看能解析出什么
  python scripts/refill_lot_criteria.py --apply    # 写入
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

    miss = [x for x in rows if not str(x.get("allow_bias_pct") or "").strip()]
    print(f"验收记录 {len(rows)} 条，其中未设允许偏倚 {len(miss)} 条\n")

    hit, still = [], []
    for x in miss:
        c, r = call(tok, f"/api/v1/reagent/lot-verifications/criteria"
                         f"?item_id={x['item_id']}&test_item_name="
                         f"{urllib.parse.quote(x.get('test_item_name') or '')}")
        if c == 200 and r.get("pct", 0) > 0:
            hit.append((x, r))
        else:
            still.append(x)

    print(f"【能自动解析到标准】{len(hit)} 条")
    for x, r in hit:
        print(f"  #{x['id']:<4}{str(x['reagent_name'])[:34]:<36}→ {r['pct']:g}  {r['label']}")

    print(f"\n【仍无标准】{len(still)} 条")
    for x in still:
        print(f"  #{x['id']:<4}{str(x['reagent_name'])[:40]}")

    if not apply_changes:
        print(f"\n模式：仅预演。加 --apply 写入这 {len(hit)} 条。")
        return

    ok = 0
    for x, r in hit:
        c, _ = call(tok, f"/api/v1/reagent/lot-verifications/{x['id']}", "PUT", {
            "allow_bias_pct": f"{r['pct']:g}",
            "bias_mode": "relative",
            "criterion_source": r["source"],
            "criterion_label": r["label"],
        })
        if c == 200:
            ok += 1
        else:
            print(f"  写入失败 #{x['id']} HTTP {c}")
    print(f"已写入 {ok}/{len(hit)} 条")


if __name__ == "__main__":
    main()
