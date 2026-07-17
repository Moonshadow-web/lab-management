import sys
sys.path.insert(0, "backend")
from fastapi.testclient import TestClient
from app.main import app
from sqlalchemy import create_engine, inspect
from app.core.config import DATA_DIR

DB = DATA_DIR / "app.db"
print("DB:", DB)

with TestClient(app) as client:
    r = client.post("/api/v1/auth/login", data={"username": "jinzizheng", "password": "Jzz6827556"})
    assert r.status_code == 200, r.text
    H = {"Authorization": f"Bearer {r.json()['access_token']}"}

    # 1) 启动种子：预设质控品应已存在
    r = client.get("/api/v1/qc-materials", headers=H)
    assert r.status_code == 200, r.text
    names = [m["name"] for m in r.json()]
    print("seeded materials:", names)
    assert "伯乐免疫多项" in names

    # 2) 新建质控品（含项目清单）
    r = client.post("/api/v1/qc-materials", headers=H, json={
        "name": "SMOKE_质控品", "items": ["ALT", "AST", "肌酐"], "note": "测试"
    })
    assert r.status_code in (200, 201), r.text
    mid = r.json()["id"]
    print("created material id:", mid, "items:", r.json()["items"])

    # 3) 建批关联该质控品
    lot = "SMOKE_MAT_LOT"
    r = client.post("/api/v1/qc-target-batches", headers=H, json={
        "qc_material_id": mid, "lot_no": lot, "level": 1,
        "instrument": "DXI800", "method": "conventional",
    })
    assert r.status_code in (200, 201), r.text
    bid = r.json()["id"]
    print("batch qc_material:", r.json()["qc_material"], "qc_material_id:", r.json()["qc_material_id"])
    assert r.json()["qc_material"] == "SMOKE_质控品"

    # 4) 统计应返回 material_items（供录入候选）
    r = client.get(f"/api/v1/qc-target-batches/{bid}/results", headers=H)
    assert r.status_code == 200, r.text
    print("stats.material_items:", r.json()["stats"]["material_items"])
    assert r.json()["stats"]["material_items"] == ["ALT", "AST", "肌酐"]

    # 5) 列存在性
    eng = create_engine(f"sqlite:///{DB}")
    cols = [c["name"] for c in inspect(eng).get_columns("qc_target_batches")]
    assert "qc_material_id" in cols
    mats_cols = [c["name"] for c in inspect(eng).get_columns("qc_materials")]
    assert "items_json" in mats_cols
    print("cols ok")

    # 6) 清理
    client.delete(f"/api/v1/qc-target-batches/{bid}", headers=H)
    client.delete(f"/api/v1/qc-materials/{mid}", headers=H)
    print("cleanup done")
print("SMOKE MATERIAL OK")
