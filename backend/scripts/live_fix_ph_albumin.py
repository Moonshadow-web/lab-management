"""线上修正：pH 质量目标（逐行 0.02/靶值）+ 白蛋白(A)=6.7%。

- seed：新增精确名 QualityRequirement 行（白蛋白(A)/白蛋白（A）/pH 标记串）。
- backfill_goals：按新逻辑重算已存月结行的 quality_goal（pH 用 _ph_relative_goal；白蛋白(A) 用覆盖表）。
- 验证：回查线上 pH / 白蛋白(A) 行。
"""
import urllib.request, urllib.parse, json

BASE = "http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com/api/v1"
import urllib.parse as up

req = urllib.request.Request(
    BASE + "/auth/login",
    data=up.urlencode({"username": "jinzizheng", "password": "Jzz6827556"}).encode(),
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    method="POST",
)
tok = json.loads(urllib.request.urlopen(req, timeout=40).read().decode())["access_token"]
H = {"Authorization": "Bearer " + tok}


def post(path, data=None):
    r = urllib.request.Request(BASE + path, data=json.dumps(data or {}).encode(),
                               headers={**H, "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def get(it):
    r = urllib.request.Request(BASE + f"/qc-summaries?test_item={urllib.parse.quote(it)}&page_size=100",
                               headers=H)
    return json.loads(urllib.request.urlopen(r, timeout=40).read().decode()).get("items", [])


print("=== 1) seed ===")
st, body = post("/quality-requirements/_meta/seed")
print("seed:", st, body.get("added", body) if isinstance(body, dict) else body)

print("=== 2) backfill_goals ===")
st, body = post("/qc-summaries/_backfill_goals")
print("backfill:", st, (body.get("updated"), body.get("total")) if isinstance(body, dict) else body)

print("=== 3) 验证线上 pH / 白蛋白(A) ===")
for it in ["pH", "白蛋白(A)"]:
    rows = get(it)
    if not rows:
        print(f"  {it!r}: (no rows)")
        continue
    # 取不同水平的目标值
    seen = {}
    for s in rows:
        key = (s.get("level"), s.get("target_mean"))
        if key not in seen:
            seen[key] = s.get("quality_goal")
    for (lvl, tm), goal in seen.items():
        print(f"  {it!r:10s} level={lvl} 靶值={tm} 质量目标={goal!r}")
