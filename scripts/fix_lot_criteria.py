"""按科室给定的允许偏倚逐项修正试剂验收记录，并移除不参与验收的项目。

用法：python scripts/fix_lot_criteria.py [--apply]
"""
import json
import sys
import urllib.parse
import urllib.request

H = "http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com"

# 试剂名关键词 → (允许偏倚, 偏倚方式, 判定标准说明)
CRITERIA = [
    ("丙型肝炎病毒抗体", 15, "relative", "科室规定：允许相对偏倚 15%"),
    ("梅毒螺旋体抗体", 15, "relative", "科室规定：允许相对偏倚 15%"),
    ("人类免疫缺陷病毒", 15, "relative", "科室规定：允许相对偏倚 15%"),
    ("乙型肝炎病毒表面抗原", 15, "relative", "科室规定：允许相对偏倚 15%"),
    ("内因子抗体", 15, "relative", "科室规定：允许相对偏倚 15%"),
    ("抗缪勒管激素", 12.5, "relative", "科室规定：允许相对偏倚 12.5%"),
    ("未结合雌三醇", 15, "relative", "科室规定：允许相对偏倚 15%"),
    ("D-二聚体", 15, "relative", "科室规定：允许相对偏倚 15%"),
    ("乳酸测定", 10, "relative", "科室规定：允许相对偏倚 10%"),
    ("二氧化碳结合力", 8, "relative",
     "科室规定：±8%（相对）或 ±5 mmHg（绝对）——如需绝对，把「偏倚方式」切成绝对、允许偏倚填 5"),
]

# 不参与批间验证的项目（关键词）
EXCLUDE = ["特异性生长因子", "抗凝血酶"]


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
    print(f"当前验收记录 {len(rows)} 条\n")

    updates, deletes = [], []
    for r in rows:
        nm = r["reagent_name"] or ""
        if any(k in nm for k in EXCLUDE):
            deletes.append(r)
            continue
        for kw, val, mode, label in CRITERIA:
            if kw in nm:
                cur = str(r.get("allow_bias_pct") or "")
                if cur.strip() == str(val) and (r.get("bias_mode") or "relative") == mode:
                    break
                updates.append((r, val, mode, label))
                break

    print(f"【需设置允许偏倚】{len(updates)} 条")
    for r, val, mode, _l in updates:
        print(f"  #{r['id']:<4}{str(r['reagent_name'])[:32]:<34}"
              f"{r.get('allow_bias_pct') or '(空)'} → {val} ({'相对%' if mode == 'relative' else '绝对'})")

    print(f"\n【需删除·不参与验收】{len(deletes)} 条")
    for r in deletes:
        print(f"  #{r['id']:<4}{str(r['reagent_name'])[:36]}")

    if not apply_changes:
        print("\n模式：仅预演。加 --apply 才真正写入。")
        return

    ok = 0
    for r, val, mode, label in updates:
        body = {"allow_bias_pct": str(val), "bias_mode": mode,
                "criterion_source": "manual", "criterion_label": label}
        c, _ = call(tok, f"/api/v1/reagent/lot-verifications/{r['id']}", "PUT", body)
        if c == 200:
            ok += 1
        else:
            print(f"  设置失败 #{r['id']} HTTP {c}")
    print(f"已设置 {ok}/{len(updates)} 条")

    dok = 0
    for r in deletes:
        c, _ = call(tok, f"/api/v1/reagent/lot-verifications/{r['id']}", "DELETE")
        if c == 200:
            dok += 1
    print(f"已删除 {dok}/{len(deletes)} 条")


if __name__ == "__main__":
    main()
