"""「项目使用仪器总型号 ↔ 仪器档案」关联的管理接口。

- 总型号(instrument_families) 对应 test_items.instrument 的取值；
- 成员(instrument_family_members) 关联具体仪器(instruments)。

提供：列表/详情/新增/改名/删除，以及成员的整体替换（供前端多选器保存）。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.security import get_current_user
from ...models.instrument import Instrument
from ...models.instrument_archive import InstrumentArchive
from ...models.instrument_family import InstrumentFamily, InstrumentFamilyMember
from ...models.test_item import TestItem
from ...models.user import User
from ...schemas import (
    InstrumentFamilyCreate,
    InstrumentFamilyMemberOut,
    InstrumentFamilyRead,
    InstrumentFamilyUpdate,
)

router = APIRouter(prefix="/instrument-families", tags=["instrument_families"])


def _member_ids(db: Session, family_id: int) -> list[int]:
    return [
        m.instrument_id
        for m in db.query(InstrumentFamilyMember)
        .filter(InstrumentFamilyMember.family_id == family_id)
        .all()
    ]


def _active_member_ids(db: Session, family_id: int) -> list[int]:
    """返回该总型号关联、且未停用的仪器 id（停用仪器不显示、不可跳转）。"""
    ids = _member_ids(db, family_id)
    if not ids:
        return []
    return [
        iid
        for (iid,) in db.query(Instrument.id)
        .filter(Instrument.id.in_(ids), Instrument.status != "停用")
        .all()
    ]


def _members_detail(db: Session, family_id: int) -> list[dict]:
    ids = _active_member_ids(db, family_id)
    insts = db.query(Instrument).filter(Instrument.id.in_(ids)).all() if ids else []
    insts.sort(key=lambda x: x.id)
    return [
        {
            "id": i.id,
            "name": i.name,
            "model": i.model,
            "dept_no": i.dept_no,
            "status": i.status,
            "has_archive": db.query(InstrumentArchive)
            .filter(InstrumentArchive.instrument_id == i.id)
            .first()
            is not None,
        }
        for i in insts
    ]


def _to_read(db: Session, fam: InstrumentFamily) -> InstrumentFamilyRead:
    ids = _active_member_ids(db, fam.id)
    # 用量：既统计「总型号」直接命中的项目，也统计「仪器组」含该 token 的项目
    used = (
        db.query(func.count(TestItem.id))
        .filter(
            (TestItem.instrument == fam.name)
            | (TestItem.instrument_group.like("%" + fam.name + "%"))
        )
        .scalar()
        or 0
    )
    return InstrumentFamilyRead(
        id=fam.id,
        name=fam.name,
        description=fam.description,
        instrument_ids=ids,
        member_count=len(ids),
        used_count=used,
        members=[InstrumentFamilyMemberOut(**m) for m in _members_detail(db, fam.id)],
        created_at=fam.created_at,
        updated_at=fam.updated_at,
    )


@router.get("", response_model=list[InstrumentFamilyRead])
def list_families(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    fams = db.query(InstrumentFamily).order_by(InstrumentFamily.name).all()
    return [_to_read(db, f) for f in fams]


@router.post("", response_model=InstrumentFamilyRead, status_code=201)
def create_family(
    body: InstrumentFamilyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="总型号名称不能为空")
    if db.query(InstrumentFamily).filter(InstrumentFamily.name == name).first():
        raise HTTPException(status_code=400, detail=f"总型号「{name}」已存在")
    fam = InstrumentFamily(name=name, description=(body.description or "").strip())
    db.add(fam)
    db.commit()
    db.refresh(fam)
    return _to_read(db, fam)


@router.get("/{family_id}", response_model=InstrumentFamilyRead)
def get_family(
    family_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    fam = db.get(InstrumentFamily, family_id)
    if not fam:
        raise HTTPException(status_code=404, detail="未找到总型号")
    return _to_read(db, fam)


@router.put("/{family_id}", response_model=InstrumentFamilyRead)
def update_family(
    family_id: int,
    body: InstrumentFamilyUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    fam = db.get(InstrumentFamily, family_id)
    if not fam:
        raise HTTPException(status_code=404, detail="未找到总型号")
    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="总型号名称不能为空")
        dup = db.query(InstrumentFamily).filter(InstrumentFamily.name == name, InstrumentFamily.id != family_id).first()
        if dup:
            raise HTTPException(status_code=400, detail=f"总型号「{name}」已存在")
        fam.name = name
    if body.description is not None:
        fam.description = body.description.strip()
    db.commit()
    db.refresh(fam)
    return _to_read(db, fam)


@router.delete("/{family_id}")
def delete_family(
    family_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    fam = db.get(InstrumentFamily, family_id)
    if not fam:
        raise HTTPException(status_code=404, detail="未找到总型号")
    db.query(InstrumentFamilyMember).filter(InstrumentFamilyMember.family_id == family_id).delete()
    db.delete(fam)
    db.commit()
    return {"ok": True}


@router.put("/{family_id}/members", response_model=InstrumentFamilyRead)
def set_members(
    family_id: int,
    body: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    fam = db.get(InstrumentFamily, family_id)
    if not fam:
        raise HTTPException(status_code=404, detail="未找到总型号")
    ids = [int(x) for x in (body.get("instrument_ids") or [])]
    # 校验仪器真实存在，且不允许关联「停用」仪器（停用仪器不显示、不可跳转）
    active = (
        {
            i.id
            for i in db.query(Instrument.id)
            .filter(Instrument.id.in_(ids), Instrument.status != "停用")
            .all()
        }
        if ids
        else set()
    )
    db.query(InstrumentFamilyMember).filter(InstrumentFamilyMember.family_id == family_id).delete()
    for iid in ids:
        if iid in active:
            db.add(InstrumentFamilyMember(family_id=family_id, instrument_id=iid))
    db.commit()
    db.refresh(fam)
    return _to_read(db, fam)
