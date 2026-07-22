"""三类项目质量要求种子数据。

来源：
  - wst403-2024: 临床化学检验常用项目分析质量标准（中华人民共和国卫生行业标准 WS/T 403—2024）
                  附录 A 表 A.1（PDF C:\\Users\\81526\\Desktop\\WST403-2024临床化学检验常用项目分析质量标准.pdf）
  - bj-hr-2025:  2025 年北京市临床检验结果互认项目（材料3，V6）
                  （PDF C:\\Users\\81526\\Desktop\\材料3：北京市检验结果互认项目精密度及重现性要求-V6.pdf）
  - nccl-2026:   2026 年国家卫健委 NCCL 室间质量评价计划（0805 版，第 94-116 页）
                  （PDF C:\\Users\\81526\\Desktop\\2026年全国临床检验室间质量评价计划0805\\2026年全国临床检验室间质量评价计划0805_94-116.pdf）

字段语义（与 quality_requirements 表保持一致）：
  cv   = 允许不精密度（CV 或 SD；空字符串表示该标准未给出此项）
  bias = 允许偏倚
  tea  = 允许总误差 / EQA 可接受范围
  unit = 推荐结果单位（仅北京互认有，其他空）
  category = 来源内部分类（WS/T 留空；北京用序号；NCCL 用计划号如 NCCL-C-01）

本文件仅作为初始灌库来源；后续修改请走 API（admin 角色）。
"""
from typing import Any
import re


# ---------------- 安全包含匹配（打通项目库名 ↔ 标准源名） ----------------
# 直接用 `a in b` 做中文包含匹配太松：单字「钙」会误入「降钙素原/降钙素/骨钙素」，
# 且「降钙素」前缀会误入「降钙素原」。仅在「多余部分」全为修饰性成分
# （标本/基质前缀、括号及括号内单位代码、并列分隔符等）时才视为同一项目。
_SAFE_PREFIXES = (
    "总", "无机", "血清", "血浆", "全血", "血液", "尿液", "尿", "脑脊液", "空白",
    "检测", "测定", "定量", "浓度", "标本", "质控品", "质控",
)


def _strip_paren_groups(s: str) -> str:
    """去掉 ( ) （ ） [ ] 【 】 及其内部内容。"""
    return re.sub(r"[\(（\[【][^\)）\]】]*[\)）\]】]", "", s)


def _is_decoration(rem: str) -> bool:
    """判断多余部分是否仅由修饰性成分构成。

    允许：标本/基质中文前缀（总/血清/血浆…）、括号及单位代码（拉丁字母/数字/分隔符，
    如 cp/pct/ct/tsh）。中文部分只能由安全前缀拼接，否则视为不同项目。
    """
    rem = _strip_paren_groups(rem)
    if not rem:
        return True
    for seg in re.findall(r"[一-鿿]+|[^一-鿿]+", rem):
        if re.match(r"^[一-鿿]+$", seg):
            i, m = 0, len(seg)
            while i < m:
                hit = False
                for tok in _SAFE_PREFIXES:
                    if seg.startswith(tok, i):
                        i += len(tok)
                        hit = True
                        break
                if not hit:
                    return False
        else:
            # 非中文段只能是纯字母/数字/分隔符（单位代码）
            if not re.match(r"^[A-Za-z0-9.\-+/]+$", seg):
                return False
            # 纯数字后缀（如「免疫球蛋白G4」误匹配「免疫球蛋白G」的 "4"）视为不同项目，
            # 不能当作修饰性成分——子类数字与单位代码字母须区分。
            if not re.search(r"[A-Za-z]", seg):
                return False
    return True


def contains_same_item(a: str, b: str) -> bool:
    """判断 a、b 是否为同一检验项目的不同叫法（安全包含匹配）。

    规则：
      1) 去除首尾空白后精确相等 → 同一项目；
      2) 含 / 、 等并列分隔符（且分隔符在括号外）时，按段递归匹配任一子项；
      3) 单向包含且「非包含部分」仅剩修饰性成分（标本前缀/括号单位码）→ 同一项目；
      4) 其余包含（如短字「钙」误入「降钙素原」、前缀「降钙素」误入「降钙素原」）
         → 视为不同项目，不匹配。

    注意：项目库名均为中文，英文代码只在别名中；故不依赖「括号代码相等」，
    避免 TG(甲状腺球蛋白) 与 TG(甘油三酯) 等缩写碰撞。
    """
    if not a or not b:
        return False
    a, b = a.strip(), b.strip()
    if a == b:
        return True
    # 仅在括号外出现并列分隔符时才按段拆分（避免单位代码 μg/L 中的 / 被误拆）
    stripped_b = _strip_paren_groups(b)
    for sep in ("/", "、", "，", ",", "；", ";"):
        if sep in stripped_b:
            for part in b.split(sep):
                part = part.strip()
                if part and contains_same_item(a, part):
                    return True
    if a in b:
        i = b.index(a)
        rem = b[:i] + b[i + len(a):]
        return _is_decoration(rem)
    if b in a:
        i = a.index(b)
        rem = a[:i] + a[i + len(b):]
        return _is_decoration(rem)
    return False


# ---------------- WS/T 403—2024 ----------------
# 80 项，覆盖 PDF 附录 A 表 A.1 的 3 页
WST403_ITEMS: list[dict[str, Any]] = [
    # 通用临床化学
    {"item_name": "钾",     "cv": "2.5%", "bias": "2.0%", "tea": "0.2 mmol/L (≤3.3 mmol/L)；6.0% (>3.3 mmol/L)"},
    {"item_name": "钠",     "cv": "1.5%", "bias": "1.5%", "tea": "4.0%"},
    {"item_name": "氯",     "cv": "1.5%", "bias": "1.5%", "tea": "4.0%"},
    {"item_name": "钙",     "cv": "2.0%", "bias": "2.0%", "tea": "0.1 mmol/L (≤2 mmol/L)；5.0% (>2 mmol/L)"},
    {"item_name": "磷酸根离子", "cv": "4.0%", "bias": "3.0%", "tea": "10.0%"},
    {"item_name": "葡萄糖", "cv": "3.0%", "bias": "2.0%", "tea": "0.21 mmol/L (≤3 mmol/L)；7.0% (>3 mmol/L)"},
    {"item_name": "尿素",   "cv": "3.0%", "bias": "3.0%", "tea": "0.32 mmol/L (≤4 mmol/L)；8.0% (>4 mmol/L)"},
    {"item_name": "尿酸",   "cv": "4.5%", "bias": "4.5%", "tea": "12.0%"},
    {"item_name": "肌酐",   "cv": "4.0%", "bias": "5.5%", "tea": "6 μmol/L (≤50 μmol/L)；12.0% (>50 μmol/L)"},
    {"item_name": "总蛋白", "cv": "2.0%", "bias": "2.0%", "tea": "5.0%"},
    {"item_name": "白蛋白", "cv": "2.5%", "bias": "2.0%", "tea": "6.0%"},
    {"item_name": "总胆固醇", "cv": "3.0%", "bias": "4.0%", "tea": "9.0%"},
    {"item_name": "甘油三酯", "cv": "5.0%", "bias": "5.0%", "tea": "14.0%"},
    {"item_name": "高密度脂蛋白胆固醇", "cv": "6.0%", "bias": "8.0%", "tea": "0.16 mmol/L (≤0.8 mmol/L)；20.0% (>0.8 mmol/L)"},
    {"item_name": "低密度脂蛋白胆固醇", "cv": "6.0%", "bias": "8.0%", "tea": "0.4 mmol/L (≤2 mmol/L)；20.0% (>2 mmol/L)"},
    {"item_name": "载脂蛋白 AⅠ", "cv": "8.0%", "bias": "10.0%", "tea": "0.2 g/L (≤0.8 g/L)；25.0% (>0.8 g/L)"},
    {"item_name": "载脂蛋白 B",   "cv": "8.0%", "bias": "10.0%", "tea": "0.15 g/L (≤0.6 g/L)；25.0% (>0.6 g/L)"},
    {"item_name": "脂蛋白(a)", "cv": "10.0%", "bias": "10.0%", "tea": "45 mg/L (≤150 mg/L)；30.0% (>150 mg/L)"},
    {"item_name": "总胆红素", "cv": "6.0%", "bias": "5.0%", "tea": "2.4 μmol/L (≤16 μmol/L)；15.0% (>16 μmol/L)"},
    {"item_name": "直接胆红素/结合胆红素", "cv": "8.0%", "bias": "6.7%", "tea": "1 μmol/L (≤5 μmol/L)；20.0% (>5 μmol/L)"},
    {"item_name": "丙氨酸氨基转移酶", "cv": "6.0%", "bias": "5.0%", "tea": "6 U/L (≤40 U/L)；15.0% (>40 U/L)"},
    {"item_name": "天门冬氨酸氨基转移酶", "cv": "6.0%", "bias": "5.0%", "tea": "6 U/L (≤40 U/L)；15.0% (>40 U/L)"},
    {"item_name": "碱性磷酸酶", "cv": "5.0%", "bias": "10.0%", "tea": "9 U/L (≤50 U/L)；18.0% (>50 U/L)"},
    {"item_name": "淀粉酶",   "cv": "4.5%", "bias": "7.5%", "tea": "9 U/L (≤60 U/L)；15.0% (>60 U/L)"},
    {"item_name": "肌酸激酶", "cv": "5.5%", "bias": "5.5%", "tea": "15.0%"},
    {"item_name": "乳酸脱氢酶", "cv": "4.0%", "bias": "4.0%", "tea": "11.0%"},
    {"item_name": "γ-谷氨酰基转移酶", "cv": "3.5%", "bias": "5.5%", "tea": "4.4 U/L (≤40 U/L)；11.0% (>40 U/L)"},
    {"item_name": "α-羟丁酸脱氢酶", "cv": "7.5%", "bias": "10.0%", "tea": "25.0%"},
    {"item_name": "胆碱酯酶", "cv": "6.0%", "bias": "8.0%", "tea": "20.0%"},
    {"item_name": "铁",       "cv": "6.5%", "bias": "4.5%", "tea": "2.1 μmol/L (≤14 μmol/L)；15.0% (>14 μmol/L)"},
    {"item_name": "镁",       "cv": "5.5%", "bias": "5.5%", "tea": "0.12 mmol/L (≤0.8 mmol/L)；15.0% (>0.8 mmol/L)"},
    {"item_name": "胱抑素 C", "cv": "6.0%", "bias": "8.0%", "tea": "20.0%"},
    {"item_name": "肌酸激酶-MB(μg/L)", "cv": "10.0%", "bias": "10.0%", "tea": "4.5 μg/L (≤15 μg/L)；30.0% (>15 μg/L)"},
    {"item_name": "肌酸激酶-MB(U/L)",  "cv": "10.0%", "bias": "8.0%",  "tea": "3.75 U/L (≤15 U/L)；25.0% (>15 U/L)"},
    {"item_name": "肌红蛋白", "cv": "10.0%", "bias": "10.0%", "tea": "30.0%"},
    {"item_name": "同型半胱氨酸", "cv": "8.0%", "bias": "10.0%", "tea": "3 μmol/L (≤12 μmol/L)；25.0% (>12 μmol/L)"},
    {"item_name": "HbA1c (NGSP 单位)", "cv": "2.0%", "bias": "3.0%", "tea": "0.4% HbA1c (≤6.7%)；6.0% (>6.7%)"},
    {"item_name": "HbA1c (IFCC 单位)", "cv": "3.0%", "bias": "3.6%", "tea": "4.3 mmol/mol (≤50)；8.6% (>50)"},
    # 血气
    {"item_name": "pH（血气）", "cv": "0.02", "bias": "0.015", "tea": "0.04"},
    {"item_name": "CO2 分压",   "cv": "4.0%", "bias": "4.0%", "tea": "5 mmHg (≤62.5)；8.0% (>62.5)"},
    {"item_name": "O2 分压",    "cv": "5.0%", "bias": "5.0%", "tea": "6 mmHg (≤60)；10.0% (>60)"},
    # 免疫
    {"item_name": "免疫球蛋白 G", "cv": "6.0%", "bias": "8.0%", "tea": "20.0%"},
    {"item_name": "免疫球蛋白 A", "cv": "6.0%", "bias": "8.0%", "tea": "20.0%"},
    {"item_name": "免疫球蛋白 M", "cv": "7.5%", "bias": "10.0%", "tea": "25.0%"},
    {"item_name": "补体 C3", "cv": "6.0%", "bias": "8.0%", "tea": "20.0%"},
    {"item_name": "补体 C4", "cv": "7.5%", "bias": "10.0%", "tea": "25.0%"},
    {"item_name": "C-反应蛋白", "cv": "7.5%", "bias": "10.0%", "tea": "25.0%"},
    {"item_name": "类风湿因子", "cv": "7.5%", "bias": "10.0%", "tea": "25.0%"},
    {"item_name": "抗链球菌溶血素 O", "cv": "7.5%", "bias": "10.0%", "tea": "25.0%"},
    {"item_name": "前白蛋白", "cv": "7.5%", "bias": "10.0%", "tea": "25.0%"},
    {"item_name": "游离三碘甲状腺原氨酸", "cv": "7.0%", "bias": "8.0%", "tea": "0.7 pmol/L (≤3.5)；20.0% (>3.5)"},
    {"item_name": "总三碘甲状腺原氨酸",   "cv": "7.0%", "bias": "8.0%", "tea": "0.26 nmol/L (≤1.3)；20.0% (>1.3)"},
    {"item_name": "游离甲状腺素", "cv": "7.0%", "bias": "8.0%", "tea": "2.4 pmol/L (≤12)；20.0% (>12)"},
    {"item_name": "总甲状腺素", "cv": "7.0%", "bias": "8.0%", "tea": "24 nmol/L (≤120)；20.0% (>120)"},
    {"item_name": "促甲状腺刺激激素", "cv": "7.0%", "bias": "8.0%", "tea": "0.1 U/L (≤0.5 mU/L)；20.0% (>0.5)"},
    {"item_name": "皮质醇", "cv": "7.0%", "bias": "8.0%", "tea": "20 nmol/L (≤100)；20.0% (>100)"},
    {"item_name": "雌二醇", "cv": "8.0%", "bias": "10.0%", "tea": "50 pmol/L (≤200)；25.0% (>200)"},
    {"item_name": "卵泡刺激素", "cv": "7.0%", "bias": "8.0%", "tea": "2 IU/L (≤10)；20.0% (>10)"},
    {"item_name": "黄体生成素", "cv": "7.0%", "bias": "8.0%", "tea": "2 IU/L (≤10)；20.0% (>10)"},
    {"item_name": "孕酮", "cv": "7.0%", "bias": "8.0%", "tea": "2 nmol/L (≤10)；20.0% (>10)"},
    {"item_name": "催乳素", "cv": "7.0%", "bias": "8.0%", "tea": "20 mIU/L (≤100)；20.0% (>100)"},
    {"item_name": "睾酮", "cv": "7.0%", "bias": "8.0%", "tea": "1 nmol/L (≤5)；20.0% (>5)"},
    {"item_name": "C-肽", "cv": "7.0%", "bias": "8.0%", "tea": "0.25 nmol/L (≤1.25)；20.0% (>1.25)"},
    {"item_name": "胰岛素", "cv": "8.0%", "bias": "12.0%", "tea": "35 pmol/L (≤140)；25.0% (>140)"},
    {"item_name": "叶酸", "cv": "9.0%", "bias": "12.0%", "tea": "2.4 nmol/L (≤8)；30.0% (>8)"},
    {"item_name": "维生素 B12", "cv": "8.0%", "bias": "10.0%", "tea": "25.0%"},
    {"item_name": "甲状腺球蛋白", "cv": "8.0%", "bias": "10.0%", "tea": "2 μg/L (≤8)；25.0% (>8)"},
    {"item_name": "甲状旁腺激素", "cv": "10.0%", "bias": "10.0%", "tea": "3 pmol/L (≤10)；30.0% (>10)"},
    {"item_name": "总前列腺特异抗原", "cv": "7.5%", "bias": "10.0%", "tea": "0.75 μg/L (≤3)；25.0% (>3)"},
    {"item_name": "游离前列腺特异抗原", "cv": "7.5%", "bias": "10.0%", "tea": "0.35 μg/L (≤1.4)；25.0% (>1.4)"},
    {"item_name": "癌胚抗原", "cv": "7.5%", "bias": "10.0%", "tea": "1.5 μg/L (≤6)；25.0% (>6)"},
    {"item_name": "甲胎蛋白", "cv": "7.5%", "bias": "10.0%", "tea": "2.5 ng/mL (≤10)；25.0% (>10)"},
    {"item_name": "糖链抗原 19-9", "cv": "7.5%", "bias": "10.0%", "tea": "5 kIU/L (≤20)；25.0% (>20)"},
    {"item_name": "糖链抗原 125", "cv": "7.5%", "bias": "10.0%", "tea": "10 kIU/L (≤40)；25.0% (>40)"},
    {"item_name": "糖链抗原 15-3", "cv": "7.5%", "bias": "10.0%", "tea": "7.5 kIU/L (≤30)；25.0% (>30)"},
    {"item_name": "β2-微球蛋白", "cv": "7.5%", "bias": "10.0%", "tea": "0.5 mg/L (≤2)；25.0% (>2)"},
    {"item_name": "铁蛋白", "cv": "7.5%", "bias": "10.0%", "tea": "6 μg/L (≤24)；25.0% (>24)"},
    {"item_name": "糖链抗原 72-4", "cv": "7.5%", "bias": "10.0%", "tea": "25.0%"},
    {"item_name": "细胞角蛋白 19 片段", "cv": "7.5%", "bias": "10.0%", "tea": "25.0%"},
    {"item_name": "特异性神经元烯醇酶", "cv": "7.5%", "bias": "10.0%", "tea": "25.0%"},
    {"item_name": "鳞状细胞癌抗原", "cv": "7.5%", "bias": "10.0%", "tea": "25.0%"},
    # 便携式血糖
    {"item_name": "葡萄糖（便携式血糖仪）",
     "cv": "SD<0.42 mmol/L (<5.5)；CV<7.5% (≥5.5)",
     "bias": "0.83 mmol/L (<5.5)；15.0% (≥5.5)",
     "tea": "1.1 mmol/L (<5.5)；20.0% (≥5.5)"},
]


# ---------------- 2025 北京市互认（材料3 V6） ----------------
# 注：北京表为「允许不精密度 + EQA 评价标准」两列；EQA 列即为「可接受范围」，
#     在本系统里记到 tea，bias 留空。category 用序号便于排序与展示。
BJHR_ITEMS: list[dict[str, Any]] = [
    {"category": "1",  "item_name": "白细胞计数(WBC)",       "cv": "6.0%",  "tea": "±15%", "unit": "10^9/L"},
    {"category": "1",  "item_name": "红细胞计数(RBC)",       "cv": "2.5%",  "tea": "±6%",  "unit": "10^12/L"},
    {"category": "1",  "item_name": "血红蛋白(Hb)",          "cv": "2.0%",  "tea": "±6%",  "unit": "g/L"},
    {"category": "1",  "item_name": "血小板计数(Plt)",       "cv": "8.0%",  "tea": "±20%", "unit": "10^9/L"},
    {"category": "1",  "item_name": "血细胞比容(Hct)",       "cv": "4.0%",  "tea": "±9%",  "unit": "%"},
    {"category": "1",  "item_name": "平均红细胞体积(MCV)",   "cv": "2.5%",  "tea": "±7%",  "unit": "fL"},
    {"category": "1",  "item_name": "平均红细胞血红蛋白含量(MCH)", "cv": "2.5%", "tea": "±7%", "unit": "pg"},
    {"category": "1",  "item_name": "平均红细胞血红蛋白浓度(MCHC)", "cv": "3.0%", "tea": "±8%", "unit": "g/L"},
    {"category": "2",  "item_name": "凝血酶原时间(PT)",      "cv": "正常6.5%/异常10.0%", "tea": "±15%"},
    {"category": "2",  "item_name": "国际标准化比值(INR)",   "cv": "正常6.5%/异常10.0%", "tea": "±20%"},
    {"category": "3",  "item_name": "活化部分凝血活酶时间(APTT)", "cv": "正常6.5%/异常10.0%", "tea": "±15%"},
    {"category": "4",  "item_name": "纤维蛋白原(Fib)",       "cv": "正常9.0%/异常12.0%", "tea": "±20%", "unit": "g/L"},
    {"category": "5",  "item_name": "凝血酶时间(TT)",        "cv": "正常10.0%/异常12.0%", "tea": "±20%"},
    {"category": "6",  "item_name": "D-二聚体(D-Dimer)",     "cv": "10.0%", "tea": "±30%", "unit": "μg/mL FEU 或 μg/mL DDU"},
    {"category": "7",  "item_name": "纤维蛋白(原)降解产物(FDP)", "cv": "11.7%", "tea": "±35%", "unit": "μg/mL"},
    {"category": "11", "item_name": "红细胞沉降率(ESR)",     "cv": "10.0%", "tea": "±3.0(≤10mm/h);±30%(>10mm/h)", "unit": "mm/h"},
    # 钾钠氯钙磷等
    {"category": "15", "item_name": "钾(K)",      "cv": "2.5%", "tea": "±6%",  "unit": "mmol/L"},
    {"category": "16", "item_name": "钠(Na)",     "cv": "1.5%", "tea": "±4%",  "unit": "mmol/L"},
    {"category": "17", "item_name": "氯(Cl)",     "cv": "1.5%", "tea": "±4%",  "unit": "mmol/L"},
    {"category": "18", "item_name": "钙(Ca)",     "cv": "2.0%", "tea": "±5%",  "unit": "mmol/L"},
    {"category": "19", "item_name": "磷(P)",      "cv": "4.0%", "tea": "±10%", "unit": "mmol/L"},
    {"category": "20", "item_name": "葡萄糖(Glu)", "cv": "3.0%", "tea": "±7%",  "unit": "mmol/L"},
    {"category": "21", "item_name": "尿素(Urea)",  "cv": "3.0%", "tea": "±8%",  "unit": "mmol/L"},
    {"category": "22", "item_name": "尿酸(UA)",    "cv": "4.5%", "tea": "±12%", "unit": "μmol/L"},
    {"category": "23", "item_name": "肌酐(Cre)",   "cv": "4.0%", "tea": "±12%", "unit": "μmol/L"},
    {"category": "24", "item_name": "白蛋白(Alb)", "cv": "2.5%", "tea": "±6%",  "unit": "g/L"},
    {"category": "25", "item_name": "总蛋白(TP)",  "cv": "2.0%", "tea": "±5%",  "unit": "g/L"},
    {"category": "26", "item_name": "总胆固醇(TC)","cv": "3.0%", "tea": "±9%",  "unit": "mmol/L"},
    {"category": "27", "item_name": "甘油三酯(TG)","cv": "5.0%", "tea": "±14%", "unit": "mmol/L"},
    {"category": "28", "item_name": "丙氨酸氨基转移酶(ALT)", "cv": "6.0%", "tea": "±16%", "unit": "U/L"},
    {"category": "29", "item_name": "天门冬氨酸氨基转移酶(AST)", "cv": "6.0%", "tea": "±15%", "unit": "U/L"},
    {"category": "30", "item_name": "总胆红素(TBil)", "cv": "6.0%", "tea": "±15%", "unit": "μmol/L"},
    {"category": "31", "item_name": "碱性磷酸酶(ALP)", "cv": "5.0%", "tea": "±18%", "unit": "U/L"},
    {"category": "32", "item_name": "淀粉酶(Amy)",     "cv": "4.5%", "tea": "±15%", "unit": "U/L"},
    {"category": "33", "item_name": "肌酸激酶(CK)",     "cv": "5.5%", "tea": "±15%", "unit": "U/L"},
    {"category": "34", "item_name": "乳酸脱氢酶(LDH)",  "cv": "4.0%", "tea": "±11%", "unit": "U/L"},
    {"category": "35", "item_name": "直接胆红素(D-Bil)","cv": "8.0%", "tea": "±20%", "unit": "μmol/L"},
    {"category": "36", "item_name": "铁(Fe)",            "cv": "6.5%", "tea": "±15%", "unit": "μmol/L"},
    {"category": "37", "item_name": "总铁结合力(TIBC)",  "cv": "6.7%", "tea": "±20%", "unit": "μmol/L"},
    {"category": "37", "item_name": "不饱和铁结合力(UIBC)", "cv": "6.7%", "tea": "±20%", "unit": "μmol/L"},
    {"category": "38", "item_name": "镁(Mg)",            "cv": "5.5%", "tea": "±15%", "unit": "mmol/L"},
    {"category": "39", "item_name": "γ-谷氨酰基转移酶(GGT)", "cv": "3.5%", "tea": "±11%", "unit": "U/L"},
    {"category": "40", "item_name": "α-羟丁酸脱氢酶(α-HBDH)", "cv": "7.5%", "tea": "±30%", "unit": "U/L"},
    {"category": "41", "item_name": "胆碱酯酶(CHE)",     "cv": "6.0%", "tea": "±20%", "unit": "U/L"},
    {"category": "42", "item_name": "脂肪酶(LIP)",       "cv": "6.7%", "tea": "±20%", "unit": "U/L"},
    {"category": "43", "item_name": "游离脂肪酸(NEFA)",  "cv": "8.3%", "tea": "±25%", "unit": "mmol/L"},
    {"category": "44", "item_name": "高密度脂蛋白胆固醇(HDL-C)", "cv": "6.0%", "tea": "±30%", "unit": "mmol/L"},
    {"category": "45", "item_name": "低密度脂蛋白胆固醇(LDL-C)", "cv": "6.0%", "tea": "±30%", "unit": "mmol/L"},
    {"category": "46", "item_name": "载脂蛋白A1(Apo-A1)","cv": "8.0%", "tea": "±30%", "unit": "g/L"},
    {"category": "47", "item_name": "载脂蛋白B(Apo-B)",  "cv": "8.0%", "tea": "±30%", "unit": "g/L"},
    {"category": "48", "item_name": "脂蛋白a(Lp(a))",    "cv": "10.0%","tea": "±30%", "unit": "mg/L"},
    {"category": "49", "item_name": "小而密低密度脂蛋白胆固醇(sdLDL-C)", "cv": "10.0%", "tea": "±30%", "unit": "mmol/L"},
    {"category": "50", "item_name": "胆汁酸(BA)",        "cv": "8.3%", "tea": "±25%", "unit": "μmol/L"},
    {"category": "51", "item_name": "肌酸激酶-MB 同工酶活性(CK-MB)", "cv": "10.0%", "tea": "±25%", "unit": "U/L"},
    {"category": "52", "item_name": "肌酸激酶-MB 同工酶质量(CK-MBmass)", "cv": "10.0%", "tea": "±30%", "unit": "μg/L"},
    {"category": "53", "item_name": "肌红蛋白(Myo)",     "cv": "10.0%", "tea": "±30%", "unit": "μg/L"},
    {"category": "54", "item_name": "肌钙蛋白I(TnI)",    "cv": "10.0%", "tea": "±30%", "unit": "μg/L"},
    {"category": "55", "item_name": "肌钙蛋白T(TnT)",    "cv": "10.0%", "tea": "±30%", "unit": "μg/L"},
    {"category": "56", "item_name": "超敏C反应蛋白(hs-CRP)","cv": "10.0%", "tea": "±30%", "unit": "mg/L"},
    {"category": "57", "item_name": "同型半胱氨酸(Hcy)",  "cv": "8.0%", "tea": "±20%", "unit": "μmol/L"},
    {"category": "58", "item_name": "脑钠肽(BNP)",       "cv": "10.0%", "tea": "±30%", "unit": "ng/L"},
    {"category": "59", "item_name": "N末端前脑钠肽(NT-ProBNP)", "cv": "10.0%", "tea": "±30%", "unit": "ng/L"},
    {"category": "60", "item_name": "糖化白蛋白(GA)",     "cv": "6.7%", "tea": "±20%", "unit": "%"},
    {"category": "61", "item_name": "视黄醇结合蛋白(RBP)","cv": "8.3%", "tea": "±25%", "unit": "mg/L"},
    {"category": "62", "item_name": "α-L-岩藻糖苷酶(AFU)","cv": "10.0%", "tea": "±30%", "unit": "U/L"},
    {"category": "63", "item_name": "糖化血红蛋白A1c(HbA1c)","cv": "2.0%", "tea": "±6%", "unit": "%"},
    {"category": "64", "item_name": "pH",                "cv": "0.02", "tea": "±0.04"},
    {"category": "64", "item_name": "PO2",               "cv": "5.0%",  "tea": "±10mmHg 或 ±10%(取大者)", "unit": "mmHg"},
    {"category": "64", "item_name": "PCO2",              "cv": "4.0%",  "tea": "±5mmHg 或 ±8%(取大者)", "unit": "mmHg"},
    {"category": "64", "item_name": "K+(血气)",          "cv": "2.5%",  "tea": "±6%", "unit": "mmol/L"},
    {"category": "64", "item_name": "Na+(血气)",         "cv": "1.5%",  "tea": "±4%", "unit": "mmol/L"},
    {"category": "64", "item_name": "Cl-(血气)",         "cv": "1.5%",  "tea": "±4%", "unit": "mmol/L"},
    {"category": "64", "item_name": "Ca2+(血气)",        "cv": "2.0%",  "tea": "±0.25mmol/L 或 ±5%(取大者)", "unit": "mmol/L"},
    # 尿系列
    {"category": "65", "item_name": "钾(尿液)",          "cv": "9.7%",  "tea": "±29%", "unit": "mmol/L"},
    {"category": "66", "item_name": "钠(尿液)",          "cv": "8.7%",  "tea": "±26%", "unit": "mmol/L"},
    {"category": "67", "item_name": "氯(尿液)",          "cv": "8.7%",  "tea": "±26%", "unit": "mmol/L"},
    {"category": "68", "item_name": "钙(尿液)",          "cv": "10.3%", "tea": "±31%", "unit": "mmol/L"},
    {"category": "69", "item_name": "镁(尿液)",          "cv": "8.3%",  "tea": "±25%", "unit": "mmol/L"},
    {"category": "70", "item_name": "磷(尿液)",          "cv": "7.7%",  "tea": "±23%", "unit": "mmol/L"},
    {"category": "71", "item_name": "葡萄糖(尿液)",      "cv": "6.7%",  "tea": "±20%", "unit": "mmol/L"},
    {"category": "72", "item_name": "尿素(尿液)",        "cv": "7.0%",  "tea": "±21%", "unit": "mmol/L"},
    {"category": "73", "item_name": "尿酸(尿液)",        "cv": "8.0%",  "tea": "±24%", "unit": "μmol/L"},
    {"category": "74", "item_name": "肌酐(尿液)",        "cv": "5.7%",  "tea": "±17%", "unit": "mmol/L"},
    {"category": "75", "item_name": "微量总蛋白(尿液)",  "cv": "14.7%", "tea": "±44%", "unit": "mg/L"},
    {"category": "76", "item_name": "淀粉酶(尿液)",      "cv": "10.0%", "tea": "±30%", "unit": "U/L"},
    {"category": "77", "item_name": "微量白蛋白(尿液)",  "cv": "10.0%", "tea": "±30%", "unit": "mg/L"},
    {"category": "77", "item_name": "尿微量白蛋白",  "cv": "10.0%", "tea": "±30%", "unit": ""},
    {"category": "77", "item_name": "尿转铁蛋白",    "cv": "8.3%",  "tea": "±25%", "unit": ""},
    # 脑脊液
    {"category": "78", "item_name": "微量总蛋白(脑脊液)","cv": "3.3%",  "tea": "±10%或±0.1g/L(取大者)", "unit": "g/L"},
    {"category": "79", "item_name": "微量白蛋白(脑脊液)","cv": "3.3%",  "tea": "±10%或±0.1g/L(取大者)", "unit": "g/L"},
    {"category": "80", "item_name": "葡萄糖(脑脊液)",    "cv": "3.3%",  "tea": "±10%或±0.1mmol/L(取大者)", "unit": "mmol/L"},
    {"category": "81", "item_name": "氯(脑脊液)",        "cv": "1.7%",  "tea": "±5%", "unit": "mmol/L"},
    {"category": "82", "item_name": "乳酸脱氢酶(脑脊液)","cv": "6.7%",  "tea": "±20%", "unit": "U/L"},
    {"category": "83", "item_name": "免疫球蛋白A(脑脊液)","cv": "8.3%", "tea": "±25%", "unit": "mg/L"},
    {"category": "84", "item_name": "免疫球蛋白G(脑脊液)","cv": "8.3%", "tea": "±25%", "unit": "mg/L"},
    {"category": "85", "item_name": "免疫球蛋白M(脑脊液)","cv": "8.3%", "tea": "±25%", "unit": "mg/L"},
    {"category": "86", "item_name": "乳酸(脑脊液)",      "cv": "6.7%",  "tea": "±20%或±0.1mmol/L(取大者)", "unit": "mmol/L"},
    # 激素
    {"category": "87", "item_name": "三碘甲状腺原氨酸(T3)",   "cv": "7.0%", "tea": "±25%", "unit": "nmol/L"},
    {"category": "88", "item_name": "游离三碘甲状腺原氨酸(FT3)", "cv": "7.0%", "tea": "±25%", "unit": "pmol/L"},
    {"category": "89", "item_name": "甲状腺素(T4)",        "cv": "7.0%", "tea": "±20%", "unit": "nmol/L"},
    {"category": "90", "item_name": "游离甲状腺素(FT4)",   "cv": "7.0%", "tea": "±25%", "unit": "pmol/L"},
    {"category": "91", "item_name": "促甲状腺素(TSH)",     "cv": "7.0%", "tea": "±25%", "unit": "mIU/L"},
    {"category": "92", "item_name": "皮质醇(Cor)",         "cv": "7.0%", "tea": "±25%", "unit": "nmol/L"},
    {"category": "92", "item_name": "游离皮质醇（尿液）",   "cv": "7.0%", "tea": "±25%", "unit": "nmol/L"},
    {"category": "93", "item_name": "卵泡刺激素(FSH)",     "cv": "7.0%", "tea": "±25%", "unit": "IU/L"},
    {"category": "94", "item_name": "黄体生成素(LH)",      "cv": "7.0%", "tea": "±25%", "unit": "IU/L"},
    {"category": "95", "item_name": "孕酮(P)",             "cv": "7.0%", "tea": "±25%", "unit": "nmol/L"},
    {"category": "96", "item_name": "催乳素(PRL)",         "cv": "7.0%", "tea": "±25%", "unit": "mIU/L"},
    {"category": "97", "item_name": "睾酮(T)",             "cv": "7.0%", "tea": "±25%", "unit": "nmol/L"},
    {"category": "98", "item_name": "雌二醇(E2)",          "cv": "8.0%", "tea": "±25%", "unit": "pmol/L"},
    {"category": "99", "item_name": "C-肽(C-P)",           "cv": "7.0%", "tea": "±25%", "unit": "nmol/L"},
    {"category": "100","item_name": "叶酸(Fol)",           "cv": "9.0%", "tea": "±30%", "unit": "nmol/L"},
    {"category": "101","item_name": "胰岛素(Ins)",         "cv": "8.0%", "tea": "±25%", "unit": "pmol/L"},
    {"category": "102","item_name": "维生素B12(VitB12)",   "cv": "8.0%", "tea": "±25%", "unit": "pmol/L"},
    {"category": "103","item_name": "25-羟维生素D(25-OH-VD)","cv": "8.3%", "tea": "±25%", "unit": "nmol/L"},
    {"category": "104","item_name": "甲状旁腺激素(PTH)",   "cv": "10.0%","tea": "±30%", "unit": "pmol/L"},
    # 肿瘤
    {"category": "105","item_name": "甲胎蛋白(AFP)",       "cv": "7.5%", "tea": "±25%", "unit": "ng/mL"},
    {"category": "106","item_name": "癌胚抗原(CEA)",       "cv": "7.5%", "tea": "±25%", "unit": "ng/mL"},
    {"category": "107","item_name": "人绒毛膜促性腺激素(HCG)","cv": "8.3%", "tea": "±25%", "unit": "IU/L"},
    {"category": "108","item_name": "β-人绒毛膜促性腺激素(β-HCG)","cv": "8.3%", "tea": "±25%", "unit": "IU/L"},
    {"category": "109","item_name": "总前列腺特异性抗原(TPSA)","cv": "7.5%", "tea": "±25%", "unit": "ng/mL"},
    {"category": "110","item_name": "游离前列腺特异性抗原(FPSA)","cv": "7.5%", "tea": "±25%", "unit": "ng/mL"},
    {"category": "111","item_name": "糖链抗原125(CA125)",  "cv": "7.5%", "tea": "±25%", "unit": "U/mL"},
    {"category": "112","item_name": "糖链抗原15-3(CA15-3)","cv": "7.5%", "tea": "±25%", "unit": "U/mL"},
    {"category": "113","item_name": "糖链抗原19-9(CA19-9)","cv": "7.5%", "tea": "±25%", "unit": "U/mL"},
    {"category": "114","item_name": "糖链抗原72-4(CA72-4)","cv": "7.5%", "tea": "±25%", "unit": "U/mL"},
    {"category": "115","item_name": "β2-微球蛋白(β2-MG)", "cv": "7.5%", "tea": "±25%", "unit": "μg/mL"},
    {"category": "116","item_name": "铁蛋白(Fer)",         "cv": "7.5%", "tea": "±25%", "unit": "ng/mL"},
    {"category": "117","item_name": "细胞角蛋白19片段(CYFRA21-1)","cv": "7.5%", "tea": "±25%", "unit": "ng/mL"},
    {"category": "118","item_name": "神经元特异性烯醇化酶(NSE)","cv": "7.5%", "tea": "±25%", "unit": "ng/mL"},
    {"category": "119","item_name": "鳞状上皮细胞癌(SCC)抗原","cv": "7.5%", "tea": "±25%", "unit": "ng/mL"},
    {"category": "120","item_name": "胃泌素释放肽前体(ProGRP)","cv": "8.3%", "tea": "±25%", "unit": "pg/mL"},
    {"category": "121","item_name": "胃蛋白酶原I(PGI)",   "cv": "10.0%","tea": "±30%", "unit": "ng/mL"},
    {"category": "122","item_name": "胃蛋白酶原II(PGII)",  "cv": "10.0%","tea": "±30%", "unit": "ng/mL"},
    # 免疫球蛋白/补体
    {"category": "123","item_name": "免疫球蛋白A(IgA)",   "cv": "6.0%", "tea": "±25%", "unit": "g/L"},
    {"category": "124","item_name": "免疫球蛋白G(IgG)",   "cv": "6.0%", "tea": "±25%", "unit": "g/L"},
    {"category": "125","item_name": "免疫球蛋白M(IgM)",   "cv": "7.5%", "tea": "±25%", "unit": "g/L"},
    {"category": "126","item_name": "免疫球蛋白E(IgE)",   "cv": "8.3%", "tea": "±25%", "unit": "KIU/L"},
    {"category": "127","item_name": "补体 C1q",            "cv": "10.0%","tea": "±30%", "unit": "mg/L"},
    {"category": "128","item_name": "补体 C3",             "cv": "6.0%", "tea": "±25%", "unit": "g/L"},
    {"category": "129","item_name": "补体 C4",             "cv": "7.5%", "tea": "±25%", "unit": "g/L"},
    {"category": "130","item_name": "C-反应蛋白(CRP)",     "cv": "7.5%", "tea": "±25%", "unit": "mg/L"},
    {"category": "131","item_name": "类风湿因子(RF)",      "cv": "7.5%", "tea": "±25%", "unit": "KU/L"},
    {"category": "132","item_name": "抗链球菌溶血素(ASO)","cv": "7.5%", "tea": "±25%", "unit": "KIU/L"},
    {"category": "133","item_name": "转铁蛋白(TRF)",       "cv": "8.3%", "tea": "±25%", "unit": "g/L"},
    {"category": "134","item_name": "前白蛋白(PA)",        "cv": "7.5%", "tea": "±25%", "unit": "mg/L"},
    # 感染
    {"category": "135","item_name": "乙肝病毒表面抗原(HBsAg)",  "cv": "", "tea": "与预期结果一致"},
    {"category": "136","item_name": "乙肝病毒表面抗体(HBsAb)",  "cv": "10%", "tea": "与预期结果一致"},
    {"category": "137","item_name": "乙肝病毒核心抗体(HBcAb)",  "cv": "10%", "tea": "与预期结果一致"},
    {"category": "138","item_name": "乙肝病毒e抗原(HBeAg)",     "cv": "10%", "tea": "与预期结果一致"},
    {"category": "139","item_name": "乙肝病毒e抗体(HBeAb)",     "cv": "10%", "tea": "与预期结果一致"},
    {"category": "140","item_name": "丙型肝炎抗体(抗-HCV)",    "cv": "10%", "tea": "与预期结果一致"},
    {"category": "141","item_name": "甲型肝炎病毒IgM抗体(抗-HAV IgM)","cv": "10%", "tea": "与预期结果一致"},
    {"category": "142","item_name": "乙型肝炎病毒核心IgM抗体(抗-HBc IgM)","cv": "10%", "tea": "与预期结果一致"},
    {"category": "143","item_name": "戊型肝炎病毒IgM抗体(抗-HEV IgM)","cv": "10%", "tea": "与预期结果一致"},
    {"category": "144","item_name": "人免疫缺陷病毒抗体(抗-HIV)","cv": "10%", "tea": "与预期结果一致"},
    {"category": "145","item_name": "梅毒螺旋体抗体(抗-TP)",   "cv": "10%", "tea": "与预期结果一致"},
    {"category": "146","item_name": "巨细胞病毒IgM抗体(CMV-IgM)","cv": "10%", "tea": "与预期结果一致"},
    {"category": "147","item_name": "巨细胞病毒IgG抗体(CMV-IgG)","cv": "10%", "tea": "与预期结果一致"},
    {"category": "148","item_name": "Ⅰ型单纯疱疹病毒IgM抗体(HSV-Ⅰ-IgM)","cv": "10%", "tea": "与预期结果一致"},
    {"category": "149","item_name": "Ⅰ型单纯疱疹病毒IgG抗体(HSV-Ⅰ-IgG)","cv": "10%", "tea": "与预期结果一致"},
    {"category": "150","item_name": "Ⅱ型单纯疱疹病毒IgM抗体(HSV-Ⅱ-IgM)","cv": "10%", "tea": "与预期结果一致"},
    {"category": "151","item_name": "Ⅱ型单纯疱疹病毒IgG抗体(HSV-Ⅱ-IgG)","cv": "10%", "tea": "与预期结果一致"},
    {"category": "152","item_name": "弓形虫IgM抗体(TOX-IgM)", "cv": "10%", "tea": "与预期结果一致"},
    {"category": "153","item_name": "弓形虫IgG抗体(TOX-IgG)", "cv": "10%", "tea": "与预期结果一致"},
    {"category": "154","item_name": "风疹病毒IgM抗体(RV-IgM)","cv": "10%", "tea": "与预期结果一致"},
    {"category": "155","item_name": "风疹病毒IgG抗体(RV-IgG)","cv": "10%", "tea": "与预期结果一致"},
    # 激素/特殊
    {"category": "156","item_name": "血清降钙素原(PCT)",  "cv": "10.0%", "tea": "±30%或±0.03μg/L(取大值)", "unit": "μg/L"},
    {"category": "157","item_name": "白细胞介素-6(IL-6)", "cv": "10.0%", "tea": "±30%", "unit": "pg/mL"},
    {"category": "158","item_name": "醛固酮(ALD)",       "cv": "8.3%",  "tea": "±25%", "unit": "pmol/L"},
    {"category": "159","item_name": "促肾上腺皮质激素(ACTH)","cv": "10.0%", "tea": "±30%", "unit": "pmol/L"},
    {"category": "160","item_name": "肾素(Renin)",       "cv": "8.3%",  "tea": "±25%", "unit": "µIU/mL 或 pg/mL"},
    {"category": "161","item_name": "血管紧张素Ⅱ(AngⅡ)","cv": "8.3%",  "tea": "±25%", "unit": "pg/mL"},
    {"category": "165","item_name": "抗缪勒管激素(AMH)", "cv": "8.3%",  "tea": "±25%", "unit": "ng/mL"},
    # 核酸（定性/定量）
    {"category": "167","item_name": "乙型肝炎病毒核酸(HBV DNA)定量检测","tea": "±3SD 或±0.4(阳性)", "unit": "IU/mL"},
    {"category": "169","item_name": "丙型肝炎病毒核酸(HCV RNA)定量检测","tea": "±3SD 或±0.4(阳性)", "unit": "IU/mL"},
]


# ---------------- 2026 NCCL EQA 计划（0805 版） ----------------
# 仅有「可接受范围」一列，存到 tea；cv/bias 留空。category 为计划号。
NCCL_ITEMS: list[dict[str, Any]] = [
    # NCCL-C-01 常规化学 A; NCCL-C-02 干化学（合并）
    {"category": "NCCL-C-01", "item_name": "钾",   "tea": "靶值 ±6%"},
    {"category": "NCCL-C-01", "item_name": "钠",   "tea": "靶值 ±4%"},
    {"category": "NCCL-C-01", "item_name": "氯",   "tea": "靶值 ±4%"},
    {"category": "NCCL-C-01", "item_name": "钙",   "tea": "靶值 ±5%"},
    {"category": "NCCL-C-01", "item_name": "磷",   "tea": "靶值 ±10%"},
    {"category": "NCCL-C-01", "item_name": "葡萄糖","tea": "靶值 ±7%"},
    {"category": "NCCL-C-01", "item_name": "尿素", "tea": "靶值 ±8%"},
    {"category": "NCCL-C-01", "item_name": "尿酸", "tea": "靶值 ±12%"},
    {"category": "NCCL-C-01", "item_name": "肌酐", "tea": "靶值 ±12%"},
    {"category": "NCCL-C-01", "item_name": "总蛋白","tea": "靶值 ±5%"},
    {"category": "NCCL-C-01", "item_name": "白蛋白","tea": "靶值 ±6%"},
    {"category": "NCCL-C-01", "item_name": "总胆固醇","tea": "靶值 ±9%"},
    {"category": "NCCL-C-01", "item_name": "甘油三酯","tea": "靶值 ±14%"},
    {"category": "NCCL-C-01", "item_name": "总胆红素","tea": "靶值 ±15%"},
    {"category": "NCCL-C-01", "item_name": "丙氨酸氨基转移酶","tea": "靶值 ±16%"},
    {"category": "NCCL-C-01", "item_name": "天门冬氨酸氨基转移酶","tea": "靶值 ±15%"},
    {"category": "NCCL-C-01", "item_name": "碱性磷酸酶","tea": "靶值 ±18%"},
    {"category": "NCCL-C-01", "item_name": "淀粉酶","tea": "靶值 ±15%"},
    {"category": "NCCL-C-01", "item_name": "肌酸激酶","tea": "靶值 ±15%"},
    {"category": "NCCL-C-01", "item_name": "乳酸脱氢酶","tea": "靶值 ±11%"},
    {"category": "NCCL-C-01", "item_name": "直接胆红素","tea": "靶值 ±20%"},
    {"category": "NCCL-C-01", "item_name": "结合胆红素","tea": "靶值±1μmol/L(≤5μmol/L) 或20%(>5μmol/L)"},
    {"category": "NCCL-C-01", "item_name": "铁","tea": "靶值 ±15%"},
    {"category": "NCCL-C-01", "item_name": "总铁结合力","tea": "靶值 ±20%"},
    {"category": "NCCL-C-01", "item_name": "镁","tea": "靶值 ±15%"},
    {"category": "NCCL-C-01", "item_name": "锂","tea": "靶值 ±0.3mmol/L 或 ±20%(取大值)"},
    {"category": "NCCL-C-01", "item_name": "铜","tea": "靶值 ±20%"},
    {"category": "NCCL-C-01", "item_name": "锌","tea": "靶值 ±20%"},
    {"category": "NCCL-C-01", "item_name": "γ-谷氨酰基转移酶","tea": "靶值 ±11%"},
    {"category": "NCCL-C-01", "item_name": "α-羟丁酸脱氢酶","tea": "靶值 ±30%"},
    {"category": "NCCL-C-01", "item_name": "胆碱酯酶","tea": "靶值 ±20%"},
    {"category": "NCCL-C-01", "item_name": "脂肪酶","tea": "靶值 ±20%"},
    {"category": "NCCL-C-01", "item_name": "肌酸激酶-MB(U/L)","tea": "靶值 ±25%"},
    {"category": "NCCL-C-01", "item_name": "糖化血清蛋白","tea": "靶值 ±20%"},
    # NCCL-C-03 心肌标志物
    {"category": "NCCL-C-03", "item_name": "肌酸激酶-MB(μg/L)","tea": "靶值 ±30%"},
    {"category": "NCCL-C-03", "item_name": "肌红蛋白","tea": "靶值 ±30%"},
    {"category": "NCCL-C-03", "item_name": "肌钙蛋白-I","tea": "靶值 ±30%"},
    {"category": "NCCL-C-03", "item_name": "肌钙蛋白-T","tea": "靶值 ±30%"},
    {"category": "NCCL-C-03", "item_name": "高敏 CRP","tea": "靶值 ±30%"},
    {"category": "NCCL-C-03", "item_name": "同型半胱氨酸","tea": "靶值 ±2.5μmol/L 或 ±20%(取大值)"},
    # NCCL-C-04 脂类 A
    {"category": "NCCL-C-04", "item_name": "胆固醇","tea": "靶值 ±9%"},
    {"category": "NCCL-C-04", "item_name": "甘油三酯","tea": "靶值 ±14%"},
    {"category": "NCCL-C-04", "item_name": "高密度脂蛋白胆固醇","tea": "靶值 ±30%"},
    {"category": "NCCL-C-04", "item_name": "低密度脂蛋白胆固醇","tea": "靶值 ±30%"},
    {"category": "NCCL-C-04", "item_name": "载脂蛋白 A Ⅰ","tea": "靶值 ±30%"},
    {"category": "NCCL-C-04", "item_name": "载脂蛋白 B","tea": "靶值 ±30%"},
    {"category": "NCCL-C-04", "item_name": "脂蛋白(a)","tea": "靶值 ±30%"},
    # NCCL-C-05 血气
    {"category": "NCCL-C-05", "item_name": "pH","tea": "靶值 ±0.04"},
    {"category": "NCCL-C-05", "item_name": "pCO2","tea": "靶值 ±5mmHg 或 ±8%(取大值)"},
    {"category": "NCCL-C-05", "item_name": "pO2","tea": "靶值 ±15mmHg 或 ±12.5%(取大值)"},
    {"category": "NCCL-C-05", "item_name": "Na+(血气)","tea": "靶值 ±4%"},
    {"category": "NCCL-C-05", "item_name": "K+(血气)","tea": "靶值 ±6%"},
    {"category": "NCCL-C-05", "item_name": "Ca2+(血气)","tea": "靶值 ±5% 或 ±0.25mmol/L(取大值)"},
    {"category": "NCCL-C-05", "item_name": "Cl-(血气)","tea": "靶值 ±4%"},
    # NCCL-C-06 特殊蛋白
    {"category": "NCCL-C-06", "item_name": "免疫球蛋白 G","tea": "靶值 ±20%"},
    {"category": "NCCL-C-06", "item_name": "免疫球蛋白 A","tea": "靶值 ±20%"},
    {"category": "NCCL-C-06", "item_name": "免疫球蛋白 E","tea": "靶值 ±25%"},
    {"category": "NCCL-C-06", "item_name": "免疫球蛋白 M","tea": "靶值 ±25%"},
    {"category": "NCCL-C-06", "item_name": "补体 C3","tea": "靶值 ±20%"},
    {"category": "NCCL-C-06", "item_name": "补体 C4","tea": "靶值 ±25%"},
    {"category": "NCCL-C-06", "item_name": "C-反应蛋白","tea": "靶值 ±25%"},
    {"category": "NCCL-C-06", "item_name": "类风湿因子","tea": "靶值 ±25%"},
    {"category": "NCCL-C-06", "item_name": "抗链球菌溶血素 O","tea": "靶值 ±25%"},
    {"category": "NCCL-C-06", "item_name": "转铁蛋白","tea": "靶值 ±25%"},
    {"category": "NCCL-C-06", "item_name": "前白蛋白","tea": "靶值 ±25%"},
    {"category": "NCCL-C-06", "item_name": "κ 轻链","tea": "靶值 ±25%"},
    {"category": "NCCL-C-06", "item_name": "λ 轻链","tea": "靶值 ±25%"},
    {"category": "NCCL-C-06", "item_name": "结合珠蛋白","tea": "靶值 ±25%"},
    {"category": "NCCL-C-06", "item_name": "免疫球蛋白 G4","tea": "靶值 ±25%"},
    # NCCL-C-07 内分泌
    {"category": "NCCL-C-07", "item_name": "游离 T3","tea": "靶值 ±20%"},
    {"category": "NCCL-C-07", "item_name": "总T3","tea": "靶值 ±20%"},
    {"category": "NCCL-C-07", "item_name": "游离 T4","tea": "靶值 ±20%"},
    {"category": "NCCL-C-07", "item_name": "总T4","tea": "靶值 ±20%"},
    {"category": "NCCL-C-07", "item_name": "TSH","tea": "靶值 ±20%"},
    {"category": "NCCL-C-07", "item_name": "皮质醇","tea": "靶值 ±20%"},
    # 游离皮质醇（尿液）卫健委 EQA 靶值同血清皮质醇
    {"category": "NCCL-C-07", "item_name": "游离皮质醇（尿液）","tea": "靶值 ±20%"},
    {"category": "NCCL-C-07", "item_name": "雌二醇","tea": "靶值 ±25%"},
    {"category": "NCCL-C-07", "item_name": "FSH","tea": "靶值 ±25%"},
    {"category": "NCCL-C-07", "item_name": "LH","tea": "靶值 ±25%"},
    {"category": "NCCL-C-07", "item_name": "孕酮","tea": "靶值 ±20%"},
    {"category": "NCCL-C-07", "item_name": "催乳素","tea": "靶值 ±25%"},
    {"category": "NCCL-C-07", "item_name": "睾酮","tea": "靶值 ±20%"},
    {"category": "NCCL-C-07", "item_name": "C-肽","tea": "靶值 ±25%"},
    {"category": "NCCL-C-07", "item_name": "叶酸","tea": "靶值 ±30%"},
    {"category": "NCCL-C-07", "item_name": "胰岛素","tea": "靶值 ±25%"},
    {"category": "NCCL-C-07", "item_name": "维生素 B12","tea": "靶值 ±25%"},
    {"category": "NCCL-C-07", "item_name": "25-OH-VD2","tea": "靶值 ±25%"},
    {"category": "NCCL-C-07", "item_name": "25-OH-VD3","tea": "靶值 ±25%"},
    {"category": "NCCL-C-07", "item_name": "总 25-OH-VD","tea": "靶值 ±25%"},
    {"category": "NCCL-C-07", "item_name": "甲状腺球蛋白(TG)","tea": "靶值 ±25%"},
    {"category": "NCCL-C-07", "item_name": "生长激素(GH)","tea": "靶值 ±25%"},
    {"category": "NCCL-C-07", "item_name": "甲状旁腺激素(PTH)","tea": "靶值 ±30%"},
    {"category": "NCCL-C-07", "item_name": "促肾上腺皮质激素(ACTH)","tea": "靶值 ±30%"},
    {"category": "NCCL-C-07", "item_name": "醛固酮(ALD)","tea": "靶值 ±25%"},
    {"category": "NCCL-C-07", "item_name": "性激素结合球蛋白(SHBG)","tea": "靶值 ±25%"},
    {"category": "NCCL-C-07", "item_name": "17-α-羟孕酮(17OHP)","tea": "靶值 ±25%"},
    {"category": "NCCL-C-07", "item_name": "硫酸脱氢表雄酮(DHEA-S)","tea": "靶值 ±25%"},
    # NCCL-C-08 肿瘤标志物 A
    {"category": "NCCL-C-08", "item_name": "CEA","tea": "靶值 ±25%"},
    {"category": "NCCL-C-08", "item_name": "AFP","tea": "靶值 ±25%"},
    {"category": "NCCL-C-08", "item_name": "HCG","tea": "靶值 ±25%"},
    {"category": "NCCL-C-08", "item_name": "PSA","tea": "靶值 ±25%"},
    {"category": "NCCL-C-08", "item_name": "CA199","tea": "靶值 ±25%"},
    {"category": "NCCL-C-08", "item_name": "CA125","tea": "靶值 ±25%"},
    {"category": "NCCL-C-08", "item_name": "CA153","tea": "靶值 ±25%"},
    {"category": "NCCL-C-08", "item_name": "β2 微球蛋白","tea": "靶值 ±25%"},
    {"category": "NCCL-C-08", "item_name": "铁蛋白","tea": "靶值 ±25%"},
    {"category": "NCCL-C-08", "item_name": "总 β-HCG","tea": "靶值 ±25%"},
    {"category": "NCCL-C-08", "item_name": "游离 PSA","tea": "靶值 ±25%"},
    # NCCL-C-12 心衰标志物
    {"category": "NCCL-C-12", "item_name": "BNP","tea": "靶值 ±30%"},
    {"category": "NCCL-C-12", "item_name": "NT-proBNP","tea": "靶值 ±30%"},
    # NCCL-C-13 尿液定量生化
    # 以下 NCCL-C-13 尿液行 tea 已按线上真实分项值校正（原种子文件统一值±20%等为漂移，DB 存真实值）
    {"category": "NCCL-C-13", "item_name": "钾(尿液)","tea": "靶值 ±6%"},
    {"category": "NCCL-C-13", "item_name": "钠(尿液)","tea": "靶值 ±4%"},
    {"category": "NCCL-C-13", "item_name": "氯(尿液)","tea": "靶值 ±4%"},
    {"category": "NCCL-C-13", "item_name": "钙(尿液)","tea": "靶值 ±5%"},
    {"category": "NCCL-C-13", "item_name": "镁(尿液)","tea": "靶值 ±15%"},
    {"category": "NCCL-C-13", "item_name": "磷(尿液)","tea": "靶值 ±10%"},
    {"category": "NCCL-C-13", "item_name": "葡萄糖(尿液)","tea": "靶值 ±7%"},
    {"category": "NCCL-C-13", "item_name": "尿素(尿液)","tea": "靶值 ±8%"},
    {"category": "NCCL-C-13", "item_name": "尿酸(尿液)","tea": "靶值 ±12%"},
    {"category": "NCCL-C-13", "item_name": "肌酐(尿液)","tea": "靶值 ±12%"},
    # 卫健委 EQA 登记名为「总蛋白」+标本类型(尿液)；对应项目库 TestItem「微量总蛋白（尿液）」，改名以精确命中
    {"category": "NCCL-C-13", "item_name": "微量总蛋白（尿液）","tea": "靶值 ±30%"},
    {"category": "NCCL-C-13", "item_name": "淀粉酶(尿液)","tea": "靶值 ±15%"},
    {"category": "NCCL-C-13", "item_name": "微量白蛋白(尿液)","tea": "靶值 ±30%"},
    # NCCL-C-14 半胱氨酸蛋白酶抑制剂 C
    {"category": "NCCL-C-14", "item_name": "半胱氨酸蛋白酶抑制剂 C","tea": "靶值 ±20%"},
    # NCCL-C-20 视黄醇结合蛋白
    {"category": "NCCL-C-20", "item_name": "视黄醇结合蛋白","tea": "靶值 ±25%"},
    # NCCL-C-21 尿液蛋白标志物
    {"category": "NCCL-C-21", "item_name": "尿免疫球蛋白 G(UIGG)","tea": "靶值 ±25%"},
    {"category": "NCCL-C-21", "item_name": "尿转铁蛋白(UTRF)","tea": "靶值 ±25%"},
    {"category": "NCCL-C-21", "item_name": "α1 微球蛋白(α1-MG)","tea": "靶值 ±25%"},
    {"category": "NCCL-C-21", "item_name": "β2 微球蛋白(尿液)","tea": "靶值 ±25%"},
    {"category": "NCCL-C-21", "item_name": "尿液视黄醇结合蛋白(RBP)","tea": "靶值 ±25%"},
    # NCCL-C-22 肿瘤标志物 B
    {"category": "NCCL-C-22", "item_name": "CA72-4","tea": "靶值 ±25%"},
    {"category": "NCCL-C-22", "item_name": "HE4","tea": "靶值 ±25%"},
    {"category": "NCCL-C-22", "item_name": "CYFRA21-1","tea": "靶值 ±25%"},
    {"category": "NCCL-C-22", "item_name": "NSE","tea": "靶值 ±25%"},
    {"category": "NCCL-C-22", "item_name": "SCCA","tea": "靶值 ±25%"},
    {"category": "NCCL-C-22", "item_name": "CA50","tea": "靶值 ±25%"},
    {"category": "NCCL-C-22", "item_name": "CA242","tea": "靶值 ±25%"},
    # NCCL-C-23 胃蛋白酶原
    {"category": "NCCL-C-23", "item_name": "胃蛋白酶原 I（PGI）","tea": "靶值 ±25%"},
    {"category": "NCCL-C-23", "item_name": "胃蛋白酶原 II（PGII）","tea": "靶值 ±25%"},
    {"category": "NCCL-C-23", "item_name": "PGI/PGII 比率（PGR）","tea": "靶值 ±25%"},
    {"category": "NCCL-C-23", "item_name": "胃泌素 17（G-17）","tea": "靶值 ±25%"},
    # NCCL-C-24 抗缪勒管激素
    {"category": "NCCL-C-24", "item_name": "抗缪勒管激素（AMH）","tea": "靶值 ±25%"},
    # NCCL-C-25 血清淀粉样蛋白 A
    {"category": "NCCL-C-25", "item_name": "血清淀粉样蛋白 A（SAA）","tea": "靶值 ±25%"},
    # NCCL-C-28 脑脊液
    {"category": "NCCL-C-28", "item_name": "白蛋白(脑脊液)","tea": "靶值 ±10% 或 ±0.04g/L(取大值)"},
    # 卫健委 EQA 登记名为「总蛋白」+标本类型(脑脊液)；对应项目库 TestItem「微量总蛋白（脑脊液）」，改名以精确命中
    {"category": "NCCL-C-28", "item_name": "微量总蛋白（脑脊液）","tea": "靶值 ±10% 或 ±0.04g/L(取大值)"},
    # 卫健委 EQA 登记名为「白蛋白」+标本类型(脑脊液)；对应项目库 TestItem「微量白蛋白（脑脊液）」
    {"category": "NCCL-C-28", "item_name": "微量白蛋白（脑脊液）","tea": "靶值 ±10% 或 ±0.04g/L(取大值)"},
    # 以下行 tea 已按线上真实分项值校正（原统一值/孤儿命名为漂移）
    {"category": "NCCL-C-28", "item_name": "氯化物(脑脊液)","tea": "靶值 ±4%"},
    {"category": "NCCL-C-28", "item_name": "葡萄糖(脑脊液)","tea": "靶值 ±7%"},
    {"category": "NCCL-C-28", "item_name": "乳酸脱氢酶(脑脊液)","tea": "靶值 ±11%"},
    # NCCL-C-29 全血五元素
    {"category": "NCCL-C-29", "item_name": "铜(全血)","tea": "靶值 ±25%"},
    {"category": "NCCL-C-29", "item_name": "锌(全血)","tea": "靶值 ±25%"},
    {"category": "NCCL-C-29", "item_name": "钙(全血)","tea": "靶值 ±25%"},
    {"category": "NCCL-C-29", "item_name": "镁(全血)","tea": "靶值 ±25%"},
    {"category": "NCCL-C-29", "item_name": "铁(全血)","tea": "靶值 ±25%"},
    # NCCL-C-30 血清蛋白电泳
    {"category": "NCCL-C-30", "item_name": "清蛋白(电泳)","tea": "靶值 ±20%"},
    {"category": "NCCL-C-30", "item_name": "α1 球蛋白","tea": "靶值 ±30%"},
    {"category": "NCCL-C-30", "item_name": "α2 球蛋白","tea": "靶值 ±30%"},
    {"category": "NCCL-C-30", "item_name": "β 球蛋白","tea": "靶值 ±30%"},
    {"category": "NCCL-C-30", "item_name": "β1 球蛋白","tea": "靶值 ±25%"},
    # NCCL-C-11 HbA1c
    {"category": "NCCL-C-11", "item_name": "糖化血红蛋白(HbA1c)","tea": "靶值 ±6%(>6.7%) 或靶值 ±0.4%(≤6.7%)"},
    # NCCL-C-09 / C-10 治疗药物
    {"category": "NCCL-C-09", "item_name": "环孢霉素","tea": "靶值 ±20%"},
    {"category": "NCCL-C-09", "item_name": "他克莫司","tea": "靶值 ±20%"},
    {"category": "NCCL-C-09", "item_name": "西罗莫司","tea": "靶值 ±20%"},
    {"category": "NCCL-C-10", "item_name": "卡马西平","tea": "靶值 ±20%"},
    {"category": "NCCL-C-10", "item_name": "地高辛","tea": "靶值 ±20% 或 ±0.2μg/L(取大值)"},
    {"category": "NCCL-C-10", "item_name": "苯妥英","tea": "靶值 ±20%"},
    {"category": "NCCL-C-10", "item_name": "茶碱","tea": "靶值 ±20%"},
    {"category": "NCCL-C-10", "item_name": "丙戊酸","tea": "靶值 ±20%"},
    {"category": "NCCL-C-10", "item_name": "拉莫三嗪","tea": "靶值 ±20%"},
    {"category": "NCCL-C-10", "item_name": "左乙拉西坦","tea": "靶值 ±20%"},
    {"category": "NCCL-C-10", "item_name": "托吡酯","tea": "靶值 ±20%"},
    {"category": "NCCL-C-10", "item_name": "10-OH-卡马西平","tea": "靶值 ±20%"},
    # NCCL-C-26 血铅
    {"category": "NCCL-C-26", "item_name": "血铅","tea": "靶值 ±20μg/L 或 ±10%(取大值)"},
    # NCCL-C-27 便携式血糖
    {"category": "NCCL-C-27", "item_name": "葡萄糖(便携式血糖仪)","tea": "靶值 ±20% 或 ±1mmol/L(取大值)"},
    # —— 以下由用户核对《2026年全国临床检验室间质量评价计划》后补充（2026-07-19）——
    {"item_name": "抗甲状腺过氧化物酶抗体", "tea": "靶值 ±30%", "remark": "卫健委EQA计划靶值(用户核对补充)"},
    {"item_name": "抗甲状腺球蛋白抗体", "tea": "靶值 ±30%", "remark": "卫健委EQA计划靶值(用户核对补充)"},
    {"item_name": "游离三碘甲状腺原氨酸", "tea": "靶值 ±20%", "remark": "卫健委EQA计划靶值(用户核对补充)"},
    {"item_name": "三碘甲状腺原氨酸", "tea": "靶值 ±20%", "remark": "卫健委EQA计划靶值(用户核对补充)"},
    {"item_name": "游离甲状腺素", "tea": "靶值 ±20%", "remark": "卫健委EQA计划靶值(用户核对补充)"},
    {"item_name": "甲状腺素", "tea": "靶值 ±20%", "remark": "卫健委EQA计划靶值(用户核对补充)"},
    {"item_name": "促甲状腺激素", "tea": "靶值 ±20%", "remark": "卫健委EQA计划靶值(用户核对补充)"},
    {"item_name": "促甲状腺激素受体抗体", "tea": "靶值 ±30%", "remark": "卫健委EQA计划靶值(用户核对补充)"},
    {"item_name": "甲胎蛋白", "tea": "靶值 ±25% 或 ±5μg/L（取大值）", "remark": "卫健委EQA计划靶值(用户核对补充)"},
    {"item_name": "癌胚抗原", "tea": "靶值 ±25%", "remark": "卫健委EQA计划靶值(用户核对补充)"},
    {"item_name": "β人绒毛膜促性腺激素", "tea": "靶值 ±25%", "remark": "卫健委EQA计划靶值(用户核对补充)"},
    {"item_name": "总前列腺特异性抗原", "tea": "靶值 ±25%", "remark": "卫健委EQA计划靶值(用户核对补充)"},
    {"item_name": "游离前列腺特异性抗原", "tea": "靶值 ±25%", "remark": "卫健委EQA计划靶值(用户核对补充)"},
    {"item_name": "白介素-6", "tea": "靶值 ±30%", "remark": "卫健委EQA计划靶值(用户核对补充)"},
    {"item_name": "维生素D", "tea": "靶值 ±25%", "remark": "卫健委EQA计划靶值(用户核对补充)"},
    {"item_name": "骨钙素", "tea": "靶值 ±30%", "remark": "卫健委EQA计划靶值(用户核对补充)"},
    {"item_name": "降钙素", "tea": "靶值 ±30%", "remark": "卫健委EQA计划靶值(用户核对补充)"},
    {"item_name": "血清降钙素原(PCT)", "tea": "靶值 ±30%或±0.03μg/L（取大值）", "remark": "卫健委EQA计划靶值(用户核对补充)"},
    {"item_name": "总Ⅰ型胶原氨基端延长肽", "tea": "靶值 ±30%", "remark": "卫健委EQA计划靶值(用户核对补充)"},
    {"item_name": "β-胶原特殊序列", "tea": "靶值 ±30%", "remark": "卫健委EQA计划靶值(用户核对补充)"},
    {"item_name": "非结合型雌三醇", "tea": "靶值 ±30%", "remark": "卫健委EQA计划靶值(用户核对补充)"},
    {"item_name": "肾素", "tea": "靶值 ±30%", "remark": "卫健委EQA计划靶值(用户核对补充)"},
    {"item_name": "凝血酶原时间", "tea": "PT 靶值 ±15%；INR 靶值 ±20%", "remark": "卫健委EQA计划靶值(用户核对补充)"},
    {"item_name": "活化部分凝血活酶时间", "tea": "靶值 ±15%", "remark": "卫健委EQA计划靶值(用户核对补充)"},
    {"item_name": "纤维蛋白原", "tea": "靶值 ±20%", "remark": "卫健委EQA计划靶值(用户核对补充)"},
    {"item_name": "凝血酶时间", "tea": "靶值 ±20%", "remark": "卫健委EQA计划靶值(用户核对补充)"},
    {"item_name": "血浆D-二聚体", "tea": "靶值 ±50%", "remark": "卫健委EQA计划靶值(用户核对补充)"},
    {"item_name": "纤维蛋白（原）降解产物", "tea": "靶值 ±35%", "remark": "卫健委EQA计划靶值(用户核对补充)"},
    {"item_name": "抗凝血酶III", "tea": "靶值 ±20%（>40% 时）或 ±8（≤40% 时）", "remark": "卫健委EQA计划靶值(用户核对补充)"},
    {"item_name": "血浆蛋白C活性", "tea": "靶值 ±15%（>60% 时）或 ±9（≤60% 时）", "remark": "卫健委EQA计划靶值(用户核对补充)"},
    {"item_name": "血浆蛋白S活性", "tea": "靶值 ±25%（>40% 时）或 ±10（≤40% 时）", "remark": "卫健委EQA计划靶值(用户核对补充)"},
    # —— 以下由用户提供的《2026年全国临床检验室间质量评价计划》PDF 88-116 页实数据补充（2026-07-19 第二轮）——
    {"item_name": "β-羟丁酸", "tea": "靶值 ±30%", "remark": "PDF NCCL-C-33 常规化学B"},
    {"item_name": "κ轻链（血清）", "tea": "靶值 ±25%", "remark": "PDF NCCL-C-06 特殊蛋白"},
    {"item_name": "λ轻链（血清）", "tea": "靶值 ±25%", "remark": "PDF NCCL-C-06 特殊蛋白"},
    {"item_name": "三型前胶原N末端肽", "tea": "靶值 ±20%", "remark": "PDF NCCL-C-40 肝纤维化(PⅢNP)"},
    {"item_name": "四型胶原", "tea": "靶值 ±20%", "remark": "PDF NCCL-C-40 肝纤维化(Col Ⅳ)"},
    {"item_name": "尿IgG", "tea": "靶值 ±25%", "remark": "PDF NCCL-C-21 尿免疫球蛋白G(UIGG)"},
    {"item_name": "尿α1微球蛋白", "tea": "靶值 ±25%", "remark": "PDF NCCL-C-21 α1-MG"},
    {"item_name": "尿κ轻链", "tea": "靶值 ±25%", "remark": "PDF NCCL-C-06 κ轻链(血清值,尿轻链沿用,待用户确认)"},
    {"item_name": "尿λ轻链", "tea": "靶值 ±25%", "remark": "PDF NCCL-C-06 λ轻链(血清值,尿轻链沿用,待用户确认)"},
    {"item_name": "层粘连蛋白", "tea": "靶值 ±20%", "remark": "PDF NCCL-C-40 肝纤维化(LN)"},
    {"item_name": "总胆汁酸", "tea": "靶值 ±25%", "remark": "PDF NCCL-C-33 常规化学B"},
    {"item_name": "胱抑素C", "tea": "靶值 ±20%", "remark": "PDF NCCL-C-14 半胱氨酸蛋白酶抑制剂C"},
    {"item_name": "腺苷脱氨酶（胸腹水）", "tea": "靶值 ±25%", "remark": "PDF NCCL-C-33 腺苷脱氨酶"},
    {"item_name": "腺苷脱氨酶（脑脊液）", "tea": "靶值 ±25%", "remark": "PDF NCCL-C-33 腺苷脱氨酶"},
    {"item_name": "血气和酸碱分析-Ca", "tea": "靶值 ±5% 或 ±0.25mmol/L（取大值）", "remark": "PDF NCCL-C-05 Ca²⁺"},
    {"item_name": "血气和酸碱分析-Cl", "tea": "靶值 ±4%", "remark": "PDF NCCL-C-05 Cl⁻"},
    {"item_name": "血气和酸碱分析-K", "tea": "靶值 ±6%", "remark": "PDF NCCL-C-05 K⁺"},
    {"item_name": "血气和酸碱分析-Na", "tea": "靶值 ±4%", "remark": "PDF NCCL-C-05 Na⁺"},
    {"item_name": "血气和酸碱分析-PCO2", "tea": "靶值 ±5mmHg 或 ±8%（取大值）", "remark": "PDF NCCL-C-05 pCO2"},
    {"item_name": "血气和酸碱分析-PO2", "tea": "靶值 ±15mmHg 或 ±12.5%（取大值）", "remark": "PDF NCCL-C-05 pO2"},
    {"item_name": "血清淀粉样蛋白A", "tea": "靶值 ±25%", "remark": "PDF NCCL-C-25 SAA"},
    {"item_name": "血清蛋白电泳-M蛋白", "tea": "靶值 ±25%", "remark": "PDF NCCL-C-30"},
    {"item_name": "血清蛋白电泳-α1球蛋白", "tea": "靶值 ±30%", "remark": "PDF NCCL-C-30"},
    {"item_name": "血清蛋白电泳-α2球蛋白", "tea": "靶值 ±30%", "remark": "PDF NCCL-C-30"},
    {"item_name": "血清蛋白电泳-β1球蛋白", "tea": "靶值 ±25%", "remark": "PDF NCCL-C-30"},
    {"item_name": "血清蛋白电泳-β2球蛋白", "tea": "靶值 ±30%", "remark": "PDF NCCL-C-30"},
    {"item_name": "血清蛋白电泳-γ球蛋白", "tea": "靶值 ±25%", "remark": "PDF NCCL-C-30"},
    {"item_name": "触珠蛋白", "tea": "靶值 ±25%", "remark": "PDF NCCL-C-06 结合珠蛋白"},
    {"item_name": "超敏C反应蛋白", "tea": "靶值 ±30%", "remark": "PDF NCCL-C-03 心肌标志物 高敏CRP"},
    {"item_name": "载脂蛋白A1", "tea": "靶值 ±30%", "remark": "PDF NCCL-C-04 脂类A 载脂蛋白AⅠ"},
    {"item_name": "透明质酸", "tea": "靶值 ±20%", "remark": "PDF NCCL-C-40 肝纤维化 HA"},
]


def all_seed() -> list[dict[str, Any]]:
    """返回全部 (source, item_name, category, cv, bias, tea, unit) 待灌库字典。"""
    out: list[dict[str, Any]] = []
    for it in WST403_ITEMS:
        out.append({
            "source": "wst403-2024", "category": it.get("category", ""),
            "item_code": it.get("item_code", ""), "item_name": it["item_name"],
            "cv": it.get("cv", ""), "bias": it.get("bias", ""), "tea": it.get("tea", ""),
            "unit": it.get("unit", ""),
        })
    for it in BJHR_ITEMS:
        out.append({
            "source": "bj-hr-2025", "category": it.get("category", ""),
            "item_code": it.get("item_code", ""), "item_name": it["item_name"],
            "cv": it.get("cv", ""), "bias": it.get("bias", ""), "tea": it.get("tea", ""),
            "unit": it.get("unit", ""),
        })
    for it in NCCL_ITEMS:
        out.append({
            "source": "nccl-2026", "category": it.get("category", ""),
            "item_code": it.get("item_code", ""), "item_name": it["item_name"],
            "cv": it.get("cv", ""), "bias": it.get("bias", ""), "tea": it.get("tea", ""),
            "unit": it.get("unit", ""),
        })
    return out
