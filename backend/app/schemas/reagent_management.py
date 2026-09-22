"""试剂管理模块 · Pydantic Schemas"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


# ── 试剂项目目录 ──
class ReagentItemBase(BaseModel):
    type: str = "试剂"
    category: str = ""
    library: str = ""
    name: str
    brand: str = ""
    spec: str = ""
    material_code: str = ""
    unit: str = ""
    manufacturer: str = ""
    supplier: str = ""
    unit_price: Optional[Decimal] = None
    min_stock: int = 0
    annual_usage: int = 0
    is_active: bool = True
    remark: str = ""


class ReagentItemCreate(ReagentItemBase):
    pass


class ReagentItemUpdate(BaseModel):
    type: Optional[str] = None
    category: Optional[str] = None
    library: Optional[str] = None
    name: Optional[str] = None
    brand: Optional[str] = None
    spec: Optional[str] = None
    material_code: Optional[str] = None
    unit: Optional[str] = None
    manufacturer: Optional[str] = None
    supplier: Optional[str] = None
    unit_price: Optional[Decimal] = None
    min_stock: Optional[int] = None
    annual_usage: Optional[int] = None
    is_active: Optional[bool] = None
    remark: Optional[str] = None


class ReagentItemRead(ReagentItemBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── 项目 ↔ 试剂 关联 ──
class TestItemReagentBase(BaseModel):
    test_item_id: int
    reagent_item_id: int
    role: str = "试剂"
    auto_matched: bool = True
    remark: str = ""


class TestItemReagentCreate(TestItemReagentBase):
    pass


class TestItemReagentUpdate(BaseModel):
    test_item_id: Optional[int] = None
    reagent_item_id: Optional[int] = None
    role: Optional[str] = None
    auto_matched: Optional[bool] = None
    remark: Optional[str] = None


class TestItemReagentRead(TestItemReagentBase):
    id: int

    class Config:
        from_attributes = True


# ── 仪器 ↔ 试剂/耗材 关联 ──
class InstrumentReagentBase(BaseModel):
    instrument_id: int
    reagent_item_id: int
    role: str = "耗材"
    auto_matched: bool = True
    remark: str = ""


class InstrumentReagentCreate(InstrumentReagentBase):
    pass


class InstrumentReagentUpdate(BaseModel):
    instrument_id: Optional[int] = None
    reagent_item_id: Optional[int] = None
    role: Optional[str] = None
    auto_matched: Optional[bool] = None
    remark: Optional[str] = None


class InstrumentReagentRead(InstrumentReagentBase):
    id: int

    class Config:
        from_attributes = True


# ── 实时库存 ──
class ReagentStockBase(BaseModel):
    item_id: int
    batch_no: str = ""
    expiry_date: Optional[date] = None
    quantity: int = 0


class ReagentStockRead(ReagentStockBase):
    id: int
    last_updated: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── 盘库 ──
class InventoryCheckItemBase(BaseModel):
    item_id: int
    batch_no: str = ""
    expiry_date: Optional[date] = None
    recorded_quantity: int = 0


class InventoryCheckItemCreate(InventoryCheckItemBase):
    pass


class InventoryCheckBase(BaseModel):
    library: str = ""
    check_date: date
    check_type: str = "月末盘库"
    operator: str = ""
    remark: str = ""


class InventoryCheckCreate(InventoryCheckBase):
    items: list[InventoryCheckItemCreate] = []


class InventoryCheckItemRead(InventoryCheckItemBase):
    id: int
    check_id: int

    class Config:
        from_attributes = True


class InventoryCheckRead(InventoryCheckBase):
    id: int
    created_at: Optional[datetime] = None
    items: list[InventoryCheckItemRead] = []

    class Config:
        from_attributes = True


# ── 订购 ──
class ReagentOrderItemBase(BaseModel):
    item_id: int
    ordered_quantity: int = 0
    unit_price: Optional[Decimal] = None
    received_quantity: int = 0
    remark: str = ""


class ReagentOrderItemCreate(ReagentOrderItemBase):
    pass


class ReagentOrderItemRead(ReagentOrderItemBase):
    id: int
    order_id: int

    class Config:
        from_attributes = True


class ReagentOrderBase(BaseModel):
    library: str = ""
    order_no: str
    order_date: date
    order_type: str = "月初订购"
    status: str = "草稿"
    operator: str = ""
    remark: str = ""


class ReagentOrderCreate(ReagentOrderBase):
    order_no: Optional[str] = ""  # 留空则由后端按「日期+顺序」自动生成（如 2026072701）
    items: list[ReagentOrderItemCreate] = []


class ReagentOrderRead(ReagentOrderBase):
    id: int
    created_by: Optional[str] = ""
    is_confirmed: bool = False
    confirmed_at: Optional[datetime] = None
    confirmed_by: Optional[str] = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    items: list[ReagentOrderItemRead] = []

    class Config:
        from_attributes = True


# ── 到货接收 ──
class ReceivingItemBase(BaseModel):
    item_id: int
    batch_no: str = ""
    expiry_date: Optional[date] = None
    quantity: int = 0
    remark: str = ""


class ReceivingItemCreate(ReceivingItemBase):
    pass


class ReceivingItemRead(ReceivingItemBase):
    id: int
    receiving_id: int
    # 该批号是否为「新批号」：本单之外没有任何其他收货记录用过它。
    # 打印收货单时会醒目备注，提醒该批号需要做批间性能验证。
    is_new_batch: bool = False

    class Config:
        from_attributes = True


class ReceivingBase(BaseModel):
    receipt_no: str
    receipt_date: date
    order_id: Optional[int] = None
    delivery_person: str = ""
    receiver: Optional[str] = None
    remark: str = ""


class ReceivingCreate(ReceivingBase):
    # 目标专业组：留空=当前登录人所在组。仅 admin / reagent_manager 可指定为他组
    # （用于把货直接入到分子组等其他专业组的库里）。
    target_group: str = ""
    items: list[ReceivingItemCreate] = []


class ReceivingRead(ReceivingBase):
    id: int
    created_at: Optional[datetime] = None
    created_by: str = ""
    is_confirmed: bool = False
    confirmed_at: Optional[datetime] = None
    confirmed_by: str = ""
    items: list[ReceivingItemRead] = []

    class Config:
        from_attributes = True


# ── 月消耗 ──
class ReagentConsumptionBase(BaseModel):
    item_id: int
    year_month: str
    opening_balance: int = 0
    total_received: int = 0
    closing_balance: int = 0
    consumption: int = 0


class ReagentConsumptionRead(ReagentConsumptionBase):
    id: int
    calculated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── 试剂批间性能验证（试剂验收）──
class LotSample(BaseModel):
    """单个比对样本。"""
    name: str = ""
    kind: str = "样本"  # 质控 / 样本
    old_value: Optional[float] = None
    new_value: Optional[float] = None
    old_qual: str = ""   # 阳性/阴性
    new_qual: str = ""   # 阳性/阴性
    bias_mode: str = ""  # 本行偏倚方式，留空则继承记录级（relative/absolute）


class ReagentLotVerificationBase(BaseModel):
    item_id: int
    library: str = ""
    item_type: str = "试剂"
    reagent_name: str = ""
    spec: str = ""
    brand: str = ""
    old_batch_no: str = ""
    old_expiry_date: Optional[date] = None
    new_batch_no: str = ""
    new_expiry_date: Optional[date] = None
    change_date: Optional[date] = None
    test_item_id: Optional[int] = None
    test_item_name: str = ""
    criterion_source: str = ""
    criterion_label: str = ""
    allow_bias_pct: str = ""
    allow_bias_abs: str = ""      # 允许绝对偏倚（与结果同单位）
    bias_mode: str = "relative"  # 记录级默认：relative / absolute
    judge_mode: str = "quantitative"  # quantitative / qualitative / both
    samples: list[LotSample] = []
    sample_count: int = 5
    operator: str = ""
    remark: str = ""


class ReagentLotVerificationCreate(ReagentLotVerificationBase):
    pass


class ReagentLotVerificationUpdate(BaseModel):
    """部分更新：只传需要改的字段。"""
    item_id: Optional[int] = None
    library: Optional[str] = None
    item_type: Optional[str] = None
    reagent_name: Optional[str] = None
    spec: Optional[str] = None
    brand: Optional[str] = None
    old_batch_no: Optional[str] = None
    old_expiry_date: Optional[date] = None
    new_batch_no: Optional[str] = None
    new_expiry_date: Optional[date] = None
    change_date: Optional[date] = None
    test_item_id: Optional[int] = None
    test_item_name: Optional[str] = None
    criterion_source: Optional[str] = None
    criterion_label: Optional[str] = None
    allow_bias_pct: Optional[str] = None
    allow_bias_abs: Optional[str] = None
    bias_mode: Optional[str] = None
    judge_mode: Optional[str] = None
    samples: Optional[list[LotSample]] = None
    sample_count: Optional[int] = None
    operator: Optional[str] = None
    remark: Optional[str] = None
    status: Optional[str] = None


class ReagentLotVerificationRead(ReagentLotVerificationBase):
    id: int
    samples_json: str = ""
    pass_count: int = 0
    conclusion: str = "待完成"
    status: str = "待验证"
    verified_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── 分页通用 ──
class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list


# ── 通用导入结果 ──
class ImportResult(BaseModel):
    total: int = 0
    imported: int = 0
    skipped: int = 0
    errors: list[str] = []
