"""EQA 室间质评 端到端 HTTP 验证脚本。
登录 admin/admin123 -> 建 4 条计划(逾期/临期/未来/已回报) -> 验证 alerts/summary/summary-text/export/notifications -> 清理。
"""
import urllib.request
import urllib.parse
import json
import datetime
import os

os.makedirs("/d/workbuddyprojects/网页版-生免速查工具/outputs", exist_ok=True)

BASE = "http://127.0.0.1:8123"
TOKEN = None
FAILS = []


def req(method, path, data=None, form=False, raw=False, headers=None):
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
    if headers:
        h.update(headers)
    r = urllib.request.Request(url, data=body, method=method, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            ct = resp.headers.get("Content-Type", "")
            if raw or "application/json" not in ct:
                return resp.status, resp.read(), resp.headers
            return resp.status, json.loads(resp.read().decode()), resp.headers
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(), e.headers


def check(name, cond, detail=""):
    mark = "PASS" if cond else "FAIL"
    print(f"[{mark}] {name}" + (f" -- {detail}" if detail else ""))
    if not cond:
        FAILS.append(name)


# 1) 登录
s, b, _ = req("POST", "/api/v1/auth/login",
              {"username": "admin", "password": "admin123"}, form=True)
check("登录 admin", s == 200 and isinstance(b, dict) and "access_token" in b, f"status={s}")
if isinstance(b, dict) and "access_token" in b:
    TOKEN = b["access_token"]

# 2) 先清理 2026 年已有计划(避免脏数据干扰)
s, b, _ = req("GET", "/api/v1/eqa-plans?year=2026&limit=100")
existing = (b or {}).get("items", []) if isinstance(b, dict) else []
for p in existing:
    req("DELETE", f"/api/v1/eqa-plans/{p['id']}")
print(f"-- 清理已有 2026 计划 {len(existing)} 条")

# 3) 建 4 条计划：A 逾期(H1)/ B 临期(H2)/ C 未来(H2)/ D 已回报(H2)
plans = [
    {"year": 2026, "org": "卫健委临检中心", "program": "生化", "item": "葡萄糖", "round_no": "R1",
     "sample_date": "2026-03-01", "due_date": "2026-03-15", "returned": False, "qualified": True, "score": "95", "result": "合格"},
    {"year": 2026, "org": "卫健委临检中心", "program": "免疫", "item": "PCT", "round_no": "R1",
     "sample_date": "2026-07-10", "due_date": "2026-07-30", "returned": False, "qualified": False, "score": "80", "result": "不合格"},
    {"year": 2026, "org": "北京市临检中心", "program": "生化", "item": "肌酐", "round_no": "R2",
     "sample_date": "2026-12-01", "due_date": "2026-12-15", "returned": False, "qualified": False, "score": "", "result": ""},
    {"year": 2026, "org": "北京市临检中心", "program": "免疫", "item": "TnI", "round_no": "R2",
     "sample_date": "2026-07-05", "due_date": "2026-07-20", "returned": True, "qualified": True, "score": "98", "result": "合格"},
]
created = []
for p in plans:
    s, b, _ = req("POST", "/api/v1/eqa-plans", p)
    check(f"创建计划 {p['program']}/{p['item']}", s in (200, 201) and isinstance(b, dict) and "id" in b, f"status={s}")
    if isinstance(b, dict) and "id" in b:
        created.append(b["id"])
print(f"-- 已创建 {len(created)} 条计划")

# 4) /alerts 应只含 A(逾期) + B(临期)，不含 C(未来>30d) 与 D(已回报)
s, b, _ = req("GET", "/api/v1/eqa-plans/alerts")
alerts = b if isinstance(b, list) else []
check("alerts 返回 200", s == 200)
check("alerts 仅含临期/逾期(2条)", len(alerts) == 2, f"got {len(alerts)}: {[a.get('round_no') for a in alerts]}")
alert_ids = {a.get("plan_id") for a in alerts}
# 通过 due_date 反推：A=2026-03-15 逾期, B=2026-07-30 临期
due_set = {a.get("due_date") for a in alerts}
check("alerts 不含未来计划(2026-12-15)", "2026-12-15" not in due_set)
check("alerts 不含已回报计划(2026-07-20)", "2026-07-20" not in due_set)
levels = {a.get("due_date"): a.get("level") for a in alerts}
check("逾期项 level=danger", levels.get("2026-03-15") == "danger", str(levels))
check("临期项 level=warning", levels.get("2026-07-30") == "warning", str(levels))

# 5) /summary 统计：全年(0)/上半年(1)/下半年(2)
s, b, _ = req("GET", "/api/v1/eqa-plans/summary?year=2026&half=0")
check("summary 全年 total=4", isinstance(b, dict) and b.get("total") == 4, str(b.get("total") if isinstance(b, dict) else b))
check("summary 全年 returned=1", isinstance(b, dict) and b.get("returned") == 1, str(b.get("returned") if isinstance(b, dict) else b))
check("summary 全年 return_rate≈25%", isinstance(b, dict) and abs((b.get("return_rate") or 0) - 25.0) < 0.1, str(b.get("return_rate") if isinstance(b, dict) else b))
check("summary 全年 qualified=2", isinstance(b, dict) and b.get("qualified") == 2, str(b.get("qualified") if isinstance(b, dict) else b))

s, b, _ = req("GET", "/api/v1/eqa-plans/summary?year=2026&half=1")
check("summary 上半年 total=1", isinstance(b, dict) and b.get("total") == 1, str(b.get("total") if isinstance(b, dict) else b))

s, b, _ = req("GET", "/api/v1/eqa-plans/summary?year=2026&half=2")
check("summary 下半年 total=3", isinstance(b, dict) and b.get("total") == 3, str(b.get("total") if isinstance(b, dict) else b))
check("summary 下半年 returned=1", isinstance(b, dict) and b.get("returned") == 1, str(b.get("returned") if isinstance(b, dict) else b))

# 6) summary-text upsert + get
txt1 = "2026年上半年室间质评共参加1个计划，回报率100%，合格率100%，总体满意。"
s, b, _ = req("PUT", "/api/v1/eqa-plans/summary-text",
              {"year": 2026, "half": 1, "summary_text": txt1})
check("summary-text PUT 200", s == 200, f"status={s}")
s, b, _ = req("GET", "/api/v1/eqa-plans/summary-text?year=2026&half=1")
check("summary-text GET 命中文字", isinstance(b, dict) and b.get("summary_text") == txt1, str(b.get("summary_text") if isinstance(b, dict) else b))

txt2 = "2026年下半年室间质评共参加3个计划，回报率33.3%，合格率66.7%，存在1项不合格需整改。"
s, b, _ = req("PUT", "/api/v1/eqa-plans/summary-text",
              {"year": 2026, "half": 2, "summary_text": txt2})
s, b, _ = req("GET", "/api/v1/eqa-plans/summary-text?year=2026&half=2")
check("summary-text 下半年文字命中", isinstance(b, dict) and b.get("summary_text") == txt2, str(b.get("summary_text") if isinstance(b, dict) else b))

# 7) export Excel 全年
s, body, hdrs = req("GET", "/api/v1/eqa-plans/export?year=2026", raw=True)
ct = hdrs.get("Content-Type", "")
disp = hdrs.get("Content-Disposition", "")
check("export 返回 200", s == 200, f"status={s}")
check("export 是 xlsx(PK头)", body[:2] == b"PK", f"head={body[:4]}")
check("export Content-Type 含 spreadsheet", "spreadsheet" in ct, ct)
check("export 文件名中文RFC6266", "UTF-8''" in disp, disp)
out = "/d/workbuddyprojects/网页版-生免速查工具/outputs/test_eqa_export.xlsx"
with open(out, "wb") as f:
    f.write(body)
print(f"-- 导出文件已存: {out}")

# 8) notifications 含 eqa_return 提醒
s, b, _ = req("GET", "/api/v1/notifications")
notes = (b or {}).get("items", []) if isinstance(b, dict) else (b if isinstance(b, list) else [])
eqa_notes = [n for n in notes if n.get("ref_type") == "eqa_return"]
check("首页提醒含 eqa_return 提醒(2条)", len(eqa_notes) == 2, f"eqa_return={len(eqa_notes)} total={len(notes)}")

# 9) 清理演示数据
for pid in created:
    req("DELETE", f"/api/v1/eqa-plans/{pid}")
s, b, _ = req("GET", "/api/v1/eqa-plans?year=2026&limit=100")
left = len((b or {}).get("items", [])) if isinstance(b, dict) else 0
check("清理后 2026 计划归零", left == 0, f"left={left}")

# 10) 清理后 alerts 也应为空(否则通知残留)
s, b, _ = req("GET", "/api/v1/eqa-plans/alerts")
check("清理后 alerts 为空", isinstance(b, list) and len(b) == 0, f"alerts={len(b) if isinstance(b,list) else b}")

print("\n==== 结果 ====")
if FAILS:
    print(f"存在 {len(FAILS)} 项失败: {FAILS}")
else:
    print("全部通过 ✅")
