"""试剂管理模块 · 数据模型

包含 9 张表，覆盖试剂目录/实时库存/盘库/订购/到货/月消耗全流程。
不与旧 reagents 表冲突（表名均不同）。
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


# =============================================================================
# 1. 试剂项目目录
# =============================================================================
REAGENT_ITEM_TYPES = ["试剂", "校准品", "质控品", "耗材"]
REAGENT_ITEM_CATEGORIES = ["生化", "免疫", "凝血", "血气", "尿液", "其他"]


class ReagentItem(Base):
    """试剂/校准品/质控品/耗材 的基础信息目录。"""

    __tablename__ = "reagent_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(20), default="试剂", index=True)
    category: Mapped[str] = mapped_column(String(50), default="", index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    brand: Mapped[str] = mapped_column(String(100), default="")
    spec: Mapped[str] = mapped_column(String(200), default="")
    material_code: Mapped[str] = mapped_column(String(50), default="", index=True)  # 设备处订购材料编码
    unit: Mapped[str] = mapped_column(String(20), default="")
    manufacturer: Mapped[str] = mapped_column(String(100), default="")
    supplier: Mapped[str] = mapped_column(String(100), default="")
    min_stock: Mapped[int] = mapped_column(Integer, default=0)  # 最低库存预警量
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    remark: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# =============================================================================
# 2. 实时库存
# =============================================================================
class ReagentStock(Base):
    """当前库存余额（按试剂+批号+效期明细）。"""

    __tablename__ = "reagent_stock"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("reagent_items.id"), nullable=False, index=True)
    batch_no: Mapped[str] = mapped_column(String(100), default="", index=True)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# =============================================================================
# 3. 盘库记录
# =============================================================================
INVENTORY_CHECK_TYPES = ["月末盘库", "月中盘库"]


class InventoryCheck(Base):
    """盘库主表（一次盘库操作）。"""

    __tablename__ = "reagent_inventory_checks"

    id: Mapped[int] = mapped_column(primary_key=True)
    check_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    check_type: Mapped[str] = mapped_column(String(20), default="月末盘库")
    operator: Mapped[str] = mapped_column(String(100), default="")
    remark: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    items: Mapped[list["InventoryCheckItem"]] = relationship(
        "InventoryCheckItem", back_populates="check", cascade="all, delete-orphan"
    )


class InventoryCheckItem(Base):
    """盘库细项。"""

    __tablename__ = "reagent_inventory_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    check_id: Mapped[int] = mapped_column(ForeignKey("reagent_inventory_checks.id"), nullable=False, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("reagent_items.id"), nullable=False, index=True)
    batch_no: Mapped[str] = mapped_column(String(100), default="")
    expiry_date: Mapped[date] = mapped_column(Date, nullable=True)
    recorded_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    check: Mapped[InventoryCheck] = relationship("InventoryCheck", back_populates="items")


# =============================================================================
# 4. 订购单
# =============================================================================
ORDER_TYPES = ["月初订购", "加订"]
ORDER_STATUSES = ["草稿", "已提交", "部分到货", "完成"]


class ReagentOrder(Base):
    """订购单。"""

    __tablename__ = "reagent_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    order_type: Mapped[str] = mapped_column(String(20), default="月初订购")
    status: Mapped[str] = mapped_column(String(20), default="草稿")
    operator: Mapped[str] = mapped_column(String(100), default="")
    remark: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items: Mapped[list["ReagentOrderItem"]] = relationship(
        "ReagentOrderItem", back_populates="order", cascade="all, delete-orphan"
    )


class ReagentOrderItem(Base):
    """订购细项。"""

    __tablename__ = "reagent_order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("reagent_orders.id"), nullable=False, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("reagent_items.id"), nullable=False, index=True)
    ordered_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    received_quantity: Mapped[int] = mapped_column(Integer, default=0)
    remark: Mapped[str] = mapped_column(Text, default="")

    order: Mapped[ReagentOrder] = relationship("ReagentOrder", back_populates="items")


# =============================================================================
# 5. 到货接收
# =============================================================================
class Receiving(Base):
    """到货接收主表。"""

    __tablename__ = "reagent_receivings"

    id: Mapped[int] = mapped_column(primary_key=True)
    receipt_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    receipt_date: Mapped[date] = mapped_column(Date, nullable=False)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("reagent_orders.id"), nullable=True)  # 可选关联订购单
    delivery_person: Mapped[str] = mapped_column(String(100), default="")
    receiver: Mapped[str] = mapped_column(String(100), nullable=False)
    remark: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    items: Mapped[list["ReceivingItem"]] = relationship(
        "ReceivingItem", back_populates="receiving", cascade="all, delete-orphan"
    )


class ReceivingItem(Base):
    """接收细项。"""

    __tablename__ = "reagent_receiving_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    receiving_id: Mapped[int] = mapped_column(ForeignKey("reagent_receivings.id"), nullable=False, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("reagent_items.id"), nullable=False, index=True)
    batch_no: Mapped[str] = mapped_column(String(100), default="")
    expiry_date: Mapped[date] = mapped_column(Date, nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    remark: Mapped[str] = mapped_column(Text, default="")

    receiving: Mapped[Receiving] = relationship("Receiving", back_populates="items")


# =============================================================================
# 6. 月消耗记录
# =============================================================================
class ReagentConsumption(Base):
    """月消耗计算记录。"""

    __tablename__ = "reagent_consumption"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("reagent_items.id"), nullable=False, index=True)
    year_month: Mapped[str] = mapped_column(String(7), nullable=False, index=True)  # YYYY-MM
    opening_balance: Mapped[int] = mapped_column(Integer, default=0)  # 月初库存（上期末结余）
    total_received: Mapped[int] = mapped_column(Integer, default=0)  # 本月入库
    closing_balance: Mapped[int] = mapped_column(Integer, default=0)  # 月末库存（盘库数）
    consumption: Mapped[int] = mapped_column(Integer, default=0)  # 月消耗 = opening + received - closing
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
