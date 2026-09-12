# -*- coding: utf-8 -*-
"""S1 第 2 批：试剂与到货相关表加 group_code（其他组要用试剂管理与到货接收）。"""
import io
import re

p = 'app/models/reagent_management.py'
s = io.open(p, encoding='utf-8').read()

classes = [
    'ReagentItem', 'ReagentStock', 'InventoryCheck', 'InventoryCheckItem',
    'ReagentOrder', 'ReagentOrderItem', 'Receiving', 'ReceivingItem',
    'ReagentConsumption', 'TestItemReagent', 'InstrumentReagent',
]
COL = '    group_code: Mapped[str] = mapped_column(String(20), server_default="sm", default="sm", index=True)  # 专业组（默认生免组）\n'

added = []
for cls in classes:
    marker = 'class %s(Base):' % cls
    if marker not in s:
        print('未找到', cls)
        continue
    idx = s.index(marker)
    # 该类的类体范围
    nxt = s.find('\nclass ', idx + 1)
    body = s[idx:nxt if nxt > 0 else len(s)]
    if 'group_code' in body:
        print('已有 group_code，跳过', cls)
        continue
    m = re.search(r'\n(    \w+: Mapped\[[^\n]*\n)', body)
    if not m:
        print('无字段可插', cls)
        continue
    insert_at = idx + m.start() + 1
    s = s[:insert_at] + COL + s[insert_at:]
    added.append(cls)

# Numeric 已导入，Mapped 也需确认
if 'Mapped' not in s.split('\n')[9]:
    pass
io.open(p, 'w', encoding='utf-8').write(s)
print('已加 group_code 的类:', added)

# 确认 Mapped/mapped_column 已导入
head = s[:2000]
need = []
if 'Mapped' not in head:
    need.append('Mapped')
if 'mapped_column' not in head:
    need.append('mapped_column')
print('缺失导入:', need or '无')
