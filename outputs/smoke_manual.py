"""验证人工覆盖(manual)功能：建批 → 录入3个值(0.95,0.95,0.94) → 失控 → 人工确认 → 状态变为在控(人工)"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

os.environ["DATABASE_URL"] = "sqlite:///./data/test_manual.db"
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal, engine, Base
from app.core.security import hash_password
from app.models.qc_target import QCTargetBatch, QCTargetResult
from app.models.qc_material import QcMaterial
from app.models.user import User

Base.metadata.drop_all(bind=engine, checkfirst=True)
Base.metadata.create_all(bind=engine, checkfirst=True)

# seed admin user (bcrypt hash)
with SessionLocal() as db:
    db.add(User(id=2, username="jinzizheng", password_hash=hash_password("Jzz6827556"),
               full_name="金子正", roles="admin,specialty_leader", must_change_password=False))
    db.commit()

client = TestClient(app)

# 登录
r = client.post("/api/v1/auth/login", data={"username": "jinzizheng", "password": "Jzz6827556"})
print("login", r.status_code, r.text[:200])
token = r.json().get("access_token")
assert token, f"login failed: {r.text}"
hdr = {"Authorization": f"Bearer {token}"}

# 先建质控品，再建批号
client.post("/api/v1/qc-materials", json={"name": "测试质控品", "items_json": json.dumps(["ALT", "AST"])}, headers=hdr)
r = client.post("/api/v1/qc-target-batches", json={
    "qc_material": "测试质控品", "lot_no": "TEST001", "level": 1,
    "instrument": "仪1", "method": "immediate", "mode": "entry"
}, headers=hdr)
batch_id = r.json().get("id") or (r.json()).get("id")
# POST returns 201, maybe id is nested
if not batch_id:
    batch_id = r.json()["id"]
print(f"Batch created: id={batch_id}")

# 录入 3 个值: 0.95, 0.95
for v in [0.95, 0.95]:
    r = client.post(f"/api/v1/qc-target-batches/{batch_id}/results",
                    json={"analyte": "ALT", "value": v, "qc_date": "2026-07-17"}, headers=hdr)
    assert r.status_code in (200, 201), f"add result {v}: {r.text}"

# 录入 0.94 → 应报失控
r = client.post(f"/api/v1/qc-target-batches/{batch_id}/results",
                json={"analyte": "ALT", "value": 0.94, "qc_date": "2026-07-17"}, headers=hdr)
res = r.json()
print(f"3rd result: status={res['row']['status']} is_out={res['row']['is_out']}")
assert res["row"]["status"] == "失控", f"预期失控，实际{res['row']['status']}"
assert res["row"]["is_out"] == True, "应标失控"
assert res["stats"]["per_analyte"]["ALT"]["status"] == "有失控" or res["stats"]["batch_status"] == "有失控"

# 获取结果列表 → 找到那行 id
r = client.get(f"/api/v1/qc-target-batches/{batch_id}/results", headers=hdr)
rows = r.json()["rows"]
out_row = [x for x in rows if x["analyte"] == "ALT" and x["is_out"]][0]
rid = out_row["id"]
print(f"失控行 id={rid}")

# 点击"人工确认" → toggle
r = client.post(f"/api/v1/qc-target-batches/{batch_id}/results/{rid}/toggle", headers=hdr)
res = r.json()
print(f"Toggle 后: row.status={res['row']['status']} manual={res['row']['manual']} is_out={res['row']['is_out']}")
print(f"Stats per_analyte ALT: {json.dumps(res['stats']['per_analyte'].get('ALT', {}), ensure_ascii=False)}")
assert res["row"]["manual"] == True, "应标 manual"
assert res["row"]["is_out"] == False, "应取消 is_out"
assert res["stats"]["per_analyte"]["ALT"]["status"] == "在控(人工)", f"预期在控(人工)，实际{res['stats']['per_analyte']['ALT']['status']}"

# 再录入第4个 0.94 → 因为 manual=True 存在，自动判定跳过
r = client.post(f"/api/v1/qc-target-batches/{batch_id}/results",
                json={"analyte": "ALT", "value": 0.94, "qc_date": "2026-07-17"}, headers=hdr)
res = r.json()
print(f"第4次录入: row.status={res['row']['status']} is_out={res['row']['is_out']} manual={res['row'].get('manual')}")
# 新的行不应被标失控，应正常纳入
assert res["row"]["is_out"] == False, f"不应标失控: {res['row']}"

print("\n✅ 所有测试通过！")
