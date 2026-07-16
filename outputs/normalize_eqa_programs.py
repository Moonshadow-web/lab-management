import sys, os, json
sys.path.insert(0, os.path.join(os.getcwd(), 'backend'))
from app.core.database import SessionLocal
from app.services.notification_service import refresh_eqa_notifications
from app.models.eqa import EqaPlan

db = SessionLocal()

# ---- 1. 统一 program(项目组) 命名为规范47项 ----
rename = {
    '常规化学': '常规化学A',
    '常规化学2': '常规化学B',
    '脂类': '脂类A',
    '糖化': '糖化血红蛋白',
    '糖化白蛋白GA': '糖化白蛋白',
    '血气': '血气和酸碱分析',
    '药物监测': '血清治疗药物监测',
    '感染快检': '感染性疾病抗原抗体快速检测',
    '感A': '感染性疾病血清学标志物系列A',
    '感B': '感染性疾病血清学标志物系列B',
    '感C': '感染性疾病血清学标志物系列C',
    '肝炎': '感染性疾病血清学标志物系列A',  # 乙肝五项，与感A同计划
    '尿定量生化': '尿液定量生化',
    'BNP': '心衰标志物',
    'CYS-C': '半胱氨酸蛋白酶抑制剂C',
    'DD FDP': 'D-二聚体检测',
    '尿蛋白标志物': '尿液蛋白标志物Ⅰ',
    'PCT': '血清降钙素原',
    'AMH': '抗缪勒管激素',
    'SAA': '血清淀粉样蛋白A',
    'IL-6': '细胞因子',
    '肝纤': '肝纤维化血清学指标',
    'VWF': '血管性血友病因子抗原检测',
    '抗Xa': '抗凝血因子Xa活性检测',
    '产筛': '中孕期母血清产前筛查',
    '唐筛': '中孕期母血清产前筛查',
    '甲功正确度': '甲功相关项目检测及正确度验证',
    '代谢物、总蛋白正确度': '代谢物、总蛋白正确度验证',
    '脂类正确度': '脂类正确度验证',
    '酶学正确度': '酶学正确度验证',
    '糖化血红蛋白正确度': '糖化血红蛋白正确度验证',
    '电解质正确度': '电解质正确度验证',
    '类固醇激素正确度': '类固醇激素正确度验证',
    '优生优育': '优生优育免疫学测定',
    'C肽和胰岛素正确度': 'C肽和胰岛素检测及正确度验证',
    '凝血': '凝血试验',
    '肿标A': '肿瘤标志物A',
}
n_changed = 0
for old, new in rename.items():
    cnt = db.query(EqaPlan).filter(EqaPlan.program == old).update({EqaPlan.program: new}, synchronize_session=False)
    if cnt:
        print(f"  {old!r} -> {new!r}: {cnt} 行")
    n_changed += cnt
db.commit()
print(f"[1] program 重命名共 {n_changed} 行")

# ---- 2. 补录缺失 4 项（卫健委/2026），每项 2 轮 ----
schedule = json.load(open(r'C:/Users/81526/.workbuddy/tmp_lnk/schedule.json', encoding='utf-8'))
by_name = {x['name']: x for x in schedule}
new_plans = [
    ('血清蛋白电泳', '生化'),
    ('脂类B', '生化'),
    ('甲状腺功能检测', '免疫'),
    ('骨代谢标志物', '生化'),
]
inserted = 0
for name, grp in new_plans:
    info = by_name.get(name)
    if not info:
        print(f"  !! 未找到排期: {name}"); continue
    code = info['code']
    for r in info['rounds']:
        existing = db.query(EqaPlan).filter(
            EqaPlan.year == 2026, EqaPlan.org == '卫健委', EqaPlan.program == name,
            EqaPlan.round_no == f"第{r['round']}次").first()
        if existing:
            print(f"  跳过已存在 {name} 第{r['round']}次"); continue
        db.add(EqaPlan(
            year=2026, org='卫健委', program=name, group=grp, item=name,
            round_no=f"第{r['round']}次",
            sample_date=r['measure'], due_date=r['deadline'],
            returned=False, result='', qualified=False, score='',
            note=f'NCCL编码：{code}（{name}）', report_file=''
        ))
        inserted += 1
        print(f"  插入 {name} 第{r['round']}次 due={r['deadline']} ({code})")
db.commit()
print(f"[2] 新增 {inserted} 行")

# ---- 3. 刷新提醒（program 改名 + 新记录后，通知文案需同步） ----
refresh_eqa_notifications(db)
print("[3] 已刷新 eqa_return 通知")
db.close()
print("DONE")
