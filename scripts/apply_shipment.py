"""按发货记录初始化：① 补全库存无批号的试剂 ② 生成批号变更的待验收记录。

依赖 outputs/shipment_analysis.json（由 analyze_shipment.py 生成）。

用法：
  python scripts/apply_shipment.py --dry-run     # 只看将要做什么
  python scripts/apply_shipment.py --apply       # 实际执行

去重规则（重要）：系统试剂目录里同一支试剂可能存在多个条目
（如「丙型肝炎病毒抗体检测试剂盒」/「（化学发光法）」/「（电化学发光法）」），
生成验收记录时按 (货号, 旧批号, 新批号) 归并，只保留一条，避免重复生成。
"""
import json
import re
import sys
import urllib.parse
import urllib.request
from collections import defaultdict

H = "http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com"
SRC = "outputs/shipment_analysis.json"


def login():
    data = urllib.parse.urlencode(
        {"username": "jinzizheng", "password": "Jzz6827556"}).encode()
    req = urllib.request.Request(H + "/api/v1/auth/login", data=data)
    return json.load(urllib.request.urlopen(req, timeout=60))["access_token"]


def get(tok, path):
    req = urllib.request.Request(H + path,
                                 headers={"Authorization": "Bearer " + tok})
    return json.load(urllib.request.urlopen(req, timeout=300))


def post(tok, path, body):
    req = urllib.request.Request(
        H + path, data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": "Bearer " + tok,
                 "Content-Type": "application/json"})
    try:
        return 200, json.load(urllib.request.urlopen(req, timeout=300))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}


def paged(tok, path, size=200):
    out, page = [], 1
    while True:
        d = get(tok, f"{path}&page={page}&page_size={size}")
        out += d["items"]
        if len(out) >= d["total"] or not d["items"]:
            break
        page += 1
    return out


METHOD_KW = ("化学发光", "电化学发光", "酶法", "免疫比浊", "凝固法", "发色底物",
             "胶乳", "比色", "电泳", "层析", "速率法", "底物法", "尿素酶",
             "己糖激酶", "乳酸脱氢酶法", "磷钼酸盐", "溴甲酚绿", "重氮盐",
             "NPP", "GPO", "PNP", "MDH", "TPTZ", "Nitroso", "酶循坏", "酶循环",
             "免疫比浊法", "胶乳增强", "尿酸酶", "胆固醇氧化酶")


def norm_name(name: str) -> str:
    """归一化名称，识别系统目录里同一试剂的重复条目。

    **只去掉「方法学」括号**（如「（化学发光法）」「（酶法）」），
    保留有区分意义的括号（如质控品的「（540-1）」），避免误合并。
    """
    if not name:
        return ""
    t = re.split(r"[/／]", str(name))[-1]

    def _strip(m):
        inner = m.group(1)
        return "" if any(k.lower() in inner.lower() for k in METHOD_KW) else m.group(0)

    t = re.sub(r"[（(]([^（）()]*)[）)]", _strip, t)
    t = re.sub(r"[\s　]", "", t).upper()
    for kw in ("测定试剂盒", "检测试剂盒", "诊断试剂盒", "测定试剂", "检测试剂",
               "试剂盒", "试剂"):
        t = t.replace(kw, "")
    return t.strip()


def item_code(name: str) -> str:
    if not name:
        return ""
    head = re.split(r"[/／\-－]", str(name))[0].strip().upper()
    return head if re.match(r"^[A-Z0-9][A-Z0-9.]{1,20}$", head or "") else ""


def main():
    apply_changes = "--apply" in sys.argv
    tok = login()
    data = json.load(open(SRC, encoding="utf-8"))
    items = {i["id"]: i for i in paged(tok, "/api/v1/reagent/items?page=1")}

    # ── ① 补批号 ──────────────────────────────────────────────
    fill = [x for x in data["fill"] if x.get("stock_id")]
    ups = [{"stock_id": x["stock_id"], "batch_no": x["batch_no"],
            "expiry_date": x["expiry"]} for x in fill]
    print(f"【① 补批号】待补 {len(ups)} 条")
    if ups:
        code, r = post(tok, "/api/v1/reagent/stock/_set-batch",
                       {"updates": ups, "dry_run": not apply_changes})
        print(f"    接口返回 HTTP {code}：count={r.get('count')} merged={r.get('merged')} "
              f"skipped={len(r.get('skipped') or [])}")
        for c in (r.get("changes") or [])[:5]:
            print(f"      stock{c['stock_id']} item{c['item_id']}: "
                  f"'{c['old_batch'] or '(空)'}' → '{c['new_batch']}' {c['new_expiry']}")
        if len(r.get("changes") or []) > 5:
            print(f"      ... 共 {len(r['changes'])} 条")

    # ── ② 生成待验收记录 ──────────────────────────────────────
    # 按 (货号, 旧批号, 新批号) 归并，同一支试剂的多个目录条目只留一条
    groups = defaultdict(list)
    for x in data["changed"]:
        it = items.get(x["item_id"])
        if not it:
            continue
        code = item_code(it.get("name"))
        # 无货号的用「归一化名称主体」做键，才能把「丙型肝炎病毒抗体检测试剂盒」
        # 与「…（化学发光法）」「…（电化学发光法）」这些重复目录条目合并
        key = code if code else ("N:" + norm_name(it.get("name")))
        if not code and not norm_name(it.get("name")):
            key = f"__id{x['item_id']}"
        key = (key, it.get("type") or "")   # 试剂/质控品/校准品 不混为一谈
        groups[(key, x["old_batch"], x["new_batch"])].append(x)

    gen_items, dropped = [], []
    for (code, ob, nb), lst in groups.items():
        # 优先取「名称最短」的条目（通常是主条目，不带方法学后缀）
        lst.sort(key=lambda z: len(str(z.get("name") or "")))
        keep = lst[0]
        gen_items.append({
            "item_id": keep["item_id"],
            "old_batch_no": ob, "new_batch_no": nb,
            "old_expiry_date": keep.get("old_expiry") or None,
            "new_expiry_date": keep.get("new_expiry") or None,
            "change_date": keep.get("new_date") or None,
        })
        if len(lst) > 1:
            dropped.append((code, ob, nb, len(lst) - 1))

    print()
    print(f"【② 生成待验收记录】{len(data['changed'])} 条 → 去重后 {len(gen_items)} 条"
          f"（合并掉 {sum(d[3] for d in dropped)} 条重复目录条目）")
    if not apply_changes:
        for g in gen_items[:10]:
            it = items.get(g["item_id"], {})
            print(f"      [预演] {str(it.get('name'))[:28]:<30} "
                  f"{g['old_batch_no']} → {g['new_batch_no']}  变更日期 {g['change_date']}")
        if len(gen_items) > 10:
            print(f"      ... 共 {len(gen_items)} 条")
    if gen_items and apply_changes:
        code, r = post(tok, "/api/v1/reagent/lot-verifications/_generate",
                       {"items": gen_items, "sample_count": 5})
        print(f"    接口返回 HTTP {code}：新建 {r.get('created_count')} 条，"
              f"跳过 {r.get('skipped_count')} 条")
        for c in (r.get("created") or [])[:8]:
            print(f"      #{c['id']} {str(c['reagent_name'])[:26]:<28} "
                  f"{c['old_batch_no']} → {c['new_batch_no']}  允许偏倚={c['allow_bias_pct']}%")
        if len(r.get("created") or []) > 8:
            print(f"      ... 共 {len(r['created'])} 条")
        miss = [c for c in (r.get("created") or []) if not c.get("allow_bias_pct")]
        if miss:
            print(f"    ⚠ 其中 {len(miss)} 条未自动匹配到判定标准，需手工填允许偏倚：")
            for c in miss[:12]:
                print(f"      #{c['id']} {str(c['reagent_name'])[:32]}")

    print()
    print("模式:", "已执行" if apply_changes else "仅预演（未改数据）")


if __name__ == "__main__":
    main()
