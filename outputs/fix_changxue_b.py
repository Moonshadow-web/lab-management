import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), 'backend'))
from app.core.database import SessionLocal
from app.services.notification_service import refresh_eqa_notifications
from app.models.eqa import EqaPlan

db = SessionLocal()
# #42,43 是北京市 常规化学B (NCCL-C-33)，批量改名时误标为 常规化学A，纠正回 常规化学B
cnt = db.query(EqaPlan).filter(
    EqaPlan.org == '北京市', EqaPlan.note.like('%常规化学B%')
).update({EqaPlan.program: '常规化学B'}, synchronize_session=False)
print('fixed 常规化学B rows:', cnt)
db.commit()
refresh_eqa_notifications(db)
db.close()
print('DONE')
