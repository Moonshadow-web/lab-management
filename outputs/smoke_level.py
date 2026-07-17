import sys
sys.path.insert(0, "backend")
from fastapi.testclient import TestClient
from app.main import app
from sqlalchemy import create_engine, inspect
from app.core.config import DATA_DIR
import os

DB = DATA_DIR / "app.db"
print("DB path:", DB, "exists:", DB.exists())

with TestClient(app) as client:
    # 真实登录（OAuth2 表单）
    r = client.post("/api/v1/auth/login", data={"username": "jinzizheng", "password": "Jzz6827556"})
    assert r.status_code in (200, 201), r.text
    token = r.json()["access_token"]
    H = {"Authorization": f"Bearer {token}"}

    # 1) 建批（level=2）
    lot = "SMOKE_LEVEL_2"
    r = client.post("/api/v1/qc-target-batches", headers=H, json={
        "qc_material": "伯乐免疫多项", "lot_no": lot, "level": 2,
        "instrument": "DXI800", "method": "conventional",
    })
    assert r.status_code in (200, 201), r.text
    bid = r.json()["id"]
    print("created batch id:", bid, "level:", r.json().get("level"))

    # 2) 读回，验证 level 持久化
    r = client.get(f"/api/v1/qc-target-batches/{bid}", headers=H)
    assert r.status_code in (200, 201), r.text
    assert r.json().get("level") == 2, r.json()
    print("read-back level:", r.json().get("level"))

    # 3) 列存在性检查
    eng = create_engine(f"sqlite:///{DB}")
    cols = [c["name"] for c in inspect(eng).get_columns("qc_target_batches")]
    print("qc_target_batches columns:", cols)
    assert "level" in cols

    # 4) 清理
    r = client.delete(f"/api/v1/qc-target-batches/{bid}", headers=H)
    print("cleanup status:", r.status_code)
print("SMOKE LEVEL OK")
