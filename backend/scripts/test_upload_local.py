"""本地复现质控上传 500：直接调用 upload_qc_summary，打印完整 traceback。"""
import io
import sys
import traceback
from datetime import datetime

from fastapi import UploadFile

# 先把 backend 加入路径
sys.path.insert(0, "d:/workbuddyprojects/网页版-生免速查工具/backend")

from app.core.database import SessionLocal, engine, Base
from app.models.user import User
from app.models.instrument import Instrument
from app.api.v1.qc_summaries import upload_qc_summary


CSV_CONTENT = """日期,项目,水平,靶值,标准差,CV%,结果,单位,失控规则,原因,处理
2026-06-01,β2微球蛋白,1,1.00,0.03,3.00,1.05,mg/L,1-3S(失控),质控品过期,重新校准
2026-06-02,β2微球蛋白,1,1.00,0.03,3.00,1.02,mg/L,,,
2026-06-03,β2微球蛋白,1,1.00,0.03,3.00,1.01,mg/L,,,
2026-06-04,β2微球蛋白,1,1.00,0.03,3.00,1.85,mg/L,1-3S(失控),,
2026-06-05,β2微球蛋白,1,1.00,0.03,3.00,1.03,mg/L,,,
""".encode("utf-8-sig")


def main():
    db = SessionLocal()
    try:
        # 确保表存在
        Base.metadata.create_all(bind=engine)

        # 找一个 admin 用户
        user = db.query(User).filter(User.username == "jinzizheng").first()
        if user is None:
            print("ERROR: 本地没有 jinzizheng 用户，请先用 seed 初始化")
            return

        # 确保有质控受控仪器
        inst = db.query(Instrument).filter(Instrument.name == "AU5800").first()
        if inst is None:
            inst = Instrument(
                name="AU5800",
                model="AU5800",
                category="生化",
                qc_instrument=True,
            )
            db.add(inst)
            db.commit()
            db.refresh(inst)
            print(f"created instrument id={inst.id}")
        else:
            print(f"using existing instrument id={inst.id}")

        fake_file = UploadFile(
            filename="test_beta2.csv",
            file=io.BytesIO(CSV_CONTENT),
        )
        result = upload_qc_summary(
            file=fake_file,
            instrument_id=inst.id,
            db=db,
            user=user,
        )
        print("SUCCESS:", result)
    except Exception:
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
