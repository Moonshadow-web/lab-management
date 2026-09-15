"""把「民航预留库」Excel 的批号/效期与系统实时库存做核对。

匹配策略（由严到宽，避免误配）：
  1) 货号精确  —— 系统试剂名里 "/" 前的货号（如 "OSR6111/直接胆红素…"）== 预留库「物料编码/货号」
  2) 编码精确  —— 系统 material_code == 预留库货号
  3) 名称精确  —— 归一化后完全相同（不做包含匹配，避免 白蛋白↔前白蛋白 之类误配）

输出：待回填 / 不一致 / 已一致 / 无库存行 / 未匹配
用法：python scripts/match_reserve_stock.py [xlsx路径]
"""
import json
import re
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

H = "http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com"
DEFAULT_XLSX = r"C:/Users/81526/Desktop/民航预留库_20260910(1).xlsx"
OUT = "outputs/预留库批号核对.xlsx"


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


def norm(name: str) -> str:
    if not name:
        return ""
    s = str(name)
    s = re.split(r"[/／]", s)[-1]            # 去掉货号前缀
    s = re.sub(r"[（(].*?[）)]", "", s)
    s = re.sub(r"[\s　]", "", s)
    s = s.replace("－", "-").replace("—", "-").upper()
    for kw in ("测定试剂盒", "检测试剂盒", "诊断试剂盒", "测定试剂", "检测试剂",
               "试剂盒", "试剂", "校准品", "定标液", "质控品", "标准品"):
        s = s.replace(kw, "")
    return s.strip()


def item_code(name: str) -> str:
    """从系统试剂名里取货号前缀，如 'OSR6111/直接胆红素…'、'OSR6107-丙氨酸…' -> 'OSR6111'。"""
    if not name:
        return ""
    head = re.split(r"[/／\-－]", str(name))[0].strip().upper()
    return head if re.match(r"^[A-Z0-9][A-Z0-9.]{1,20}$", head or "") else ""


def read_excel(path):
    ws = load_workbook(path)[load_workbook(path).sheetnames[0]]
    rows, seen = [], {}
    for r in ws.iter_rows(min_row=2, values_only=True):
        if not r[4]:
            continue
        exp = r[7]
        if isinstance(exp, datetime):
            exp = exp.date()
        elif isinstance(exp, str) and exp.strip():
            exp = exp.strip()[:10]
        else:
            exp = None
        rec = {"code": str(r[3] or "").strip().upper(),
               "name": str(r[4] or "").strip(),
               "spec": str(r[5] or "").strip(),
               "batch_no": str(r[6] or "").strip(),
               "expiry_date": exp, "qty": r[9],
               "maker": str(r[12] or "").strip()}
        # 同货号+同批号合并数量（同一批货可能分行存放）
        k = (rec["code"], rec["batch_no"], str(exp))
        if k in seen:
            seen[k]["qty"] = (seen[k]["qty"] or 0) + (rec["qty"] or 0)
            continue
        seen[k] = rec
        rows.append(rec)
    return rows


def main():
    xlsx = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_XLSX
    tok = login()
    items = {i["id"]: i for i in paged(tok, "/api/v1/reagent/items?page=1")}
    stock = paged(tok, "/api/v1/reagent/stock?page=1")

    stock_by_item = defaultdict(list)
    for s in stock:
        stock_by_item[s["item_id"]].append(s)

    idx_code, idx_mat, idx_name = defaultdict(list), defaultdict(list), defaultdict(list)
    for iid, it in items.items():
        c = item_code(it.get("name"))
        if c:
            idx_code[c].append(iid)
        mc = (it.get("material_code") or "").strip().upper()
        if mc:
            idx_mat[mc].append(iid)
        idx_name[norm(it.get("name"))].append(iid)

    reserve = read_excel(xlsx)
    to_fill, conflict, same, no_stock, unmatched = [], [], [], [], []
    pairs = []

    for r in reserve:
        hits, how = [], ""
        if r["code"] and r["code"] in idx_code:
            hits, how = idx_code[r["code"]], "货号"
        if not hits and r["code"] and r["code"] in idx_mat:
            hits, how = idx_mat[r["code"]], "材料编码"
        if not hits:
            n = norm(r["name"])
            if n and n in idx_name:
                hits, how = idx_name[n], "名称精确"
        hits = sorted(set(hits))
        if not hits:
            unmatched.append(r)
            continue
        with_stock = [i for i in hits if i in stock_by_item]
        if not with_stock:
            no_stock.append((r, hits, how))
            continue
        rr = dict(r)
        rr["how"] = how
        pairs.append({"rec": rr, "hits": with_stock})

    # 预留库按 item 归组：一个试剂可能有多个批次
    res_by_item = defaultdict(list)
    for p in pairs:
        for iid in p["hits"]:
            res_by_item[iid].append(p["rec"])

    only_sys = []
    for iid, rlist in res_by_item.items():
        it = items[iid]
        res_batches = {(x["batch_no"].upper(), str(x["expiry_date"] or "")): x for x in rlist}
        sys_rows = stock_by_item[iid]
        empty_rows = [s for s in sys_rows if not (s["batch_no"] or "").strip()]
        filled = [s for s in sys_rows if (s["batch_no"] or "").strip()]

        # ① 无批号的库存行 → 用预留库回填；多批次时按「效期近的优先」取，并标注
        if empty_rows:
            cands = sorted(rlist, key=lambda x: str(x["expiry_date"] or "9999"))
            pick = cands[0]
            for s in empty_rows:
                to_fill.append({
                    "item_id": iid, "name": it.get("name"),
                    "spec": it.get("spec"), "type": it.get("type"),
                    "library": it.get("library"), "qty": s["quantity"],
                    "stock_id": s["id"], "new_batch": pick["batch_no"],
                    "new_expiry": str(pick["expiry_date"] or ""),
                    "how": pick["how"], "reserve_name": pick["name"],
                    "reserve_code": pick["code"], "reserve_qty": pick["qty"],
                    "maker": pick["maker"],
                    "multi": len(cands) > 1,
                    "other_batches": [f"{c['batch_no']}/{c['expiry_date']}"
                                      for c in cands[1:]],
                })

        # ② 已有批号的库存行 → 与预留库同试剂的批号集合比对
        for s in filled:
            b = (s["batch_no"] or "").strip()
            e = str(s["expiry_date"] or "")
            if (b.upper(), e) in res_batches:
                same.append({"item_id": iid, "name": it.get("name"),
                             "qty": s["quantity"], "batch": b, "expiry": e,
                             "how": "货号"})
                continue
            hit_b = [x for x in rlist if x["batch_no"].upper() == b.upper()]
            if hit_b:
                # 批号相同但效期不同 —— 真不一致
                conflict.append({
                    "item_id": iid, "name": it.get("name"),
                    "spec": it.get("spec"), "library": it.get("library"),
                    "qty": s["quantity"], "stock_id": s["id"],
                    "sys_batch": b, "sys_expiry": e,
                    "res_batch": hit_b[0]["batch_no"],
                    "res_expiry": str(hit_b[0]["expiry_date"] or ""),
                    "reserve_name": hit_b[0]["name"], "how": "货号",
                    "kind": "效期不同",
                })
            else:
                # 系统有这个批次、预留库没有 —— 多为科室现存旧批，非错误
                only_sys.append({
                    "item_id": iid, "name": it.get("name"),
                    "library": it.get("library"), "qty": s["quantity"],
                    "batch": b, "expiry": e,
                    "res_batches": [f"{x['batch_no']}/{x['expiry_date']}" for x in rlist],
                })

    # 注：multi / other_batches 在构建时已按「该试剂在预留库里有几个批次」计算好，此处不要再覆盖

    print(f"预留库 {len(reserve)} 条（已合并同批次）｜系统目录 {len(items)} 条、库存 {len(stock)} 行\n")
    print("=" * 104)
    print(f"【1】待回填（系统无批号 → 用预留库批号/效期）：{len(to_fill)} 条")
    print("=" * 104)
    for x in to_fill:
        flag = f"  ⚠多批次，另有 {'、'.join(x['other_batches'])}" if x["multi"] else ""
        print(f"  item{x['item_id']:<5}{str(x['name'])[:32]:<34}现存{x['qty']:<4} "
              f"→ {x['new_batch']:<12} {x['new_expiry']}{flag}")

    print()
    print("=" * 104)
    print(f"【2】真正不一致（批号相同但效期不同 / 系统批号与预留库不同）：{len(conflict)} 条")
    print("=" * 104)
    for x in conflict:
        print(f"  item{x['item_id']:<5}{str(x['name'])[:30]:<32}现存{x['qty']}  ({x['kind']})")
        print(f"        系统：{x['sys_batch']!r}  {x['sys_expiry']}")
        print(f"        预留：{x['res_batch']!r}  {x['res_expiry']}")

    print()
    print("=" * 104)
    print(f"【3】系统独有批次（科室现存、预留库已无此批，属正常）：{len(only_sys)} 条")
    print("=" * 104)
    for x in only_sys:
        print(f"  item{x['item_id']:<5}{str(x['name'])[:30]:<32}现存{x['qty']:<4}"
              f"{x['batch']} / {x['expiry']}   预留库现有：{'、'.join(x['res_batches'])}")

    print()
    print(f"【4】已一致：{len(same)} 条")
    for x in same:
        print(f"  item{x['item_id']:<5}{str(x['name'])[:30]:<32}{x['batch']} / {x['expiry']}")

    print()
    print(f"【5】预留库有、但系统无库存行（无法回填）：{len(no_stock)} 条")
    for r, hits, how in no_stock:
        print(f"  {r['code']:<10}{r['name'][:30]:<32}{r['batch_no']:<12}{r['expiry_date']}"
              f"  目录id={hits[:3]}")

    print()
    print(f"【6】预留库有、系统目录里找不到：{len(unmatched)} 条")
    for r in unmatched:
        print(f"  {r['code']:<10}{r['name'][:34]:<36}{r['batch_no']:<12}{r['expiry_date']}")

    # Excel 报告
    wb = Workbook()
    head_fill = PatternFill("solid", fgColor="1A365D")
    warn = PatternFill("solid", fgColor="FFF2CC")
    red = PatternFill("solid", fgColor="FCE4E4")

    def sheet(title, headers, rows, widths, fill_rows=None):
        ws = wb.create_sheet(title)
        ws.append(headers)
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = head_fill
            c.alignment = Alignment(horizontal="center", vertical="center")
        for row in rows:
            ws.append(row)
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w
        ws.freeze_panes = "A2"
        for r_ in ws.iter_rows(min_row=2):
            for c in r_:
                c.alignment = Alignment(vertical="center", wrap_text=True)
        if fill_rows:
            for r_ in ws.iter_rows(min_row=2):
                fill_rows(r_)
        return ws

    wb.remove(wb.active)
    sheet("待回填", ["物品ID", "系统试剂名称", "规格", "类型", "责任库", "现存",
                     "拟填批号", "拟填效期", "匹配方式", "预留库名称", "预留库货号", "预留库数量"],
          [[x["item_id"], x["name"], x["spec"], x["type"], x["library"], x["qty"],
            x["new_batch"], x["new_expiry"], x["how"], x["reserve_name"],
            x["reserve_code"], x["reserve_qty"]] for x in to_fill],
          [8, 38, 20, 8, 10, 8, 16, 12, 10, 32, 12, 10],
          lambda r: [c.__setattr__("fill", warn) for c in r] if r[0].row and False else None)
    ws = wb["待回填"]
    for r_ in ws.iter_rows(min_row=2):
        if str(r_[8].value or "") != "货号":
            for c in r_:
                c.fill = warn

    sheet("不一致", ["物品ID", "系统试剂名称", "责任库", "现存", "系统批号", "系统效期",
                     "预留库批号", "预留库效期", "预留库名称", "匹配方式"],
          [[x["item_id"], x["name"], x["library"], x["qty"], x["sys_batch"],
            x["sys_expiry"], x["res_batch"], x["res_expiry"],
            x["reserve_name"], x["how"]] for x in conflict],
          [8, 38, 10, 8, 16, 12, 16, 12, 32, 10],
          lambda r: [c.__setattr__("fill", red) for c in r] if False else None)
    sheet("系统独有批次", ["物品ID", "系统试剂名称", "责任库", "现存", "系统批号", "系统效期",
                           "预留库现有批次", "说明"],
          [[x["item_id"], x["name"], x["library"], x["qty"], x["batch"], x["expiry"],
            "、".join(x["res_batches"]), "科室现存旧批，预留库已无此批（正常）"]
           for x in only_sys],
          [8, 38, 10, 8, 16, 12, 28, 30])
    sheet("已一致", ["物品ID", "系统试剂名称", "现存", "批号", "效期"],
          [[x["item_id"], x["name"], x["qty"], x["batch"], x["expiry"]] for x in same],
          [8, 40, 8, 16, 12])
    sheet("预留库未匹配", ["货号", "名称", "批号", "效期", "数量", "生产厂商"],
          [[r["code"], r["name"], r["batch_no"], str(r["expiry_date"]),
            r["qty"], r["maker"]] for r in unmatched],
          [14, 40, 14, 12, 8, 30])
    sheet("预留库无库存行", ["货号", "名称", "批号", "效期", "目录ID"],
          [[r["code"], r["name"], r["batch_no"], str(r["expiry_date"]),
            ",".join(map(str, hits[:5]))] for r, hits, _h in no_stock],
          [14, 40, 14, 12, 16])

    ws0 = wb.create_sheet("汇总", 0)
    ws0.append(["项目", "数量"])
    for c in ws0[1]:
        c.font = Font(bold=True)
    for k, v in [("预留库记录（已合并同批次）", len(reserve)),
                 ("① 待回填（系统无批号）", len(to_fill)),
                 ("② 真正不一致（需人工确认）", len(conflict)),
                 ("③ 系统独有批次（正常）", len(only_sys)),
                 ("④ 已一致", len(same)),
                 ("⑤ 预留库有但系统无库存行", len(no_stock)),
                 ("⑥ 预留库有但目录无此试剂", len(unmatched))]:
        ws0.append([k, v])
    ws0.column_dimensions["A"].width = 30
    ws0.column_dimensions["B"].width = 12
    wb.save(OUT)
    print(f"\n报告已生成：{OUT}")

    json.dump({"to_fill": to_fill, "conflict": conflict, "same": same,
               "no_stock": [{"code": r["code"], "name": r["name"],
                             "batch": r["batch_no"], "expiry": str(r["expiry_date"]),
                             "ids": hits} for r, hits, _ in no_stock],
               "unmatched": unmatched},
              open("outputs/reserve_match.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1, default=str)


if __name__ == "__main__":
    main()
