"""分析「民航2026年发货记录」：可补批号的试剂 / 2026 年发生批号变更的试剂。

匹配方式同 match_reserve_stock.py：系统试剂名里 "/" 或 "-" 前的货号 == 发货记录「物料编码/货号」。
用法：python scripts/analyze_shipment.py [xlsx路径]
"""
import json
import re
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime

H = "http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com"
DEFAULT_XLSX = r"C:/Users/81526/Desktop/民航2026年发货记录_20260914(2).xlsx"


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


def item_code(name: str) -> str:
    if not name:
        return ""
    head = re.split(r"[/／\-－]", str(name))[0].strip().upper()
    return head if re.match(r"^[A-Z0-9][A-Z0-9.]{1,20}$", head or "") else ""


def norm(name: str) -> str:
    if not name:
        return ""
    s = re.split(r"[/／]", str(name))[-1]
    s = re.sub(r"[（(].*?[）)]", "", s)
    s = re.sub(r"[\s　]", "", s).upper()
    for kw in ("测定试剂盒", "检测试剂盒", "诊断试剂盒", "测定试剂", "检测试剂",
               "试剂盒", "试剂", "校准品", "定标液", "质控品", "标准品"):
        s = s.replace(kw, "")
    return s.strip()


# 非「试剂」的发货行关键词（本模块只验收试剂，不含校准品/质控品/电解质）
NON_REAGENT_KW = ("校准", "定标", "质控", "标准品", "参考品", "电解质", "参比液",
                  "内标液", "参比电极", "缓冲液")


def is_reagent_row(name: str) -> bool:
    """判断发货记录商品名是否为「试剂」（排除校准品/质控品/电解质等）。"""
    n = str(name or "")
    return not any(kw in n for kw in NON_REAGENT_KW)


def read_excel(path):
    from openpyxl import load_workbook
    wb = load_workbook(path)
    ws = wb[wb.sheetnames[0]]
    rows = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        if not r[5] and not r[15]:
            continue
        dt = r[1]
        if isinstance(dt, datetime):
            dt = dt.date()
        elif isinstance(dt, str):
            dt = dt.strip()[:10]
        exp = r[10]
        if isinstance(exp, datetime):
            exp = exp.date()
        elif isinstance(exp, str) and exp.strip():
            exp = exp.strip()[:10]
        else:
            exp = None
        rows.append({
            "date": str(dt or ""), "goods": str(r[5] or "").strip(),
            "spec": str(r[6] or "").strip(), "batch_no": str(r[8] or "").strip(),
            "expiry": exp, "qty": r[11], "code": str(r[14] or "").strip().upper(),
            "name": str(r[15] or "").strip(), "maker": str(r[18] or "").strip(),
        })
    return rows


def main():
    xlsx = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_XLSX
    tok = login()
    items = {i["id"]: i for i in paged(tok, "/api/v1/reagent/items?page=1")}
    stock = paged(tok, "/api/v1/reagent/stock?page=1")
    stock_by_item = defaultdict(list)
    for s in stock:
        stock_by_item[s["item_id"]].append(s)

    idx_code, idx_name = defaultdict(list), defaultdict(list)
    for iid, it in items.items():
        c = item_code(it.get("name"))
        if c:
            idx_code[c].append(iid)
        idx_name[norm(it.get("name"))].append(iid)

    ship = read_excel(xlsx)
    print(f"发货记录 {len(ship)} 行；系统目录 {len(items)} 条、库存 {len(stock)} 行\n")

    # 按 item 归组
    by_item = defaultdict(list)
    unmatched = []
    skipped_nonreagent = []
    for r in ship:
        hits = idx_code.get(r["code"], []) if r["code"] else []
        if not hits:
            n = norm(r["name"])
            if n and n in idx_name:
                hits = idx_name[n]
        hits = sorted(set(hits))
        if not hits:
            unmatched.append(r)
            continue
        # 只保留 type=试剂的目录项；发货记录本身是校准品/质控品/电解质的行直接跳过
        hits = [i for i in hits if (items[i].get("type") or "") == "试剂"]
        if not hits or not is_reagent_row(r["name"]):
            if hits:
                skipped_nonreagent.append(r)
            else:
                unmatched.append(r)
            continue
        # 只取在库里有库存行的
        with_stock = [i for i in hits if i in stock_by_item] or hits
        for iid in with_stock:
            by_item[iid].append(r)

    # 每个 item 的批号时间线（按发货日期）
    fill, changed, unchanged = [], [], []
    for iid, recs in by_item.items():
        it = items[iid]
        if it.get("type") not in ("试剂", "质控品"):
            continue
        # 按批号聚合：最早发货日期、效期
        batches = {}
        for r in recs:
            b = r["batch_no"]
            if not b:
                continue
            d = r["date"] or ""
            if b not in batches or d < batches[b]["date"]:
                batches[b] = {"date": d, "expiry": str(r["expiry"] or ""),
                              "qty": r["qty"], "maker": r["maker"]}
        if not batches:
            continue
        tl = sorted(batches.items(), key=lambda x: x[1]["date"])
        latest = tl[-1]
        cur = [s for s in stock_by_item.get(iid, [])]
        cur_batches = [((s["batch_no"] or "").strip(), str(s["expiry_date"] or "")) for s in cur]

        if len(tl) >= 2:
            # 2026 年出现 ≥2 个批号 → 批号变更
            prev = tl[-2]
            changed.append({
                "item_id": iid, "name": it.get("name"), "spec": it.get("spec"),
                "type": it.get("type"), "library": it.get("library"),
                "old_batch": prev[0], "old_date": prev[1]["date"],
                "old_expiry": prev[1]["expiry"],
                "new_batch": latest[0], "new_date": latest[1]["date"],
                "new_expiry": latest[1]["expiry"],
                "batch_count": len(tl),
                "all_batches": [f"{b}/{v['date']}" for b, v in tl],
                "cur_batches": cur_batches,
            })
        else:
            unchanged.append({"item_id": iid, "name": it.get("name"),
                              "batch": latest[0], "date": latest[1]["date"]})

        # 需要补批号的（库存无批号）
        if cur and not any((s["batch_no"] or "").strip() for s in cur):
            fill.append({
                "item_id": iid, "name": it.get("name"), "spec": it.get("spec"),
                "type": it.get("type"), "library": it.get("library"),
                "batch_no": latest[0], "expiry": latest[1]["expiry"],
                "ship_date": latest[1]["date"], "qty": cur[0]["quantity"],
                "stock_id": cur[0]["id"],
            })

    print("=" * 100)
    print(f"【A】2026 年发生批号变更（≥2 个批号）的试剂/质控品：{len(changed)} 个")
    print("=" * 100)
    for x in sorted(changed, key=lambda x: (x["library"] or "", x["name"] or "")):
        print(f"  {x['library'] or '':<6}{str(x['name'])[:30]:<32}"
              f"旧 {x['old_batch']}({x['old_date']}) → 新 {x['new_batch']}({x['new_date']})  共{x['batch_count']}批")

    print()
    print("=" * 100)
    print(f"【B】可补批号（系统库存无批号）：{len(fill)} 个")
    print("=" * 100)
    for x in sorted(fill, key=lambda x: (x["library"] or "", x["name"] or "")):
        print(f"  {x['library'] or '':<6}{str(x['name'])[:32]:<34}→ {x['batch_no']:<12} 效期 {x['expiry']} (发货{x['ship_date']})")

    print()
    print(f"【C】2026 年只有一个批号（无需批间验证）：{len(unchanged)} 个")
    print(f"【D】发货记录本身是校准品/质控品/电解质等（按规则不验收）：{len(skipped_nonreagent)} 行")
    print(f"【E】发货记录未匹配到系统试剂：{len(unmatched)} 行")
    for r in unmatched[:15]:
        print(f"  {r['code']:<12}{r['name'][:34]:<36}{r['batch_no']:<12}{r['date']}")

    json.dump({"changed": changed, "fill": fill, "unchanged": unchanged,
               "skipped_nonreagent": len(skipped_nonreagent),
               "unmatched": [{"code": r["code"], "name": r["name"],
                              "batch": r["batch_no"], "date": r["date"]}
                             for r in unmatched]},
              open("outputs/shipment_analysis.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1, default=str)
    print("\n明细已存 outputs/shipment_analysis.json")


if __name__ == "__main__":
    main()
