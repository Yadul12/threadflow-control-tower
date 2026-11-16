import json
from datetime import datetime, date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import (
    Order,
    OrderItem,
    Shipment,
    Carrier,
    Customer,
    Warehouse,
    Product,
    Category,
    Inventory,
    StockMovement,
    ReturnRecord,
    ReturnReason,
    OperationalException,
    Supplier,
    PurchaseOrder,
)

router = APIRouter(prefix="/api/outbound", tags=["Workspace C: Outbound Order & Fulfilment"])


class OrderStatusTransitionRequest(BaseModel):
    status: str  # ALLOCATED, PICKING, PACKED, DISPATCHED, IN_TRANSIT, DELIVERED, DELAYED, CANCELLED
    carrier_id: Optional[int] = None
    cancellation_reason: Optional[str] = None


class ShipmentUpdateRequest(BaseModel):
    status: str  # MANIFESTED, PICKED_UP, IN_TRANSIT, HUB_REACHED, OUT_FOR_DELIVERY, DELIVERED, DELIVERY_EXCEPTION
    carrier_id: Optional[int] = None
    current_hub: Optional[str] = None
    delay_hours: Optional[float] = None
    exception_code: Optional[str] = None
    note: Optional[str] = None


class ReturnUpdateRequest(BaseModel):
    status: str  # APPROVED, QC_PASSED, QC_FAILED, EXCHANGE_DISPATCHED, REFUND_PROCESSED, CLOSED
    qc_notes: Optional[str] = None
    refund_status: Optional[str] = None  # PENDING, INITIATED, PROCESSED, NOT_APPLICABLE
    restock_eligible: Optional[bool] = None


class ExceptionUpdateRequest(BaseModel):
    status: Optional[str] = None  # OPEN, IN_PROGRESS, ESCALATED, RESOLVED
    severity: Optional[str] = None
    assigned_to: Optional[str] = None
    assigned_role: Optional[str] = None
    root_cause: Optional[str] = None
    resolution_notes: Optional[str] = None


class ExceptionCreateRequest(BaseModel):
    domain: str
    severity: str = "HIGH"
    title: str
    description: str
    warehouse_id: Optional[int] = None
    supplier_id: Optional[int] = None
    product_id: Optional[int] = None
    assigned_to: str = "Operations Queue"
    assigned_role: str = "Warehouse Ops Manager"
    financial_impact_inr: float = 50000.0


# --- 1. ORDER MANAGEMENT ---
@router.get("/orders")
def list_orders(
    status: Optional[str] = None,
    warehouse_id: Optional[int] = None,
    sla_breached: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Order)
    if status and status != "ALL":
        q = q.filter(Order.status == status)
    if warehouse_id:
        q = q.filter(Order.warehouse_id == warehouse_id)
    if sla_breached is not None:
        q = q.filter(Order.sla_breached == sla_breached)

    orders = q.order_by(Order.id.desc()).all()
    customers = {c.id: c for c in db.query(Customer).all()}
    warehouses = {w.id: w for w in db.query(Warehouse).all()}
    products = {p.id: p for p in db.query(Product).all()}
    shipments = {s.order_id: s for s in db.query(Shipment).all()}

    results = []
    for o in orders:
        cust = customers.get(o.customer_id)
        wh = warehouses.get(o.warehouse_id)
        sh = shipments.get(o.id)
        results.append({
            "id": o.id,
            "order_number": o.order_number,
            "customer_name": cust.full_name if cust else "",
            "customer_city": cust.city if cust else "",
            "customer_tier": cust.tier if cust else "STANDARD",
            "warehouse_id": o.warehouse_id,
            "warehouse_code": wh.code if wh else "",
            "warehouse_name": wh.name if wh else "",
            "order_date": o.order_date.strftime("%Y-%m-%d %H:%M"),
            "status": o.status,
            "payment_mode": o.payment_mode,
            "total_items": o.total_items,
            "total_amount_inr": o.total_amount_inr,
            "processing_hours": o.processing_hours,
            "sla_breached": o.sla_breached,
            "promised_delivery_date": o.promised_delivery_date.isoformat(),
            "actual_delivery_date": o.actual_delivery_date.isoformat() if o.actual_delivery_date else None,
            "cancellation_reason": o.cancellation_reason,
            "awb_number": sh.awb_number if sh else None,
            "shipment_status": sh.status if sh else None,
            "items": [
                {
                    "id": item.id,
                    "product_id": item.product_id,
                    "sku": products[item.product_id].sku if item.product_id in products else "",
                    "product_name": products[item.product_id].name if item.product_id in products else "",
                    "quantity": item.quantity,
                    "net_price_inr": item.net_price_inr,
                }
                for item in o.items
            ],
        })

    all_orders = db.query(Order).all()
    return {
        "orders": results,
        "summary": {
            "total_orders": len(all_orders),
            "pending_fulfilment_count": sum(1 for o in all_orders if o.status in ("PENDING", "ALLOCATED", "PICKING", "PACKED")),
            "in_transit_count": sum(1 for o in all_orders if o.status in ("DISPATCHED", "IN_TRANSIT", "DELAYED")),
            "delivered_count": sum(1 for o in all_orders if o.status == "DELIVERED"),
            "sla_breached_count": sum(1 for o in all_orders if o.sla_breached),
            "avg_processing_hours": round(sum(o.processing_hours for o in all_orders) / max(len(all_orders), 1), 1),
        },
    }


@router.patch("/orders/{order_id}/status")
def transition_order_status(order_id: int, req: OrderStatusTransitionRequest, db: Session = Depends(get_db)):
    order_obj = db.query(Order).filter(Order.id == order_id).first()
    if not order_obj:
        raise HTTPException(status_code=404, detail="Order not found")

    prev_status = order_obj.status
    order_obj.status = req.status
    now_dt = datetime(2026, 11, 16, 14, 0, 0)

    for oi in order_obj.items:
        oi.fulfilment_status = req.status

    if req.status == "CANCELLED":
        order_obj.cancellation_reason = req.cancellation_reason or "Cancelled by operations control desk"
        # Release reserved inventory
        for oi in order_obj.items:
            inv = db.query(Inventory).filter(
                Inventory.product_id == oi.product_id,
                Inventory.warehouse_id == order_obj.warehouse_id,
            ).first()
            if inv and inv.reserved_qty >= oi.quantity:
                inv.reserved_qty -= oi.quantity
                inv.available_qty = max(0, inv.on_hand_qty - inv.reserved_qty)

    elif req.status in ("PACKED", "DISPATCHED", "IN_TRANSIT", "DELIVERED"):
        sh = db.query(Shipment).filter(Shipment.order_id == order_obj.id).first()
        carrier_id = req.carrier_id or 1
        carrier = db.query(Carrier).filter(Carrier.id == carrier_id).first() or db.query(Carrier).first()
        wh = db.query(Warehouse).filter(Warehouse.id == order_obj.warehouse_id).first()

        if not sh:
            awb = f"AWB{carrier.code[-4:]}{900000 + order_obj.id}"
            sh = Shipment(
                awb_number=awb,
                order_id=order_obj.id,
                warehouse_id=order_obj.warehouse_id,
                carrier_id=carrier.id,
                status="MANIFESTED" if req.status == "PACKED" else ("PICKED_UP" if req.status == "DISPATCHED" else req.status),
                pick_started_at=now_dt - timedelta(hours=3),
                pack_completed_at=now_dt - timedelta(hours=1),
                dispatched_at=now_dt if req.status in ("DISPATCHED", "IN_TRANSIT", "DELIVERED") else None,
                promised_delivery_date=order_obj.promised_delivery_date,
                actual_delivery_date=date(2026, 11, 16) if req.status == "DELIVERED" else None,
                dispatch_hours=order_obj.processing_hours or 6.5,
                delay_hours=0.0,
                on_time=not order_obj.sla_breached,
                current_hub=f"{wh.city if wh else 'Origin'} Fulfilment Dock",
                tracking_timeline_json=json.dumps([
                    {"step": f"STATUS_{req.status}", "timestamp": now_dt.strftime("%Y-%m-%d %H:%M"), "location": wh.code if wh else "FC", "note": f"Order advanced to {req.status}"}
                ]),
                is_synthetic=True,
            )
            db.add(sh)
        else:
            if req.status == "DISPATCHED":
                sh.status = "PICKED_UP"
                sh.dispatched_at = now_dt
                order_obj.actual_dispatch_at = now_dt
            elif req.status == "DELIVERED":
                sh.status = "DELIVERED"
                sh.actual_delivery_date = date(2026, 11, 16)
                order_obj.actual_delivery_date = date(2026, 11, 16)
            else:
                sh.status = req.status

    db.commit()
    return {
        "status": "updated",
        "order_id": order_obj.id,
        "order_number": order_obj.order_number,
        "previous_status": prev_status,
        "new_status": order_obj.status,
    }


# --- 2. FULFILMENT & SHIPMENT MANAGEMENT ---
@router.get("/fulfilment")
def get_fulfilment_workspace(
    warehouse_id: Optional[int] = None,
    shipment_status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    warehouses = db.query(Warehouse).all()
    carriers = db.query(Carrier).all()
    wh_map = {w.id: w for w in warehouses}
    cr_map = {c.id: c for c in carriers}
    orders = {o.id: o for o in db.query(Order).all()}

    q = db.query(Shipment)
    if warehouse_id:
        q = q.filter(Shipment.warehouse_id == warehouse_id)
    if shipment_status and shipment_status != "ALL":
        q = q.filter(Shipment.status == shipment_status)

    shipments = q.order_by(Shipment.id.desc()).all()
    sh_list = []
    for sh in shipments:
        ord_obj = orders.get(sh.order_id)
        wh = wh_map.get(sh.warehouse_id)
        cr = cr_map.get(sh.carrier_id)
        sh_list.append({
            "id": sh.id,
            "awb_number": sh.awb_number,
            "order_id": sh.order_id,
            "order_number": ord_obj.order_number if ord_obj else "",
            "order_status": ord_obj.status if ord_obj else "",
            "warehouse_id": sh.warehouse_id,
            "warehouse_code": wh.code if wh else "",
            "warehouse_name": wh.name if wh else "",
            "carrier_id": sh.carrier_id,
            "carrier_name": cr.name if cr else "",
            "service_type": cr.service_type if cr else "",
            "status": sh.status,
            "pick_started_at": sh.pick_started_at.strftime("%Y-%m-%d %H:%M") if sh.pick_started_at else None,
            "pack_completed_at": sh.pack_completed_at.strftime("%Y-%m-%d %H:%M") if sh.pack_completed_at else None,
            "dispatched_at": sh.dispatched_at.strftime("%Y-%m-%d %H:%M") if sh.dispatched_at else None,
            "promised_delivery_date": sh.promised_delivery_date.isoformat(),
            "actual_delivery_date": sh.actual_delivery_date.isoformat() if sh.actual_delivery_date else None,
            "dispatch_hours": sh.dispatch_hours,
            "delay_hours": sh.delay_hours,
            "on_time": sh.on_time,
            "current_hub": sh.current_hub,
            "exception_code": sh.exception_code,
            "tracking_timeline": json.loads(sh.tracking_timeline_json or "[]"),
        })

    # Active wave queue (orders in PENDING, ALLOCATED, PICKING, PACKED)
    wave_orders = [
        {
            "id": o.id,
            "order_number": o.order_number,
            "warehouse_code": wh_map[o.warehouse_id].code if o.warehouse_id in wh_map else "",
            "status": o.status,
            "total_items": o.total_items,
            "processing_hours": o.processing_hours,
            "sla_breached": o.sla_breached,
        }
        for o in orders.values()
        if o.status in ("PENDING", "ALLOCATED", "PICKING", "PACKED")
    ]

    return {
        "warehouses": [
            {
                "id": w.id,
                "code": w.code,
                "name": w.name,
                "city": w.city,
                "active_pickers": w.active_pickers,
                "avg_processing_hours": w.avg_processing_hours,
                "sla_dispatch_hours": w.sla_dispatch_hours,
                "bottleneck_status": w.bottleneck_status,
                "manager_name": w.manager_name,
            }
            for w in warehouses
        ],
        "carriers": [
            {
                "id": c.id,
                "code": c.code,
                "name": c.name,
                "service_type": c.service_type,
                "avg_transit_days": c.avg_transit_days,
                "on_time_rate_pct": c.on_time_rate_pct,
                "rto_rate_pct": c.rto_rate_pct,
                "active_shipments": c.active_shipments,
            }
            for c in carriers
        ],
        "wave_queue": wave_orders,
        "shipments": sh_list,
    }


@router.patch("/shipments/{shipment_id}")
def update_shipment(shipment_id: int, req: ShipmentUpdateRequest, db: Session = Depends(get_db)):
    sh = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not sh:
        raise HTTPException(status_code=404, detail="Shipment not found")

    sh.status = req.status
    if req.carrier_id is not None:
        sh.carrier_id = req.carrier_id
    if req.current_hub is not None:
        sh.current_hub = req.current_hub
    if req.delay_hours is not None:
        sh.delay_hours = req.delay_hours
        sh.on_time = req.delay_hours <= 0
    if req.exception_code is not None:
        sh.exception_code = req.exception_code

    ord_obj = db.query(Order).filter(Order.id == sh.order_id).first()
    if req.status == "DELIVERED":
        sh.actual_delivery_date = date(2026, 11, 16)
        sh.exception_code = None
        if ord_obj:
            ord_obj.status = "DELIVERED"
            ord_obj.actual_delivery_date = date(2026, 11, 16)
    elif req.status == "DELIVERY_EXCEPTION" and ord_obj:
        ord_obj.status = "DELAYED"
        ord_obj.sla_breached = True

    timeline = json.loads(sh.tracking_timeline_json or "[]")
    timeline.append({
        "step": req.status,
        "timestamp": datetime(2026, 11, 16, 14, 5).strftime("%Y-%m-%d %H:%M"),
        "location": sh.current_hub,
        "note": req.note or f"Shipment status updated to {req.status}",
    })
    sh.tracking_timeline_json = json.dumps(timeline)
    db.commit()

    return {
        "status": "updated",
        "shipment_id": sh.id,
        "awb_number": sh.awb_number,
        "shipment_status": sh.status,
        "on_time": sh.on_time,
        "delay_hours": sh.delay_hours,
    }


# --- 3. DELIVERY INTELLIGENCE ---
@router.get("/delivery-intelligence")
def get_delivery_intelligence(db: Session = Depends(get_db)):
    shipments = db.query(Shipment).all()
    warehouses = {w.id: w for w in db.query(Warehouse).all()}
    carriers = {c.id: c for c in db.query(Carrier).all()}
    orders = {o.id: o for o in db.query(Order).all()}

    wh_delivery = {}
    for sh in shipments:
        wh = warehouses.get(sh.warehouse_id)
        w_code = wh.code if wh else "UNKNOWN"
        entry = wh_delivery.setdefault(w_code, {
            "warehouse_code": w_code,
            "warehouse_name": wh.name if wh else "",
            "bottleneck_status": wh.bottleneck_status if wh else "",
            "total_shipments": 0,
            "on_time_count": 0,
            "delayed_count": 0,
            "exception_count": 0,
            "sum_dispatch_hours": 0.0,
            "sum_delay_hours": 0.0,
        })
        entry["total_shipments"] += 1
        if sh.on_time:
            entry["on_time_count"] += 1
        else:
            entry["delayed_count"] += 1
        if sh.status == "DELIVERY_EXCEPTION":
            entry["exception_count"] += 1
        entry["sum_dispatch_hours"] += sh.dispatch_hours
        entry["sum_delay_hours"] += sh.delay_hours

    warehouse_sla_breakdown = []
    for w_code, st in wh_delivery.items():
        tot = max(st["total_shipments"], 1)
        warehouse_sla_breakdown.append({
            "warehouse_code": w_code,
            "warehouse_name": st["warehouse_name"],
            "bottleneck_status": st["bottleneck_status"],
            "total_shipments": st["total_shipments"],
            "on_time_delivery_pct": round((st["on_time_count"] / tot) * 100.0, 1),
            "delayed_count": st["delayed_count"],
            "exception_count": st["exception_count"],
            "avg_dispatch_hours": round(st["sum_dispatch_hours"] / tot, 1),
            "avg_delay_hours": round(st["sum_delay_hours"] / tot, 1),
        })

    delayed_list = []
    for sh in shipments:
        if not sh.on_time or sh.status == "DELIVERY_EXCEPTION":
            ord_obj = orders.get(sh.order_id)
            wh = warehouses.get(sh.warehouse_id)
            cr = carriers.get(sh.carrier_id)
            delayed_list.append({
                "shipment_id": sh.id,
                "awb_number": sh.awb_number,
                "order_number": ord_obj.order_number if ord_obj else "",
                "warehouse_code": wh.code if wh else "",
                "carrier_name": cr.name if cr else "",
                "status": sh.status,
                "promised_delivery_date": sh.promised_delivery_date.isoformat(),
                "actual_delivery_date": sh.actual_delivery_date.isoformat() if sh.actual_delivery_date else "In Transit / Held",
                "dispatch_hours": sh.dispatch_hours,
                "delay_hours": sh.delay_hours,
                "current_hub": sh.current_hub,
                "exception_code": sh.exception_code or "SLA_LATENCY",
            })

    return {
        "warehouse_sla_breakdown": warehouse_sla_breakdown,
        "delayed_and_exception_shipments": delayed_list,
    }


# --- 4. RETURNS & EXCHANGES ---
@router.get("/returns")
def list_returns_and_exchanges(
    status: Optional[str] = None,
    reason_category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    returns = db.query(ReturnRecord).order_by(ReturnRecord.id.desc()).all()
    reasons = {r.id: r for r in db.query(ReturnReason).all()}
    products = {p.id: p for p in db.query(Product).all()}
    categories = {c.id: c for c in db.query(Category).all()}
    orders = {o.id: o for o in db.query(Order).all()}
    customers = {c.id: c for c in db.query(Customer).all()}
    warehouses = {w.id: w for w in db.query(Warehouse).all()}

    items = []
    reason_breakdown = {}
    sku_return_counts = {}

    for r in returns:
        rr = reasons.get(r.return_reason_id)
        prod = products.get(r.product_id)
        cat = categories.get(prod.category_id) if prod else None
        ord_obj = orders.get(r.order_id)
        cust = customers.get(r.customer_id)
        wh = warehouses.get(r.warehouse_id)

        r_cat = rr.category if rr else "OTHER"
        reason_breakdown[r_cat] = reason_breakdown.get(r_cat, 0) + 1

        if prod:
            st = sku_return_counts.setdefault(prod.sku, {
                "sku": prod.sku,
                "product_name": prod.name,
                "category_name": cat.name if cat else "",
                "completeness_score": prod.completeness_score,
                "has_size_chart": prod.has_size_chart,
                "return_count": 0,
                "top_reason": r_cat,
            })
            st["return_count"] += 1

        if status and status != "ALL" and r.status != status:
            continue
        if reason_category and reason_category != "ALL" and r_cat != reason_category:
            continue

        items.append({
            "id": r.id,
            "rma_number": r.rma_number,
            "order_number": ord_obj.order_number if ord_obj else "",
            "customer_name": cust.full_name if cust else "",
            "warehouse_code": wh.code if wh else "",
            "sku": prod.sku if prod else "",
            "product_name": prod.name if prod else "",
            "category_name": cat.name if cat else "",
            "request_type": r.request_type,
            "status": r.status,
            "reason_code": rr.code if rr else "",
            "reason_category": r_cat,
            "reason_description": rr.description if rr else "",
            "recommended_action": rr.recommended_action if rr else "",
            "requested_at": r.requested_at.strftime("%Y-%m-%d %H:%M"),
            "resolved_at": r.resolved_at.strftime("%Y-%m-%d %H:%M") if r.resolved_at else None,
            "qc_notes": r.qc_notes,
            "refund_amount_inr": r.refund_amount_inr,
            "refund_status": r.refund_status,
            "exchange_order_number": r.exchange_order_number,
            "restock_eligible": r.restock_eligible,
        })

    top_returned_skus = sorted(sku_return_counts.values(), key=lambda x: x["return_count"], reverse=True)[:10]

    return {
        "returns": items,
        "reason_breakdown": [
            {"category": k, "count": v, "share_pct": round((v / max(len(returns), 1)) * 100.0, 1)}
            for k, v in sorted(reason_breakdown.items(), key=lambda x: x[1], reverse=True)
        ],
        "product_return_trends": top_returned_skus,
    }


@router.patch("/returns/{return_id}")
def update_return_case(return_id: int, req: ReturnUpdateRequest, db: Session = Depends(get_db)):
    ret = db.query(ReturnRecord).filter(ReturnRecord.id == return_id).first()
    if not ret:
        raise HTTPException(status_code=404, detail="Return RMA record not found")

    prev_status = ret.status
    ret.status = req.status
    if req.qc_notes is not None:
        ret.qc_notes = req.qc_notes
    if req.restock_eligible is not None:
        ret.restock_eligible = req.restock_eligible

    if req.status == "QC_PASSED":
        ret.restock_eligible = True
        ret.qc_notes = req.qc_notes or "QC Passed: garment steam-pressed, barcode verified, restocked to active bin."
        if ret.request_type == "RETURN_REFUND":
            ret.refund_status = "INITIATED"
        # Restock 1 unit back to warehouse inventory
        inv = db.query(Inventory).filter(
            Inventory.product_id == ret.product_id,
            Inventory.warehouse_id == ret.warehouse_id,
        ).first()
        if inv:
            inv.on_hand_qty += 1
            inv.available_qty = max(0, inv.on_hand_qty - inv.reserved_qty)
            db.add(StockMovement(
                product_id=ret.product_id,
                warehouse_id=ret.warehouse_id,
                movement_type="RETURN_RESTOCK",
                quantity_delta=1,
                reference_code=ret.rma_number,
                performed_by="Reverse Logistics QC Desk",
                notes=f"Restocked after QC_PASSED on {ret.rma_number}",
            ))
    elif req.status == "QC_FAILED":
        ret.restock_eligible = False
        ret.qc_notes = req.qc_notes or "QC Failed: defect confirmed; quarantined for supplier debit note."
    elif req.status == "REFUND_PROCESSED":
        ret.refund_status = "PROCESSED"
        ret.resolved_at = datetime.utcnow()
    elif req.status == "EXCHANGE_DISPATCHED":
        ret.exchange_order_number = ret.exchange_order_number or f"EXCH-2026-{9500 + ret.id}"
        ret.resolved_at = datetime.utcnow()
    elif req.status == "CLOSED":
        if ret.request_type == "RETURN_REFUND":
            ret.refund_status = "PROCESSED"
        ret.resolved_at = datetime.utcnow()

    if req.refund_status is not None:
        ret.refund_status = req.refund_status

    db.commit()
    return {
        "status": "updated",
        "return_id": ret.id,
        "rma_number": ret.rma_number,
        "previous_status": prev_status,
        "new_status": ret.status,
        "refund_status": ret.refund_status,
        "exchange_order_number": ret.exchange_order_number,
    }


# --- 5. OPERATIONS EXCEPTIONS COMMAND QUEUE ---
@router.get("/exceptions")
def list_operational_exceptions(
    domain: Optional[str] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(OperationalException)
    if domain and domain != "ALL":
        q = q.filter(OperationalException.domain == domain)
    if status and status != "ALL":
        q = q.filter(OperationalException.status == status)
    if severity and severity != "ALL":
        q = q.filter(OperationalException.severity == severity)

    exceptions = q.order_by(OperationalException.id.asc()).all()
    warehouses = {w.id: w for w in db.query(Warehouse).all()}
    suppliers = {s.id: s for s in db.query(Supplier).all()}
    products = {p.id: p for p in db.query(Product).all()}
    pos = {p.id: p for p in db.query(PurchaseOrder).all()}
    shipments = {s.id: s for s in db.query(Shipment).all()}

    items = []
    for ex in exceptions:
        wh = warehouses.get(ex.warehouse_id)
        sup = suppliers.get(ex.supplier_id)
        prod = products.get(ex.product_id)
        po = pos.get(ex.po_id)
        sh = shipments.get(ex.shipment_id)

        items.append({
            "id": ex.id,
            "exception_code": ex.exception_code,
            "domain": ex.domain,
            "severity": ex.severity,
            "status": ex.status,
            "title": ex.title,
            "description": ex.description,
            "warehouse_code": wh.code if wh else None,
            "supplier_name": sup.name if sup else None,
            "sku": prod.sku if prod else None,
            "po_number": po.po_number if po else None,
            "awb_number": sh.awb_number if sh else None,
            "assigned_to": ex.assigned_to,
            "assigned_role": ex.assigned_role,
            "root_cause": ex.root_cause,
            "resolution_notes": ex.resolution_notes,
            "financial_impact_inr": ex.financial_impact_inr,
            "detected_at": ex.detected_at.strftime("%Y-%m-%d %H:%M"),
            "resolved_at": ex.resolved_at.strftime("%Y-%m-%d %H:%M") if ex.resolved_at else None,
        })

    all_ex = db.query(OperationalException).all()
    return {
        "exceptions": items,
        "summary": {
            "total": len(all_ex),
            "open_count": sum(1 for e in all_ex if e.status == "OPEN"),
            "in_progress_count": sum(1 for e in all_ex if e.status == "IN_PROGRESS"),
            "escalated_count": sum(1 for e in all_ex if e.status == "ESCALATED"),
            "resolved_count": sum(1 for e in all_ex if e.status == "RESOLVED"),
            "total_financial_exposure_inr": round(sum(e.financial_impact_inr for e in all_ex if e.status != "RESOLVED"), 2),
        },
    }


@router.patch("/exceptions/{exception_id}")
def update_operational_exception(exception_id: int, req: ExceptionUpdateRequest, db: Session = Depends(get_db)):
    ex = db.query(OperationalException).filter(OperationalException.id == exception_id).first()
    if not ex:
        raise HTTPException(status_code=404, detail="Operational exception not found")

    if req.status is not None:
        ex.status = req.status
        if req.status == "RESOLVED":
            ex.resolved_at = datetime.utcnow()
    if req.severity is not None:
        ex.severity = req.severity
    if req.assigned_to is not None:
        ex.assigned_to = req.assigned_to
    if req.assigned_role is not None:
        ex.assigned_role = req.assigned_role
    if req.root_cause is not None:
        ex.root_cause = req.root_cause
    if req.resolution_notes is not None:
        ex.resolution_notes = req.resolution_notes

    ex.updated_at = datetime.utcnow()
    db.commit()
    return {
        "status": "updated",
        "exception_id": ex.id,
        "exception_code": ex.exception_code,
        "new_status": ex.status,
        "assigned_to": ex.assigned_to,
        "assigned_role": ex.assigned_role,
    }


@router.post("/exceptions")
def create_operational_exception(req: ExceptionCreateRequest, db: Session = Depends(get_db)):
    next_id = db.query(OperationalException).count() + 1
    code = f"EXC-2026-{next_id:03d}"
    while db.query(OperationalException).filter(OperationalException.exception_code == code).first():
        next_id += 1
        code = f"EXC-2026-{next_id:03d}"

    ex = OperationalException(
        exception_code=code,
        domain=req.domain,
        severity=req.severity,
        status="OPEN",
        title=req.title,
        description=req.description,
        warehouse_id=req.warehouse_id,
        supplier_id=req.supplier_id,
        product_id=req.product_id,
        assigned_to=req.assigned_to,
        assigned_role=req.assigned_role,
        financial_impact_inr=req.financial_impact_inr,
        is_synthetic=True,
    )
    db.add(ex)
    db.commit()
    db.refresh(ex)
    return {"status": "created", "exception_id": ex.id, "exception_code": ex.exception_code}
