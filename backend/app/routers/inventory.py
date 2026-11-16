import math
from datetime import datetime, date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import (
    Inventory,
    StockMovement,
    Product,
    Category,
    Supplier,
    Warehouse,
    PurchaseOrder,
    PurchaseOrderItem,
)

router = APIRouter(prefix="/api/inventory", tags=["Workspace B: Inventory Intelligence"])


class StockAdjustRequest(BaseModel):
    inventory_id: int
    quantity_delta: int
    movement_type: str = "CYCLE_COUNT_ADJ"
    notes: str = "Manual inventory ledger adjustment"
    performed_by: str = "Inventory Planner"


class ReplenishOrderRequest(BaseModel):
    override_qty: Optional[int] = None
    created_by: str = "Inventory Planner"


def recalculate_inventory_metrics(inv: Inventory, lead_time_days: float):
    inv.available_qty = max(0, inv.on_hand_qty - inv.reserved_qty)
    inv.forecast_daily_demand = round(0.60 * inv.avg_daily_sales_7d + 0.40 * inv.avg_daily_sales_30d, 2)
    inv.safety_stock_qty = int(math.ceil(inv.forecast_daily_demand * max(5.0, 0.35 * lead_time_days)))
    inv.reorder_point_qty = int(math.ceil((inv.forecast_daily_demand * lead_time_days) + inv.safety_stock_qty))
    inv.days_of_cover = round(inv.available_qty / max(inv.forecast_daily_demand, 0.1), 1)

    if inv.available_qty == 0:
        inv.stock_status = "STOCKOUT"
    elif inv.available_qty <= inv.reorder_point_qty:
        inv.stock_status = "LOW_STOCK"
    elif inv.days_of_cover > 65.0 and (inv.age_bucket_61_90_qty + inv.age_bucket_90_plus_qty) > 40:
        inv.stock_status = "EXCESS"
    elif inv.avg_daily_sales_30d < 1.0 and inv.on_hand_qty > 70:
        inv.stock_status = "SLOW_MOVING"
    else:
        inv.stock_status = "HEALTHY"


# --- 1. INVENTORY OVERVIEW ---
@router.get("/overview")
def get_inventory_overview(
    warehouse_id: Optional[int] = None,
    category_id: Optional[int] = None,
    stock_status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    warehouses = db.query(Warehouse).all()
    wh_map = {w.id: w for w in warehouses}
    products = {p.id: p for p in db.query(Product).all()}
    categories = {c.id: c for c in db.query(Category).all()}
    suppliers = {s.id: s for s in db.query(Supplier).all()}

    q = db.query(Inventory)
    if warehouse_id:
        q = q.filter(Inventory.warehouse_id == warehouse_id)
    if stock_status and stock_status != "ALL":
        q = q.filter(Inventory.stock_status == stock_status)

    inv_rows = q.order_by(Inventory.available_qty.asc(), Inventory.id.asc()).all()

    items = []
    for inv in inv_rows:
        prod = products.get(inv.product_id)
        if not prod:
            continue
        if category_id and prod.category_id != category_id:
            continue
        if search:
            term = search.lower()
            if term not in prod.sku.lower() and term not in prod.name.lower() and term not in prod.brand.lower():
                continue

        wh = wh_map.get(inv.warehouse_id)
        cat = categories.get(prod.category_id)
        sup = suppliers.get(prod.supplier_id)
        items.append({
            "id": inv.id,
            "product_id": prod.id,
            "sku": prod.sku,
            "style_code": prod.style_code,
            "product_name": prod.name,
            "brand": prod.brand,
            "category_name": cat.name if cat else "",
            "supplier_name": sup.name if sup else "",
            "warehouse_id": inv.warehouse_id,
            "warehouse_code": wh.code if wh else "",
            "warehouse_name": wh.name if wh else "",
            "on_hand_qty": inv.on_hand_qty,
            "reserved_qty": inv.reserved_qty,
            "available_qty": inv.available_qty,
            "damaged_qty": inv.damaged_qty,
            "in_transit_qty": inv.in_transit_qty,
            "safety_stock_qty": inv.safety_stock_qty,
            "reorder_point_qty": inv.reorder_point_qty,
            "days_of_cover": inv.days_of_cover,
            "stock_status": inv.stock_status,
            "cost_price": prod.cost_price,
            "inventory_value_inr": round(inv.on_hand_qty * prod.cost_price, 2),
            "age_bucket_0_30_qty": inv.age_bucket_0_30_qty,
            "age_bucket_31_60_qty": inv.age_bucket_31_60_qty,
            "age_bucket_61_90_qty": inv.age_bucket_61_90_qty,
            "age_bucket_90_plus_qty": inv.age_bucket_90_plus_qty,
            "last_received_date": inv.last_received_date.isoformat() if inv.last_received_date else None,
        })

    # Warehouse summary cards
    all_inv = db.query(Inventory).all()
    wh_summary = []
    for w in warehouses:
        w_inv = [i for i in all_inv if i.warehouse_id == w.id]
        wh_summary.append({
            "id": w.id,
            "code": w.code,
            "name": w.name,
            "city": w.city,
            "region": w.region,
            "capacity_units": w.capacity_units,
            "utilized_units": w.utilized_units,
            "utilization_pct": round((w.utilized_units / max(w.capacity_units, 1)) * 100.0, 1),
            "bottleneck_status": w.bottleneck_status,
            "total_on_hand": sum(i.on_hand_qty for i in w_inv),
            "total_reserved": sum(i.reserved_qty for i in w_inv),
            "total_available": sum(i.available_qty for i in w_inv),
            "stockout_skus": sum(1 for i in w_inv if i.stock_status == "STOCKOUT"),
            "low_stock_skus": sum(1 for i in w_inv if i.stock_status == "LOW_STOCK"),
            "excess_skus": sum(1 for i in w_inv if i.stock_status in ("EXCESS", "SLOW_MOVING")),
        })

    movements = db.query(StockMovement).order_by(StockMovement.id.desc()).limit(25).all()
    movement_list = [
        {
            "id": m.id,
            "sku": products[m.product_id].sku if m.product_id in products else "",
            "warehouse_code": wh_map[m.warehouse_id].code if m.warehouse_id in wh_map else "",
            "movement_type": m.movement_type,
            "quantity_delta": m.quantity_delta,
            "reference_code": m.reference_code,
            "performed_by": m.performed_by,
            "notes": m.notes,
            "created_at": m.created_at.strftime("%Y-%m-%d %H:%M"),
        }
        for m in movements
    ]

    return {
        "warehouses": wh_summary,
        "inventory": items,
        "recent_movements": movement_list,
    }


# --- 2. DEMAND FORECASTING & REPLENISHMENT ---
@router.get("/demand-replenishment")
def get_demand_and_replenishment(
    warehouse_id: Optional[int] = None,
    only_actionable: bool = True,
    db: Session = Depends(get_db),
):
    q = db.query(Inventory)
    if warehouse_id:
        q = q.filter(Inventory.warehouse_id == warehouse_id)
    inv_rows = q.all()

    products = {p.id: p for p in db.query(Product).all()}
    warehouses = {w.id: w for w in db.query(Warehouse).all()}
    suppliers = {s.id: s for s in db.query(Supplier).all()}
    categories = {c.id: c for c in db.query(Category).all()}

    recommendations = []
    for inv in inv_rows:
        prod = products.get(inv.product_id)
        if not prod:
            continue
        sup = suppliers.get(prod.supplier_id)
        wh = warehouses.get(inv.warehouse_id)
        cat = categories.get(prod.category_id)
        lead_days = sup.actual_avg_lead_time_days if sup else 18.0
        review_buffer_days = 14.0

        # Recommended Order Quantity formula:
        # ROQ = max(0, ceil(forecast_daily_demand * (lead_time + 14d review cycle) + safety_stock - (available_qty + in_transit_qty)))
        target_stock = math.ceil(inv.forecast_daily_demand * (lead_days + review_buffer_days)) + inv.safety_stock_qty
        net_position = inv.available_qty + inv.in_transit_qty
        recommended_qty = max(0, int(target_stock - net_position))

        needs_replenishment = inv.stock_status in ("STOCKOUT", "LOW_STOCK") or inv.available_qty <= inv.reorder_point_qty
        if only_actionable and not needs_replenishment:
            continue

        if recommended_qty == 0 and needs_replenishment:
            recommended_qty = max(40, inv.reorder_point_qty - inv.available_qty)

        recommendations.append({
            "inventory_id": inv.id,
            "product_id": prod.id,
            "sku": prod.sku,
            "product_name": prod.name,
            "category_name": cat.name if cat else "",
            "warehouse_id": inv.warehouse_id,
            "warehouse_code": wh.code if wh else "",
            "supplier_id": prod.supplier_id,
            "supplier_code": sup.code if sup else "",
            "supplier_name": sup.name if sup else "",
            "supplier_lead_time_days": lead_days,
            "on_hand_qty": inv.on_hand_qty,
            "reserved_qty": inv.reserved_qty,
            "available_qty": inv.available_qty,
            "in_transit_qty": inv.in_transit_qty,
            "avg_daily_sales_7d": inv.avg_daily_sales_7d,
            "avg_daily_sales_30d": inv.avg_daily_sales_30d,
            "forecast_daily_demand": inv.forecast_daily_demand,
            "safety_stock_qty": inv.safety_stock_qty,
            "reorder_point_qty": inv.reorder_point_qty,
            "days_of_cover": inv.days_of_cover,
            "stock_status": inv.stock_status,
            "recommended_order_qty": recommended_qty,
            "unit_cost_inr": prod.cost_price,
            "estimated_po_value_inr": round(recommended_qty * prod.cost_price, 2),
            "urgency": "CRITICAL_STOCKOUT" if inv.available_qty == 0 else ("HIGH_BELOW_SAFETY" if inv.available_qty < inv.safety_stock_qty else "REPLENISH_AT_ROP"),
        })

    recommendations.sort(key=lambda r: (0 if r["urgency"] == "CRITICAL_STOCKOUT" else 1, r["days_of_cover"]))

    return {
        "methodology_documentation": {
            "method_name": "Weighted 7-Day / 30-Day Moving Average Baseline with Lead-Time Safety Stock",
            "forecast_formula": "Forecast Daily Demand = (0.60 × ADS_7d) + (0.40 × ADS_30d)",
            "safety_stock_formula": "Safety Stock = CEIL(Forecast Daily Demand × MAX(5, 0.35 × Supplier Actual Avg Lead Time))",
            "reorder_point_formula": "Reorder Point (ROP) = (Forecast Daily Demand × Supplier Lead Time) + Safety Stock",
            "reorder_qty_formula": "Recommended Order Qty = MAX(0, CEIL(Forecast × (Lead Time + 14d Review Buffer) + Safety Stock - (Available + In-Transit)))",
            "documented_limitations": [
                "Moving averages are backward-looking and lag behind sudden demand inflections or end-of-season cliff drops.",
                "Unadjusted zero-sales days during complete stockouts can censor observed 7-day velocity downward.",
                "Price elasticity from upcoming promotional campaigns is not endogenously modeled without planner override.",
                "No untested ML accuracy claims are made; all replenishment triggers are deterministic and auditable.",
            ],
        },
        "recommendations": recommendations,
        "summary": {
            "actionable_sku_count": len(recommendations),
            "critical_stockout_count": sum(1 for r in recommendations if r["urgency"] == "CRITICAL_STOCKOUT"),
            "total_recommended_units": sum(r["recommended_order_qty"] for r in recommendations),
            "total_replenishment_budget_inr": round(sum(r["estimated_po_value_inr"] for r in recommendations), 2),
        },
    }


@router.post("/replenishment/{inventory_id}/create-po")
def convert_replenishment_to_po(
    inventory_id: int,
    req: ReplenishOrderRequest,
    db: Session = Depends(get_db),
):
    inv = db.query(Inventory).filter(Inventory.id == inventory_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Inventory record not found")

    prod = db.query(Product).filter(Product.id == inv.product_id).first()
    sup = db.query(Supplier).filter(Supplier.id == prod.supplier_id).first()
    wh = db.query(Warehouse).filter(Warehouse.id == inv.warehouse_id).first()

    lead_days = int(round(sup.actual_avg_lead_time_days)) if sup else 18
    target_stock = math.ceil(inv.forecast_daily_demand * (lead_days + 14)) + inv.safety_stock_qty
    default_roq = max(60, int(target_stock - (inv.available_qty + inv.in_transit_qty)))
    order_qty = req.override_qty if (req.override_qty and req.override_qty > 0) else default_roq

    today = date(2026, 11, 16)
    next_num = db.query(PurchaseOrder).count() + 1001
    po_number = f"PO-2026-{next_num}"
    while db.query(PurchaseOrder).filter(PurchaseOrder.po_number == po_number).first():
        next_num += 1
        po_number = f"PO-2026-{next_num}"

    line_val = round(order_qty * prod.cost_price, 2)
    po = PurchaseOrder(
        po_number=po_number,
        supplier_id=sup.id,
        warehouse_id=wh.id,
        category_id=prod.category_id,
        status="ISSUED",
        order_date=today,
        expected_delivery_date=today + timedelta(days=lead_days),
        supplier_acknowledged=False,
        total_ordered_qty=order_qty,
        total_received_qty=0,
        pending_qty=order_qty,
        discrepancy_qty=0,
        total_value_inr=line_val,
        notes=f"Auto-generated from Replenishment Workbench for {prod.sku} (DOC={inv.days_of_cover}d)",
        created_by=req.created_by,
        is_synthetic=True,
    )
    db.add(po)
    db.flush()

    db.add(PurchaseOrderItem(
        po_id=po.id,
        product_id=prod.id,
        ordered_qty=order_qty,
        received_qty=0,
        pending_qty=order_qty,
        rejected_qty=0,
        unit_cost_inr=prod.cost_price,
        line_total_inr=line_val,
    ))

    inv.in_transit_qty += order_qty
    inv.updated_at = datetime.utcnow()
    db.commit()

    return {
        "status": "po_created",
        "po_id": po.id,
        "po_number": po.po_number,
        "sku": prod.sku,
        "warehouse_code": wh.code,
        "ordered_qty": order_qty,
        "total_value_inr": line_val,
        "new_in_transit_qty": inv.in_transit_qty,
    }


# --- 3. INVENTORY PERFORMANCE & AGEING ---
@router.get("/performance")
def get_inventory_performance(db: Session = Depends(get_db)):
    inv_rows = db.query(Inventory).all()
    products = {p.id: p for p in db.query(Product).all()}
    categories = {c.id: c for c in db.query(Category).all()}
    warehouses = {w.id: w for w in db.query(Warehouse).all()}

    cat_stats = {}
    excess_and_slow_items = []
    stockout_items = []

    for inv in inv_rows:
        prod = products.get(inv.product_id)
        if not prod:
            continue
        cat = categories.get(prod.category_id)
        wh = warehouses.get(inv.warehouse_id)
        c_name = cat.name if cat else "Uncategorized"

        st = cat_stats.setdefault(c_name, {
            "category_name": c_name,
            "department": cat.department if cat else "",
            "sku_warehouse_count": 0,
            "total_on_hand_units": 0,
            "total_available_units": 0,
            "stockout_count": 0,
            "excess_count": 0,
            "slow_moving_count": 0,
            "sum_turnover": 0.0,
            "sum_sell_through": 0.0,
            "total_inventory_value_inr": 0.0,
            "aged_60_plus_value_inr": 0.0,
        })

        st["sku_warehouse_count"] += 1
        st["total_on_hand_units"] += inv.on_hand_qty
        st["total_available_units"] += inv.available_qty
        st["sum_turnover"] += inv.turnover_ratio
        st["sum_sell_through"] += inv.sell_through_pct
        st["total_inventory_value_inr"] += inv.on_hand_qty * prod.cost_price
        aged_units = inv.age_bucket_61_90_qty + inv.age_bucket_90_plus_qty
        st["aged_60_plus_value_inr"] += aged_units * prod.cost_price

        if inv.stock_status == "STOCKOUT":
            st["stockout_count"] += 1
            stockout_items.append({
                "inventory_id": inv.id,
                "sku": prod.sku,
                "product_name": prod.name,
                "category_name": c_name,
                "warehouse_code": wh.code if wh else "",
                "on_hand_qty": inv.on_hand_qty,
                "reserved_qty": inv.reserved_qty,
                "in_transit_qty": inv.in_transit_qty,
                "forecast_daily_demand": inv.forecast_daily_demand,
                "estimated_daily_revenue_loss_inr": round(inv.forecast_daily_demand * prod.selling_price, 2),
            })
        elif inv.stock_status in ("EXCESS", "SLOW_MOVING"):
            if inv.stock_status == "EXCESS":
                st["excess_count"] += 1
            else:
                st["slow_moving_count"] += 1
            excess_and_slow_items.append({
                "inventory_id": inv.id,
                "sku": prod.sku,
                "product_name": prod.name,
                "category_name": c_name,
                "warehouse_code": wh.code if wh else "",
                "stock_status": inv.stock_status,
                "on_hand_qty": inv.on_hand_qty,
                "days_of_cover": inv.days_of_cover,
                "turnover_ratio": inv.turnover_ratio,
                "sell_through_pct": inv.sell_through_pct,
                "age_61_90_qty": inv.age_bucket_61_90_qty,
                "age_90_plus_qty": inv.age_bucket_90_plus_qty,
                "aged_value_inr": round(aged_units * prod.cost_price, 2),
                "recommended_markdown_pct": 30.0 if inv.age_bucket_90_plus_qty > 40 else 20.0,
            })

    category_performance = []
    for c_name, st in cat_stats.items():
        cnt = max(st["sku_warehouse_count"], 1)
        category_performance.append({
            "category_name": c_name,
            "department": st["department"],
            "sku_warehouse_count": st["sku_warehouse_count"],
            "total_on_hand_units": st["total_on_hand_units"],
            "total_available_units": st["total_available_units"],
            "stockout_rate_pct": round((st["stockout_count"] / cnt) * 100.0, 1),
            "avg_turnover_ratio": round(st["sum_turnover"] / cnt, 2),
            "avg_sell_through_pct": round(st["sum_sell_through"] / cnt, 1),
            "total_inventory_value_inr": round(st["total_inventory_value_inr"], 2),
            "aged_60_plus_value_inr": round(st["aged_60_plus_value_inr"], 2),
            "excess_and_slow_count": st["excess_count"] + st["slow_moving_count"],
        })

    excess_and_slow_items.sort(key=lambda x: x["aged_value_inr"], reverse=True)
    stockout_items.sort(key=lambda x: x["estimated_daily_revenue_loss_inr"], reverse=True)

    return {
        "category_performance": category_performance,
        "excess_and_slow_moving": excess_and_slow_items,
        "stockout_analysis": stockout_items,
    }


@router.post("/adjust")
def adjust_inventory_stock(req: StockAdjustRequest, db: Session = Depends(get_db)):
    inv = db.query(Inventory).filter(Inventory.id == req.inventory_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Inventory record not found")

    prod = db.query(Product).filter(Product.id == inv.product_id).first()
    sup = db.query(Supplier).filter(Supplier.id == prod.supplier_id).first() if prod else None
    lead_time = sup.actual_avg_lead_time_days if sup else 18.0

    new_on_hand = max(0, inv.on_hand_qty + req.quantity_delta)
    actual_delta = new_on_hand - inv.on_hand_qty
    inv.on_hand_qty = new_on_hand
    inv.age_bucket_0_30_qty = max(0, inv.age_bucket_0_30_qty + actual_delta)

    recalculate_inventory_metrics(inv, lead_time)
    inv.updated_at = datetime.utcnow()

    db.add(StockMovement(
        product_id=inv.product_id,
        warehouse_id=inv.warehouse_id,
        movement_type=req.movement_type,
        quantity_delta=actual_delta,
        reference_code=f"ADJ-{datetime.utcnow().strftime('%H%M%S')}",
        performed_by=req.performed_by,
        notes=req.notes,
    ))
    db.commit()

    return {
        "status": "adjusted",
        "inventory_id": inv.id,
        "on_hand_qty": inv.on_hand_qty,
        "available_qty": inv.available_qty,
        "days_of_cover": inv.days_of_cover,
        "stock_status": inv.stock_status,
    }
