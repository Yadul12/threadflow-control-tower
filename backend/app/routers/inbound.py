import json
from datetime import datetime, date, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import (
    Supplier,
    Category,
    Warehouse,
    Product,
    ProductAttribute,
    PurchaseOrder,
    PurchaseOrderItem,
    Inventory,
    StockMovement,
    Promotion,
)
from ..seed import compute_completeness

router = APIRouter(prefix="/api/inbound", tags=["Workspace A: Inbound Procurement & Catalogue"])


# --- Pydantic Schemas ---
class SupplierCreateRequest(BaseModel):
    code: str
    name: str
    tier: str = "TIER_1"
    category_specialization: str
    contact_name: str
    contact_email: str
    contact_phone: str
    city: str
    state: str
    payment_terms: str = "NET_45"
    contracted_lead_time_days: int = 16


class SupplierUpdateRequest(BaseModel):
    tier: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    contracted_lead_time_days: Optional[int] = None
    actual_avg_lead_time_days: Optional[float] = None
    on_time_delivery_rate: Optional[float] = None
    fill_rate: Optional[float] = None
    quality_pass_rate: Optional[float] = None
    status: Optional[str] = None
    new_issue_note: Optional[str] = None
    new_issue_severity: Optional[str] = "MEDIUM"


class POLineItemInput(BaseModel):
    product_id: int
    ordered_qty: int


class PurchaseOrderCreateRequest(BaseModel):
    supplier_id: int
    warehouse_id: int
    expected_delivery_days: Optional[int] = None
    notes: Optional[str] = None
    created_by: str = "Procurement Lead"
    items: List[POLineItemInput]


class PurchaseOrderStatusUpdateRequest(BaseModel):
    status: str  # ACKNOWLEDGED, DELAYED, PARTIALLY_RECEIVED, RECEIVED, CLOSED, CANCELLED
    supplier_acknowledged: Optional[bool] = None
    delay_days: Optional[int] = None
    delay_reason: Optional[str] = None
    received_ratio: Optional[float] = None  # e.g. 1.0 for full, 0.7 for partial
    discrepancy_qty: Optional[int] = None
    discrepancy_reason: Optional[str] = None


class CatalogueUpdateRequest(BaseModel):
    description: Optional[str] = None
    has_description: Optional[bool] = None
    image_count: Optional[int] = None
    has_size_chart: Optional[bool] = None
    has_fabric_care: Optional[bool] = None
    wash_care: Optional[str] = None
    is_duplicate_flag: Optional[bool] = None


class PricingUpdateRequest(BaseModel):
    mrp: Optional[float] = None
    discount_pct: Optional[float] = None
    selling_price: Optional[float] = None
    cost_price: Optional[float] = None
    reason: str = "Manual Merchandising Price Update"


class PromotionCreateRequest(BaseModel):
    code: str
    name: str
    campaign_type: str = "SEASONAL_SALE"
    category_id: Optional[int] = None
    discount_pct: float
    start_date: str
    end_date: str
    status: str = "ACTIVE"
    baseline_daily_units: float = 100.0
    promo_daily_units: float = 145.0


# --- 1. SUPPLIER MANAGEMENT ---
@router.get("/suppliers")
def list_suppliers(
    status: Optional[str] = None,
    tier: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Supplier)
    if status and status != "ALL":
        q = q.filter(Supplier.status == status)
    if tier and tier != "ALL":
        q = q.filter(Supplier.tier == tier)
    suppliers = q.order_by(Supplier.id.asc()).all()

    pos = db.query(PurchaseOrder).all()
    po_by_sup = {}
    for po in pos:
        po_by_sup.setdefault(po.supplier_id, []).append(po)

    results = []
    for s in suppliers:
        if search:
            term = search.lower()
            if term not in s.name.lower() and term not in s.code.lower() and term not in s.city.lower() and term not in s.category_specialization.lower():
                continue
        s_pos = po_by_sup.get(s.id, [])
        results.append({
            "id": s.id,
            "code": s.code,
            "name": s.name,
            "tier": s.tier,
            "category_specialization": s.category_specialization,
            "contact_name": s.contact_name,
            "contact_email": s.contact_email,
            "contact_phone": s.contact_phone,
            "city": s.city,
            "state": s.state,
            "payment_terms": s.payment_terms,
            "contracted_lead_time_days": s.contracted_lead_time_days,
            "actual_avg_lead_time_days": s.actual_avg_lead_time_days,
            "lead_time_variance_days": round(s.actual_avg_lead_time_days - s.contracted_lead_time_days, 1),
            "on_time_delivery_rate": s.on_time_delivery_rate,
            "fill_rate": s.fill_rate,
            "quality_pass_rate": s.quality_pass_rate,
            "issue_count": s.issue_count,
            "issue_history": json.loads(s.issue_history_json or "[]"),
            "status": s.status,
            "total_pos": len(s_pos),
            "delayed_pos": sum(1 for p in s_pos if p.status == "DELAYED" or p.delay_days > 0),
            "total_po_value_inr": round(sum(p.total_value_inr for p in s_pos), 2),
            "is_synthetic": s.is_synthetic,
        })
    return {"suppliers": results, "total": len(results)}


@router.get("/suppliers/{supplier_id}")
def get_supplier_detail(supplier_id: int, db: Session = Depends(get_db)):
    s = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Supplier not found")
    s_pos = db.query(PurchaseOrder).filter(PurchaseOrder.supplier_id == s.id).order_by(PurchaseOrder.order_date.desc()).all()
    s_prods = db.query(Product).filter(Product.supplier_id == s.id).limit(25).all()
    return {
        "supplier": {
            "id": s.id,
            "code": s.code,
            "name": s.name,
            "tier": s.tier,
            "category_specialization": s.category_specialization,
            "contact_name": s.contact_name,
            "contact_email": s.contact_email,
            "contact_phone": s.contact_phone,
            "city": s.city,
            "state": s.state,
            "payment_terms": s.payment_terms,
            "contracted_lead_time_days": s.contracted_lead_time_days,
            "actual_avg_lead_time_days": s.actual_avg_lead_time_days,
            "on_time_delivery_rate": s.on_time_delivery_rate,
            "fill_rate": s.fill_rate,
            "quality_pass_rate": s.quality_pass_rate,
            "issue_count": s.issue_count,
            "issue_history": json.loads(s.issue_history_json or "[]"),
            "status": s.status,
            "is_synthetic": s.is_synthetic,
        },
        "historical_purchase_orders": [
            {
                "id": p.id,
                "po_number": p.po_number,
                "status": p.status,
                "order_date": p.order_date.isoformat(),
                "expected_delivery_date": p.expected_delivery_date.isoformat(),
                "actual_delivery_date": p.actual_delivery_date.isoformat() if p.actual_delivery_date else None,
                "total_ordered_qty": p.total_ordered_qty,
                "total_received_qty": p.total_received_qty,
                "discrepancy_qty": p.discrepancy_qty,
                "total_value_inr": p.total_value_inr,
                "delay_days": p.delay_days,
            }
            for p in s_pos
        ],
        "supplied_skus": [
            {
                "id": pr.id,
                "sku": pr.sku,
                "name": pr.name,
                "cost_price": pr.cost_price,
                "selling_price": pr.selling_price,
                "completeness_score": pr.completeness_score,
            }
            for pr in s_prods
        ],
    }


@router.post("/suppliers")
def create_supplier(req: SupplierCreateRequest, db: Session = Depends(get_db)):
    existing = db.query(Supplier).filter(Supplier.code == req.code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Supplier code {req.code} already exists")
    sup = Supplier(
        code=req.code.strip().upper(),
        name=req.name.strip(),
        tier=req.tier,
        category_specialization=req.category_specialization,
        contact_name=req.contact_name,
        contact_email=req.contact_email,
        contact_phone=req.contact_phone,
        city=req.city,
        state=req.state,
        payment_terms=req.payment_terms,
        contracted_lead_time_days=req.contracted_lead_time_days,
        actual_avg_lead_time_days=float(req.contracted_lead_time_days),
        on_time_delivery_rate=95.0,
        fill_rate=96.0,
        quality_pass_rate=98.0,
        issue_count=0,
        issue_history_json="[]",
        status="ACTIVE",
        is_synthetic=True,
    )
    db.add(sup)
    db.commit()
    db.refresh(sup)
    return {"status": "created", "supplier_id": sup.id, "code": sup.code}


@router.patch("/suppliers/{supplier_id}")
def update_supplier(supplier_id: int, req: SupplierUpdateRequest, db: Session = Depends(get_db)):
    sup = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not sup:
        raise HTTPException(status_code=404, detail="Supplier not found")

    if req.tier is not None:
        sup.tier = req.tier
    if req.contact_name is not None:
        sup.contact_name = req.contact_name
    if req.contact_email is not None:
        sup.contact_email = req.contact_email
    if req.contact_phone is not None:
        sup.contact_phone = req.contact_phone
    if req.contracted_lead_time_days is not None:
        sup.contracted_lead_time_days = req.contracted_lead_time_days
    if req.actual_avg_lead_time_days is not None:
        sup.actual_avg_lead_time_days = req.actual_avg_lead_time_days
    if req.on_time_delivery_rate is not None:
        sup.on_time_delivery_rate = req.on_time_delivery_rate
    if req.fill_rate is not None:
        sup.fill_rate = req.fill_rate
    if req.quality_pass_rate is not None:
        sup.quality_pass_rate = req.quality_pass_rate
    if req.status is not None:
        sup.status = req.status

    if req.new_issue_note:
        issues = json.loads(sup.issue_history_json or "[]")
        issues.insert(0, {
            "date": date.today().isoformat(),
            "type": "OPERATIONAL_ISSUE_LOGGED",
            "severity": req.new_issue_severity or "MEDIUM",
            "summary": req.new_issue_note,
        })
        sup.issue_history_json = json.dumps(issues)
        sup.issue_count = len(issues)

    sup.updated_at = datetime.utcnow()
    db.commit()
    return {"status": "updated", "supplier_id": sup.id, "issue_count": sup.issue_count, "supplier_status": sup.status}


# --- 2. PURCHASE ORDER MANAGEMENT ---
@router.get("/purchase-orders")
def list_purchase_orders(
    status: Optional[str] = None,
    supplier_id: Optional[int] = None,
    warehouse_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    q = db.query(PurchaseOrder)
    if status and status != "ALL":
        q = q.filter(PurchaseOrder.status == status)
    if supplier_id:
        q = q.filter(PurchaseOrder.supplier_id == supplier_id)
    if warehouse_id:
        q = q.filter(PurchaseOrder.warehouse_id == warehouse_id)

    pos = q.order_by(PurchaseOrder.id.desc()).all()
    suppliers = {s.id: s for s in db.query(Supplier).all()}
    warehouses = {w.id: w for w in db.query(Warehouse).all()}
    categories = {c.id: c for c in db.query(Category).all()}
    products = {p.id: p for p in db.query(Product).all()}

    results = []
    for po in pos:
        sup = suppliers.get(po.supplier_id)
        wh = warehouses.get(po.warehouse_id)
        cat = categories.get(po.category_id)
        results.append({
            "id": po.id,
            "po_number": po.po_number,
            "supplier_id": po.supplier_id,
            "supplier_code": sup.code if sup else "",
            "supplier_name": sup.name if sup else "",
            "warehouse_id": po.warehouse_id,
            "warehouse_code": wh.code if wh else "",
            "warehouse_name": wh.name if wh else "",
            "category_name": cat.name if cat else "",
            "status": po.status,
            "order_date": po.order_date.isoformat(),
            "expected_delivery_date": po.expected_delivery_date.isoformat(),
            "actual_delivery_date": po.actual_delivery_date.isoformat() if po.actual_delivery_date else None,
            "supplier_acknowledged": po.supplier_acknowledged,
            "acknowledged_at": po.acknowledged_at.isoformat() if po.acknowledged_at else None,
            "total_ordered_qty": po.total_ordered_qty,
            "total_received_qty": po.total_received_qty,
            "pending_qty": po.pending_qty,
            "discrepancy_qty": po.discrepancy_qty,
            "total_value_inr": po.total_value_inr,
            "delay_days": po.delay_days,
            "delay_reason": po.delay_reason,
            "notes": po.notes,
            "created_by": po.created_by,
            "items": [
                {
                    "id": item.id,
                    "product_id": item.product_id,
                    "sku": products[item.product_id].sku if item.product_id in products else "",
                    "product_name": products[item.product_id].name if item.product_id in products else "",
                    "ordered_qty": item.ordered_qty,
                    "received_qty": item.received_qty,
                    "pending_qty": item.pending_qty,
                    "rejected_qty": item.rejected_qty,
                    "unit_cost_inr": item.unit_cost_inr,
                    "line_total_inr": item.line_total_inr,
                    "discrepancy_reason": item.discrepancy_reason,
                }
                for item in po.items
            ],
        })

    return {
        "purchase_orders": results,
        "summary": {
            "total_count": len(results),
            "delayed_count": sum(1 for r in results if r["status"] == "DELAYED"),
            "unacknowledged_count": sum(1 for r in results if not r["supplier_acknowledged"]),
            "total_pending_units": sum(r["pending_qty"] for r in results),
            "total_discrepancy_units": sum(r["discrepancy_qty"] for r in results),
            "total_open_value_inr": round(sum(r["total_value_inr"] for r in results if r["status"] not in ("RECEIVED", "CLOSED", "CANCELLED")), 2),
        },
    }


@router.post("/purchase-orders")
def create_purchase_order(req: PurchaseOrderCreateRequest, db: Session = Depends(get_db)):
    sup = db.query(Supplier).filter(Supplier.id == req.supplier_id).first()
    wh = db.query(Warehouse).filter(Warehouse.id == req.warehouse_id).first()
    if not sup or not wh:
        raise HTTPException(status_code=400, detail="Valid supplier_id and warehouse_id are required")
    if not req.items:
        raise HTTPException(status_code=400, detail="At least one PO line item is required")

    lead_days = req.expected_delivery_days or sup.contracted_lead_time_days
    today = date(2026, 11, 16)
    exp_date = today + timedelta(days=lead_days)

    next_num = db.query(PurchaseOrder).count() + 1001
    po_number = f"PO-2026-{next_num}"
    while db.query(PurchaseOrder).filter(PurchaseOrder.po_number == po_number).first():
        next_num += 1
        po_number = f"PO-2026-{next_num}"

    first_prod = db.query(Product).filter(Product.id == req.items[0].product_id).first()
    cat_id = first_prod.category_id if first_prod else 1

    po = PurchaseOrder(
        po_number=po_number,
        supplier_id=sup.id,
        warehouse_id=wh.id,
        category_id=cat_id,
        status="ISSUED",
        order_date=today,
        expected_delivery_date=exp_date,
        supplier_acknowledged=False,
        notes=req.notes or f"Replenishment order issued to {sup.name}",
        created_by=req.created_by,
        is_synthetic=True,
    )
    db.add(po)
    db.flush()

    tot_qty = 0
    tot_val = 0.0
    for item_in in req.items:
        prod = db.query(Product).filter(Product.id == item_in.product_id).first()
        if not prod:
            continue
        qty = max(1, item_in.ordered_qty)
        line_val = round(qty * prod.cost_price, 2)
        db.add(PurchaseOrderItem(
            po_id=po.id,
            product_id=prod.id,
            ordered_qty=qty,
            received_qty=0,
            pending_qty=qty,
            rejected_qty=0,
            unit_cost_inr=prod.cost_price,
            line_total_inr=line_val,
        ))
        tot_qty += qty
        tot_val += line_val

        # Update warehouse in_transit_qty
        inv = db.query(Inventory).filter(
            Inventory.product_id == prod.id,
            Inventory.warehouse_id == wh.id,
        ).first()
        if inv:
            inv.in_transit_qty += qty

    po.total_ordered_qty = tot_qty
    po.pending_qty = tot_qty
    po.total_value_inr = round(tot_val, 2)
    db.commit()
    db.refresh(po)
    return {
        "status": "created",
        "po_id": po.id,
        "po_number": po.po_number,
        "total_ordered_qty": po.total_ordered_qty,
        "total_value_inr": po.total_value_inr,
    }


@router.patch("/purchase-orders/{po_id}/status")
def update_purchase_order_status(po_id: int, req: PurchaseOrderStatusUpdateRequest, db: Session = Depends(get_db)):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")

    old_status = po.status
    po.status = req.status

    if req.supplier_acknowledged is not None:
        po.supplier_acknowledged = req.supplier_acknowledged
        if req.supplier_acknowledged and not po.acknowledged_at:
            po.acknowledged_at = datetime.utcnow()

    if req.status == "ACKNOWLEDGED":
        po.supplier_acknowledged = True
        po.acknowledged_at = datetime.utcnow()

    if req.status == "DELAYED":
        po.delay_days = req.delay_days if req.delay_days is not None else max(3, po.delay_days + 3)
        po.delay_reason = req.delay_reason or "Supplier production line delay reported"

    if req.status in ("PARTIALLY_RECEIVED", "RECEIVED"):
        po.supplier_acknowledged = True
        po.actual_delivery_date = date(2026, 11, 16)
        ratio = req.received_ratio if req.received_ratio is not None else (0.65 if req.status == "PARTIALLY_RECEIVED" else 1.0)
        tot_rec = 0
        tot_pend = 0
        tot_disc = req.discrepancy_qty or 0

        for idx, item in enumerate(po.items):
            item_disc = tot_disc if idx == 0 else 0
            rec_q = max(0, int(round(item.ordered_qty * ratio)) - item_disc)
            delta_received = max(0, rec_q - item.received_qty)
            item.received_qty = rec_q
            item.rejected_qty = item_disc
            item.pending_qty = max(0, item.ordered_qty - rec_q - item_disc)
            if item_disc > 0:
                item.discrepancy_reason = req.discrepancy_reason or "GRN short-shipment / QC reject"
            tot_rec += item.received_qty
            tot_pend += item.pending_qty

            if delta_received > 0:
                inv = db.query(Inventory).filter(
                    Inventory.product_id == item.product_id,
                    Inventory.warehouse_id == po.warehouse_id,
                ).first()
                if inv:
                    inv.on_hand_qty += delta_received
                    inv.available_qty = max(0, inv.on_hand_qty - inv.reserved_qty)
                    inv.in_transit_qty = max(0, inv.in_transit_qty - delta_received)
                    inv.age_bucket_0_30_qty += delta_received
                    inv.days_of_cover = round(inv.available_qty / max(inv.forecast_daily_demand, 0.1), 1)
                    if inv.available_qty > inv.reorder_point_qty:
                        inv.stock_status = "HEALTHY"
                db.add(StockMovement(
                    product_id=item.product_id,
                    warehouse_id=po.warehouse_id,
                    movement_type="GRN_INBOUND",
                    quantity_delta=delta_received,
                    reference_code=po.po_number,
                    performed_by="Inbound GRN Supervisor",
                    notes=f"Goods received against {po.po_number} ({req.status})",
                ))

        po.total_received_qty = tot_rec
        po.pending_qty = tot_pend
        po.discrepancy_qty = tot_disc

    po.updated_at = datetime.utcnow()
    db.commit()
    return {
        "status": "updated",
        "po_id": po.id,
        "po_number": po.po_number,
        "previous_status": old_status,
        "new_status": po.status,
        "total_received_qty": po.total_received_qty,
        "pending_qty": po.pending_qty,
        "discrepancy_qty": po.discrepancy_qty,
    }


# --- 3. CATALOGUE QUALITY & MERCHANDISING ---
@router.get("/catalogue")
def list_catalogue_quality(
    category_id: Optional[int] = None,
    only_issues: bool = False,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Product)
    if category_id:
        q = q.filter(Product.category_id == category_id)
    if only_issues:
        q = q.filter((Product.completeness_score < 100.0) | (Product.is_duplicate_flag == True))

    products = q.order_by(Product.completeness_score.asc(), Product.id.asc()).all()
    categories = {c.id: c for c in db.query(Category).all()}
    suppliers = {s.id: s for s in db.query(Supplier).all()}
    attrs = {a.product_id: a for a in db.query(ProductAttribute).all()}

    items = []
    for p in products:
        if search:
            term = search.lower()
            if term not in p.sku.lower() and term not in p.name.lower() and term not in p.brand.lower() and term not in p.style_code.lower():
                continue
        cat = categories.get(p.category_id)
        sup = suppliers.get(p.supplier_id)
        attr = attrs.get(p.id)
        items.append({
            "id": p.id,
            "sku": p.sku,
            "style_code": p.style_code,
            "name": p.name,
            "brand": p.brand,
            "category_id": p.category_id,
            "category_name": cat.name if cat else "",
            "department": cat.department if cat else "",
            "supplier_name": sup.name if sup else "",
            "season": p.season,
            "size": attr.size if attr else "M",
            "color": attr.color if attr else "Navy",
            "color_hex": attr.color_hex if attr else "#1E293B",
            "gsm_or_weight": attr.gsm_or_weight if attr else "",
            "fabric_composition": attr.fabric_composition if attr else "",
            "fit_type": attr.fit_type if attr else "",
            "wash_care": attr.wash_care if attr else "",
            "description": p.description or "",
            "has_description": p.has_description,
            "has_images": p.has_images,
            "image_count": p.image_count,
            "has_size_chart": p.has_size_chart,
            "has_fabric_care": p.has_fabric_care,
            "is_duplicate_flag": p.is_duplicate_flag,
            "duplicate_of_sku": p.duplicate_of_sku,
            "completeness_score": p.completeness_score,
            "missing_fields": json.loads(p.missing_fields_json or "[]"),
            "lifecycle_stage": p.lifecycle_stage,
        })

    all_prods = db.query(Product).all()
    return {
        "catalogue": items,
        "summary": {
            "total_skus": len(all_prods),
            "avg_completeness_score": round(sum(p.completeness_score for p in all_prods) / max(len(all_prods), 1), 1),
            "incomplete_sku_count": sum(1 for p in all_prods if p.completeness_score < 100.0),
            "missing_size_chart_count": sum(1 for p in all_prods if not p.has_size_chart),
            "missing_images_count": sum(1 for p in all_prods if p.image_count < 4),
            "duplicate_listing_count": sum(1 for p in all_prods if p.is_duplicate_flag),
        },
    }


@router.patch("/catalogue/{product_id}")
def update_catalogue_item(product_id: int, req: CatalogueUpdateRequest, db: Session = Depends(get_db)):
    prod = db.query(Product).filter(Product.id == product_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Product SKU not found")

    attr = db.query(ProductAttribute).filter(ProductAttribute.product_id == prod.id).first()

    if req.description is not None:
        prod.description = req.description
        prod.has_description = len(req.description.strip()) > 0
    if req.has_description is not None:
        prod.has_description = req.has_description
        if req.has_description and not prod.description:
            prod.description = f"Verified AW26 merchandising specification for {prod.name}."
    if req.image_count is not None:
        prod.image_count = max(0, req.image_count)
        prod.has_images = prod.image_count > 0
    if req.has_size_chart is not None:
        prod.has_size_chart = req.has_size_chart
    if req.has_fabric_care is not None:
        prod.has_fabric_care = req.has_fabric_care
        if attr and req.has_fabric_care and attr.wash_care == "Not specified":
            attr.wash_care = "Machine wash cold 30C gentle cycle, line dry in shade"
    if req.wash_care is not None and attr:
        attr.wash_care = req.wash_care
    if req.is_duplicate_flag is not None:
        prod.is_duplicate_flag = req.is_duplicate_flag
        if not req.is_duplicate_flag:
            prod.duplicate_of_sku = None

    score, missing = compute_completeness(
        prod.has_description,
        prod.image_count,
        prod.has_size_chart,
        prod.has_fabric_care,
        prod.is_duplicate_flag,
    )
    prod.completeness_score = score
    prod.missing_fields_json = json.dumps(missing)
    prod.updated_at = datetime.utcnow()
    db.commit()

    return {
        "status": "updated",
        "product_id": prod.id,
        "sku": prod.sku,
        "completeness_score": prod.completeness_score,
        "missing_fields": missing,
    }


# --- 4. PRICING & PROMOTIONS ---
@router.get("/pricing")
def list_pricing_and_promotions(
    category_id: Optional[int] = None,
    below_target_margin: bool = False,
    db: Session = Depends(get_db),
):
    q = db.query(Product)
    if category_id:
        q = q.filter(Product.category_id == category_id)
    prods = q.order_by(Product.id.asc()).all()
    cats = {c.id: c for c in db.query(Category).all()}

    pricing_rows = []
    for p in prods:
        cat = cats.get(p.category_id)
        target_gm = cat.target_gross_margin_pct if cat else 52.0
        margin_gap = round(p.gross_margin_pct - target_gm, 2)
        if below_target_margin and margin_gap >= 0:
            continue
        pricing_rows.append({
            "id": p.id,
            "sku": p.sku,
            "style_code": p.style_code,
            "name": p.name,
            "brand": p.brand,
            "category_id": p.category_id,
            "category_name": cat.name if cat else "",
            "cost_price": p.cost_price,
            "mrp": p.mrp,
            "selling_price": p.selling_price,
            "discount_pct": p.discount_pct,
            "tax_rate_pct": p.tax_rate_pct,
            "gross_margin_pct": p.gross_margin_pct,
            "target_gross_margin_pct": target_gm,
            "margin_variance_pct": margin_gap,
            "margin_status": "ABOVE_TARGET" if margin_gap >= 0 else ("GUARDRAIL_WARN" if margin_gap >= -5.0 else "MARGIN_BREACH"),
            "lifecycle_stage": p.lifecycle_stage,
            "price_history": json.loads(p.price_history_json or "[]"),
        })

    promos = db.query(Promotion).order_by(Promotion.id.asc()).all()
    promo_list = [
        {
            "id": pr.id,
            "code": pr.code,
            "name": pr.name,
            "campaign_type": pr.campaign_type,
            "category_id": pr.category_id,
            "category_name": cats[pr.category_id].name if pr.category_id in cats else "All Categories",
            "discount_pct": pr.discount_pct,
            "start_date": pr.start_date.isoformat(),
            "end_date": pr.end_date.isoformat(),
            "status": pr.status,
            "baseline_daily_units": pr.baseline_daily_units,
            "promo_daily_units": pr.promo_daily_units,
            "uplift_pct": pr.uplift_pct,
            "revenue_generated_inr": pr.revenue_generated_inr,
            "gross_margin_impact_pct": pr.gross_margin_impact_pct,
        }
        for pr in promos
    ]

    return {
        "pricing_ledger": pricing_rows,
        "promotions": promo_list,
        "summary": {
            "avg_realized_margin_pct": round(sum(r["gross_margin_pct"] for r in pricing_rows) / max(len(pricing_rows), 1), 2),
            "avg_discount_pct": round(sum(r["discount_pct"] for r in pricing_rows) / max(len(pricing_rows), 1), 1),
            "margin_breach_count": sum(1 for r in pricing_rows if r["margin_status"] == "MARGIN_BREACH"),
            "active_promotions_count": sum(1 for p in promo_list if p["status"] == "ACTIVE"),
        },
    }


@router.patch("/pricing/{product_id}")
def update_sku_pricing(product_id: int, req: PricingUpdateRequest, db: Session = Depends(get_db)):
    prod = db.query(Product).filter(Product.id == product_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Product SKU not found")

    if req.mrp is not None and req.mrp > 0:
        prod.mrp = round(req.mrp, 2)
    if req.cost_price is not None and req.cost_price > 0:
        prod.cost_price = round(req.cost_price, 2)

    if req.discount_pct is not None:
        prod.discount_pct = max(0.0, min(85.0, round(req.discount_pct, 2)))
        prod.selling_price = round(prod.mrp * (1.0 - prod.discount_pct / 100.0), 2)
    elif req.selling_price is not None and req.selling_price > 0:
        prod.selling_price = min(prod.mrp, round(req.selling_price, 2))
        prod.discount_pct = round(((prod.mrp - prod.selling_price) / max(prod.mrp, 1.0)) * 100.0, 2)

    net_revenue = prod.selling_price / (1.0 + (prod.tax_rate_pct / 100.0))
    prod.gross_margin_pct = round(((net_revenue - prod.cost_price) / max(net_revenue, 1.0)) * 100.0, 2)

    hist = json.loads(prod.price_history_json or "[]")
    hist.insert(0, {
        "date": date(2026, 11, 16).isoformat(),
        "mrp": prod.mrp,
        "selling_price": prod.selling_price,
        "discount_pct": prod.discount_pct,
        "reason": req.reason,
    })
    prod.price_history_json = json.dumps(hist[:10])
    prod.updated_at = datetime.utcnow()
    db.commit()

    return {
        "status": "updated",
        "product_id": prod.id,
        "sku": prod.sku,
        "mrp": prod.mrp,
        "selling_price": prod.selling_price,
        "discount_pct": prod.discount_pct,
        "gross_margin_pct": prod.gross_margin_pct,
    }


@router.post("/promotions")
def create_promotion(req: PromotionCreateRequest, db: Session = Depends(get_db)):
    uplift = round(((req.promo_daily_units - req.baseline_daily_units) / max(req.baseline_daily_units, 1.0)) * 100.0, 1)
    promo = Promotion(
        code=req.code.strip().upper(),
        name=req.name.strip(),
        campaign_type=req.campaign_type,
        category_id=req.category_id,
        discount_pct=req.discount_pct,
        start_date=date.fromisoformat(req.start_date),
        end_date=date.fromisoformat(req.end_date),
        status=req.status,
        baseline_daily_units=req.baseline_daily_units,
        promo_daily_units=req.promo_daily_units,
        uplift_pct=uplift,
        revenue_generated_inr=round(req.promo_daily_units * 1450.0 * 7, 2) if req.status == "ACTIVE" else 0.0,
        gross_margin_impact_pct=round(-req.discount_pct * 0.22, 2),
        is_synthetic=True,
    )
    db.add(promo)
    db.commit()
    db.refresh(promo)
    return {"status": "created", "promotion_id": promo.id, "code": promo.code}
