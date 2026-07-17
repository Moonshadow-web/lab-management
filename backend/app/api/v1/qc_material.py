"""质控品主数据接口：增删改查。
- 一种质控品（如「伯乐免疫多项」）含项目清单 items_json（JSON 数组）。
- 同一质控品的不同批号共享此清单；建批选质控品后，录入结果的分析物下拉由它预填。
"""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.security import get_current_user, require_roles
from ...models.qc_material import QcMaterial
from ...models.user import User

router = APIRouter(prefix="/qc-materials", tags=["qc_materials"])

WRITE = require_roles("admin", "qc_manager")


class QcMaterialBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str = ""
    items: list[str] = []
    note: str = ""


class QcMaterialCreate(QcMaterialBase):
    pass


class QcMaterialUpdate(QcMaterialBase):
    pass


class QcMaterialRead(QcMaterialBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


def _ser(m: QcMaterial) -> dict:
    try:
        items = json.loads(m.items_json or "[]")
    except Exception:
        items = []
    if not isinstance(items, list):
        items = []
    return {
        "id": m.id,
        "name": m.name,
        "items": items,
        "note": m.note,
        "created_at": m.created_at,
        "updated_at": m.updated_at,
    }


@router.get("", response_model=None)
def list_materials(q: str = "", db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    qry = db.query(QcMaterial)
    if q:
        qry = qry.filter(QcMaterial.name.contains(q))
    rows = qry.order_by(QcMaterial.name).all()
    return [QcMaterialRead(**_ser(r)) for r in rows]


@router.post("", response_model=None)
def create_material(payload: QcMaterialCreate, db: Session = Depends(get_db), user: User = Depends(WRITE)):
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="请填写质控品名称")
    if db.query(QcMaterial).filter(QcMaterial.name == name).first():
        raise HTTPException(status_code=400, detail="该质控品已存在")
    items = [x.strip() for x in payload.items if str(x).strip()]
    m = QcMaterial(name=name, items_json=json.dumps(items, ensure_ascii=False), note=payload.note or "")
    db.add(m)
    db.commit()
    db.refresh(m)
    return QcMaterialRead(**_ser(m))


@router.put("/{mid}", response_model=None)
def update_material(mid: int, payload: QcMaterialUpdate, db: Session = Depends(get_db), user: User = Depends(WRITE)):
    m = db.get(QcMaterial, mid)
    if not m:
        raise HTTPException(status_code=404, detail="质控品不存在")
    name = (payload.name or "").strip()
    if name and name != m.name:
        if db.query(QcMaterial).filter(QcMaterial.name == name).first():
            raise HTTPException(status_code=400, detail="该质控品名称已存在")
        m.name = name
    items = [x.strip() for x in payload.items if str(x).strip()]
    m.items_json = json.dumps(items, ensure_ascii=False)
    m.note = payload.note or ""
    db.commit()
    db.refresh(m)
    return QcMaterialRead(**_ser(m))


@router.delete("/{mid}", response_model=None)
def delete_material(mid: int, db: Session = Depends(get_db), user: User = Depends(WRITE)):
    m = db.get(QcMaterial, mid)
    if not m:
        raise HTTPException(status_code=404, detail="质控品不存在")
    db.delete(m)
    db.commit()
    return {"ok": True}
