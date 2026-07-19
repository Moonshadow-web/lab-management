"""项目查询库(test_items)与室间质评库(eqa_plans)的关联查询 + 质量要求标准整合。

该模块只提供只读接口，返回：
  1) 项目与 EQA 计划的匹配关系（按项目名称/别名归一化匹配）
  2) 三个质量标准源（WS/T 403-2024 / 北京市互认 / 卫健委 NCCL）的允许误差指标
形成「一行看全景」的项目质控总览。
"""
import re
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.security import get_current_user
from ...models.eqa import EqaPlan
from ...models.quality_requirement import QualityRequirement
from ...models.test_item import TestItem

router = APIRouter(prefix="/eqa-associations", tags=["eqa-associations"])


# ---------------------------------------------------------------------------
# 同义映射：EQA 细项常见缩写/异名 → test_items 规范名（用于匹配补全）
# ---------------------------------------------------------------------------
_CURATED_EQA_ALIASES = {
    "tpab": "梅毒特异性抗体",
    "tppa": "梅毒特异性抗体",
    "trust": "梅毒甲苯胺红不加热血清试验",
    "inr": "凝血酶原时间",
    "aptt": "活化部分凝血活酶时间",
    "pt": "凝血酶原时间",
    "fib": "纤维蛋白原",
    "tt": "凝血酶时间",
    "d-二聚体": "血浆d-二聚体",
    "fdp": "纤维蛋白（原）降解产物",
    "atiii": "抗凝血酶iii",
    "ck-mb": "肌酸激酶同工酶",
    "ckmb": "肌酸激酶同工酶",
    "肌酸激酶-mb": "肌酸激酶同工酶",
    # Tg 消歧：质评 token「Tg」应=甲状腺球蛋白，但甘油三酯别名「TG」归一化后同为 tg 且 id 更小会误占
    "tg": "甲状腺球蛋白",
    # IgG/IgM 消歧：裸 token「IgG/IgM」应=免疫球蛋白G/M，但抗-X-IgG/IgM 别名含 igg/igm 词且 id 更小会误占
    "igg": "免疫球蛋白G",
    "igm": "免疫球蛋白M",
    "ctni": "肌钙蛋白i",
    "肌钙蛋白i": "肌钙蛋白i",
    "ctnt": "肌钙蛋白t",
    "nt-probnp": "n末端b型钠尿肽前体",
    "probnp": "n末端b型钠尿肽前体",
    "bnp": "b型钠尿肽",
    "pct": "降钙素原",
    "il-6": "白介素-6",
    "cys-c": "胱抑素c",
    "cysc": "胱抑素c",
    "saa": "血清淀粉样蛋白a",
    "hba1c": "糖化血红蛋白",
    "ga": "糖化白蛋白",
    # 电泳同义：EQA 细项用「清蛋白」，项目库拆分后用「白蛋白」
    "清蛋白": "白蛋白",
    "血清蛋白电泳-清蛋白": "血清蛋白电泳-白蛋白",
}


# ---------------------------------------------------------------------------
# 手动关联修正：自动匹配漏掉的项，按 test_item id 指定其质评归属
# 适用场景：①标本变体（脑脊液/尿液版被血清版 exact 先占）；②略称/异名（TP1NP/HAV-IgM 等）；
#          ③罗马数字写法差异（Ⅱ vs II）；④跨 program 归属（如 蛋白C 在「抗凝蛋白」）。
# 结构：test_item id → [(机构, 展示用EQA细项标签), ...]。若项目库重导致 id 变化需同步更新。
# ---------------------------------------------------------------------------
_MANUAL_ASSOCIATIONS = {
    77:  [("卫健委", "TP1NP（骨代谢标志物）")],                       # 总Ⅰ型胶原氨基端延长肽
    193: [("卫健委", "皮质醇（内分泌）"), ("北京市", "皮质醇（内分泌）")],  # 游离皮质醇（尿液）同皮质醇
    175: [("北京市", "HAV-IgM（感染性疾病血清学标志物系列B）")],       # 甲型肝炎病毒IgM抗体
    60:  [("卫健委", "Tg（内分泌）")],                                # 甲状腺球蛋白
    40:  [("卫健委", "肌酸激酶-MB（心肌标志物）")],                    # 肌酸激酶同工酶 CKMB
    188: [("卫健委", "血管紧张素II（醛固酮和肾素）")],                 # 血管紧张素Ⅱ
    132: [("卫健委", "蛋白C（抗凝蛋白）")],                           # 血浆蛋白C活性
    205: [("卫健委", "乳酸脱氢酶（脑脊液生化）")],                     # 乳酸脱氢酶（脑脊液）
    111: [("卫健委", "IgG（特殊蛋白）")],                             # 免疫球蛋白G
    112: [("卫健委", "IgM（特殊蛋白）")],                             # 免疫球蛋白M
    143: [("卫健委", "尿素（尿液定量生化）")],                         # 尿素（尿液）
    # —— 尿液定量生化（卫健委）：EQA 细项为尿液专用，但被同名血清版 exact 先占，需按 id 显式补标 ——
    139: [("卫健委", "钠（尿液定量生化）")],                            # 钠（尿液）
    140: [("卫健委", "钾（尿液定量生化）")],                            # 钾（尿液）
    141: [("卫健委", "氯（尿液定量生化）")],                            # 氯（尿液）
    142: [("卫健委", "葡萄糖（尿液定量生化）")],                        # 葡萄糖（尿液）
    144: [("卫健委", "肌酐（尿液定量生化）")],                          # 肌酐（尿液）
    145: [("卫健委", "尿酸（尿液定量生化）")],                          # 尿酸（尿液）
    146: [("卫健委", "钙（尿液定量生化）")],                            # 总钙（尿液）
    147: [("卫健委", "镁（尿液定量生化）")],                            # 镁（尿液）
    148: [("卫健委", "磷（尿液定量生化）")],                            # 磷（尿液）
    149: [("卫健委", "淀粉酶（尿液定量生化）")],                        # 淀粉酶（尿液）
    150: [("卫健委", "总蛋白（尿液定量生化）")],                        # 微量总蛋白（尿液）
    # —— 脑脊液生化（卫健委）：EQA 细项为脑脊液专用，被同名血清版 exact 先占，按 id 显式补标 ——
    151: [("卫健委", "微量总蛋白（脑脊液生化）")],                      # 微量总蛋白（脑脊液）
    152: [("卫健委", "氯（脑脊液生化）")],                              # 氯（脑脊液）
    153: [("卫健委", "葡萄糖（脑脊液生化）")],                          # 葡萄糖（脑脊液）
    210: [("卫健委", "微量白蛋白（脑脊液生化）")],                      # 微量白蛋白（脑脊液）
    # —— 腺苷脱氨酶：EQA 计划(常规化学B,卫健委)仅列「腺苷脱氨酶」血清版，
    #    但 test_items 只有 156(胸腹水)/206(脑脊液) 两个标本变体；156 已被子串匹配先占，
    #    206 因 base 不同未被家族传播带出，需按 id 显式补标有质评 ——
    206: [("卫健委", "腺苷脱氨酶（常规化学B）")],                        # 腺苷脱氨酶（脑脊液）↔血清腺苷脱氨酶
    # —— 胸腹水：用户要求忽略样本类型，直接对应到血清版（常规化学A，卫健委+北京市）—— 156 腺苷脱氨酶/174 癌胚抗原 已自动命中，不重复 ——
    154: [("卫健委", "总蛋白（常规化学A）"), ("北京市", "总蛋白（常规化学A）")],  # 总蛋白（胸腹水）↔血清总蛋白
    155: [("卫健委", "白蛋白（常规化学A）"), ("北京市", "白蛋白（常规化学A）")],  # 白蛋白（胸腹水）↔血清白蛋白
    157: [("卫健委", "乳酸脱氢酶（常规化学A）"), ("北京市", "乳酸脱氢酶（常规化学A）")],  # 乳酸脱氢酶（胸腹水）↔血清乳酸脱氢酶
    158: [("卫健委", "葡萄糖（常规化学A）"), ("北京市", "血糖（常规化学A）")],  # 葡萄糖（胸腹水）↔血清葡萄糖
}


# ---------------------------------------------------------------------------
# 质量标准源常量
# ---------------------------------------------------------------------------
_QR_SOURCES = ["wst403-2024", "bj-hr-2025", "nccl-2026"]

# 同义词：项目库名称 → 标准源可能用名（与 quality_requirements matrix 接口一致）
_QR_SYNONYMS = {
    "二氧化碳": ["碳酸氢根", "HCO3", "Bicarbonate", "总二氧化碳", "二氧化碳结合力", "CO2"],
}


# ---------------------------------------------------------------------------
# 响应模型
# ---------------------------------------------------------------------------
class QualityReqDetail(BaseModel):
    """单个质量标准源的允许误差指标。"""
    cv: Optional[str] = None      # 允许不精密度
    bias: Optional[str] = None    # 允许偏倚
    tea: Optional[str] = None     # 允许总误差 / 可接受范围 / EQA评价标准
    unit: Optional[str] = None    # 单位（北京互认独有）
    item_name: Optional[str] = None  # 标准源中的原始项目名

    class Config:
        from_attributes = True


def _qr_to_detail(qr: Optional[QualityRequirement]) -> Optional[QualityReqDetail]:
    if not qr:
        return None
    return QualityReqDetail(
        cv=qr.cv or None,
        bias=qr.bias or None,
        tea=qr.tea or None,
        unit=qr.unit or None,
        item_name=qr.item_name or None,
    )


class EqaAssociationItem(BaseModel):
    id: int
    name: str
    category: str
    specimen: str
    unit: str
    instrument: str
    brand: str
    has_eqa: bool
    has_wjw: bool
    has_bj: bool
    wjw_tokens: list[str]
    bj_tokens: list[str]
    match_score: str  # 'exact' / 'alias' / 'substring' / 'curated'
    # ── 质量要求标准整合 ──
    wst403: Optional[QualityReqDetail] = None   # 行标 WS/T 403—2024
    bj_hr: Optional[QualityReqDetail] = None     # 北京市互认 2025
    nccl: Optional[QualityReqDetail] = None      # 卫健委 NCCL EQA 2026

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# 归一化与拆分（与 eqa.py 保持一致风格）
# ---------------------------------------------------------------------------
def _norm(s: str) -> str:
    s = (s or "").strip().replace("（", "(").replace("）", ")").replace("　", " ").replace(" ", "")
    return s.lower()


_SPEC_RE = re.compile(r"[（(](尿液|脑脊液|胸腹水|胸水|腹水|血浆|血清)[)）]")


def _strip_specimen(s: str) -> str:
    return _SPEC_RE.sub("", s or "").strip()


def _split_eqa_items(raw: str) -> list[str]:
    raw = re.sub(r"^(具体项目|项目|检测项目)[：:]\s*", "", raw or "")
    return [p.strip() for p in re.split(r"[、,，/]", raw) if p.strip()]


# ---------------------------------------------------------------------------
# 质量要求匹配辅助（与 matrix_view 逻辑一致）
# ---------------------------------------------------------------------------
def _norm_qr(s: str) -> str:
    """归一化：去括号/空格/连字符，用于模糊匹配。"""
    return re.sub(r"[\s\-（）().]", "", s or "").lower()


def _find_qr_for_item(item_name: str, qr_map: dict) -> Optional[QualityRequirement]:
    """从某标准源的 item_name→QR 字典中查找匹配项。"""
    # 精确
    hit = qr_map.get(item_name)
    if hit:
        return hit
    # 归一化精确
    n = _norm_qr(item_name)
    for k, v in qr_map.items():
        if _norm_qr(k) == n:
            return v
    # 包含匹配（双向）
    for k, v in qr_map.items():
        if item_name in k or k in item_name:
            return v
    # 同义词
    syns = _QR_SYNONYMS.get(item_name, [])
    for s in syns:
        hit = qr_map.get(s)
        if hit:
            return hit
        for k, v in qr_map.items():
            if s in k or k in s:
                return v
    return None


def _build_qr_maps(db: Session) -> dict[str, dict]:
    """构建三个标准源的 {item_name: QualityRequirement} 快速索引。"""
    maps = {}
    for src in _QR_SOURCES:
        rows = db.query(QualityRequirement).filter(QualityRequirement.source == src).all()
        maps[src] = {r.item_name: r for r in rows}
    return maps


def _build_test_item_index(db: Session):
    """构建 test_items 匹配索引：每项包含 id/name/keys/规范化名。"""
    rows = db.query(TestItem.id, TestItem.name, TestItem.aliases, TestItem.category,
                    TestItem.specimen, TestItem.unit, TestItem.instrument, TestItem.brand).all()
    index = []
    for tid, name, aliases, category, specimen, unit, instrument, brand in rows:
        keys = {_norm(name)}
        # name 本身按分隔符拆分（处理复合名如 血清蛋白电泳-白蛋白/...）
        for part in re.split(r"[、,，/]", name):
            p = part.strip()
            if p:
                keys.add(_norm(p))
        # aliases 按逗号拆分；保留整段（归一化后去空格），同时取空格分隔的词
        for seg in (aliases or "").replace("，", ",").split(","):
            seg = seg.strip()
            if seg:
                keys.add(_norm(seg))
                for w in seg.split():
                    w = w.strip()
                    if len(_norm(w)) >= 2:
                        keys.add(_norm(w))
        index.append({
            "id": tid,
            "name": name,
            "category": category or "",
            "specimen": specimen or "",
            "unit": unit or "",
            "instrument": instrument or "",
            "brand": brand or "",
            "keys": keys,
            "norm_name": _norm(name),
            # 拆分项「血清蛋白电泳-白蛋白」的 base = 「血清蛋白电泳」，用于同族传播
            "base": _norm(name.split("-")[0].strip()) if "-" in name else _norm(name),
        })
    return index


def _match_eqa_token(token: str, index: list) -> tuple[Optional[dict], str]:
    """把单个 EQA 细项 token 匹配到 test_items 索引中的某一项。"""
    nn = _norm(token)
    nn2 = _norm(_strip_specimen(token))
    forms = [nn] + ([nn2] if nn2 != nn else [])

    # 1. 精确匹配（含 curated 别名）
    for form in forms:
        curated = _CURATED_EQA_ALIASES.get(form)
        if curated:
            form = _norm(curated)
        for it in index:
            if form in it["keys"]:
                return it, "exact"

    # 2. 子串匹配（长度>=2）
    for form in forms:
        if len(form) < 2:
            continue
        for it in index:
            for k in it["keys"]:
                if len(k) >= 2 and (k in form or form in k):
                    return it, "substring"
    return None, ""


# ---------------------------------------------------------------------------
# 核心服务：计算关联矩阵
# ---------------------------------------------------------------------------
def _apply_org(assoc_map, families, tid, org_name, token, score):
    """把一个 EQA 细项对某个 test_item 的匹配，写入其机构标志；
    若为精确/同义匹配（exact/curated），则同族（按 base 前缀）拆分项一并标记。"""
    rec = assoc_map[tid]
    is_wjw = org_name == "卫健委"
    is_bj = org_name == "北京市"
    if is_wjw:
        if token not in rec["wjw_tokens"]:
            rec["wjw_tokens"].append(token)
        rec["has_wjw"] = True
        rec["match_score"] = score or rec["match_score"]
    elif is_bj:
        if token not in rec["bj_tokens"]:
            rec["bj_tokens"].append(token)
        rec["has_bj"] = True
        rec["match_score"] = score or rec["match_score"]
    else:
        return
    # 同族传播：精确/同义匹配时，拆分出的子项（如 血清蛋白电泳-白蛋白/α1/...）共享父项 EQA
    if score in ("exact", "curated"):
        for fid in families.get(rec["base"], []):
            if fid == tid:
                continue
            frec = assoc_map[fid]
            if is_wjw:
                frec["has_wjw"] = True
            if is_bj:
                frec["has_bj"] = True
            if frec["match_score"] in ("", "none"):
                frec["match_score"] = "family"


def _compute_associations(db: Session, category: Optional[str] = None,
                          has_eqa: Optional[str] = None, org: Optional[str] = None,
                          keyword: Optional[str] = None):
    index = _build_test_item_index(db)
    # 先初始化每个 test_item 的关联容器
    assoc_map = {
        it["id"]: {
            **it,
            "has_wjw": False,
            "has_bj": False,
            "wjw_tokens": [],
            "bj_tokens": [],
            "match_score": "",
        }
        for it in index
    }

    # 同族索引：base 前缀 → 该项目库内所有 test_item id（用于拆分项共享父项 EQA）
    families = {}
    for it in index:
        families.setdefault(it["base"], []).append(it["id"])

    plans = db.query(EqaPlan.org, EqaPlan.program, EqaPlan.item).all()
    for org_name, program, item in plans:
        if "正确度" in (program or ""):
            continue
        for token in _split_eqa_items(item):
            it, score = _match_eqa_token(token, index)
            if not it:
                continue
            _apply_org(assoc_map, families, it["id"], org_name, token, score)

    # 手动关联修正：把自动匹配漏掉的项（标本变体/略称/罗马数字/跨program）补标为有质评
    for tid, entries in _MANUAL_ASSOCIATIONS.items():
        rec = assoc_map.get(tid)
        if not rec:
            continue
        for org_name, label in entries:
            if org_name == "卫健委":
                if label not in rec["wjw_tokens"]:
                    rec["wjw_tokens"].append(label)
                rec["has_wjw"] = True
            elif org_name == "北京市":
                if label not in rec["bj_tokens"]:
                    rec["bj_tokens"].append(label)
                rec["has_bj"] = True
        if rec["match_score"] in ("", "none"):
            rec["match_score"] = "manual"

    # ── 质量要求标准整合 ──
    qr_maps = _build_qr_maps(db)
    for tid, rec in assoc_map.items():
        name = rec["name"]
        rec["wst403"] = _qr_to_detail(_find_qr_for_item(name, qr_maps.get("wst403-2024", {})))
        rec["bj_hr"] = _qr_to_detail(_find_qr_for_item(name, qr_maps.get("bj-hr-2025", {})))
        rec["nccl"] = _qr_to_detail(_find_qr_for_item(name, qr_maps.get("nccl-2026", {})))

    results = []
    for rec in assoc_map.values():
        rec["has_eqa"] = rec["has_wjw"] or rec["has_bj"]
        if rec["match_score"] == "":
            rec["match_score"] = "none"

        # 过滤
        if category and rec["category"] != category:
            continue
        if has_eqa == "yes" and not rec["has_eqa"]:
            continue
        if has_eqa == "no" and rec["has_eqa"]:
            continue
        if org == "wjw" and not rec["has_wjw"]:
            continue
        if org == "bj" and not rec["has_bj"]:
            continue
        if keyword:
            kw = keyword.lower()
            hay = (rec["name"] + rec["category"] + rec["specimen"] + rec["instrument"] +
                   "".join(rec["wjw_tokens"] + rec["bj_tokens"]))
            # 也搜索质量要求中的文字
            for src_key in ("wst403", "bj_hr", "nccl"):
                d = rec.get(src_key)
                if d:
                    hay += (d.cv or "") + (d.bias or "") + (d.tea or "") + (d.item_name or "")
            if kw not in hay.lower():
                continue

        results.append(EqaAssociationItem(**{k: rec[k] for k in [
            "id", "name", "category", "specimen", "unit", "instrument", "brand",
            "has_eqa", "has_wjw", "has_bj", "wjw_tokens", "bj_tokens", "match_score",
            "wst403", "bj_hr", "nccl",
        ]}))

    # 排序：有质量要求的项目优先（被提及源数降序），再按类别、名称
    def _sort_key(x):
        n = 0
        if x.wst403: n += 1
        if x.bj_hr: n += 1
        if x.nccl: n += 1
        return (-n, x.category or "", x.name)

    results.sort(key=_sort_key)
    return results


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------
@router.get("", response_model=list[EqaAssociationItem], summary="项目库与室间质评关联查询（含质量标准）")
def list_eqa_associations(
    category: Optional[str] = Query(None, description="项目类别：生化/免疫/凝血/其他"),
    has_eqa: Optional[str] = Query(None, description="全部all/有yes/无no"),
    org: Optional[str] = Query(None, description="全部all/卫健委wjw/北京市bj"),
    keyword: Optional[str] = Query(None, description="关键词搜索（也搜质量要求中的文字）"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """返回 test_items 与 eqa_plans 的自动匹配关联 + 三个质量标准的允许误差指标。

    每行包含：
    - EQA 计划覆盖情况（卫健委/北京市 有无 + 细项名）
    - WS/T 403—2024 行标（CV / Bias / TEa）
    - 北京市互认标准（CV / EQA评价标准）
    - 卫健委 NCCL EQA 标准（可接受范围）
    """
    return _compute_associations(db, category=category, has_eqa=has_eqa, org=org, keyword=keyword)
