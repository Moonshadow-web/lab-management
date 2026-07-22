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
    order_no: str
    order_date: date
    order_type: str = "月初订购"
    status: str = "草稿"
    operator: str = ""
    remark: str = ""


class ReagentOrderCreate(ReagentOrderBase):
    items: list[ReagentOrderItemCreate] = []


class ReagentOrderRead(ReagentOrderBase):
    id: int
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
    items: list[ReceivingItemCreate] = []


class ReceivingRead(ReceivingBase):
    id: int
    created_at: Optional[datetime] = None
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
