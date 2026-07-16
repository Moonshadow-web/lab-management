import json
import urllib.request
import urllib.parse
import urllib.error

BASE = "http://127.0.0.1:8123"
TOKEN = None

DATA_FILE = "D:/workbuddyprojects/网页版-生免速查工具/outputs/beijing_eqa_2026_data.json"


def req(method, path, data=None, form=False):
    url = BASE + path
    h = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
    body = None
    if data is not None:
        if form:
            body = urllib.parse.urlencode(data).encode()
            h["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            body = json.dumps(data).encode()
            h["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=body, method=method, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=15) as resp:
            ct = resp.headers.get("Content-Type", "")
            if "application/json" in ct:
                return resp.status, json.loads(resp.read().decode())
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode()
            return e.code, json.loads(body) if body.startswith("{") else body
        except Exception:
            return e.code, ""


# 1) 登录
s, b = req("POST", "/api/v1/auth/login", {"username": "admin", "password": "admin123"}, form=True)
if s != 200 or not isinstance(b, dict) or "access_token" not in b:
    print("登录失败", s, b)
    raise SystemExit(1)
TOKEN = b["access_token"]
print("登录成功")

with open(DATA_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

year = data["year"]

# 2) 清理旧 2026 北京市 生化/免疫计划
print(f"-- 清理旧 {year} 北京市 生化/免疫计划")
for program in ["生化", "免疫"]:
    page = 1
    while True:
        params = urllib.parse.urlencode({
            "year": year,
            "org": "北京市",
            "program": program,
            "page": page,
            "page_size": 100
        }, quote_via=urllib.parse.quote)
        s, b = req("GET", f"/api/v1/eqa-plans?{params}")
        if s != 200 or not isinstance(b, dict):
            break
        items = b.get("items", [])
        if not items:
            break
        for it in items:
            ds, db = req("DELETE", f"/api/v1/eqa-plans/{it['id']}")
            print(f"  删除 {program} {it.get('item')} 轮次{it.get('round_no')} id={it['id']} status={ds}")
        page += 1

# 3) 导入新计划
imported = 0
for plan in data["plans"]:
    for r in plan["rounds"]:
        payload = {
            "year": year,
            "org": plan["org"],
            "program": plan["program"],
            "item": plan["item"],
            "round_no": r["round_no"],
            "sample_date": r["sample_date"],
            "due_date": r["due_date"],
            "returned": False,
            "result": "",
            "qualified": False,
            "score": "",
            "note": f"细项：{plan['detail']}",
        }
        s, b = req("POST", "/api/v1/eqa-plans", payload)
        if s not in (200, 201):
            print(f"FAIL 导入 {plan['program']} {plan['item']} 轮次{r['round_no']}: {s} {b}")
        else:
            imported += 1

print(f"\n导入完成：共 {imported} 条")

# 4) 简单验证
s, b = req("GET", f"/api/v1/eqa-plans/summary?year={year}&half=0")
print(f"\n全年统计：{b}")

s, b = req("GET", f"/api/v1/eqa-plans/alerts")
print(f"当前检测提醒：{len(b) if isinstance(b, list) else b} 条")

if data.get("missing_pages"):
    print(f"\n⚠️ 以下 {len(data['missing_pages'])} 项因缺少北京计划表第 3/4 页，未导入：")
    for m in data["missing_pages"]:
        print(f"  - {m['category']} {m['docx_group']}（{m['docx_detail']}）：{m['reason']}")
