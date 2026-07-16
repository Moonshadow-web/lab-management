"""项目「使用仪器」总型号 → 仪器档案(instruments) 的对应关系。

项目表的 `instrument` 字段是用户填的「总型号」（如「罗氏 Cobas6000」「AU生化仪」
「DxI800」），一台总型号往往对应多台具体仪器（罗氏 Cobas6000 = e601/e602/e411，
AU生化仪 = AU5822/AU5800急诊/AU5821 A/B）。本模块从数据库关联表
`instrument_families` + `instrument_family_members` 读取这种「一对多」关系，
供项目查询页点击跳转仪器档案使用。

关联数据由管理界面维护（见 instrument_families 路由）。对尚未在关联表中登记的
新总型号，resolve_family_instruments 会再尝试一次基于型号关键词的兜底匹配，
保证旧行为不丢失。
"""

from sqlalchemy.orm import Session

from ..models.instrument import Instrument
from ..models.instrument_family import InstrumentFamily, InstrumentFamilyMember
from ..models.test_item import TestItem


def _norm(s: str) -> str:
    return "".join(ch for ch in str(s).lower() if ch.isalnum())


def _archive_flag(db: Session, instrument_id: int) -> bool:
    from ..models.instrument_archive import InstrumentArchive

    return (
        db.query(InstrumentArchive)
        .filter(InstrumentArchive.instrument_id == instrument_id)
        .first()
        is not None
    )


def build_family_map(db: Session) -> dict[str, list[dict]]:
    """返回 { 总型号: [ {id,name,model,dept_no,has_archive}, ... ] }。

    遍历全部已登记的总型号（instrument_families），附带每个总型号被多少个项目
    使用（test_items.instrument == name）。用于项目查询页渲染「关联仪器」芯片。
    """
    rows = db.query(InstrumentFamily).order_by(InstrumentFamily.name).all()
    result: dict[str, list[dict]] = {}
    for fam in rows:
        member_ids = [
            m.instrument_id
            for m in db.query(InstrumentFamilyMember)
            .filter(InstrumentFamilyMember.family_id == fam.id)
            .all()
        ]
        insts = (
            db.query(Instrument)
            .filter(Instrument.id.in_(member_ids), Instrument.status != "停用")
            .all()
        )
        insts.sort(key=lambda x: x.id)
        result[fam.name] = [
            {
                "id": i.id,
                "name": i.name,
                "model": i.model,
                "dept_no": i.dept_no,
                "has_archive": _archive_flag(db, i.id),
            }
            for i in insts
        ]
    return result


def resolve_family_instruments(db: Session, family: str | None) -> list[Instrument]:
    """返回某个总型号对应的具体仪器列表（按 id 升序）。

    优先用 instrument_families 关联表精确匹配；命中为空且 family 非空时，
    再用型号关键词兜底匹配（仪器 model 归一化后含于 family 归一化串，则视为对应）。
    """
    if not family:
        return []
    fam = family.strip()
    row = db.query(InstrumentFamily).filter(InstrumentFamily.name == fam).first()
    if row is not None:
        member_ids = [
            m.instrument_id
            for m in db.query(InstrumentFamilyMember)
            .filter(InstrumentFamilyMember.family_id == row.id)
            .all()
        ]
        if member_ids:
            insts = (
                db.query(Instrument)
                .filter(Instrument.id.in_(member_ids), Instrument.status != "停用")
                .all()
            )
            insts.sort(key=lambda x: x.id)
            return insts
        # 已登记但无成员（如纯手工法「胶体金法」）→ 返回空
        return []
    # 未在关联表中的新总型号：兜底按型号关键词匹配
    nf = _norm(fam)
    matched: list[Instrument] = []
    seen = set()
    for inst in db.query(Instrument).filter(Instrument.status != "停用").all():
        nm = _norm(inst.model or "")
        if nm and nm in nf and inst.id not in seen:
            matched.append(inst)
            seen.add(inst.id)
    matched.sort(key=lambda x: x.id)
    return matched


def build_instrument_test_items_map(db: Session) -> dict[int, list[TestItem]]:
    """反向索引：instrument_id -> 引用它的项目列表（与项目查询页芯片对称）。

    与前端 `linkedInstruments` 的正向解析完全对称：每个项目的
    `instrument_group` 以 '/' 分隔的每个 token 若命中某个 family，则该 family
    下的仪器都视为「使用该项目的仪器」；instrument_group 为空或未命中时，
    回退用总型号 `instrument` 命中 family。仅统计出现在 familyMap 中的仪器
    （即非停用的在用仪器），与正向跳转保持一致。
    """
    family_map = build_family_map(db)
    fam_inst_ids: dict[str, set[int]] = {
        name: {i["id"] for i in insts} for name, insts in family_map.items()
    }
    result: dict[int, list[TestItem]] = {}
    for ti in db.query(TestItem).all():
        linked: set[int] = set()
        grp = (ti.instrument_group or "").strip()
        if grp:
            for tk in grp.split("/"):
                tk = tk.strip()
                if tk and tk in fam_inst_ids:
                    linked |= fam_inst_ids[tk]
        if not linked and ti.instrument and ti.instrument in fam_inst_ids:
            linked |= fam_inst_ids[ti.instrument]
        for iid in linked:
            result.setdefault(iid, []).append(ti)
    return result
