import urllib.request, urllib.parse, json, time

BASE = "http://127.0.0.1:8123"

def req(method, path, token=None, data=None, ctype="application/json"):
    url = BASE + path
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    body = None
    if data is not None:
        if isinstance(data, str):
            body = data.encode("utf-8")
        elif isinstance(data, bytes):
            body = data
        else:
            body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = ctype
    r = urllib.request.Request(url, method=method, headers=headers, data=body)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")

# wait for backend
for i in range(20):
    try:
        s, _ = req("GET", "/docs")
        if s == 200:
            break
    except Exception:
        pass
    time.sleep(1)
else:
    print("backend not up"); raise SystemExit(1)

# login (OAuth2 form)
s, b = req("POST", "/api/v1/auth/login", data=urllib.parse.urlencode({"username": "admin", "password": "admin123"}), ctype="application/x-www-form-urlencoded")
assert s == 200, (s, b)
token = json.loads(b)["access_token"]

# list 2026
s, b = req("GET", "/api/v1/eqa-plans?year=2026&page_size=500", token=token)
assert s == 200, (s, b)
rows = json.loads(b)["items"]
print("2026 计划总数:", len(rows))

# renamed check: 常规化学B should appear for 北京市 ids 42/43
cx = [r for r in rows if r["id"] in (42, 43)]
for r in cx:
    print(f"  #{r['id']} program={r['program']!r} (期望 常规化学B) ->", "OK" if r["program"]=="常规化学B" else "FAIL")

# new records check
for nm in ["血清蛋白电泳","脂类B","甲状腺功能检测","骨代谢标志物"]:
    rs = [r for r in rows if r["program"]==nm]
    print(f"  {nm}: {len(rs)} 行 program={rs[0]['program']!r} group={rs[0]['group']!r} due={rs[0]['due_date']}")

# any leftover abbreviation?
leftover = [r["program"] for r in rows if r["program"] in ("唐筛","产筛","感A","感B","感C","血气","脂类","糖化","常规化学","常规化学2","BNP","CYS-C","IL-6","PCT","AMH","SAA","VWF","抗Xa","肝炎","DD FDP","尿定量生化","尿蛋白标志物","药物监测","感染快检","甲功正确度","凝血","肿标A","肝纤")]
print("残留缩写 program:", leftover if leftover else "无")

# notifications refreshed?
s, b = req("GET", "/api/v1/notifications?ref_type=eqa_return&page_size=500", token=token)
nts = json.loads(b)["items"] if s==200 else []
print("eqa_return 通知条数:", len(nts))
# show a sample
if nts:
    print("  示例:", nts[0]["title"])
print("VERIFY DONE")
