"""从校准品(calibrator)文本识别试剂/仪器品牌。

品牌标识不单独建表，而是根据已有的 calibrator（校准品）字段文本，
按关键词匹配出品牌名，用于列表展示、统计与导出。
覆盖常见厂家，新增厂家直接在 BRAND_KEYWORDS 追加即可。
"""
from __future__ import annotations

# 品牌关键词（顺序即优先级，靠前的优先匹配）
BRAND_KEYWORDS: list[str] = [
    "贝克曼", "罗氏", "安图", "沃芬", "沃文特", "柏定", "柏荣",
    "迈瑞", "西门子", "雅培", "东芝", "日立", "优利特", "迪瑞",
    "利德曼", "九强", "美康", "透景", "科美", "基蛋", "奥森", "积水",
]


def extract_brand(calibrator: str | None) -> str:
    """根据校准品文本识别品牌；无法识别时返回空字符串。"""
    if not calibrator:
        return ""
    text = str(calibrator)
    for kw in BRAND_KEYWORDS:
        if kw and kw in text:
            return kw
    return ""


def resolve_brand(calibrator: str | None, brand: str | None = "") -> str:
    """解析品牌：优先使用显式存储的 brand 字段，否则回退到从校准品推导。"""
    stored = (brand or "").strip()
    if stored:
        return stored
    return extract_brand(calibrator)
