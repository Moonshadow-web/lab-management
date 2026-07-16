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
    reference_lab: str = ""
    compared_at: str = ""
    operator: str = ""
    reviewer: str = ""
    summary: str = ""
    conclusion: str = ""
    handle_plan: str = ""
    status: str = "draft"
    report_filename: str = ""


class InterlabPlanCreate(InterlabPlanBase):
    items: list[InterlabItemRow] = []   # 可选：直接随计划创建结果行
    auto_fill: bool = True              # 为 True 且未提供 items 时，按仪器自动带出必做项目


class InterlabPlanUpdate(BaseModel):
    year: Optional[int] = None
    half: Optional[int] = None
    instrument_id: Optional[int] = None
    reference_lab: Optional[str] = None
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
    report_path: str = ""
    created_by: str = ""
    created_at: Any = None
    updated_at: Any = None


# ---------------------------------------------------------------------------
# 结果录入
# ---------------------------------------------------------------------------
class InterlabItemRow(BaseModel):
    item: str
    unit: str = ""
    our_value: str = ""
    ref_value: str = ""
    te: str = "0"
    mode: str = "relative"  # relative(相对%) / absolute(绝对)
    kind: str = "定量"       # 定性 / 定量（决定套用 BG-SM-CZ-018 / 019 模板）
    note: str = ""


class InterlabResultsPayload(BaseModel):
    items: list[InterlabItemRow] = []


# ---------------------------------------------------------------------------
# 候选项目（按仪器 + 室间比对可用筛选）
# ---------------------------------------------------------------------------
class InterlabProject(BaseModel):
    id: int
    code: str = ""
    name: str = ""
    unit: str = ""
    instrument: str = ""
