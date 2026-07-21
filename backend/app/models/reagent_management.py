"""试剂管理模块 · 数据模型

包含 9 张表，覆盖试剂目录/实时库存/盘库/订购/到货/月消耗全流程。
不与旧 reagents 表冲突（表名均不同）。
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


# =============================================================================
# 0. 字典与辅助函数
# =============================================================================
REAGENT_ITEM_TYPES = ["试剂", "校准品", "质控品", "耗材"]
REAGENT_ITEM_CATEGORIES = ["生化", "免疫", "凝血", "血气", "尿液", "其他"]
# 两个责任库：生化+凝血 合并为「生化凝血」，免疫单独成库（由两人分别负责）
REAGENT_LIBRARIES = ["生化凝血", "免疫"]


def detect_reagent_type(name: str) -> str:
    """根据名称关键词判定试剂类型（试剂/校准品/质控品/耗材）。

    优先级：校准品 > 质控品 > 试剂盒/试剂 > 耗材（吸头/杯/清洗液/电极…） > 试剂。
    注意「电极法」是检测方法，试剂盒本身仍判为试剂；「稀释液/缓冲液」判为试剂。
    """
    s = (name or "").strip()
    if any(k in s for k in ("校准品", "校准", "定标", "校准物")):
        return "校准品"
    if any(k in s for k in ("质控品", "质控物", "质控", "控制品")):
        return "质控品"
    if "试剂盒" in s or "试剂" in s:
        return "试剂"
    if any(k in s for k in ("吸头", "吸嘴", "加样尖", "加样tip", "比色杯", "反应杯",
                             "清洗", "冲洗", "针头", "管路", "废液", "标签", "打印纸", "电极")):
        return "耗材"
    return "试剂"


def derive_library(category: str) -> str:
    """由专业组/类别推导责任库：生化/凝血→生化凝血，免疫→免疫，其它→空。"""
    c = (category or "").strip()
    if c in ("生化", "凝血"):
        return "生化凝血"
    if c == "免疫":
        return "免疫"
    return ""


# =============================================================================
# 1. 试剂项目目录
# =============================================================================
class ReagentItem(Base):
    """试剂/校准品/质控品/耗材 的基础信息目录。"""

    __tablename__ = "reagent_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(20), default="试剂", index=True)
    category: Mapped[str] = mapped_column(String(50), default="", index=True)
    library: Mapped[str] = mapped_column(String(20), default="", index=True)  # 责任库：生化凝血/免疫
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    brand: Mapped[str] = mapped_column(String(100), default="")
    spec: Mapped[str] = mapped_column(String(200), default="")
    material_code: Mapped[str] = mapped_column(String(50), default="", index=True)  # 设备处订购材料编码
    unit: Mapped[str] = mapped_column(String(20), default="")
    manufacturer: Mapped[str] = mapped_column(String(100), default="")
    supplier: Mapped[str] = mapped_column(String(100), default="")
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)  # 目录参考单价
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


# =============================================================================
# 7. 项目 ↔ 试剂 关联（便于试剂订购等开发）
# =============================================================================
class TestItemReagent(Base):
    """检验项目与试剂的对应关系：一个项目可对应多种试剂，有的还含校准品/质控品。"""

    __tablename__ = "test_item_reagents"

    id: Mapped[int] = mapped_column(primary_key=True)
    test_item_id: Mapped[int] = mapped_column(ForeignKey("test_items.id"), nullable=False, index=True)
    reagent_item_id: Mapped[int] = mapped_column(ForeignKey("reagent_items.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), default="试剂")  # 试剂/校准品/质控品
    auto_matched: Mapped[bool] = mapped_column(Boolean, default=True)  # 是否由自动匹配生成（供审核页区分）
    remark: Mapped[str] = mapped_column(Text, default="")

    test_item: Mapped["TestItem"] = relationship("TestItem")
    reagent_item: Mapped["ReagentItem"] = relationship("ReagentItem")

    __table_args__ = (
        UniqueConstraint("test_item_id", "reagent_item_id", name="uq_test_item_reagent"),
    )


# =============================================================================
# 8. 仪器 ↔ 试剂/耗材 关联（耗材对应仪器）
# =============================================================================
class InstrumentReagent(Base):
    """仪器与试剂/耗材的对应关系：主要表达「耗材对应仪器」（如吸头/清洗液对应某仪器）。"""

    __tablename__ = "instrument_reagents"

    id: Mapped[int] = mapped_column(primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), nullable=False, index=True)
    reagent_item_id: Mapped[int] = mapped_column(ForeignKey("reagent_items.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), default="耗材")  # 耗材/试剂
    auto_matched: Mapped[bool] = mapped_column(Boolean, default=True)
    remark: Mapped[str] = mapped_column(Text, default="")

    instrument: Mapped["Instrument"] = relationship("Instrument")
    reagent_item: Mapped["ReagentItem"] = relationship("ReagentItem")

    __table_args__ = (
        UniqueConstraint("instrument_id", "reagent_item_id", name="uq_instrument_reagent"),
    )
