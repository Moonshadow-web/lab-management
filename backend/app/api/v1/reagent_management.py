"""试剂管理：试剂目录/库存/盘库/订购/接收/月消耗 API"""

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ...core.crud_base import paginate
from ...core.database import get_db
from ...core.security import get_current_user, require_roles
from ...models.reagent_management import (
    ReagentItem, ReagentStock, InventoryCheck, InventoryCheckItem,
    ReagentOrder, ReagentOrderItem, Receiving, ReceivingItem, ReagentConsumption,
)
from ...models.user import User
from ...schemas.reagent_management import (
    ReagentItemCreate, ReagentItemUpdate, ReagentItemRead,
    ReagentStockRead, InventoryCheckCreate, InventoryCheckRead,
    ReagentOrderCreate, ReagentOrderRead, ReceivingCreate, ReceivingRead,
    ReagentConsumptionRead, ImportResult,
)

router = APIRouter(prefix="/reagent", tags=["reagent-management"])


# =============================================================================
# 1. 试剂目录 CRUD
# =============================================================================

@router.get("/items", response_model=dict)
def list_reagent_items(
    q: str = Query("", description="搜索（名称/品牌/材料编码）"),
    type: Optional[str] = Query(None, description="类型筛选"),
    category: Optional[str] = Query(None, description="类别筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    base = db.query(ReagentItem)
    if q.strip():
        kw = f"%{q.strip()}%"
        base = base.filter(
            or_(ReagentItem.name.like(kw), ReagentItem.brand.like(kw),
                ReagentItem.material_code.like(kw), ReagentItem.spec.like(kw))
        )
    if type:
        base = base.filter(ReagentItem.type == type)
    if category:
        base = base.filter(ReagentItem.category == category)
    total = base.count()
    items = base.order_by(ReagentItem.type, ReagentItem.category, ReagentItem.id).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.get("/items/{item_id}", response_model=ReagentItemRead)
def get_reagent_item(item_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    item = db.query(ReagentItem).get(item_id)
    if not item:
        raise HTTPException(404, "试剂未找到")
    return item


@router.post("/items", response_model=ReagentItemRead)
def create_reagent_item(
    data: ReagentItemCreate, db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "lab_technician")),
):
    item = ReagentItem(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/items/{item_id}", response_model=ReagentItemRead)
def update_reagent_item(
    item_id: int, data: ReagentItemUpdate, db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "lab_technician")),
):
    item = db.query(ReagentItem).get(item_id)
    if not item:
        raise HTTPException(404, "试剂未找到")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/items/{item_id}")
def delete_reagent_item(
    item_id: int, db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin")),
):
    item = db.query(ReagentItem).get(item_id)
    if not item:
        raise HTTPException(404, "试剂未找到")
    db.delete(item)
    db.commit()
    return {"ok": True}


# =============================================================================
# 2. 实时库存
# =============================================================================

@router.get("/stock", response_model=dict)
def list_stock(
    q: str = Query("", description="搜索试剂名称/品牌"),
    type: Optional[str] = Query(None),
    low_stock_only: bool = Query(False, description="只显示低于最低库存预警的"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    base = db.query(ReagentStock)
    if q.strip():
        kw = f"%{q.strip()}%"
        item_ids = [r[0] for r in db.query(ReagentItem.id).filter(
            or_(ReagentItem.name.like(kw), ReagentItem.brand.like(kw))
        ).all()]
        base = base.filter(ReagentStock.item_id.in_(item_ids))
    if type:
        item_ids2 = [r[0] for r in db.query(ReagentItem.id).filter(ReagentItem.type == type).all()]
        base = base.filter(ReagentStock.item_id.in_(item_ids2))
    total = base.count()
    items = base.order_by(ReagentStock.item_id).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size, "items": items}


# =============================================================================
# 3. 盘库
# =============================================================================

@router.get("/inventory-checks", response_model=dict)
def list_inventory_checks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    total = db.query(InventoryCheck).count()
    items = db.query(InventoryCheck).order_by(InventoryCheck.check_date.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.get("/inventory-checks/{check_id}", response_model=InventoryCheckRead)
def get_inventory_check(check_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    check = db.query(InventoryCheck).get(check_id)
    if not check:
        raise HTTPException(404, "盘库未找到")
    return check


@router.post("/inventory-checks", response_model=InventoryCheckRead)
def create_inventory_check(
    data: InventoryCheckCreate, db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "lab_technician")),
):
    check = InventoryCheck(
        check_date=data.check_date,
        check_type=data.check_type,
        operator=user.full_name or user.username,
        remark=data.remark,
    )
    db.add(check)
    db.flush()  # 获取 id
    for it in data.items:
        item = InventoryCheckItem(
            check_id=check.id, item_id=it.item_id, batch_no=it.batch_no,
            expiry_date=it.expiry_date, recorded_quantity=it.recorded_quantity,
        )
        db.add(item)
        # 同步更新 reagent_stock
        stock = db.query(ReagentStock).filter(
            ReagentStock.item_id == it.item_id,
            ReagentStock.batch_no == it.batch_no,
        ).first()
        if stock:
            stock.quantity = it.recorded_quantity
            stock.last_updated = datetime.utcnow()
        else:
            db.add(ReagentStock(
                item_id=it.item_id, batch_no=it.batch_no,
                expiry_date=it.expiry_date, quantity=it.recorded_quantity,
            ))
    db.commit()
    db.refresh(check)
    return check


# =============================================================================
# 4. 订购
# =============================================================================

@router.get("/orders", response_model=dict)
def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    total = db.query(ReagentOrder).count()
    items = db.query(ReagentOrder).order_by(ReagentOrder.order_date.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.get("/orders/{order_id}", response_model=ReagentOrderRead)
def get_order(order_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    order = db.query(ReagentOrder).get(order_id)
    if not order:
        raise HTTPException(404, "订购单未找到")
    return order


@router.post("/orders", response_model=ReagentOrderRead)
def create_order(
    data: ReagentOrderCreate, db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "lab_technician")),
):
    order = ReagentOrder(
        order_no=data.order_no, order_date=data.order_date,
        order_type=data.order_type, status="草稿",
        operator=user.full_name or user.username, remark=data.remark,
    )
    db.add(order)
    db.flush()
    for it in data.items:
        db.add(ReagentOrderItem(order_id=order.id, **it.model_dump()))
    db.commit()
    db.refresh(order)
    return order


@router.put("/orders/{order_id}", response_model=ReagentOrderRead)
def update_order(
    order_id: int, data: ReagentOrderCreate, db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "lab_technician")),
):
    order = db.query(ReagentOrder).get(order_id)
    if not order:
        raise HTTPException(404, "订购单未找到")
    order.order_date = data.order_date
    order.order_type = data.order_type
    order.status = data.status
    order.remark = data.remark
    order.operator = user.full_name or user.username
    # 先删旧细项再重建
    db.query(ReagentOrderItem).filter(ReagentOrderItem.order_id == order.id).delete()
    for it in data.items:
        db.add(ReagentOrderItem(order_id=order.id, **it.model_dump()))
    db.commit()
    db.refresh(order)
    return order


@router.delete("/orders/{order_id}")
def delete_order(
    order_id: int, db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin")),
):
    order = db.query(ReagentOrder).get(order_id)
    if not order:
        raise HTTPException(404, "订购单未找到")
    db.delete(order)
    db.commit()
    return {"ok": True}


@router.get("/orders/{order_id}/export-form")
def export_order_form(
    order_id: int, db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """导出向设备科提交的订购表（后续实现 openpyxl 下载）。"""
    order = db.query(ReagentOrder).get(order_id)
    if not order:
        raise HTTPException(404, "订购单未找到")
    # TODO: 返回 Excel 文件下载
    return {"msg": "导出功能将在后续实现"}


# =============================================================================
# 5. 到货接收
# =============================================================================

@router.get("/receivings", response_model=dict)
def list_receivings(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    total = db.query(Receiving).count()
    items = db.query(Receiving).order_by(Receiving.receipt_date.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.get("/receivings/{receiving_id}", response_model=ReceivingRead)
def get_receiving(receiving_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    r = db.query(Receiving).get(receiving_id)
    if not r:
        raise HTTPException(404, "收货记录未找到")
    return r


@router.post("/receivings", response_model=ReceivingRead)
def create_receiving(
    data: ReceivingCreate, db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "lab_technician")),
):
    rec = Receiving(
        receipt_no=data.receipt_no, receipt_date=data.receipt_date,
        order_id=data.order_id, delivery_person=data.delivery_person,
        receiver=user.full_name or user.username, remark=data.remark,
    )
    db.add(rec)
    db.flush()
    for it in data.items:
        db.add(ReceivingItem(
            receiving_id=rec.id, item_id=it.item_id, batch_no=it.batch_no,
            expiry_date=it.expiry_date, quantity=it.quantity, remark=it.remark,
        ))
        # 库存增加
        stock = db.query(ReagentStock).filter(
            ReagentStock.item_id == it.item_id,
            ReagentStock.batch_no == it.batch_no,
        ).first()
        if stock:
            stock.quantity += it.quantity
            stock.last_updated = datetime.utcnow()
        else:
            db.add(ReagentStock(
                item_id=it.item_id, batch_no=it.batch_no,
                expiry_date=it.expiry_date, quantity=it.quantity,
            ))
    db.commit()
    db.refresh(rec)
    return rec


# =============================================================================
# 6. 月消耗
# =============================================================================

@router.get("/consumption", response_model=dict)
def list_consumption(
    year_month: Optional[str] = Query(None, description="YYYY-MM"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    base = db.query(ReagentConsumption)
    if year_month:
        base = base.filter(ReagentConsumption.year_month == year_month)
    total = base.count()
    items = base.order_by(ReagentConsumption.year_month.desc(), ReagentConsumption.item_id).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.post("/consumption/_calculate")
def calculate_consumption(
    year_month: str = Query(..., description="YYYY-MM"),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "lab_technician")),
):
    """盘库后触发：对所有 reagent_items 计算月消耗。"""
    items = db.query(ReagentItem).filter(ReagentItem.is_active == True).all()
    added = 0
    for it in items:
        # 本期入库汇总
        total_recv = db.query(ReagentStock).filter(ReagentStock.item_id == it.id).with_entities(ReagentStock.quantity).all()
        closing = sum(r[0] for r in total_recv)
        # 上月消耗记录的 closing 作为本期 opening
        prev = db.query(ReagentConsumption).filter(
            ReagentConsumption.item_id == it.id,
        ).order_by(ReagentConsumption.year_month.desc()).first()
        opening = prev.closing_balance if prev else 0
        # 本月入库量（从 receiving 计算）
        # 简化版：暂取 stock quantity 之和
        consumption = opening + closing - closing  # placeholder
        # 实际计算 month_received
        month_start = date(int(year_month[:4]), int(year_month[5:7]), 1)
        if month_start.month == 12:
            month_end = date(month_start.year + 1, 1, 1)
        else:
            month_end = date(month_start.year, month_start.month + 1, 1)
        total_received_qty = db.query(ReagentStock).filter(
            ReagentStock.item_id == it.id,
        ).with_entities(ReagentStock.quantity).all()
        closing_qty = sum(r[0] for r in total_received_qty)
        consumption = opening - closing_qty  # 暂简算
        if consumption < 0:
            consumption = 0
        # upsert
        existing = db.query(ReagentConsumption).filter(
            ReagentConsumption.item_id == it.id,
            ReagentConsumption.year_month == year_month,
        ).first()
        if existing:
            existing.opening_balance = opening
            existing.closing_balance = closing_qty
            existing.total_received = total_received_qty
            existing.consumption = consumption
            existing.calculated_at = datetime.utcnow()
        else:
            db.add(ReagentConsumption(
                item_id=it.id, year_month=year_month,
                opening_balance=opening, total_received=0,
                closing_balance=closing_qty, consumption=consumption,
            ))
            added += 1
    db.commit()
    return {"added": added, "year_month": year_month}


# =============================================================================
# 7. Excel 导入试剂目录
# =============================================================================

@router.post("/items/_import-excel", response_model=ImportResult)
def import_reagent_from_excel(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin")),
    _file: UploadFile = File(...),
):
    """从 Excel 导入试剂目录（要求：第1行表头，需含 'name' 或 '试剂名称' 列）。"""
    result = ImportResult()
    try:
        import openpyxl
    except ImportError:
        raise HTTPException(400, "服务端未安装 openpyxl，无法处理 Excel")
    wb = openpyxl.load_workbook(_file.file)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise HTTPException(400, "Excel 为空")
    headers = [str(h or "").strip() for h in rows[0]]
    # 尝试推断列映射
    col_map = {}
    for col in ["name", "试剂名称", "名称", "名称(试剂名称)", "试剂名"]:
        if col in headers:
            col_map["name"] = headers.index(col)
            break
    if "name" not in col_map:
        raise HTTPException(400, "找不到 'name/试剂名称' 列")
    for col in ["type", "类型", "试剂类型"]:
        if col in headers:
            col_map["type"] = headers.index(col)
            break
    for col in ["category", "类别", "专业"]:
        if col in headers:
            col_map["category"] = headers.index(col)
            break
    for col in ["brand", "品牌", "生产厂家", "厂家"]:
        if col in headers:
            col_map["brand"] = headers.index(col)
            break
    for col in ["spec", "规格", "包装规格"]:
        if col in headers:
            col_map["spec"] = headers.index(col)
            break
    for col in ["material_code", "材料编码", "编码", "订购编码"]:
        if col in headers:
            col_map["material_code"] = headers.index(col)
            break
    for col in ["unit", "单位"]:
        if col in headers:
            col_map["unit"] = headers.index(col)
            break
    for col in ["manufacturer", "生产厂家2", "制造商"]:
        if col in headers:
            col_map["manufacturer"] = headers.index(col)
            break
    for col in ["supplier", "供应商"]:
        if col in headers:
            col_map["supplier"] = headers.index(col)
            break

    imported = 0
    skipped = 0
    for i, row in enumerate(rows[1:], 2):
        try:
            name = str(row[col_map["name"]] or "").strip()
            if not name:
                skipped += 1
                continue
            # 去重检查
            existing = db.query(ReagentItem).filter(ReagentItem.name == name).first()
            if existing:
                # 更新材料编码等
                if "material_code" in col_map:
                    mc = str(row[col_map["material_code"]] or "").strip()
                    if mc:
                        existing.material_code = mc
                skipped += 1
                continue
            item = ReagentItem(name=name)
            if "type" in col_map:
                item.type = str(row[col_map["type"]] or "试剂").strip()
            if "category" in col_map:
                item.category = str(row[col_map["category"]] or "").strip()
            if "brand" in col_map:
                item.brand = str(row[col_map["brand"]] or "").strip()
            if "spec" in col_map:
                item.spec = str(row[col_map["spec"]] or "").strip()
            if "material_code" in col_map:
                item.material_code = str(row[col_map["material_code"]] or "").strip()
            if "unit" in col_map:
                item.unit = str(row[col_map["unit"]] or "").strip()
            if "manufacturer" in col_map:
                item.manufacturer = str(row[col_map["manufacturer"]] or "").strip()
            if "supplier" in col_map:
                item.supplier = str(row[col_map["supplier"]] or "").strip()
            db.add(item)
            imported += 1
        except Exception as e:
            result.errors.append(f"第{i}行: {e}")
            skipped += 1
    db.commit()
    result.total = len(rows) - 1
    result.imported = imported
    result.skipped = skipped
    return result
