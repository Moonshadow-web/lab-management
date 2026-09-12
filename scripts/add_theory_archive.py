# -*- coding: utf-8 -*-
"""岗前理论考核答题记录：模型 + schema + 路由 + 公开提交时写归档。"""
import io
import re

# ---------------- 1) 模型 ----------------
p = 'app/models/education.py'
s = io.open(p, encoding='utf-8').read()
if 'PreJobTheoryRecord' not in s:
    s = s.rstrip() + '''


# =========================================================================
# 岗前理论考核答题记录（扫码/在线答题的独立归档，每次提交一条，不覆盖）
# =========================================================================
class PreJobTheoryRecord(Base):
    """一次理论答题的归档记录（可作为理论考核归档留存）。"""

    __tablename__ = "prejob_theory_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    pre_job_auth_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, default=None)  # 关联岗前考核单
    name: Mapped[str] = mapped_column(String(50), index=True, default="")  # 被考核人
    posts_json: Mapped[str] = mapped_column(Text, default="[]")  # 考核岗位（多选）
    papers_json: Mapped[str] = mapped_column(Text, default="{}")  # 试卷快照（题目与标准答案，防题库改版无法复核）
    answers_json: Mapped[str] = mapped_column(Text, default="{}")  # 作答明细 {岗位:{s0:..,m0:[],j0:..}}
    detail_json: Mapped[str] = mapped_column(Text, default="{}")  # 各岗位得分 {岗位:{score,full,pct}}
    score_raw: Mapped[int] = mapped_column(Integer, default=0)  # 原始分合计
    score_full: Mapped[int] = mapped_column(Integer, default=0)  # 原始满分合计
    score_pct: Mapped[int] = mapped_column(Integer, default=0)  # 百分制（各岗位平均）
    attempt_no: Mapped[int] = mapped_column(Integer, default=1)  # 第几次作答
    source: Mapped[str] = mapped_column(String(20), default="qr")  # qr=扫码 / online=登录在线
    submit_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
'''
    io.open(p, 'w', encoding='utf-8').write(s)
    print('模型 PreJobTheoryRecord 已加')

# 注册模型
p = 'app/models/__init__.py'
s = io.open(p, encoding='utf-8').read()
if 'PreJobTheoryRecord' not in s:
    m = re.search(r'from \.education import \(([^)]*)\)', s, re.S)
    if m:
        inner = m.group(1).rstrip()
        if not inner.endswith(','):
            inner += ','
        inner += '\n    PreJobTheoryRecord,'
        s = s[:m.start()] + 'from .education import (' + inner + '\n)' + s[m.end():]
    else:
        m2 = re.search(r'from \.education import ([^\n]+)\n', s)
        assert m2, 'education import line not found'
        s = s.replace(m2.group(0), m2.group(0).rstrip() + '\nfrom .education import PreJobTheoryRecord\n', 1)
    io.open(p, 'w', encoding='utf-8').write(s)
    print('models/__init__ 已注册')

# ---------------- 2) schema ----------------
p = 'app/schemas/education.py'
s = io.open(p, encoding='utf-8').read()
if 'PreJobTheoryRecordBase' not in s:
    s = s.rstrip() + '''


class PreJobTheoryRecordBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    pre_job_auth_id: int | None = None
    name: str = ""
    posts_json: list = []
    papers_json: dict = {}
    answers_json: dict = {}
    detail_json: dict = {}
    score_raw: int = 0
    score_full: int = 0
    score_pct: int = 0
    attempt_no: int = 1
    source: str = "qr"
    submit_at: datetime | None = None

    @field_validator("posts_json", mode="before")
    @classmethod
    def _tr_list(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v or "[]")
            except Exception:
                return []
        return v or []

    @field_validator("papers_json", "answers_json", "detail_json", mode="before")
    @classmethod
    def _tr_dict(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v or "{}")
            except Exception:
                return {}
        return v or {}


class PreJobTheoryRecordCreate(PreJobTheoryRecordBase):
    pass


class PreJobTheoryRecordUpdate(PreJobTheoryRecordBase):
    pass


class PreJobTheoryRecordRead(PreJobTheoryRecordBase):
    id: int
'''
    io.open(p, 'w', encoding='utf-8').write(s)
    print('schema 已加')

# ---------------- 3) 路由 ----------------
p = 'app/api/v1/education.py'
s = io.open(p, encoding='utf-8').read()
inc0 = s.count('router.include_router')
# 导入模型与 schema
if 'PreJobTheoryRecord,' not in s:
    s = s.replace('    PreJobAuth, ExamBank, PostInstrumentMap,', '    PreJobAuth, ExamBank, PostInstrumentMap, PreJobTheoryRecord,', 1)
if 'PreJobTheoryRecordRead,' not in s:
    s = s.replace('    PostInstrumentMapCreate, PostInstrumentMapUpdate, PostInstrumentMapRead,',
                  '    PostInstrumentMapCreate, PostInstrumentMapUpdate, PostInstrumentMapRead,\n    PreJobTheoryRecordCreate, PreJobTheoryRecordUpdate, PreJobTheoryRecordRead,', 1)
# 路由定义（放在文件末尾 include 之前）
if 'theoryrec_router' not in s:
    defn = '''
# L. 岗前理论考核答题记录（归档）
theoryrec_router = make_router(
    PreJobTheoryRecord, PreJobTheoryRecordRead, PreJobTheoryRecordCreate, PreJobTheoryRecordUpdate,
    search_fields=["name"], filter_fields=["pre_job_auth_id", "source"],
    order_by=[PreJobTheoryRecord.submit_at.desc(), PreJobTheoryRecord.id.desc()],
    prefix="/prejob-theory-records", write_roles=("admin", "training_manager"),
    json_fields=["posts_json", "papers_json", "answers_json", "detail_json"],
)
'''
    anchor = 'router.include_router(personnel_router)'
    assert anchor in s
    s = s.replace(anchor, defn.strip() + '\n\n' + anchor, 1)
    s = s.rstrip() + '\nrouter.include_router(theoryrec_router)\n'
    print('路由已加')
io.open(p, 'w', encoding='utf-8').write(s)
print('include 前/后:', inc0, s.count('router.include_router'))

# ---------------- 4) 提交时写归档 ----------------
s = io.open(p, encoding='utf-8').read()
if 'PreJobTheoryRecord(' not in s:
    old = '''    pcts = [v["pct"] for v in detail.values()]
    avg_pct = int(round(sum(pcts) / len(pcts))) if pcts else 0
    return {"ok": True, "score": total, "full": full, "pct": avg_pct, "detail": detail}'''
    new = '''    pcts = [v["pct"] for v in detail.values()]
    avg_pct = int(round(sum(pcts) / len(pcts))) if pcts else 0

    # 归档：每次提交单独留存一条（失败不影响考生提交）
    try:
        papers = {}
        for post in positions:
            b = db.query(ExamBank).filter(ExamBank.post == post).first()
            T = json.loads((b.theory_json if b else None) or "{}")
            papers[post] = T
        prev = db.query(PreJobTheoryRecord).filter(PreJobTheoryRecord.pre_job_auth_id == p.id).count()
        db.add(PreJobTheoryRecord(
            pre_job_auth_id=p.id,
            name=p.name,
            posts_json=json.dumps(positions, ensure_ascii=False),
            papers_json=json.dumps(papers, ensure_ascii=False),
            answers_json=json.dumps(answers, ensure_ascii=False),
            detail_json=json.dumps(detail, ensure_ascii=False),
            score_raw=total,
            score_full=full,
            score_pct=avg_pct,
            attempt_no=prev + 1,
            source=str(payload.get("source") or "qr"),
            submit_at=datetime.now(),
        ))
        db.commit()
    except Exception as e:  # noqa: BLE001
        db.rollback()
        try:
            logger.warning("理论答题归档写入失败(忽略): %s", e)
        except Exception:  # noqa: BLE001
            pass

    return {"ok": True, "score": total, "full": full, "pct": avg_pct, "detail": detail}'''
    assert old in s, 'submit return block not found'
    s = s.replace(old, new, 1)
    if 'logger' not in s.split('def public_exam_submit')[0][-3000:]:
        s = s.replace('import json\n', 'import json\nimport logging\n\nlogger = logging.getLogger(__name__)\n', 1)
    io.open(p, 'w', encoding='utf-8').write(s)
    print('提交归档逻辑已加')
