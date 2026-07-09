"""种子数据导入：库为空时写入管理员账号，并从 seed_data.json（由 extract_data.js 从 data.js 解析得到）导入项目、仪器、说明书。"""
import json
import shutil
from pathlib import Path

from ..core.config import PROJECT_ROOT, UPLOAD_ROOT
from ..core.security import hash_password
from ..models.document import Document, DocumentVersion
from ..models.instrument import Instrument
from ..models.test_item import TestItem
from ..models.user import User

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
