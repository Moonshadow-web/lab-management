"""试剂管理：试剂目录/库存/盘库/订购/接收/月消耗 API"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy import or_, func
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
    rows = base.order_by(ReagentItem.type, ReagentItem.category, ReagentItem.id).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size,
            "items": [ReagentItemRead.model_validate(r) for r in rows]}


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
    if low_stock_only:
        # 仅显示低于最低库存预警的：join 试剂目录，按 min_stock>0 且 数量<min_stock 过滤
        base = base.join(ReagentItem, ReagentItem.id == ReagentStock.item_id).filter(
            ReagentItem.min_stock > 0,
            ReagentStock.quantity < ReagentItem.min_stock,
        )
    total = base.count()
    rows = base.order_by(ReagentStock.item_id).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size,
            "items": [ReagentStockRead.model_validate(r) for r in rows]}


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
    rows = db.query(InventoryCheck).order_by(InventoryCheck.check_date.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size,
            "items": [InventoryCheckRead.model_validate(r) for r in rows]}


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
    rows = db.query(ReagentOrder).order_by(ReagentOrder.order_date.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size,
            "items": [ReagentOrderRead.model_validate(r) for r in rows]}


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
    """导出向设备科提交的订购表（含材料编码/名称/规格/品牌/数量/单位）。"""
    order = db.query(ReagentOrder).get(order_id)
    if not order:
        raise HTTPException(404, "订购单未找到")
    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment, Border, Side
    except ImportError:
        raise HTTPException(400, "服务端未安装 openpyxl，无法导出 Excel")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "设备科订购表"
    headers = ["材料编码", "试剂名称", "规格", "品牌", "订购数量", "单位", "备注"]
    ws.append(headers)
    head_font = Font(bold=True, color="FFFFFF")
    head_fill = openpyxl.styles.PatternFill("solid", fgColor="1A365D")
    thin = Side(style="thin", color="D0D5DD")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    for c in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=c)
        cell.font = head_font
        cell.fill = head_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border
    for it in order.items:
        item = db.query(ReagentItem).get(it.item_id)
        ws.append([
            item.material_code if item else "",
            item.name if item else f"(id={it.item_id})",
            item.spec if item else "",
            item.brand if item else "",
            it.ordered_quantity,
            item.unit if item else "",
            it.remark or "",
        ])
    for r in range(2, ws.max_row + 1):
        for c in range(1, len(headers) + 1):
            ws.cell(row=r, column=c).border = border
    widths = [16, 28, 22, 14, 12, 8, 24]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"设备科订购表_{order.order_no}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
    rows = db.query(Receiving).order_by(Receiving.receipt_date.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size,
            "items": [ReceivingRead.model_validate(r) for r in rows]}


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
        receiver=data.receiver or user.full_name or user.username, remark=data.remark,
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
    rows = base.order_by(ReagentConsumption.year_month.desc(), ReagentConsumption.item_id).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size,
            "items": [ReagentConsumptionRead.model_validate(r) for r in rows]}


@router.post("/consumption/_calculate")
def calculate_consumption(
    year_month: str = Query(..., description="YYYY-MM"),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "lab_technician")),
):
    """盘库后触发：对所有 reagent_items 计算月消耗。

    公式：月消耗 = 期初库存(opening) + 本月入库(received) - 期末库存(closing)
      - 期末库存 = 当前实时库存合计（月末盘库已回写 ReagentStock）
      - 本月入库 = 当月到货接收合计（Receiving.receipt_date 在区间内）
      - 期初库存 = 上月消耗记录的期末库存
    """
    if not (len(year_month) == 7 and year_month[4] == "-"):
        raise HTTPException(400, "year_month 格式应为 YYYY-MM")
    try:
        y, m = int(year_month[:4]), int(year_month[5:7])
    except ValueError:
        raise HTTPException(400, "year_month 格式应为 YYYY-MM")
    month_start = date(y, m, 1)
    if m == 12:
        month_end = date(y + 1, 1, 1)
    else:
        month_end = date(y, m + 1, 1)

    items = db.query(ReagentItem).filter(ReagentItem.is_active == True).all()
    added, updated = 0, 0
    for it in items:
        # 期末库存：当前实时库存合计
        closing_qty = db.query(func.coalesce(func.sum(ReagentStock.quantity), 0)).filter(
            ReagentStock.item_id == it.id
        ).scalar() or 0
        # 本月入库：当月到货接收细项合计
        received_qty = db.query(func.coalesce(func.sum(ReceivingItem.quantity), 0)).join(
            Receiving, ReceivingItem.receiving_id == Receiving.id
        ).filter(
            ReceivingItem.item_id == it.id,
            Receiving.receipt_date >= month_start,
            Receiving.receipt_date < month_end,
        ).scalar() or 0
        # 期初库存：上月消耗记录的期末库存
        prev = db.query(ReagentConsumption).filter(
            ReagentConsumption.item_id == it.id,
        ).order_by(ReagentConsumption.year_month.desc()).first()
        opening = prev.closing_balance if prev else 0
        consumption = opening + received_qty - closing_qty
        if consumption < 0:
            consumption = 0

        existing = db.query(ReagentConsumption).filter(
            ReagentConsumption.item_id == it.id,
            ReagentConsumption.year_month == year_month,
        ).first()
        if existing:
            existing.opening_balance = opening
            existing.total_received = received_qty
            existing.closing_balance = closing_qty
            existing.consumption = consumption
            existing.calculated_at = datetime.utcnow()
            updated += 1
        elif opening or received_qty or closing_qty:
            # 仅当有数据时落库，避免大量空行
            db.add(ReagentConsumption(
                item_id=it.id, year_month=year_month,
                opening_balance=opening, total_received=received_qty,
                closing_balance=closing_qty, consumption=consumption,
            ))
            added += 1
    db.commit()
    return {"added": added, "updated": updated, "year_month": year_month}


# =============================================================================
# 7. Excel 导入试剂目录
# =============================================================================

@router.post("/items/_import-excel", response_model=ImportResult)
def import_reagent_from_excel(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin")),
    file: UploadFile = File(...),
):
    """从 Excel 导入试剂目录（要求：第1行表头，需含 'name' 或 '试剂名称' 列）。"""
    result = ImportResult()
    try:
        import openpyxl
    except ImportError:
        raise HTTPException(400, "服务端未安装 openpyxl，无法处理 Excel")
    wb = openpyxl.load_workbook(file.file)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise HTTPException(400, "Excel 为空")
    headers = [str(h or "").strip() for h in rows[0]]
    # 尝试推断列映射
    col_map = {}
    for col in ["name", "试剂名称", "材料名称", "名称", "名称(试剂名称)", "试剂名"]:
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
    for col in ["spec", "规格", "规格型号", "包装规格"]:
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
    for col in ["unit_price", "单价", "价格", "参考单价"]:
        if col in headers:
            col_map["unit_price"] = headers.index(col)
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
                # 已存在：用本次导入信息补全/覆盖目录字段
                for key in ("material_code", "spec", "brand", "unit", "category", "unit_price", "manufacturer", "supplier"):
                    if key not in col_map:
                        continue
                    v = row[col_map[key]]
                    if v is None or str(v).strip() == "":
                        continue
                    if key == "unit_price":
                        try:
                            setattr(existing, key, Decimal(str(v)))
                        except Exception:
                            pass
                    else:
                        setattr(existing, key, str(v).strip())
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
            if "unit_price" in col_map:
                v = row[col_map["unit_price"]]
                if v is not None and str(v).strip() != "":
                    try:
                        item.unit_price = Decimal(str(v))
                    except Exception:
                        pass
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
