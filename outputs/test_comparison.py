import requests, json, os

BASE = "http://127.0.0.1:8123/api/v1"
s = requests.Session()

# 登录
r = s.post(f"{BASE}/auth/login", data={"username": "jinzizheng", "password": "Jzz6827556"})
print("login", r.status_code, r.text[:120])
tok = r.json()["access_token"]
s.headers.update({"Authorization": f"Bearer {tok}"})

# 1) 分组列表（应已种子 6 个）
r = s.get(f"{BASE}/comparison/groups")
groups = r.json()
print("\n[groups]", r.status_code, "count=", len(groups))
for g in groups:
    print("  -", g["id"], g["name"], g["category"], g["form_code"], "items=", len(g["items"]),
          "ref=", g["reference_instrument_id"], "insts=", g["instrument_ids"])

# 2) 取生化分析仪分组，建一个计划
bio = next(g for g in groups if g["name"] == "生化分析仪")
pid = None
r = s.post(f"{BASE}/comparison/plans", json={
    "group_id": bio["id"], "year": 2026, "half": 1,
    "form_code": bio["form_code"], "form_title": bio["form_title"],
    "compared_at": "2026-03-15", "operator": "金子正", "reviewer": "王学晶",
    "summary": "各仪器上述所有项目均比对合格。", "conclusion": "可接受", "status": "done",
})
print("\n[create plan]", r.status_code)
plan = r.json(); pid = plan["id"]
print("  plan id=", pid, "report=", plan.get("report_path"))

# 3) 录入定量结果：取前 3 个项目 × 水平1、2
items = bio["items"][:3]
lv = 1
quant = []
for it in items:
    # 参照值 100，仪器按偏倚~1% 给值
    ref = 100.0
    vals = {}
    for iid in bio["instrument_ids"]:
        if iid == bio["reference_instrument_id"]:
            continue
        refv = round(ref * (1 + 0.01 * (len(vals) + 1)), 2)
        vals[str(iid)] = str(refv)
    quant.append({"item": it["name"], "level": lv, "reference_value": str(ref), "values": vals})
r = s.put(f"{BASE}/comparison/plans/{pid}/results", json={"quant": quant, "qual": []})
print("\n[save results]", r.status_code, r.text)

# 4) 读取结果
r = s.get(f"{BASE}/comparison/plans/{pid}/results")
print("\n[get results]", r.status_code, "quant rows=", len(r.json()["quant"]))

# 5) 生成报告
r = s.post(f"{BASE}/comparison/plans/{pid}/report/generate")
print("\n[generate report]", r.status_code, "report_path=", r.json().get("report_path"),
      "filename=", r.json().get("report_filename"))

# 6) 预览 HTML
r = s.get(f"{BASE}/comparison/plans/{pid}/report/preview")
html = r.json().get("html", "")
print("\n[preview]", r.status_code, "html len=", len(html), "has 表格编号:", "BG-SM-CZ-025" in html)

# 7) 下载报告
r = s.get(f"{BASE}/comparison/plans/{pid}/report")
print("\n[download]", r.status_code, "ctype=", r.headers.get("content-type"), "bytes=", len(r.content))
out = "/d/workbuddyprojects/网页版-生免速查工具/outputs/test_report_bio.docx"
with open(out, "wb") as f:
    f.write(r.content)
print("  saved ->", out)

# 8) 定性分组快速验证
qual = next(g for g in groups if g["category"] == "定性")
r = s.post(f"{BASE}/comparison/plans", json={
    "group_id": qual["id"], "year": 2026, "half": 1,
    "form_code": qual["form_code"], "form_title": qual["form_title"],
    "compared_at": "2026-04-01", "operator": "金子正", "reviewer": "王学晶", "status": "done",
})
qpid = r.json()["id"]
inst_ids = qual["instrument_ids"] or [qual["reference_instrument_id"]]
refid = qual["reference_instrument_id"] or (inst_ids[0] if inst_ids else 0)
qual_rows = []
for it in qual["items"][:2]:
    res = {}
    for iid in inst_ids:
        if iid == refid:
            res[str(iid)] = ["P", "N", "P", "N", "P"]
        else:
            res[str(iid)] = ["P", "N", "P", "N", "P"]
    # 制造一个不一致
    if len(inst_ids) > 1 and str(inst_ids[-1]) != str(refid):
        res[str(inst_ids[-1])] = ["N", "N", "P", "N", "P"]
    qual_rows.append({"item": it["name"], "results": res})
r = s.put(f"{BASE}/comparison/plans/{qpid}/results", json={"quant": [], "qual": qual_rows})
print("\n[qual save]", r.status_code)
r = s.post(f"{BASE}/comparison/plans/{qpid}/report/generate")
print("[qual generate]", r.status_code, r.json().get("report_filename"))
r = s.get(f"{BASE}/comparison/plans/{qpid}/report/preview")
print("[qual preview] has BG-SM-CZ-021:", "BG-SM-CZ-021" in r.json().get("html", ""))

print("\nALL DONE")
