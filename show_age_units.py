# -*- coding: utf-8 -*-
import pandas as pd

df = pd.read_excel(r'C:\Users\81526\Desktop\检验科参考值维护数据(2).xlsx')
df.columns = [str(c).strip() for c in df.columns]

targets = ['尿素', '肌酐', '总蛋白', '钾', '氯', '钠']

with open('d:/workbuddyprojects/网页版-生免速查工具/age_units_output.txt', 'w', encoding='utf-8') as f:
    for t in targets:
        sub = df[df['检验项目中文全称'].fillna('').str.contains(t, na=False)]
        sub2 = sub[sub['标本全称'].fillna('').str.contains('血清|血浆', na=False)]
        # 去重
        seen = set()
        f.write(f"\n{'='*80}\n")
        f.write(f"【{t}】\n")
        f.write(f"{'='*80}\n")
        for _, row in sub2.iterrows():
            key = (str(row['年龄下限']), str(row['年龄上限']), str(row['性别']), str(row['正常值下限']), str(row['正常值上限']))
            if key in seen:
                continue
            seen.add(key)
            age_unit_low = str(row.get('(无列名)', ''))
            age_unit_up = str(row.get('(无列名).1', ''))
            # 处理nan
            age_unit_low = '' if age_unit_low == 'nan' else age_unit_low
            age_unit_up = '' if age_unit_up == 'nan' else age_unit_up
            
            f.write(f"  性别={str(row['性别']) or '通用'} | 年龄={row['年龄下限']}{age_unit_low}~{row['年龄上限']}{age_unit_up} | {row['正常值下限']}~{row['正常值上限']} | 标本={row['标本全称']} | 设备={row['设备简称']}\n")

print("Done!")
