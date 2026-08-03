import os, sys, requests

BASE = "http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com/api/v1"
TARGET = ["SM-SOP-552", "SM-SOP-553", "SM-SOP-554", "SM-SOP-555"]
APPLY = os.environ.get("APPLY") == "1"

r = requests.post(BASE + "/auth/login", data={"username": "jinzizheng", "password": "Jzz6827556"}, timeout=120)
tok = r.json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}

# 全量翻页
items = []
page = 1
while True:
    rr = requests.get(BASE + "/documents", params={"page": page, "page_size": 200}, headers=H, timeout=120)
    j = rr.json()
    items += j["items"]
    if page * 200 >= j.get("total", 0) or not j["items"]:
        break
    page += 1

hits = [it for it in items if (it.get("doc_number") or "").replace("MHZYY-JYK-", "").replace("HZYY-JYK-", "") in TARGET]
print(f"匹配到 {len(hits)} 条:")
for it in hits:
    print(f"  id={it['id']} doc_number={it['doc_number']!r} status={it['status']!r} title={it['title']!r}")

if not APPLY:
    print("\n[DRY_RUN] 未执行变更，设置 APPLY=1 后运行。")
    sys.exit(0)

ok, fail = 0, 0
for it in hits:
    if it["status"] == "生效":
        print(f"  id={it['id']} 已是生效，跳过")
        ok += 1
        continue
    rr = requests.patch(BASE + f"/documents/{it['id']}", json={"status": "生效"}, headers=H, timeout=120)
    if rr.ok:
        print(f"  id={it['id']} 状态 {it['status']} → 生效  ✅")
        ok += 1
    else:
        print(f"  id={it['id']} 失败 {rr.status_code} {rr.text[:120]}  ❌")
        fail += 1

print(f"\n结果: 成功={ok}  失败={fail}")
