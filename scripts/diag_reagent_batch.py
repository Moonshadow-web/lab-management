"""深挖单张收货单/盘库单明细：确认时间、操作人、细项，并全局搜索指定批号。"""
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


def get(tok, path):
    req = urllib.request.Request(H + path,
                                 headers={"Authorization": "Bearer " + tok})
    return json.load(urllib.request.urlopen(req, timeout=300))


def paged(tok, path, size=200):
    out, page = [], 1
    while True:
        d = get(tok, f"{path}&page={page}&page_size={size}")
        out += d["items"]
        if len(out) >= d["total"] or not d["items"]:
            break
        page += 1
    return out


def main():
    tok = login()
    names = {i["id"]: i for i in paged(tok, "/api/v1/reagent/items?page=1")}
    stock = paged(tok, "/api/v1/reagent/stock?page=1")
    recs = paged(tok, "/api/v1/reagent/receivings?page=1")
    checks = paged(tok, "/api/v1/reagent/inventory-checks?page=1")

    # 1) 全局搜索可疑批号
    print("【全局批号搜索】")
    for kw in ("98090501", "90890501", "93076201"):
        hit = [s for s in stock if (s["batch_no"] or "") == kw]
        print(f"  批号 {kw}: 库存行 {len(hit)} 条 -> "
              + ("; ".join(f"item{s['item_id']}({names.get(s['item_id'],{}).get('name','')[:18]})×{s['quantity']}"
                           for s in hit) or "无"))

    # 2) 08-05 两张单的完整对比
    print("\n【08-05 两张收货单对比】")
    for r in recs:
        if r["receipt_no"] in ("RCV-2026-08-660", "RCV-2026-08-430"):
            print(f"  {r['receipt_no']} id={r['id']} 日期={r['receipt_date']} "
                  f"确认={r.get('is_confirmed')} 确认时间={r.get('confirmed_at')} "
                  f"确认人={r.get('confirmed_by')} 创建人={r.get('created_by')} "
                  f"送货人={r.get('delivery_person')} 备注={r.get('remark')!r} 细项{len(r.get('items') or [])}")

    # 3) 目标 item 在这两张单里的细项
    for iid in (74, 112):
        print(f"\n  item{iid} {names.get(iid,{}).get('name','')[:26]}:")
        for r in sorted(recs, key=lambda x: (x["receipt_date"], x["id"])):
            for li in (r.get("items") or []):
                if li["item_id"] == iid:
                    print(f"    {r['receipt_date']} {r['receipt_no']} id={r['id']} "
                          f"批号={li['batch_no']!r} 数量={li['quantity']} "
                          f"确认={r.get('is_confirmed')} 确认于={r.get('confirmed_at')}")

    # 4) 盘库单里目标 item 出现次数
    print("\n【盘库单中目标 item 出现次数】")
    for iid in (74, 112):
        for c in sorted(checks, key=lambda x: (x["check_date"], x["id"])):
            rows = [li for li in (c.get("items") or []) if li["item_id"] == iid]
            if rows:
                vals = [f"{li['batch_no'] or '(空)'}:{li['recorded_quantity']}" for li in rows]
                print(f"  item{iid}  #{c['id']} {c['check_date']} {c.get('check_type')} "
                      f"出现 {len(rows)} 次 -> {vals}")


if __name__ == "__main__":
    main()
