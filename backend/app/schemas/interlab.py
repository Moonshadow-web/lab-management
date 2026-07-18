"""室间比对模块 Pydantic 模型。"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# 计划
# ---------------------------------------------------------------------------
class InterlabPlanBase(BaseModel):
    year: int
    half: int = 1  # 1=上半年 2=下半年
    instrument_id: int = 0
    reference_lab: Optional[str] = ""
    compared_instrument2: Optional[str] = ""
    compared_at: Optional[str] = ""
    operator: Optional[str] = ""
    reviewer: Optional[str] = ""
    summary: Optional[str] = ""
    conclusion: Optional[str] = ""
    handle_plan: Optional[str] = ""
    status: str = "draft"
    report_filename: Optional[str] = ""


class InterlabItemRow(BaseModel):
    """创建计划时一行项目元数据（不含结果水平）。"""
    item: str
    unit: str = ""
    te: str = "0"
    mode: str = "relative"  # relative(相对%) / absolute(绝对)
    kind: str = "定量"       # 定性 / 定量


class InterlabPlanCreate(InterlabPlanBase):
    items: list[InterlabItemRow] = []
    auto_fill: bool = True


class InterlabPlanUpdate(BaseModel):
    year: Optional[int] = None
    half: Optional[int] = None
    instrument_id: Optional[int] = None
    reference_lab: Optional[str] = None
    compared_instrument2: Optional[str] = None
    compared_at: Optional[str] = None
    operator: Optional[str] = None
    reviewer: Optional[str] = None
    summary: Optional[str] = None
    conclusion: Optional[str] = None
    handle_plan: Optional[str] = None
    status: Optional[str] = None
    report_filename: Optional[str] = None


class InterlabPlanRead(InterlabPlanBase):
    id: int
    report_path: Optional[str] = ""
    compared_instrument2: Optional[str] = ""
    created_by: Optional[str] = ""
    created_at: Any = None
    updated_at: Any = None


# ---------------------------------------------------------------------------
# 水平结果
# ---------------------------------------------------------------------------
class InterlabLevelRow(BaseModel):
    """一个项目的一个水平（1~5）。"""
    level_num: int = 1
    # 我室均值 X
    our_value: str = ""
    # 比较系统1（通常即唯一参比实验室）
    ref1_y1: str = ""
    ref1_y2: str = ""
    ref1_mean: str = ""
    # 比较系统2（可空缺）
    ref2_y1: str = ""
    ref2_y2: str = ""
    ref2_mean: str = ""


class InterlabItemWithLevels(BaseModel):
    """项目 + 其 1~5 水平结果（录入/回显用）。"""
    item: str
    unit: str = ""
    te: str = "0"
    mode: str = "relative"
    kind: str = "定量"
    note: str = ""
    levels: list[InterlabLevelRow] = []


class InterlabResultsPayload(BaseModel):
    """批量保存一整个计划的结果。"""
    items: list[InterlabItemWithLevels] = []


class InterlabItemRead(BaseModel):
    """get_results 返回的单项目结构。"""
    item: str
    unit: str = ""
    te: str = "0"
    mode: str = "relative"
    kind: str = "定量"
    note: str = ""
    levels: list[InterlabLevelRow] = []


class InterlabResultsRead(BaseModel):
    """get_results 返回。"""
    instrument_name: str = ""
    reference_lab: str = ""
    items: list[InterlabItemRead] = []


# ---------------------------------------------------------------------------
# 候选项目
# ---------------------------------------------------------------------------
class InterlabProject(BaseModel):
    id: int
    code: str = ""
    name: str = ""
    unit: str = ""
    instrument: str = ""
    mandatory: bool = True
