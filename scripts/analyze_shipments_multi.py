"""分析多份发货/销售记录（支持不同表格式），找出：① 可补批号的试剂 ② 批号变更需验证的试剂。

支持的表格式：
  A. 安图销售数据：表头第1行，列=序号/发货单号/发货日期/客户简称/存货名称/存货编码/规格型号/批号/数量
  B. 销售明细表：第1行大标题、第2行表头、第3行起数据，单据日期有合并单元格需前向填充；
     列=单据日期/商品名称/规格型号/批次/生产日期/到期日/单位/数量
  C. 民航预留库/发货记录（此前用过）：dynreport，列含 业务日期/商品名/批号/有效期/物料编码货号/器械货品名

统一归一化为 {date, name, spec, batch_no, expiry, qty, code} 后合并处理。
用法：python scripts/analyze_shipments_multi.py
"""
import json
import re
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date, datetime

from openpyxl import load_workbook

H = "http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com"
OUT = "outputs/shipment_analysis_multi.json"

# 非「试剂」关键词：本模块只验收试剂，排除校准品/质控品/电解质/耗材及科室明确不做的项目
NON_REAGENT_KW = ("校准", "定标", "质控", "标准品", "参考品", "电解质", "参比液",
                  "内标液", "参比电极", "缓冲液", "特异性生长因子", "抗凝血酶",
                  "狼疮抗凝物",
                  # 耗材/辅助
                  "清洗液", "反应杯", "分析杯", "分析头", "底物液", "稀释液",
                  "洗针液", "缓冲", "ProCell", "CleanCell", "ProbeWash", "ProClean")

SOURCES = [
    {"path": r"C:/Users/81526/Desktop/民航1-9销售数据安图.xlsx",
     "sheet": "Sheet2", "header": 1, "kind": "autobio"},
    {"path": r"C:/Users/81526/Desktop/销售明细表-2026-1-9.xlsx",
     "sheet": "sheet1", "header": 2, "data_start": 3, "kind": "sales"},
]


# ── 名称归一化 ────────────────────────────────────────────────
METHOD_KW = ("化学发光", "电化学发光", "酶法", "免疫比浊", "凝固法", "发色底物",
             "胶乳", "比色", "电泳", "层析", "速率法", "底物法", "尿素酶",
             "己糖激酶", "乳酸脱氢酶法", "磷钼酸盐", "溴甲酚绿", "重氮盐",
             "NPP", "GPO", "PNP", "MDH", "TPTZ", "Nitroso", "酶循坏", "酶循环",
             "免疫透射比浊", "胶乳增强", "颗粒增强型", "磁微粒", "苯三酚红")


_ROMAN = {"Ⅰ": "I", "Ⅱ": "II", "Ⅲ": "III", "Ⅳ": "IV", "Ⅴ": "V"}


def norm_name(name: str) -> str:
    """归一化名称：去厂家后缀、方法学括号、通用词，用于跨表匹配。"""
    if not name:
        return ""
    t = str(name)
    for k, v in _ROMAN.items():      # 罗马数字→拉丁字母：Ⅱ型 ↔ II型
        t = t.replace(k, v)
    t = re.split(r"[/／]", t)[-1]
    # 厂家后缀：-罗 / -德 / -柏荣 / -日新 / （罗）等
    t = re.sub(r"[-－—]+\s*(罗|德|柏荣|日新|安图|雅培|西门子|迈瑞|贝克曼|利德曼)\s*$", "", t)
    t = re.sub(r"[（(](罗|德|柏荣|日新|安图|雅培|西门子|迈瑞|贝克曼|利德曼)[）)]\s*$", "", t)

    def _strip(m):
        inner = m.group(1)
        return "" if any(k.lower() in inner.lower() for k in METHOD_KW) else m.group(0)

    t = re.sub(r"[（(]([^（）()]*)[）)]", _strip, t)
    t = re.sub(r"[\s　]", "", t).upper()
    t = re.sub(r"[（()）\[\]【】]", "", t)
    # ① 先去掉尾部英文缩写（HBeAg / Anti-HBc / total P1NP 等）——必须在「抗体」处理之前，
    #    否则系统名「…核心抗体检测试剂盒Anti-HBc」清理不到尾部缩写，导致与表名对不上
    t = re.sub(r"(HBEAG|ANTI-?HBS|ANTI-?HBC|ANTI-?HBE|TOTAL-?P1NP|P1NP|HBSAG|HBCAB|HBSAB)$", "", t)
    # ② 「抗体」不删除而是移到末尾：既解决「戊型肝炎病毒抗体IgM」vs「戊型肝炎病毒IgM抗体」
    #    的词序差异，又不会把「甲状腺球蛋白抗体」错并成「甲状腺球蛋白」
    has_ab = "抗体" in t
    for kw in ("测定试剂盒", "检测试剂盒", "诊断试剂盒", "测定试剂", "检测试剂",
               "试剂盒", "试剂", "测定", "检测", "抗体"):
        t = t.replace(kw, "")
    if has_ab and not t.endswith("抗体"):
        t += "抗体"
    t = re.sub(r"[-－—]+$", "", t)   # 清理残留连字符（厂家后缀去掉后可能剩 --）
    return t.strip()


# ── 人工确认映射（用户 2026-09-18 核对确认的「表内商品名 ↔ 系统试剂名」）──
# key = 表侧归一化名, value = 系统侧归一化名。这些名称差异靠算法无法安全判定，
# 必须人工确认后写死，避免误配到错误的试剂。
MANUAL_MAP = {
    "皮质醇": "人皮质醇",              # 系统叫「人皮质醇检测试剂盒（磁微粒化学发光法）」
    "载脂蛋白A1": "载脂蛋白A1合",       # 系统名有错别字「试剂合」（应为盒）
    "癌胚抗原": "癌胚抗原定量",         # 系统叫「癌胚抗原定量测定试剂盒」
    "微量白蛋白": "微量白蛋白液体尿",     # 系统叫「微量白蛋白液体试剂盒（尿）」
    "免疫球蛋白G": "尿免疫球蛋白G",      # 柏荣，id=210（注意 id=209 是德赛的血清 IgG，非同一试剂）
    "转铁蛋白": "尿转铁蛋白",           # 柏荣，id=215
    # 「脑脊液与尿蛋白」：表里写「连苯三酚红法」，系统写「邻苯三酚红法」，同一方法异写
    "脑脊液与尿蛋白": "脑脊液与尿蛋白",
}


def item_code(name: str) -> str:
    if not name:
        return ""
    head = re.split(r"[/／\-－]", str(name))[0].strip().upper()
    return head if re.match(r"^[A-Z0-9][A-Z0-9.]{1,20}$", head or "") else ""


def is_reagent_name(name: str) -> bool:
    n = str(name or "")
    return not any(kw in n for kw in NON_REAGENT_KW)


def to_date(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str) and v.strip():
        return v.strip()[:10]
    return None


# ── 读表 ──────────────────────────────────────────────────────
def read_autobio(path, sheet, header):
    ws = load_workbook(path, read_only=True)[sheet]
    out = []
    for r in ws.iter_rows(min_row=header + 1, values_only=True):
        if not r[4]:
            continue
        out.append({"date": str(to_date(r[2]) or ""), "name": str(r[4]).strip(),
                    "spec": str(r[6] or "").strip(), "batch_no": str(r[7] or "").strip(),
                    "expiry": None, "qty": r[8], "code": str(r[5] or "").strip().upper(),
                    "src": "安图"})
    return out


def read_sales(path, sheet, header, data_start):
    ws = load_workbook(path, read_only=True)[sheet]
    out, last_date = [], ""
    for r in ws.iter_rows(min_row=data_start, values_only=True):
        if not r[1]:
            continue
        d = to_date(r[0])
        if d:
            last_date = str(d)
        out.append({"date": last_date, "name": str(r[1]).strip(),
                    "spec": str(r[2] or "").strip(), "batch_no": str(r[3] or "").strip(),
                    "expiry": to_date(r[5]), "qty": r[7], "code": "",
                    "src": "销售明细"})
    return out


def read_all():
    rows = []
    for s in SOURCES:
        if s["kind"] == "autobio":
            part = read_autobio(s["path"], s["sheet"], s["header"])
        else:
            part = read_sales(s["path"], s["sheet"], s["header"], s.get("data_start", 3))
        print(f"  {s['path'].split('/')[-1]} ({s['kind']}): {len(part)} 行")
        rows += part
    return rows


# ── API ───────────────────────────────────────────────────────
def login():
    data = urllib.parse.urlencode(
        {"username": "jinzizheng", "password": "Jzz6827556"}).encode()
    r = urllib.request.Request(H + "/api/v1/auth/login", data=data)
    return json.load(urllib.request.urlopen(r, timeout=60))["access_token"]


def get(tok, path):
    r = urllib.request.Request(H + path,
                               headers={"Authorization": "Bearer " + tok})
    return json.load(urllib.request.urlopen(r, timeout=300))


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
    print("读取发货/销售记录：")
    ship = read_all()
    print(f"合计 {len(ship)} 行\n")

    tok = login()
    items = {i["id"]: i for i in paged(tok, "/api/v1/reagent/items?page=1")}
    stock = paged(tok, "/api/v1/reagent/stock?page=1")
    stock_by_item = defaultdict(list)
    for s in stock:
        stock_by_item[s["item_id"]].append(s)

    idx_code, idx_name = defaultdict(list), defaultdict(list)
    for iid, it in items.items():
        if (it.get("type") or "") != "试剂":
            continue                      # 只看试剂
        c = item_code(it.get("name"))
        if c:
            idx_code[c].append(iid)
        n = norm_name(it.get("name"))
        if n:
            idx_name[n].append(iid)
    print(f"系统试剂目录 {len(items)} 条（其中试剂 {sum(1 for i in items.values() if i.get('type') == '试剂')} 条）")

    by_item, unmatched, excluded = defaultdict(list), [], []
    for r in ship:
        if not is_reagent_name(r["name"]):
            excluded.append(r)
            continue
        hits = idx_code.get(r["code"], []) if r["code"] else []
        how = "货号"
        if not hits:
            n = norm_name(r["name"])
            hits = idx_name.get(n, [])
            how = "名称"
        if not hits:
            # 包含匹配兜底：要求表侧归一化名 ≥5 字且候选唯一，避免误配
            n = norm_name(r["name"])
            if len(n) >= 5:
                cands = sorted({iid for key, ids in idx_name.items()
                                if n and (n in key or key in n) for iid in ids})
                if len(cands) == 1:
                    hits, how = cands, "名称包含"
        if not hits:
            # 人工确认映射兜底
            n = norm_name(r["name"])
            tgt = MANUAL_MAP.get(n)
            if tgt:
                hits = idx_name.get(tgt, [])
                how = "人工映射"
        hits = sorted(set(hits))
        if not hits:
            unmatched.append(r)
            continue
        for iid in hits:
            by_item[iid].append({**r, "how": how})

    fill, changed, unchanged = [], [], []
    for iid, recs in by_item.items():
        it = items[iid]
        batches = {}
        for r in recs:
            b = r["batch_no"]
            if not b:
                continue
            d = r["date"] or ""
            if b not in batches or d < batches[b]["date"]:
                batches[b] = {"date": d, "expiry": str(r["expiry"] or ""),
                              "qty": r["qty"], "how": r.get("how", "")}
        if not batches:
            continue
        tl = sorted(batches.items(), key=lambda x: x[1]["date"])
        latest = tl[-1]
        cur = stock_by_item.get(iid, [])
        cur_batches = [((s["batch_no"] or "").strip(), str(s["expiry_date"] or "")) for s in cur]

        if len(tl) >= 2:
            prev = tl[-2]
            changed.append({
                "item_id": iid, "name": it.get("name"), "spec": it.get("spec"),
                "library": it.get("library"),
                "old_batch": prev[0], "old_date": prev[1]["date"], "old_expiry": prev[1]["expiry"],
                "new_batch": latest[0], "new_date": latest[1]["date"], "new_expiry": latest[1]["expiry"],
                "batch_count": len(tl),
                "all_batches": [f"{b}/{v['date']}" for b, v in tl],
                "cur_batches": cur_batches, "how": latest[1]["how"],
            })
        else:
            unchanged.append({"item_id": iid, "name": it.get("name"),
                              "batch": latest[0], "date": latest[1]["date"]})

        if cur and not any((s["batch_no"] or "").strip() for s in cur):
            fill.append({"item_id": iid, "name": it.get("name"), "spec": it.get("spec"),
                         "library": it.get("library"), "batch_no": latest[0],
                         "expiry": latest[1]["expiry"], "ship_date": latest[1]["date"],
                         "qty": cur[0]["quantity"], "stock_id": cur[0]["id"]})

    print()
    print("=" * 104)
    print(f"【A】2026 年有批号变更（≥2 批）的试剂：{len(changed)} 个")
    print("=" * 104)
    for x in sorted(changed, key=lambda z: (z["library"] or "", z["name"] or "")):
        print(f"  {x['library'] or '':<6}{str(x['name'])[:30]:<32}"
              f"旧 {x['old_batch']}({x['old_date']}) → 新 {x['new_batch']}({x['new_date']})  共{x['batch_count']}批")
    print()
    print(f"【B】可补批号（系统库存无批号）：{len(fill)} 个")
    for x in sorted(fill, key=lambda z: (z["library"] or "", z["name"] or "")):
        print(f"  {x['library'] or '':<6}{str(x['name'])[:32]:<34}→ {x['batch_no']:<14} "
              f"效期 {x['expiry'] or '(无)'} (发货{x['ship_date']})")
    print()
    print(f"【C】只有一个批号（无需批间验证）：{len(unchanged)} 个")
    print(f"【D】按规则排除（校准品/质控品/耗材/电解质等）：{len(excluded)} 行")
    print(f"【E】未匹配到系统试剂：{len(unmatched)} 行")
    for r in unmatched[:12]:
        print(f"      [{r['src']}] {str(r['name'])[:36]:<38}批号 {r['batch_no']}")

    json.dump({"changed": changed, "fill": fill, "unchanged": unchanged,
               "excluded_count": len(excluded),
               "unmatched": [{"src": r["src"], "name": r["name"], "batch": r["batch_no"],
                              "date": r["date"]} for r in unmatched]},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(f"\n明细已存 {OUT}")


if __name__ == "__main__":
    main()
