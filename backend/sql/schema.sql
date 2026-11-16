-- =============================================================================
-- THREADFLOW: Fashion Supply Chain & Merchandising Control Tower
-- PostgreSQL Production Relational Schema & Indexing Specification
-- Version: 2.4.0
-- Policy: All seeded records carry is_synthetic = TRUE
-- =============================================================================

-- 1. SUPPLIERS
CREATE TABLE IF NOT EXISTS suppliers (
    id SERIAL PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(160) NOT NULL,
    tier VARCHAR(32) NOT NULL DEFAULT 'TIER_1', -- TIER_1, TIER_2, STRATEGIC
    category_specialization VARCHAR(100) NOT NULL,
    contact_name VARCHAR(120) NOT NULL,
    contact_email VARCHAR(160) NOT NULL,
    contact_phone VARCHAR(40) NOT NULL,
    city VARCHAR(80) NOT NULL,
    state VARCHAR(80) NOT NULL,
    payment_terms VARCHAR(64) NOT NULL DEFAULT 'NET_45',
    contracted_lead_time_days INTEGER NOT NULL CHECK (contracted_lead_time_days > 0),
    actual_avg_lead_time_days NUMERIC(6,2) NOT NULL CHECK (actual_avg_lead_time_days >= 0),
    on_time_delivery_rate NUMERIC(5,2) NOT NULL CHECK (on_time_delivery_rate BETWEEN 0 AND 100),
    fill_rate NUMERIC(5,2) NOT NULL CHECK (fill_rate BETWEEN 0 AND 100),
    quality_pass_rate NUMERIC(5,2) NOT NULL CHECK (quality_pass_rate BETWEEN 0 AND 100),
    issue_count INTEGER NOT NULL DEFAULT 0,
    issue_history_json TEXT NOT NULL DEFAULT '[]',
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, ON_HOLD, UNDER_AUDIT
    is_synthetic BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_suppliers_status_tier ON suppliers(status, tier);
CREATE INDEX IF NOT EXISTS idx_suppliers_category ON suppliers(category_specialization);

-- 2. CATEGORIES
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(120) NOT NULL,
    department VARCHAR(80) NOT NULL, -- MENSWEAR, WOMENSWEAR, ACTIVEWEAR, FOOTWEAR, KIDS, ACCESSORIES
    parent_category VARCHAR(80) NOT NULL,
    season VARCHAR(32) NOT NULL DEFAULT 'AW26',
    target_gross_margin_pct NUMERIC(5,2) NOT NULL,
    return_benchmark_pct NUMERIC(5,2) NOT NULL
);

-- 3. WAREHOUSES
CREATE TABLE IF NOT EXISTS warehouses (
    id SERIAL PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(140) NOT NULL,
    city VARCHAR(80) NOT NULL,
    region VARCHAR(40) NOT NULL, -- SOUTH, NORTH, WEST, EAST
    capacity_units INTEGER NOT NULL CHECK (capacity_units > 0),
    utilized_units INTEGER NOT NULL CHECK (utilized_units >= 0),
    active_pickers INTEGER NOT NULL DEFAULT 25,
    avg_processing_hours NUMERIC(6,2) NOT NULL DEFAULT 6.0,
    sla_dispatch_hours NUMERIC(6,2) NOT NULL DEFAULT 12.0,
    bottleneck_status VARCHAR(32) NOT NULL DEFAULT 'NORMAL', -- NORMAL, ELEVATED, CRITICAL_BACKLOG
    manager_name VARCHAR(120) NOT NULL,
    is_synthetic BOOLEAN NOT NULL DEFAULT TRUE
);

-- 4. PRODUCTS (SKUs)
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(48) NOT NULL UNIQUE,
    style_code VARCHAR(40) NOT NULL,
    name VARCHAR(200) NOT NULL,
    brand VARCHAR(100) NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    supplier_id INTEGER NOT NULL REFERENCES suppliers(id),
    season VARCHAR(32) NOT NULL DEFAULT 'AW26',
    cost_price NUMERIC(10,2) NOT NULL CHECK (cost_price >= 0),
    mrp NUMERIC(10,2) NOT NULL CHECK (mrp >= 0),
    selling_price NUMERIC(10,2) NOT NULL CHECK (selling_price >= 0),
    discount_pct NUMERIC(5,2) NOT NULL DEFAULT 0,
    tax_rate_pct NUMERIC(5,2) NOT NULL DEFAULT 12.0,
    gross_margin_pct NUMERIC(6,2) NOT NULL,
    description TEXT,
    has_description BOOLEAN NOT NULL DEFAULT TRUE,
    has_images BOOLEAN NOT NULL DEFAULT TRUE,
    image_count INTEGER NOT NULL DEFAULT 4,
    has_size_chart BOOLEAN NOT NULL DEFAULT TRUE,
    has_fabric_care BOOLEAN NOT NULL DEFAULT TRUE,
    is_duplicate_flag BOOLEAN NOT NULL DEFAULT FALSE,
    duplicate_of_sku VARCHAR(48),
    completeness_score NUMERIC(5,2) NOT NULL CHECK (completeness_score BETWEEN 0 AND 100),
    missing_fields_json TEXT NOT NULL DEFAULT '[]',
    lifecycle_stage VARCHAR(32) NOT NULL DEFAULT 'CORE', -- NEW_LAUNCH, CORE, SEASONAL, CLEARANCE
    price_history_json TEXT NOT NULL DEFAULT '[]',
    is_synthetic BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_products_category_supplier ON products(category_id, supplier_id);
CREATE INDEX IF NOT EXISTS idx_products_completeness ON products(completeness_score, is_duplicate_flag);
CREATE INDEX IF NOT EXISTS idx_products_style_code ON products(style_code);

-- 5. PRODUCT ATTRIBUTES
CREATE TABLE IF NOT EXISTS product_attributes (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL UNIQUE REFERENCES products(id) ON DELETE CASCADE,
    size VARCHAR(24) NOT NULL,
    color VARCHAR(64) NOT NULL,
    color_hex VARCHAR(16) NOT NULL DEFAULT '#27272A',
    ean_barcode VARCHAR(32) NOT NULL,
    gsm_or_weight VARCHAR(32) NOT NULL,
    fabric_composition VARCHAR(140) NOT NULL,
    fit_type VARCHAR(64) NOT NULL,
    wash_care VARCHAR(140) NOT NULL,
    hsn_code VARCHAR(24) NOT NULL DEFAULT '61091000'
);

CREATE INDEX IF NOT EXISTS idx_product_attr_size_color ON product_attributes(size, color);

-- 6. PURCHASE ORDERS
CREATE TABLE IF NOT EXISTS purchase_orders (
    id SERIAL PRIMARY KEY,
    po_number VARCHAR(40) NOT NULL UNIQUE,
    supplier_id INTEGER NOT NULL REFERENCES suppliers(id),
    warehouse_id INTEGER NOT NULL REFERENCES warehouses(id),
    category_id INTEGER NOT NULL REFERENCES categories(id),
    status VARCHAR(32) NOT NULL, -- DRAFT, ISSUED, ACKNOWLEDGED, PARTIALLY_RECEIVED, RECEIVED, DELAYED, CLOSED, CANCELLED
    order_date DATE NOT NULL,
    expected_delivery_date DATE NOT NULL,
    actual_delivery_date DATE,
    supplier_acknowledged BOOLEAN NOT NULL DEFAULT FALSE,
    acknowledged_at TIMESTAMP,
    total_ordered_qty INTEGER NOT NULL DEFAULT 0,
    total_received_qty INTEGER NOT NULL DEFAULT 0,
    pending_qty INTEGER NOT NULL DEFAULT 0,
    discrepancy_qty INTEGER NOT NULL DEFAULT 0,
    total_value_inr NUMERIC(14,2) NOT NULL DEFAULT 0,
    delay_days INTEGER NOT NULL DEFAULT 0,
    delay_reason VARCHAR(200),
    notes TEXT,
    created_by VARCHAR(100) NOT NULL DEFAULT 'Procurement Lead',
    is_synthetic BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_po_supplier_status ON purchase_orders(supplier_id, status);
CREATE INDEX IF NOT EXISTS idx_po_expected_date ON purchase_orders(expected_delivery_date);

-- 7. PURCHASE ORDER ITEMS
CREATE TABLE IF NOT EXISTS purchase_order_items (
    id SERIAL PRIMARY KEY,
    po_id INTEGER NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    ordered_qty INTEGER NOT NULL CHECK (ordered_qty > 0),
    received_qty INTEGER NOT NULL DEFAULT 0 CHECK (received_qty >= 0),
    pending_qty INTEGER NOT NULL DEFAULT 0 CHECK (pending_qty >= 0),
    rejected_qty INTEGER NOT NULL DEFAULT 0 CHECK (rejected_qty >= 0),
    unit_cost_inr NUMERIC(10,2) NOT NULL,
    line_total_inr NUMERIC(12,2) NOT NULL,
    discrepancy_reason VARCHAR(160)
);

CREATE INDEX IF NOT EXISTS idx_po_items_po_product ON purchase_order_items(po_id, product_id);

-- 8. INVENTORY (WAREHOUSE x SKU)
CREATE TABLE IF NOT EXISTS inventory (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id),
    warehouse_id INTEGER NOT NULL REFERENCES warehouses(id),
    on_hand_qty INTEGER NOT NULL DEFAULT 0 CHECK (on_hand_qty >= 0),
    reserved_qty INTEGER NOT NULL DEFAULT 0 CHECK (reserved_qty >= 0),
    available_qty INTEGER NOT NULL DEFAULT 0,
    damaged_qty INTEGER NOT NULL DEFAULT 0 CHECK (damaged_qty >= 0),
    in_transit_qty INTEGER NOT NULL DEFAULT 0 CHECK (in_transit_qty >= 0),
    safety_stock_qty INTEGER NOT NULL DEFAULT 15,
    reorder_point_qty INTEGER NOT NULL DEFAULT 30,
    avg_daily_sales_7d NUMERIC(8,2) NOT NULL DEFAULT 0,
    avg_daily_sales_30d NUMERIC(8,2) NOT NULL DEFAULT 0,
    forecast_daily_demand NUMERIC(8,2) NOT NULL DEFAULT 0,
    days_of_cover NUMERIC(8,1) NOT NULL DEFAULT 0,
    sell_through_pct NUMERIC(5,2) NOT NULL DEFAULT 0,
    turnover_ratio NUMERIC(6,2) NOT NULL DEFAULT 0,
    age_bucket_0_30_qty INTEGER NOT NULL DEFAULT 0,
    age_bucket_31_60_qty INTEGER NOT NULL DEFAULT 0,
    age_bucket_61_90_qty INTEGER NOT NULL DEFAULT 0,
    age_bucket_90_plus_qty INTEGER NOT NULL DEFAULT 0,
    stock_status VARCHAR(32) NOT NULL DEFAULT 'HEALTHY', -- HEALTHY, LOW_STOCK, STOCKOUT, EXCESS, SLOW_MOVING
    last_received_date DATE,
    last_sold_date DATE,
    is_synthetic BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_id, warehouse_id)
);

CREATE INDEX IF NOT EXISTS idx_inventory_wh_status ON inventory(warehouse_id, stock_status);
CREATE INDEX IF NOT EXISTS idx_inventory_product ON inventory(product_id);

-- 9. STOCK MOVEMENTS
CREATE TABLE IF NOT EXISTS stock_movements (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id),
    warehouse_id INTEGER NOT NULL REFERENCES warehouses(id),
    movement_type VARCHAR(40) NOT NULL, -- GRN_INBOUND, ORDER_RESERVATION, ORDER_DISPATCH, RETURN_RESTOCK, INTER_WH_TRANSFER, CYCLE_COUNT_ADJ
    quantity_delta INTEGER NOT NULL,
    reference_code VARCHAR(64) NOT NULL,
    performed_by VARCHAR(100) NOT NULL,
    notes VARCHAR(240),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_stock_movements_wh_prod ON stock_movements(warehouse_id, product_id, created_at);

-- 10. PROMOTIONS
CREATE TABLE IF NOT EXISTS promotions (
    id SERIAL PRIMARY KEY,
    code VARCHAR(40) NOT NULL UNIQUE,
    name VARCHAR(160) NOT NULL,
    campaign_type VARCHAR(64) NOT NULL, -- SEASONAL_SALE, CLEARANCE_MARKDOWN, CATEGORY_SPOTLIGHT, BUNDLE_OFFER
    category_id INTEGER REFERENCES categories(id),
    product_id INTEGER REFERENCES products(id),
    discount_pct NUMERIC(5,2) NOT NULL CHECK (discount_pct BETWEEN 0 AND 90),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, SCHEDULED, EXPIRED, PAUSED
    baseline_daily_units NUMERIC(8,2) NOT NULL DEFAULT 0,
    promo_daily_units NUMERIC(8,2) NOT NULL DEFAULT 0,
    uplift_pct NUMERIC(6,2) NOT NULL DEFAULT 0,
    revenue_generated_inr NUMERIC(14,2) NOT NULL DEFAULT 0,
    gross_margin_impact_pct NUMERIC(6,2) NOT NULL DEFAULT 0,
    is_synthetic BOOLEAN NOT NULL DEFAULT TRUE
);

-- 11. CUSTOMERS
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE,
    full_name VARCHAR(140) NOT NULL,
    email VARCHAR(160) NOT NULL,
    phone VARCHAR(32) NOT NULL,
    city VARCHAR(80) NOT NULL,
    state VARCHAR(80) NOT NULL,
    pin_code VARCHAR(16) NOT NULL,
    tier VARCHAR(32) NOT NULL DEFAULT 'STANDARD', -- VIP, INSIDER, STANDARD
    total_orders INTEGER NOT NULL DEFAULT 1,
    return_count INTEGER NOT NULL DEFAULT 0,
    is_synthetic BOOLEAN NOT NULL DEFAULT TRUE
);

-- 12. CARRIERS
CREATE TABLE IF NOT EXISTS carriers (
    id SERIAL PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(120) NOT NULL,
    service_type VARCHAR(48) NOT NULL, -- SURFACE_EXPRESS, AIR_PRIORITY, SAME_DAY_METRO
    avg_transit_days NUMERIC(5,2) NOT NULL,
    on_time_rate_pct NUMERIC(5,2) NOT NULL,
    rto_rate_pct NUMERIC(5,2) NOT NULL,
    active_shipments INTEGER NOT NULL DEFAULT 0,
    escalation_contact VARCHAR(160) NOT NULL
);

-- 13. ORDERS
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    order_number VARCHAR(40) NOT NULL UNIQUE,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    warehouse_id INTEGER NOT NULL REFERENCES warehouses(id),
    order_date TIMESTAMP NOT NULL,
    status VARCHAR(32) NOT NULL, -- PENDING, ALLOCATED, PICKING, PACKED, DISPATCHED, IN_TRANSIT, DELIVERED, DELAYED, CANCELLED, RETURN_REQUESTED
    payment_mode VARCHAR(32) NOT NULL DEFAULT 'PREPAID_UPI', -- PREPAID_UPI, PREPAID_CARD, COD
    total_items INTEGER NOT NULL CHECK (total_items > 0),
    subtotal_inr NUMERIC(12,2) NOT NULL,
    discount_inr NUMERIC(12,2) NOT NULL DEFAULT 0,
    total_amount_inr NUMERIC(12,2) NOT NULL,
    promised_dispatch_at TIMESTAMP NOT NULL,
    actual_dispatch_at TIMESTAMP,
    promised_delivery_date DATE NOT NULL,
    actual_delivery_date DATE,
    processing_hours NUMERIC(6,2) NOT NULL DEFAULT 0,
    sla_breached BOOLEAN NOT NULL DEFAULT FALSE,
    cancellation_reason VARCHAR(160),
    is_synthetic BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_orders_wh_status ON orders(warehouse_id, status);
CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date);

-- 14. ORDER ITEMS
CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_inr NUMERIC(10,2) NOT NULL,
    discount_inr NUMERIC(10,2) NOT NULL DEFAULT 0,
    net_price_inr NUMERIC(10,2) NOT NULL,
    cost_price_inr NUMERIC(10,2) NOT NULL,
    fulfilment_status VARCHAR(32) NOT NULL DEFAULT 'ALLOCATED'
);

CREATE INDEX IF NOT EXISTS idx_order_items_order_prod ON order_items(order_id, product_id);

-- 15. SHIPMENTS
CREATE TABLE IF NOT EXISTS shipments (
    id SERIAL PRIMARY KEY,
    awb_number VARCHAR(48) NOT NULL UNIQUE,
    order_id INTEGER NOT NULL UNIQUE REFERENCES orders(id) ON DELETE CASCADE,
    warehouse_id INTEGER NOT NULL REFERENCES warehouses(id),
    carrier_id INTEGER NOT NULL REFERENCES carriers(id),
    status VARCHAR(32) NOT NULL, -- MANIFESTED, PICKED_UP, IN_TRANSIT, HUB_REACHED, OUT_FOR_DELIVERY, DELIVERED, DELIVERY_EXCEPTION, RTO_INITIATED
    pick_started_at TIMESTAMP,
    pack_completed_at TIMESTAMP,
    dispatched_at TIMESTAMP,
    promised_delivery_date DATE NOT NULL,
    actual_delivery_date DATE,
    dispatch_hours NUMERIC(6,2) NOT NULL DEFAULT 0,
    delay_hours NUMERIC(6,2) NOT NULL DEFAULT 0,
    on_time BOOLEAN NOT NULL DEFAULT TRUE,
    current_hub VARCHAR(120) NOT NULL,
    exception_code VARCHAR(64),
    tracking_timeline_json TEXT NOT NULL DEFAULT '[]',
    is_synthetic BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_shipments_carrier_status ON shipments(carrier_id, status);
CREATE INDEX IF NOT EXISTS idx_shipments_wh ON shipments(warehouse_id);

-- 16. RETURN REASONS
CREATE TABLE IF NOT EXISTS return_reasons (
    id SERIAL PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE,
    category VARCHAR(48) NOT NULL, -- SIZE_FIT, QUALITY_DEFECT, CATALOGUE_MISMATCH, LATE_DELIVERY, DAMAGED_IN_TRANSIT, CHANGED_MIND
    description VARCHAR(180) NOT NULL,
    controllable_by_ops BOOLEAN NOT NULL DEFAULT TRUE,
    recommended_action VARCHAR(200) NOT NULL
);

-- 17. RETURNS & EXCHANGES
CREATE TABLE IF NOT EXISTS returns (
    id SERIAL PRIMARY KEY,
    rma_number VARCHAR(40) NOT NULL UNIQUE,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    order_item_id INTEGER NOT NULL REFERENCES order_items(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    warehouse_id INTEGER NOT NULL REFERENCES warehouses(id),
    return_reason_id INTEGER NOT NULL REFERENCES return_reasons(id),
    request_type VARCHAR(32) NOT NULL, -- RETURN_REFUND, SIZE_EXCHANGE, STYLE_EXCHANGE
    status VARCHAR(32) NOT NULL, -- REQUESTED, APPROVED, PICKUP_SCHEDULED, IN_TRANSIT_RETURN, QC_PASSED, QC_FAILED, EXCHANGE_DISPATCHED, REFUND_PROCESSED, CLOSED
    requested_at TIMESTAMP NOT NULL,
    resolved_at TIMESTAMP,
    qc_notes VARCHAR(240),
    refund_amount_inr NUMERIC(10,2) NOT NULL DEFAULT 0,
    refund_status VARCHAR(32) NOT NULL DEFAULT 'PENDING', -- PENDING, INITIATED, PROCESSED, NOT_APPLICABLE
    exchange_order_number VARCHAR(40),
    restock_eligible BOOLEAN NOT NULL DEFAULT TRUE,
    is_synthetic BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_returns_prod_reason ON returns(product_id, return_reason_id);
CREATE INDEX IF NOT EXISTS idx_returns_status ON returns(status);

-- 18. OPERATIONAL EXCEPTIONS
CREATE TABLE IF NOT EXISTS operational_exceptions (
    id SERIAL PRIMARY KEY,
    exception_code VARCHAR(40) NOT NULL UNIQUE,
    domain VARCHAR(40) NOT NULL, -- INBOUND_PO, CATALOGUE_QUALITY, INVENTORY_RISK, WAREHOUSE_BOTTLENECK, DISPATCH_DELAY, DELIVERY_SLA, RETURN_SPIKE
    severity VARCHAR(24) NOT NULL, -- CRITICAL, HIGH, MEDIUM, LOW
    status VARCHAR(32) NOT NULL DEFAULT 'OPEN', -- OPEN, IN_PROGRESS, ESCALATED, RESOLVED
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    supplier_id INTEGER REFERENCES suppliers(id),
    product_id INTEGER REFERENCES products(id),
    warehouse_id INTEGER REFERENCES warehouses(id),
    po_id INTEGER REFERENCES purchase_orders(id),
    order_id INTEGER REFERENCES orders(id),
    shipment_id INTEGER REFERENCES shipments(id),
    assigned_to VARCHAR(120) NOT NULL DEFAULT 'Unassigned',
    assigned_role VARCHAR(80) NOT NULL DEFAULT 'Operations Queue',
    root_cause TEXT,
    resolution_notes TEXT,
    financial_impact_inr NUMERIC(12,2) NOT NULL DEFAULT 0,
    detected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    is_synthetic BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_exceptions_domain_status ON operational_exceptions(domain, status, severity);

-- 19. PRODUCT ANALYTICS & MIXPANEL TELEMETRY LEDGER
CREATE TABLE IF NOT EXISTS analytics_events (
    id SERIAL PRIMARY KEY,
    event_name VARCHAR(80) NOT NULL,
    user_role VARCHAR(80) NOT NULL,
    workspace VARCHAR(64) NOT NULL,
    supplier_id VARCHAR(48),
    sku_id VARCHAR(64),
    warehouse_id VARCHAR(48),
    exception_type VARCHAR(64),
    action_status VARCHAR(48) NOT NULL,
    duration_seconds INTEGER,
    delivery_channel VARCHAR(48) NOT NULL DEFAULT 'LOCAL_POSTGRES_ADAPTER', -- LOCAL_POSTGRES_ADAPTER, MIXPANEL_AND_LOCAL
    properties_json TEXT NOT NULL DEFAULT '{}',
    event_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_analytics_event_name ON analytics_events(event_name, workspace);
CREATE INDEX IF NOT EXISTS idx_analytics_timestamp ON analytics_events(event_timestamp);
