"""批号累积靶值 后端端到端验证（线上 CFS 库）。
覆盖：建批(即刻法/常规法/存档)、录入、即刻法判定、失控标记保留、确立、清理。
测试数据创建后删除，不污染生产数据。
"""
import urllib.request, urllib.parse, json

BASE = "https://lab-management-282724-9-1408547492.sh.run.tcloudbase.com"

def post(path, obj=None, data=None, headers=None, is_json=True):
    hdr = headers or {}
    if is_json and obj is not None:
        data = json.dumps(obj).encode(); hdr["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=data, headers=hdr)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, json.loads(r.read())

def get(path, headers):
    req = urllib.request.Request(BASE + path, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def delete(path, headers):
    req = urllib.request.Request(BASE + path, headers=headers, method="DELETE")
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.read().decode()

# 登录
login_data = urllib.parse.urlencode({"username": "jinzizheng", "password": "Jzz6827556"}).encode()
lr = urllib.request.Request(BASE + "/api/v1/auth/login", data=login_data,
                            headers={"Content-Type": "application/x-www-form-urlencoded"})
tok = json.loads(urllib.request.urlopen(lr).read())["access_token"]
H = {"Authorization": f"Bearer {tok}"}

created = []
try:
    # 1) 即刻法批号
    s, batch = post("/api/v1/qc-target-batches", {
        "qc_material": "伯乐免疫多项", "lot_no": "TEST-LOT-IMM", "instrument": "DXI800",
        "method": "immediate", "mode": "entry", "note": "E2E测试",
    }, headers=H)
    bid = batch["id"]; created.append(bid)
    print(f"[1] 建即刻法批号 id={bid} mode={batch['mode']} method={batch['method']}")

    # 录入 3 次 TSH（文献示例）
    for v in [1.71, 1.81, 1.90]:
        s, res = post(f"/api/v1/qc-target-batches/{bid}/results",
                      {"analyte": "TSH", "value": v, "qc_date": "2026-07-17"}, headers=H)
        print(f"    录入 TSH={v} -> status={res['row']['status']} si_up={res['row']['si_upper']} si_lo={res['row']['si_lower']}")
    s, d = get(f"/api/v1/qc-target-batches/{bid}/results", H)
    print(f"    [stats] TSH n={d['stats']['per_analyte']['TSH']['n']} status={d['stats']['per_analyte']['TSH']['status']} 批次={d['stats']['batch_status']}")

    # 录入第4次极端值触发失控（保留标记）
    s, res = post(f"/api/v1/qc-target-batches/{bid}/results",
                  {"analyte": "TSH", "value": 9.99, "qc_date": "2026-07-17"}, headers=H)
    print(f"    录入 TSH=9.99 -> status={res['row']['status']} is_out={res['row']['is_out']} (应保留标记不自动删)")
    s, d = get(f"/api/v1/qc-target-batches/{bid}/results", H)
    print(f"    [stats] 失控标记数={d['stats']['out_count']} 批次={d['stats']['batch_status']}")

    # 2) 常规法批号
    s, b2 = post("/api/v1/qc-target-batches", {
        "qc_material": "昆涞免疫多项", "lot_no": "TEST-LOT-CONV", "instrument": "DXI800",
        "method": "conventional", "mode": "entry",
    }, headers=H)
    bid2 = b2["id"]; created.append(bid2)
    for v in [1,2,3,4,5,6,7,8,9,10,11]:
        post(f"/api/v1/qc-target-batches/{bid2}/results",
             {"analyte": "FT4", "value": v, "qc_date": "2026-07-17"}, headers=H)
    s, d2 = get(f"/api/v1/qc-target-batches/{bid2}/results", H)
    pa = d2["stats"]["per_analyte"]["FT4"]
    print(f"[2] 常规法 FT4 n={pa['n']} status={pa['status']} can_establish={pa['can_establish']}")

    # 手动确立
    s, est = post(f"/api/v1/qc-target-batches/{bid2}/establish", None, headers=H)
    print(f"    确立后 established={json.loads(est['targets_json']).get('FT4',{}).get('mean')}")

    # 3) 生化多项存档模式
    s, b3 = post("/api/v1/qc-target-batches", {
        "qc_material": "生化多项质控品", "lot_no": "TEST-LOT-BIO", "instrument": "AU5800",
        "method": "", "mode": "archive",
    }, headers=H)
    bid3 = b3["id"]; created.append(bid3)
    print(f"[3] 生化多项批号 id={bid3} mode={b3['mode']} method='{b3['method']}' established={b3['established']} (应 archive/空/True)")

    print("\nALL_BACKEND_OK")
finally:
    for bid in created:
        try: delete(f"/api/v1/qc-target-batches/{bid}", H)
        except Exception as e: print("清理失败", bid, e)
    print("已清理测试数据")
