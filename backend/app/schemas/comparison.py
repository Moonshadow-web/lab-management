"""仪器间比对模块 Pydantic 模型。"""

from typing import Any, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# 比对分组
# ---------------------------------------------------------------------------
class GroupItem(BaseModel):
    """分组内单个比对项目：名称、允许偏倚(TE)、偏倚计算方式、适用仪器。

    TE / mode 解析：
    - 项目级 te + mode：默认（一般用于相对偏倚%）
    - low_threshold + low_te：当靶机结果 ≤ low_threshold 时，用「绝对偏倚 = low_te」
      留空或不可解析 → 不启用，按项目级 te + mode 计算
    """
    name: str
    label: str = ""  # 中文名（便于识别），name 可为项目代码
    te: str = "0"  # 项目级允许偏倚（一般用于高浓度相对%）；如 "2"、"0.02"
    mode: str = "relative"  # relative(相对%) / absolute(绝对)，与 te 配合
    instrument_ids: list[int] = []  # 该项目实际适用的仪器 id；空=组内全部仪器
    # 低浓度用绝对偏倚：当参考值 ≤ low_threshold 时用绝对偏倚 = low_te
    # 例：钾 "0.2 mmol/L (≤3.3 mmol/L)" → low_threshold="3.3", low_te="0.2"
    #     钙 "0.1 mmol/L (≤2 mmol/L)"   → low_threshold="2",   low_te="0.1"
    # 单位不强制，low_threshold 解析为浮点与参考值比较；low_te 直接作为绝对偏倚
    low_threshold: str = ""  # 留空=不启用低浓度绝对偏倚
    low_te: str = ""  # 留空=不启用低浓度绝对偏倚


class ComparisonGroupBase(BaseModel):
    name: str
    category: str = "定量"  # 定量 / 定性
    form_code: str = ""
    form_title: str = ""
    instrument_ids: list[int] = []
    reference_instrument_id: int = 0
    levels: int = 5
    items: list[GroupItem] = []
    sample_desc: str = ""
    note: str = ""


class ComparisonGroupCreate(ComparisonGroupBase):
    pass


class ResolveItemsPayload(BaseModel):
    """按仪器档案解析共有项目的请求。"""
    instrument_ids: list[int] = []
    category: str = "定量"  # 定量 / 定性
    min_count: int = 2  # 至少几台仪器共有才纳入


class ComparisonGroupUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    form_code: Optional[str] = None
    form_title: Optional[str] = None
    instrument_ids: Optional[list[int]] = None
    reference_instrument_id: Optional[int] = None
    levels: Optional[int] = None
    items: Optional[list[GroupItem]] = None
    sample_desc: Optional[str] = None
    note: Optional[str] = None


class ComparisonGroupRead(ComparisonGroupBase):
    id: int
    created_by: str = ""
    created_at: Any = None
    updated_at: Any = None


# ---------------------------------------------------------------------------
# 比对计划
# ---------------------------------------------------------------------------
class ComparisonPlanBase(BaseModel):
    group_id: int
    year: int
    half: int = 1  # 1=上半年 2=下半年
    form_code: str = ""
    form_title: str = ""
    compared_at: str = ""
    operator: str = ""
    reviewer: str = ""
    summary: str = ""
    conclusion: str = ""
    handle_plan: str = ""
    status: str = "draft"
    only_uncompared: bool = False
    report_filename: str = ""


class ComparisonPlanCreate(ComparisonPlanBase):
    pass


class ComparisonPlanUpdate(BaseModel):
    group_id: Optional[int] = None
    year: Optional[int] = None
    half: Optional[int] = None
    form_code: Optional[str] = None
    form_title: Optional[str] = None
    compared_at: Optional[str] = None
    operator: Optional[str] = None
    reviewer: Optional[str] = None
    summary: Optional[str] = None
    conclusion: Optional[str] = None
    handle_plan: Optional[str] = None
    status: Optional[str] = None
    only_uncompared: Optional[bool] = None
    report_filename: Optional[str] = None


class ComparisonPlanRead(ComparisonPlanBase):
    id: int
    report_path: str = ""
    created_by: str = ""
    created_at: Any = None
    updated_at: Any = None


# ---------------------------------------------------------------------------
# 结果录入
# ---------------------------------------------------------------------------
class QuantResultRow(BaseModel):
    item: str
    level: int
    reference_value: str = ""
    values: dict[str, str] = {}  # 仪器id(字符串) -> 检测值(字符串)


class QualResultRow(BaseModel):
    item: str
    results: dict[str, list[str]] = {}  # 仪器id(字符串) -> [样本1..5 的 P/N]


class ComparisonResultsPayload(BaseModel):
    quant: list[QuantResultRow] = []
    qual: list[QualResultRow] = []


# ---------------------------------------------------------------------------
# 报告预览数据（由服务层计算后返回前端）
# ---------------------------------------------------------------------------
class ReportComputed(BaseModel):
    group: dict
    plan: dict
    category: str
    instruments: list[dict]  # [{id, name, is_reference}]
    computed: Any = None  # 计算结果（定量矩阵 / 定性矩阵）
    html: str = ""  # 预览用 HTML
