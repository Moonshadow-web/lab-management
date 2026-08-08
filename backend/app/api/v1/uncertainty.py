"""测量不确定度评估（对应 BG-SM-CZ-072 评定报告）。

数据模型 UncertaintyAssessment：输入 L1/L2 室内质控数据，后端存原始数据与
计算结果（均值/SD/CV%、合成与扩展不确定度、判定）；报告 HTML 由前端生成
（单项目报告 + 汇总表），支持预览/下载/存档。
"""
from ...core.crud_base import make_router
from ...models.uncertainty import UncertaintyAssessment
from ...schemas import (
    UncertaintyAssessmentCreate,
    UncertaintyAssessmentRead,
    UncertaintyAssessmentUpdate,
)

router = make_router(
    UncertaintyAssessment,
    UncertaintyAssessmentRead,
    UncertaintyAssessmentCreate,
    UncertaintyAssessmentUpdate,
    search_fields=["project_name", "project_code", "instrument"],
    json_fields=["l1_values", "l2_values"],
    prefix="/uncertainty",
    order_by=[UncertaintyAssessment.id.desc()],
)
