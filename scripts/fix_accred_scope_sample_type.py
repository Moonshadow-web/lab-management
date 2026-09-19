"""15189 认可能力范围：AC/AD 标本类型规范化（同名项目合并为一条）。

规则（用户 2026-09-19 指定）：
  - 葡萄糖、肌酸激酶同工酶CK-MB → 「血清/血浆」
  - B型钠尿肽(BNP)、肌红蛋白、肌钙蛋白I → 「血浆」
  - 其余 AC(临床化学) / AD(临床免疫学) 项目 → 「血清」

做法：按 item_name 分组（仅限 AC/AD），保留 id 最小的一条并改 sample_type，其余重复行删除。
AA(临床血液学) 不动。

用法：
  python scripts/fix_accred_scope_sample_type.py            # 预演（不改数据，输出备份）
  python scripts/fix_accred_scope_sample_type.py --apply    # 真正写入
"""
import json
import sys
import urllib.parse
import urllib.request
from collections import OrderedDict

H = "http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com"
TARGET_CATS = {"AC 临床化学", "AD 临床免疫学"}
PLASMA_ONLY = {"B型钠尿肽", "BNP", "肌红蛋白", "肌钙蛋白I", "肌钙蛋白T"}
SERUM_PLASMA = {"葡萄糖", "肌酸激酶同工酶CK-MB", "肌酸激酶同工酶"}
# 专业例外：不做「→血清」的机械替换（改了就是错的）
EXCEPTIONS = {
    "糖化血红蛋白": "全血(加肝素抗凝剂)",   # HbA1c 只能测全血（红细胞内血红蛋白），血清无意义
}


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


def target_type(name: str) -> str:
    n = (name or "").strip()
    if n in EXCEPTIONS:
        return EXCEPTIONS[n]
    if n in PLASMA_ONLY:
        return "血浆"
    if n in SERUM_PLASMA:
        return "血清/血浆"
    return "血清"


def main():
    apply_changes = "--apply" in sys.argv
    tok = login()
    rows, page = [], 1
    while True:
        c, d = call(tok, f"/api/v1/accredited-scope?page={page}&page_size=300")
        rows += d["items"]
        if len(rows) >= d["total"] or not d["items"]:
            break
        page += 1
    print(f"认可能力范围共 {len(rows)} 条")

    # 备份（无论预演都存，便于回滚）
    bak = "outputs/accredited_scope_backup_before_sample_type.json"
    json.dump(rows, open(bak, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"已备份原始数据 → {bak}\n")

    groups = OrderedDict()
    for r in rows:
        if r["category_l2"] not in TARGET_CATS:
            continue
        groups.setdefault(r["item_name"], []).append(r)

    keep, drop, unchanged = [], [], []
    for name, g in groups.items():
        g.sort(key=lambda x: x["id"])
        first = g[0]
        new_type = target_type(name)
        if first["sample_type"] != new_type:
            keep.append((first, new_type))
        else:
            unchanged.append(first)
        for extra in g[1:]:
            drop.append(extra)

    print(f"AC/AD 去重后剩 {len(groups)} 个项目"
          f"（原 {sum(len(g) for g in groups.values())} 条）\n")
    print(f"【需改标本类型】{len(keep)} 条：")
    for r, t in keep:
        print(f"  id={r['id']:<4}{str(r['item_name'])[:24]:<26}{r['sample_type']!r} → {t!r}")
    print(f"\n【标本类型已正确，不改】{len(unchanged)} 条")
    print(f"\n【需删除的重复行】{len(drop)} 条：")
    for r in drop:
        print(f"  id={r['id']:<4}{str(r['item_name'])[:24]:<26}sample_type={r['sample_type']!r}")

    print("\n【规则应用结果预览】")
    for name in sorted(groups):
        print(f"  {name[:24]:<26}→ {target_type(name)}")

    if not apply_changes:
        print("\n模式：仅预演。加 --apply 写入。")
        return

    ok = 0
    for r, t in keep:
        c, _ = call(tok, f"/api/v1/accredited-scope/{r['id']}", "PUT",
                    {"sample_type": t})
        if c == 200:
            ok += 1
        else:
            print(f"  更新失败 id={r['id']} HTTP {c}")
    print(f"\n标本类型已更新 {ok}/{len(keep)} 条")

    dok = 0
    for r in drop:
        c, _ = call(tok, f"/api/v1/accredited-scope/{r['id']}", "DELETE")
        if c == 200:
            dok += 1
        else:
            print(f"  删除失败 id={r['id']} HTTP {c}")
    print(f"重复行已删除 {dok}/{len(drop)} 条")


if __name__ == "__main__":
    main()
