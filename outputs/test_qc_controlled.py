import urllib.request, json, urllib.parse, io, csv, random, os

BASE = "http://127.0.0.1:8123"

def login():
    data = urllib.parse.urlencode({"username": "admin", "password": "admin123"}).encode()
    req = urllib.request.Request(BASE + "/api/v1/auth/login", data=data,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    return json.loads(urllib.request.urlopen(req).read())["access_token"]

TOKEN = login()
H = {"Authorization": "Bearer " + TOKEN}

def get(path):
    return json.loads(urllib.request.urlopen(urllib.request.Request(BASE + path, headers=H)).read())

def put_json(path, obj):
    data = json.dumps(obj).encode()
    req = urllib.request.Request(BASE + path, data=data, headers={**H, "Content-Type": "application/json"}, method="PUT")
    return json.loads(urllib.request.urlopen(req).read())

def multipart(path, fields: dict, file_bytes: bytes, filename: str):
    boundary = "----qcformboundary"
    body = b""
    for k, v in fields.items():
        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode()
        body += str(v).encode() + b"\r\n"
    body += f"--{boundary}\r\n".encode()
    body += f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode()
    body += b"Content-Type: text/csv\r\n\r\n"
    body += file_bytes + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(BASE + path, data=body,
                                 headers={**H, "Content-Type": f"multipart/form-data; boundary={boundary}"},
                                 method="POST")
    return json.loads(urllib.request.urlopen(req).read())

# 1) 选受控仪器：DXI800急诊 id=6
INST_ID = 6
inst = get(f"/api/v1/instruments/{INST_ID}")
print(f"[仪器] id={INST_ID} name={inst['name']} dept_no={inst['dept_no']}")

# 2) 生成受控 CSV（无 仪器 列，受控绑定）
random.seed(11)
specs = [
    ("甲胎蛋白", "LOT-A1", "1", "ug/L", 11.1, 0.55),
    ("甲胎蛋白", "LOT-A2", "2", "ug/L", 33.8, 1.67),
    ("游离雌三醇", "LOT-B1", "1", "ug/L", 0.535, 0.04),
]
dates = ["2025-03-03", "2025-03-06", "2025-03-09", "2025-03-12", "2025-03-15", "2025-03-18"]
rows = []
for (ti, lot, lvl, unit, mean, sd) in specs:
    for i, d in enumerate(dates):
        v = round(mean + random.gauss(0, sd * 0.4), 4)
        if i == 2: v = round(mean + 3.6 * sd, 4)   # 1-3s
        if i in (4, 5): v = round(mean + 2.4 * sd, 4)  # 2-2s
        rows.append({"项目": ti, "批号": lot, "水平": lvl, "单位": unit,
                     "日期": d, "测值": v, "靶值": mean, "SD": sd})
csv_path = "outputs/test_qc_controlled.csv"
with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["项目", "批号", "水平", "单位", "日期", "测值", "靶值", "SD"])
    w.writeheader(); w.writerows(rows)

with open(csv_path, "rb") as f:
    fb = f.read()
up = multipart("/api/v1/qc-summaries/upload", {"instrument_id": INST_ID}, fb, "test_qc_controlled.csv")
print(f"[上传] created={up['created']} updated={up['updated']} groups={up['groups']}")
print("  首条:", up["items"][0])

# 3) 列表按 instrument_id 过滤（2025-03）
lst = get("/api/v1/qc-summaries?year=2025&month=3&instrument_id=6&page_size=500")
print(f"[列表] 该仪器2025-03 共 {len(lst['items'])} 条")
for it in lst["items"]:
    assert it["instrument_id"] == INST_ID, "instrument_id 未绑定!"
    assert it["instrument"] == inst["name"], f"仪器名应为 {inst['name']}，实际 {it['instrument']}"
    assert it["instrument_no"] == inst["dept_no"], "仪器编号缺失"
print("  instrument_id / instrument / instrument_no 均正确绑定")

# 4) 取报告（自动草拟）
rep = get(f"/api/v1/qc-summaries/report?instrument_id=6&year=2025&month=3")
print("[报告-自动草拟]")
for k in ["operation_status", "drift_trend", "cv_setting_ok", "cv_calc_ok", "freq_ok"]:
    print(f"  {k}: {rep[k][:80]}")
assert "趋势" in rep["drift_trend"] or "漂移" in rep["drift_trend"] or "稳定" in rep["drift_trend"]

# 5) 编辑报告
put_json("/api/v1/qc-summaries/report", {
    "instrument_id": 6, "instrument": inst["name"], "instrument_no": inst["dept_no"],
    "year": 2025, "month": 3,
    "operation_status": "本仪器本月运行正常（已人工复核）。",
    "drift_trend": rep["drift_trend"], "cv_setting_ok": rep["cv_setting_ok"],
    "cv_calc_ok": rep["cv_calc_ok"], "freq_ok": rep["freq_ok"],
})
rep2 = get(f"/api/v1/qc-summaries/report?instrument_id=6&year=2025&month=3")
assert rep2["operation_status"] == "本仪器本月运行正常（已人工复核）。", "报告保存未生效"
print("[报告-编辑] 保存生效:", rep2["operation_status"])

# 6) 导出（含文字段），校验
import openpyxl
r = urllib.request.Request(BASE + "/api/v1/qc-summaries/export?year=2025&month=3&instrument_id=6", headers=H)
blob = urllib.request.urlopen(r).read()
exp_path = "outputs/test_export_controlled.xlsx"
with open(exp_path, "wb") as f:
    f.write(blob)
print(f"[导出] 字节={len(blob)} -> {exp_path}")
wb = openpyxl.load_workbook(io.BytesIO(blob))
ws = wb.active
alltext = []
for row in ws.iter_rows(values_only=True):
    for c in row:
        if isinstance(c, str):
            alltext.append(c)
joined = "\n".join(alltext)
for label in ["一、仪器运行情况", "二、各项目是否出现漂移或趋势性改变",
              "三、各项目CV%设置是否达标", "四、各项目计算CV%是否达标",
              "五、各项目质控频次是否达标", "编号：" + inst["dept_no"]]:
    assert label in joined, f"导出缺少文字段: {label}"
print("[导出] 含五段文字 + 仪器编号，校验通过")

print("\n=== 全链路验证通过 ===")
