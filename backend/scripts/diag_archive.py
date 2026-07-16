"""诊断：在用仪器型号、仪器族成员、test_items 的 instrument/instrument_group 关联。"""
from app.core.database import SessionLocal
from app.models.instrument import Instrument
from app.models.instrument_family import InstrumentFamily, InstrumentFamilyMember
from app.models.test_item import TestItem


def main():
    db = SessionLocal()
    print("===== 在用仪器（status=在用）=====")
    for i in db.query(Instrument).order_by(Instrument.id).all():
        if (getattr(i, "status", "") or "") == "在用":
            print(f"  id={i.id:>3} model={i.model!r:40} name={i.name!r}")

    print("\n===== 仪器族 families & members =====")
    fid2name = {f.id: f.name for f in db.query(InstrumentFamily).all()}
    from collections import defaultdict
    fam_members = defaultdict(list)
    for m in db.query(InstrumentFamilyMember).all():
        fam_members[m.family_id].append(m.instrument_id)
    for fid, name in fid2name.items():
        print(f"  family[{fid}] {name!r:24} members={fam_members.get(fid, [])}")

    print("\n===== test_items.instrument / instrument_group (前40条非空) =====")
    n = 0
    for ti in db.query(TestItem).all():
        ig = (ti.instrument_group or "").strip()
        inst = (ti.instrument or "").strip()
        if ig or inst:
            print(f"  code={ti.code!r:14} name={ti.name!r:16} instrument={inst!r:14} group={ig!r}")
            n += 1
            if n >= 40:
                break
    print("total test_items:", db.query(TestItem).count())
    db.close()


if __name__ == "__main__":
    main()
