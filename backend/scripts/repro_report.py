import sys, os, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # backend/
from app.core.database import SessionLocal
from app.models.comparison import ComparisonPlan, ComparisonGroup
from app.services import comparison_report as svc

db = SessionLocal()
plans = db.query(ComparisonPlan).order_by(ComparisonPlan.id).all()
print("TOTAL plans:", len(plans))
for p in plans:
    g = db.get(ComparisonGroup, p.group_id)
    if not g:
        print(f"[plan {p.id}] NO GROUP (group_id={p.group_id})")
        continue
    tag = f"[plan {p.id} group='{g.name}' cat={g.category}]"
    try:
        data = svc.compute_data(db, g, p)
        cat = data.get("category")
        nblk = len(data.get("matrix", []))
        if cat == "定量":
            nrows = sum(len(b["rows"]) for b in data["matrix"])
            print(f"{tag} compute_data OK 定量 blocks={nblk} rows={nrows}")
        else:
            print(f"{tag} compute_data OK 定性 items={len(data['matrix'])}")
    except Exception as e:
        print(f"{tag} compute_data ERROR {type(e).__name__}: {e}")
        traceback.print_exc()
        continue
    # build_html
    try:
        html = svc.build_html(g, p, data)
        print(f"{tag} build_html OK len={len(html)}")
    except Exception as e:
        print(f"{tag} build_html ERROR {type(e).__name__}: {e}")
        traceback.print_exc()
    # build_docx
    try:
        out = os.path.join(os.path.dirname(__file__), "..", "tmp_report_test.docx")
        svc.build_docx(db, g, p, data, out)
        print(f"{tag} build_docx OK")
    except Exception as e:
        print(f"{tag} build_docx ERROR {type(e).__name__}: {e}")
        traceback.print_exc()
db.close()
print("DONE")
