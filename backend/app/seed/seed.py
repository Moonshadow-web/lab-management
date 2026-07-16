"""种子数据导入：库为空时写入管理员账号，并从 seed_data.json（由 extract_data.js 从 data.js 解析得到）导入项目、仪器、说明书。"""
import json
import shutil
from pathlib import Path

from ..core.config import PROJECT_ROOT, UPLOAD_ROOT
from ..core.security import hash_password
from ..models.document import Document, DocumentVersion
from ..models.instrument import Instrument
from ..models.instrument_family import InstrumentFamily, InstrumentFamilyMember
from ..models.test_item import TestItem
from ..models.user import User
from .seed_users import seed_users


SEED_JSON = Path(__file__).resolve().parent / "seed_data.json"
FILES_DIR = PROJECT_ROOT / "files"


def _s(v):
    return "" if v is None else str(v)


def _map_test_item(it: dict) -> dict:
    return {
        "code": _s(it.get("code")),
        "name": _s(it.get("name")),
        "aliases": _s(it.get("aliases")),
        "category": _s(it.get("category")),
        "specimen": _s(it.get("specimen")),
        "method": _s(it.get("detectionMethod")),
        "unit": _s(it.get("unit")),
        "reference": _s(it.get("reference")),
        "fee": _s(it.get("fee")),
        "instrument": _s(it.get("instrument")),
        "instrument_group": _s(it.get("instrumentGroup")),
        "linear_range": _s(it.get("linearRange")),
        "dilution_fold": _s(it.get("dilutionFold")),
        "reportable_range": _s(it.get("reportableRange")),
        "diluent": _s(it.get("diluent")),
        "calibrator": _s(it.get("calibrator")),
        "traceability": _s(it.get("traceability")),
        "last_update": _s(it.get("lastUpdate")),
        "interference_hemolysis": _s(it.get("interferenceHemolysis")),
        "interference_bilirubin": _s(it.get("interferenceBilirubin")),
        "interference_lipemia": _s(it.get("interferenceLipemia")),
    }


def _map_instrument(it: dict) -> dict:
    return {
        "name": _s(it.get("name")),
        "dept_no": _s(it.get("deptNo")),
        "model": _s(it.get("model")),
        "manufacturer": _s(it.get("brand")),
        "category": _s(it.get("category")),
        "location": _s(it.get("location")),
        "status": _s(it.get("status")) or "在用",
        "serial_no": _s(it.get("serialNo")),
        "purchase_date": _s(it.get("purchaseDate")),
        "start_date": _s(it.get("startDate")),
        "owner": _s(it.get("owner")),
    }


def _seed_document(db, it: dict):
    name = _s(it.get("name"))
    pdf = _s(it.get("pdfPath"))
    rel = ""
    original = ""
    if pdf:
        src = PROJECT_ROOT / pdf
        if src.exists():
            dest_dir = UPLOAD_ROOT / "manuals"
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / src.name
            if not dest.exists():
                shutil.copy(src, dest)
            rel = f"manuals/{src.name}"
            original = src.name
    d = Document(
        title=name,
        category="项目说明书",
        version="1.0",
        file_path=rel,
        original_filename=original,
        uploader="系统",
        status="生效",
        description="试剂说明书（初始导入）",
    )
    db.add(d)
    db.flush()
    if rel:
        db.add(DocumentVersion(document_id=d.id, version="1.0", file_path=rel, uploader="系统", note="初始导入"))


def run_seed(db):
    if db.query(User).count() == 0:
        db.add(
            User(
                username="admin",
                full_name="管理员",
                password_hash=hash_password("admin123"),
                role="admin",
                department="生免组",
                email="815268425@qq.com",
                notify_email=True,
                is_active=True,
            )
        )
        db.commit()

    if not SEED_JSON.exists():
        return

    data = json.loads(SEED_JSON.read_text(encoding="utf-8"))

    if db.query(TestItem).count() == 0 and data.get("performanceData"):
        for it in data["performanceData"]:
            db.add(TestItem(**_map_test_item(it)))
        db.commit()

    if db.query(Instrument).count() == 0 and data.get("instrumentData"):
        for it in data["instrumentData"]:
            db.add(Instrument(**_map_instrument(it)))
        db.commit()

    if db.query(Document).count() == 0 and data.get("manualData"):
        for it in data["manualData"]:
            _seed_document(db, it)
        db.commit()

    seed_families(db)
    seed_token_families(db)
    seed_users(db)


# 原写死在 core/instrument_link.FAMILY_MAP 的「总型号 → 仪器」关系，迁移为数据库关联表。
# 按仪器 name/model 子串匹配，对 id 变化不敏感；按 name 去重，可重复执行。
_FAMILY_SEED = [
    ("罗氏 Cobas6000", ["e601", "e602", "e411"]),
    ("AU生化仪", ["AU5822", "AU5800", "AU5821"]),
    ("DxI800", ["DXI800", "DxI800"]),
    ("日立HT7600", ["HT7600"]),
    ("安图A6200", ["A6200"]),
    ("ACL TOP700", ["TOP700"]),
    ("胶体金法", []),  # 纯手工快速法，无仪器
    ("Stago CompactMax", ["CompactMax"]),
    ("东曹HLC-723 G8", ["HLC-723G8"]),
    ("FUJI FILM DRI-CHEM", ["DRI-CHEN", "DRI-CHEM"]),
    ("西门子RapidPoint血气分析仪", ["RapidPoint"]),
    ("Sebia Capillarys 3 OCTA毛细管电泳仪", ["Capillarys"]),
    ("Sebia HYDRASYS免疫固定电泳仪", ["Hydrasys"]),
    ("爱林-数显混匀器 ORBITAL SHAKER TA-2000A", ["数显混匀器"]),
    ("爱康全自动酶联免疫仪", ["URANUS"]),
]

# 仪器组精确关联：用户在项目「仪器组」里写的就是具体机号 / 总型号缩写，
# 直接一一对应到具体仪器档案（不再按总型号模糊匹配）。
# 键 = 仪器组 token（与 test_items.instrument_group 中以 '/' 分隔的片段一致），
# 值 = 具体仪器 id 列表（已逐一核对档案，均为在用）。
#   AU58-1 → AU5821 A(id67)；AU58-2 → AU5821 B(id68)；AU5800 → AU5800急诊(id5)
#   HT7600 → 日立HT7600(id12)
#   ①号机 → DXI800 1(id69)；②号机 → DXI800 2(id70)；③号机 → DXI800 3(id71)；④号机 → DXI800 4(id72)
#   e601/e602/e411 → 罗氏 e601/e602/e411 (id14/15/16)
#   急诊 → 贝克曼DXI800急(id73)；唐筛 → 贝克曼DXI800唐(id74)
_TOKEN_FAMILY_SEED = [
    ("AU58-1", [67]),
    ("AU58-2", [68]),
    ("AU5800", [5]),
    ("HT7600", [12]),
    ("①号机", [69]),
    ("②号机", [70]),
    ("③号机", [71]),
    ("④号机", [72]),
    ("e601", [14]),
    ("e602", [15]),
    ("e411", [16]),
    ("急诊", [73]),
    ("唐筛", [74]),
]


def seed_families(db):
    instruments = db.query(Instrument).all()
    for name, keys in _FAMILY_SEED:
        if db.query(InstrumentFamily).filter(InstrumentFamily.name == name).first():
            continue
        fam = InstrumentFamily(name=name)
        db.add(fam)
        db.flush()
        if keys:
            matched = set()
            for inst in instruments:
                hay = (inst.name or "") + " " + (inst.model or "")
                hay_l = hay.lower()
                for k in keys:
                    if k.lower() in hay_l:
                        matched.add(inst.id)
                        break
            for iid in sorted(matched):
                db.add(InstrumentFamilyMember(family_id=fam.id, instrument_id=iid))
    db.commit()


def seed_token_families(db):
    """写入「仪器组 token → 具体仪器」的精确关联（幂等，按 name 去重）。"""
    existing = {f.name for f in db.query(InstrumentFamily).all()}
    valid_ids = {i.id for i in db.query(Instrument.id).all()}
    for name, ids in _TOKEN_FAMILY_SEED:
        if name in existing:
            continue
        fam = InstrumentFamily(name=name)
        db.add(fam)
        db.flush()
        for iid in ids:
            if iid in valid_ids:
                db.add(InstrumentFamilyMember(family_id=fam.id, instrument_id=iid))
    db.commit()
