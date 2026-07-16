#!/usr/bin/env python3
import os, sys
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend = os.path.join(BASE, 'backend')
if backend not in sys.path:
    sys.path.insert(0, backend)

from app.core.database import SessionLocal
from app.services.notification_service import refresh_eqa_notifications

db = SessionLocal()
try:
    refresh_eqa_notifications(db)
    print('EQA notifications refreshed')
finally:
    db.close()
