-- =============================================================================
-- THREADFLOW: Analytical SQL Views for Control Tower KPIs & Tableau BI Layer
-- Covers Procurement, Inventory Intelligence, and Outbound Fulfilment & Returns
-- =============================================================================

-- VIEW 1: PROCUREMENT — Supplier Performance, Lead Time & PO Fulfilment
CREATE OR REPLACE VIEW vw_tableau_procurement_scorecard AS
SELECT
    s.id AS supplier_id,
    s.code AS supplier_code,
    s.name AS supplier_name,
    s.tier AS supplier_tier,
    s.category_specialization,
    s.city,
    s.state,
    s.contracted_lead_time_days,
    s.actual_avg_lead_time_days,
    ROUND(s.actual_avg_lead_time_days - s.contracted_lead_time_days, 2) AS lead_time_variance_days,
    s.on_time_delivery_rate,
    s.fill_rate AS po_fulfilment_rate_pct,
    s.quality_pass_rate,
    s.issue_count,
    s.status AS supplier_status,
    COUNT(po.id) AS total_purchase_orders,
    SUM(CASE WHEN po.status = 'DELAYED' OR po.delay_days > 0 THEN 1 ELSE 0 END) AS delayed_po_count,
    COALESCE(SUM(po.total_ordered_qty), 0) AS total_ordered_units,
    COALESCE(SUM(po.total_received_qty), 0) AS total_received_units,
    COALESCE(SUM(po.discrepancy_qty), 0) AS total_discrepancy_units,
    COALESCE(SUM(po.total_value_inr), 0) AS total_procurement_value_inr
FROM suppliers s
LEFT JOIN purchase_orders po ON po.supplier_id = s.id
GROUP BY
    s.id, s.code, s.name, s.tier, s.category_specialization, s.city, s.state,
    s.contracted_lead_time_days, s.actual_avg_lead_time_days, s.on_time_delivery_rate,
    s.fill_rate, s.quality_pass_rate, s.issue_count, s.status;

-- VIEW 2: PROCUREMENT — Category Procurement Volume & Catalogue Completeness
CREATE OR REPLACE VIEW vw_tableau_category_merchandising AS
SELECT
    c.id AS category_id,
    c.code AS category_code,
    c.name AS category_name,
    c.department,
    c.season,
    c.target_gross_margin_pct,
    c.return_benchmark_pct,
    COUNT(DISTINCT p.id) AS active_sku_count,
    ROUND(AVG(p.completeness_score), 2) AS avg_catalogue_completeness_pct,
    SUM(CASE WHEN p.completeness_score < 85 THEN 1 ELSE 0 END) AS incomplete_sku_count,
    SUM(CASE WHEN p.is_duplicate_flag = TRUE THEN 1 ELSE 0 END) AS duplicate_sku_count,
    ROUND(AVG(p.gross_margin_pct), 2) AS realized_gross_margin_pct,
    COALESCE(SUM(po.total_value_inr), 0) AS procurement_spend_inr
FROM categories c
LEFT JOIN products p ON p.category_id = c.id
LEFT JOIN purchase_orders po ON po.category_id = c.id
GROUP BY
    c.id, c.code, c.name, c.department, c.season, c.target_gross_margin_pct, c.return_benchmark_pct;

-- VIEW 3: INVENTORY — Warehouse & SKU Stock Health, Ageing & Replenishment
CREATE OR REPLACE VIEW vw_tableau_inventory_intelligence AS
SELECT
    i.id AS inventory_id,
    w.code AS warehouse_code,
    w.name AS warehouse_name,
    w.region AS warehouse_region,
    p.sku,
    p.style_code,
    p.name AS product_name,
    p.brand,
    c.name AS category_name,
    c.department,
    s.name AS supplier_name,
    s.actual_avg_lead_time_days AS supplier_lead_time_days,
    i.on_hand_qty,
    i.reserved_qty,
    i.available_qty,
    i.in_transit_qty,
    i.safety_stock_qty,
    i.reorder_point_qty,
    i.avg_daily_sales_7d,
    i.avg_daily_sales_30d,
    i.forecast_daily_demand,
    i.days_of_cover,
    i.sell_through_pct,
    i.turnover_ratio,
    i.age_bucket_0_30_qty,
    i.age_bucket_31_60_qty,
    i.age_bucket_61_90_qty,
    i.age_bucket_90_plus_qty,
    ROUND(i.on_hand_qty * p.cost_price, 2) AS inventory_cost_value_inr,
    ROUND((i.age_bucket_61_90_qty + i.age_bucket_90_plus_qty) * p.cost_price, 2) AS aged_excess_value_inr,
    i.stock_status,
    GREATEST(0, CEIL((i.forecast_daily_demand * (s.actual_avg_lead_time_days + 14)) + i.safety_stock_qty - (i.available_qty + i.in_transit_qty))) AS recommended_reorder_qty
FROM inventory i
JOIN products p ON p.id = i.product_id
JOIN categories c ON c.id = p.category_id
JOIN suppliers s ON s.id = p.supplier_id
JOIN warehouses w ON w.id = i.warehouse_id;

-- VIEW 4: OUTBOUND — Warehouse Fulfilment, Carrier SLA & Delivery Performance
CREATE OR REPLACE VIEW vw_tableau_outbound_fulfilment AS
SELECT
    o.id AS order_id,
    o.order_number,
    o.order_date,
    o.status AS order_status,
    o.payment_mode,
    o.total_items,
    o.total_amount_inr,
    o.processing_hours,
    o.sla_breached,
    o.promised_delivery_date,
    o.actual_delivery_date,
    w.code AS warehouse_code,
    w.name AS warehouse_name,
    w.region AS warehouse_region,
    w.bottleneck_status,
    sh.awb_number,
    sh.status AS shipment_status,
    sh.dispatch_hours,
    sh.delay_hours,
    sh.on_time AS delivered_on_time,
    sh.current_hub,
    cr.code AS carrier_code,
    cr.name AS carrier_name,
    cr.service_type AS carrier_service_type
FROM orders o
JOIN warehouses w ON w.id = o.warehouse_id
LEFT JOIN shipments sh ON sh.order_id = o.id
LEFT JOIN carriers cr ON cr.id = sh.carrier_id;

-- VIEW 5: OUTBOUND — Returns, Exchanges & Root-Cause Attribution
CREATE OR REPLACE VIEW vw_tableau_returns_analysis AS
SELECT
    r.id AS return_id,
    r.rma_number,
    r.request_type,
    r.status AS return_status,
    r.requested_at,
    r.resolved_at,
    r.refund_amount_inr,
    r.refund_status,
    r.restock_eligible,
    rr.code AS reason_code,
    rr.category AS reason_category,
    rr.description AS reason_description,
    rr.controllable_by_ops,
    p.sku,
    p.name AS product_name,
    p.brand,
    p.completeness_score AS sku_completeness_score,
    c.name AS category_name,
    c.department,
    s.name AS supplier_name,
    w.code AS warehouse_code
FROM returns r
JOIN return_reasons rr ON rr.id = r.return_reason_id
JOIN products p ON p.id = r.product_id
JOIN categories c ON c.id = p.category_id
JOIN suppliers s ON s.id = p.supplier_id
JOIN warehouses w ON w.id = r.warehouse_id;
