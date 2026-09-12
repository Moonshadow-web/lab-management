# -*- coding: utf-8 -*-
"""S1 第 1 批：给用户 + 三个核心模块（项目/文件/仪器）加 group_code 列，并种子专业组字典。

安全要点：
- 列定义带 server_default='sm' → ALTER ADD COLUMN 在非空表上安全（MySQL 允许
  NOT NULL + DEFAULT），且存量行自动为 'sm'（= 生免组），不改动任何查询逻辑。
- 只加列、不改逻辑，向后完全兼容。
"""
import io
import re

# 1) 四个模型加列
targets = {
    'app/models/user.py': ('class User(Base):', 'group_code'),
    'app/models/test_item.py': ('class TestItem(Base):', 'group_code'),
    'app/models/document.py': ('class Document(Base):', 'group_code'),
    'app/models/instrument.py': ('class Instrument(Base):', 'group_code'),
}
COL = '    group_code: Mapped[str] = mapped_column(String(20), server_default="sm", default="sm", index=True)  # 专业组（默认生免组）\n'

for path, (cls_line, colname) in targets.items():
    s = io.open(path, encoding='utf-8').read()
    if 'group_code' in s:
        print('已有 group_code，跳过', path)
        continue
    assert cls_line in s, cls_line + ' not found in ' + path
    # 插到类定义的第一个字段之后（保持缩进一致）
    idx = s.index(cls_line)
    # 找到类体内第一行的位置，插到类体开头
    body_start = s.index('\n', idx) + 1
    # 跳过类文档字符串/空行，插在第一个 mapped_column 行之前
    m = re.search(r'\n(    \w+: Mapped\[[^\n]*\n)', s[idx:])
    assert m, 'no mapped column found in ' + path
    insert_at = idx + m.start() + 1
    s = s[:insert_at] + COL + s[insert_at:]
    io.open(path, 'w', encoding='utf-8').write(s)
    print('已加 group_code →', path)

# 2) models/__init__.py 注册
p = 'app/models/__init__.py'
s = io.open(p, encoding='utf-8').read()
if 'lab_group' not in s:
    s = s.replace('from .instrument import CalibrationRecord, Instrument, InstrumentRepair',
                  'from .lab_group import LAB_GROUPS, DEFAULT_GROUP_CODE, LabGroup\nfrom .instrument import CalibrationRecord, Instrument, InstrumentRepair', 1)
    io.open(p, 'w', encoding='utf-8').write(s)
    print('已注册 LabGroup 模型')

# 3) main.py：启动时幂等种子专业组字典
p = 'app/main.py'
s = io.open(p, encoding='utf-8').read()
if '_seed_lab_groups' not in s:
    fn = '''

def _seed_lab_groups():
    """幂等种子：专业组字典（生免/临检/微生物/分子/血库）。缺失才插入，不覆盖已有。"""
    try:
        from .models.lab_group import LAB_GROUPS, LabGroup
        with SessionLocal() as db:
            existing = {row[0] for row in db.query(LabGroup.code).all()}
            added = 0
            for code, name, sort_no in LAB_GROUPS:
                if code in existing:
                    continue
                db.add(LabGroup(code=code, name=name, sort_no=sort_no, is_active=True))
                added += 1
            if added:
                db.commit()
                logger.info("专业组字典种子：新增 %d 个组", added)
    except Exception as e:  # noqa: BLE001
        logger.warning("专业组字典种子失败(忽略): %s", e)


def _ensure_missing_columns():'''
    s = s.replace('\n\ndef _ensure_missing_columns():', fn, 1)
    io.open(p, 'w', encoding='utf-8').write(s)
    print('已加入 _seed_lab_groups')

# 4) lifespan 中调用（建表之后）
s = io.open(p, encoding='utf-8').read()
if '_seed_lab_groups()' not in s.split('def _seed_lab_groups')[0] and '        _seed_lab_groups()' not in s:
    old = """    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:  # noqa: BLE001
        logger.error("init error (create_all): %s", e)"""
    new = old + """
    try:
        _seed_lab_groups()
    except Exception as e:  # noqa: BLE001
        logger.warning("seed lab_groups error (non-fatal): %s", e)"""
    assert old in s, 'create_all block not found'
    s = s.replace(old, new, 1)
    io.open(p, 'w', encoding='utf-8').write(s)
    print('已在 lifespan 调用种子')
