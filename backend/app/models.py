from datetime import datetime, date
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Text,
    Date,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from .database import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(32), unique=True, nullable=False, index=True)
    name = Column(String(160), nullable=False)
    tier = Column(String(32), nullable=False, default="TIER_1")
    category_specialization = Column(String(100), nullable=False)
    contact_name = Column(String(120), nullable=False)
    contact_email = Column(String(160), nullable=False)
    contact_phone = Column(String(40), nullable=False)
    city = Column(String(80), nullable=False)
    state = Column(String(80), nullable=False)
    payment_terms = Column(String(64), nullable=False, default="NET_45")
    contracted_lead_time_days = Column(Integer, nullable=False, default=18)
    actual_avg_lead_time_days = Column(Float, nullable=False, default=19.5)
    on_time_delivery_rate = Column(Float, nullable=False, default=90.0)
    fill_rate = Column(Float, nullable=False, default=94.0)
    quality_pass_rate = Column(Float, nullable=False, default=96.5)
    issue_count = Column(Integer, nullable=False, default=0)
    issue_history_json = Column(Text, nullable=False, default="[]")
    status = Column(String(32), nullable=False, default="ACTIVE")
    is_synthetic = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    products = relationship("Product", back_populates="supplier")
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")

    __table_args__ = (
        Index("idx_suppliers_status_tier", "status", "tier"),
        Index("idx_suppliers_category", "category_specialization"),
    )


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(32), unique=True, nullable=False)
    name = Column(String(120), nullable=False)
    department = Column(String(80), nullable=False)
    parent_category = Column(String(80), nullable=False)
    season = Column(String(32), nullable=False, default="AW26")
    target_gross_margin_pct = Column(Float, nullable=False, default=52.0)
    return_benchmark_pct = Column(Float, nullable=False, default=18.0)

    products = relationship("Product", back_populates="category")


class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(32), unique=True, nullable=False)
    name = Column(String(140), nullable=False)
    city = Column(String(80), nullable=False)
    region = Column(String(40), nullable=False)
    capacity_units = Column(Integer, nullable=False)
    utilized_units = Column(Integer, nullable=False)
    active_pickers = Column(Integer, nullable=False, default=28)
    avg_processing_hours = Column(Float, nullable=False, default=6.2)
    sla_dispatch_hours = Column(Float, nullable=False, default=12.0)
    bottleneck_status = Column(String(32), nullable=False, default="NORMAL")
    manager_name = Column(String(120), nullable=False)
    is_synthetic = Column(Boolean, nullable=False, default=True)


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(48), unique=True, nullable=False, index=True)
    style_code = Column(String(40), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    brand = Column(String(100), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    season = Column(String(32), nullable=False, default="AW26")
    cost_price = Column(Float, nullable=False)
    mrp = Column(Float, nullable=False)
    selling_price = Column(Float, nullable=False)
    discount_pct = Column(Float, nullable=False, default=0.0)
    tax_rate_pct = Column(Float, nullable=False, default=12.0)
    gross_margin_pct = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    has_description = Column(Boolean, nullable=False, default=True)
    has_images = Column(Boolean, nullable=False, default=True)
    image_count = Column(Integer, nullable=False, default=4)
    has_size_chart = Column(Boolean, nullable=False, default=True)
    has_fabric_care = Column(Boolean, nullable=False, default=True)
    is_duplicate_flag = Column(Boolean, nullable=False, default=False)
    duplicate_of_sku = Column(String(48), nullable=True)
    completeness_score = Column(Float, nullable=False, default=100.0)
    missing_fields_json = Column(Text, nullable=False, default="[]")
    lifecycle_stage = Column(String(32), nullable=False, default="CORE")
    price_history_json = Column(Text, nullable=False, default="[]")
    is_synthetic = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    category = relationship("Category", back_populates="products")
    supplier = relationship("Supplier", back_populates="products")
    attributes = relationship("ProductAttribute", back_populates="product", uselist=False, cascade="all, delete-orphan")
    inventory_records = relationship("Inventory", back_populates="product")

    __table_args__ = (
        Index("idx_products_category_supplier", "category_id", "supplier_id"),
        Index("idx_products_completeness", "completeness_score", "is_duplicate_flag"),
    )


class ProductAttribute(Base):
    __tablename__ = "product_attributes"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), unique=True, nullable=False)
    size = Column(String(24), nullable=False)
    color = Column(String(64), nullable=False)
    color_hex = Column(String(16), nullable=False, default="#27272A")
    ean_barcode = Column(String(32), nullable=False)
    gsm_or_weight = Column(String(32), nullable=False)
    fabric_composition = Column(String(140), nullable=False)
    fit_type = Column(String(64), nullable=False)
    wash_care = Column(String(140), nullable=False)
    hsn_code = Column(String(24), nullable=False, default="61091000")

    product = relationship("Product", back_populates="attributes")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    po_number = Column(String(40), unique=True, nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    status = Column(String(32), nullable=False, default="ISSUED")
    order_date = Column(Date, nullable=False)
    expected_delivery_date = Column(Date, nullable=False)
    actual_delivery_date = Column(Date, nullable=True)
    supplier_acknowledged = Column(Boolean, nullable=False, default=False)
    acknowledged_at = Column(DateTime, nullable=True)
    total_ordered_qty = Column(Integer, nullable=False, default=0)
    total_received_qty = Column(Integer, nullable=False, default=0)
    pending_qty = Column(Integer, nullable=False, default=0)
    discrepancy_qty = Column(Integer, nullable=False, default=0)
    total_value_inr = Column(Float, nullable=False, default=0.0)
    delay_days = Column(Integer, nullable=False, default=0)
    delay_reason = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(String(100), nullable=False, default="Procurement Lead")
    is_synthetic = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    supplier = relationship("Supplier", back_populates="purchase_orders")
    warehouse = relationship("Warehouse")
    category = relationship("Category")
    items = relationship("PurchaseOrderItem", back_populates="purchase_order", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_po_supplier_status", "supplier_id", "status"),
        Index("idx_po_expected_date", "expected_delivery_date"),
    )


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id = Column(Integer, primary_key=True, index=True)
    po_id = Column(Integer, ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    ordered_qty = Column(Integer, nullable=False)
    received_qty = Column(Integer, nullable=False, default=0)
    pending_qty = Column(Integer, nullable=False, default=0)
    rejected_qty = Column(Integer, nullable=False, default=0)
    unit_cost_inr = Column(Float, nullable=False)
    line_total_inr = Column(Float, nullable=False)
    discrepancy_reason = Column(String(160), nullable=True)

    purchase_order = relationship("PurchaseOrder", back_populates="items")
    product = relationship("Product")


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    on_hand_qty = Column(Integer, nullable=False, default=0)
    reserved_qty = Column(Integer, nullable=False, default=0)
    available_qty = Column(Integer, nullable=False, default=0)
    damaged_qty = Column(Integer, nullable=False, default=0)
    in_transit_qty = Column(Integer, nullable=False, default=0)
    safety_stock_qty = Column(Integer, nullable=False, default=15)
    reorder_point_qty = Column(Integer, nullable=False, default=30)
    avg_daily_sales_7d = Column(Float, nullable=False, default=0.0)
    avg_daily_sales_30d = Column(Float, nullable=False, default=0.0)
    forecast_daily_demand = Column(Float, nullable=False, default=0.0)
    days_of_cover = Column(Float, nullable=False, default=0.0)
    sell_through_pct = Column(Float, nullable=False, default=0.0)
    turnover_ratio = Column(Float, nullable=False, default=0.0)
    age_bucket_0_30_qty = Column(Integer, nullable=False, default=0)
    age_bucket_31_60_qty = Column(Integer, nullable=False, default=0)
    age_bucket_61_90_qty = Column(Integer, nullable=False, default=0)
    age_bucket_90_plus_qty = Column(Integer, nullable=False, default=0)
    stock_status = Column(String(32), nullable=False, default="HEALTHY")
    last_received_date = Column(Date, nullable=True)
    last_sold_date = Column(Date, nullable=True)
    is_synthetic = Column(Boolean, nullable=False, default=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    product = relationship("Product", back_populates="inventory_records")
    warehouse = relationship("Warehouse")

    __table_args__ = (
        UniqueConstraint("product_id", "warehouse_id", name="uq_inventory_product_warehouse"),
        Index("idx_inventory_wh_status", "warehouse_id", "stock_status"),
    )


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    movement_type = Column(String(40), nullable=False)
    quantity_delta = Column(Integer, nullable=False)
    reference_code = Column(String(64), nullable=False)
    performed_by = Column(String(100), nullable=False)
    notes = Column(String(240), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    product = relationship("Product")
    warehouse = relationship("Warehouse")


class Promotion(Base):
    __tablename__ = "promotions"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(40), unique=True, nullable=False)
    name = Column(String(160), nullable=False)
    campaign_type = Column(String(64), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    discount_pct = Column(Float, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String(32), nullable=False, default="ACTIVE")
    baseline_daily_units = Column(Float, nullable=False, default=0.0)
    promo_daily_units = Column(Float, nullable=False, default=0.0)
    uplift_pct = Column(Float, nullable=False, default=0.0)
    revenue_generated_inr = Column(Float, nullable=False, default=0.0)
    gross_margin_impact_pct = Column(Float, nullable=False, default=0.0)
    is_synthetic = Column(Boolean, nullable=False, default=True)

    category = relationship("Category")
    product = relationship("Product")


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(32), unique=True, nullable=False)
    full_name = Column(String(140), nullable=False)
    email = Column(String(160), nullable=False)
    phone = Column(String(32), nullable=False)
    city = Column(String(80), nullable=False)
    state = Column(String(80), nullable=False)
    pin_code = Column(String(16), nullable=False)
    tier = Column(String(32), nullable=False, default="STANDARD")
    total_orders = Column(Integer, nullable=False, default=1)
    return_count = Column(Integer, nullable=False, default=0)
    is_synthetic = Column(Boolean, nullable=False, default=True)


class Carrier(Base):
    __tablename__ = "carriers"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(32), unique=True, nullable=False)
    name = Column(String(120), nullable=False)
    service_type = Column(String(48), nullable=False)
    avg_transit_days = Column(Float, nullable=False)
    on_time_rate_pct = Column(Float, nullable=False)
    rto_rate_pct = Column(Float, nullable=False)
    active_shipments = Column(Integer, nullable=False, default=0)
    escalation_contact = Column(String(160), nullable=False)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(40), unique=True, nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    order_date = Column(DateTime, nullable=False)
    status = Column(String(32), nullable=False)
    payment_mode = Column(String(32), nullable=False, default="PREPAID_UPI")
    total_items = Column(Integer, nullable=False, default=1)
    subtotal_inr = Column(Float, nullable=False)
    discount_inr = Column(Float, nullable=False, default=0.0)
    total_amount_inr = Column(Float, nullable=False)
    promised_dispatch_at = Column(DateTime, nullable=False)
    actual_dispatch_at = Column(DateTime, nullable=True)
    promised_delivery_date = Column(Date, nullable=False)
    actual_delivery_date = Column(Date, nullable=True)
    processing_hours = Column(Float, nullable=False, default=0.0)
    sla_breached = Column(Boolean, nullable=False, default=False)
    cancellation_reason = Column(String(160), nullable=True)
    is_synthetic = Column(Boolean, nullable=False, default=True)

    customer = relationship("Customer")
    warehouse = relationship("Warehouse")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    shipment = relationship("Shipment", back_populates="order", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_orders_wh_status", "warehouse_id", "status"),
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price_inr = Column(Float, nullable=False)
    discount_inr = Column(Float, nullable=False, default=0.0)
    net_price_inr = Column(Float, nullable=False)
    cost_price_inr = Column(Float, nullable=False)
    fulfilment_status = Column(String(32), nullable=False, default="ALLOCATED")

    order = relationship("Order", back_populates="items")
    product = relationship("Product")


class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, index=True)
    awb_number = Column(String(48), unique=True, nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), unique=True, nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    carrier_id = Column(Integer, ForeignKey("carriers.id"), nullable=False)
    status = Column(String(32), nullable=False)
    pick_started_at = Column(DateTime, nullable=True)
    pack_completed_at = Column(DateTime, nullable=True)
    dispatched_at = Column(DateTime, nullable=True)
    promised_delivery_date = Column(Date, nullable=False)
    actual_delivery_date = Column(Date, nullable=True)
    dispatch_hours = Column(Float, nullable=False, default=0.0)
    delay_hours = Column(Float, nullable=False, default=0.0)
    on_time = Column(Boolean, nullable=False, default=True)
    current_hub = Column(String(120), nullable=False)
    exception_code = Column(String(64), nullable=True)
    tracking_timeline_json = Column(Text, nullable=False, default="[]")
    is_synthetic = Column(Boolean, nullable=False, default=True)

    order = relationship("Order", back_populates="shipment")
    warehouse = relationship("Warehouse")
    carrier = relationship("Carrier")


class ReturnReason(Base):
    __tablename__ = "return_reasons"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(32), unique=True, nullable=False)
    category = Column(String(48), nullable=False)
    description = Column(String(180), nullable=False)
    controllable_by_ops = Column(Boolean, nullable=False, default=True)
    recommended_action = Column(String(200), nullable=False)


class ReturnRecord(Base):
    __tablename__ = "returns"

    id = Column(Integer, primary_key=True, index=True)
    rma_number = Column(String(40), unique=True, nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    order_item_id = Column(Integer, ForeignKey("order_items.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    return_reason_id = Column(Integer, ForeignKey("return_reasons.id"), nullable=False)
    request_type = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False)
    requested_at = Column(DateTime, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    qc_notes = Column(String(240), nullable=True)
    refund_amount_inr = Column(Float, nullable=False, default=0.0)
    refund_status = Column(String(32), nullable=False, default="PENDING")
    exchange_order_number = Column(String(40), nullable=True)
    restock_eligible = Column(Boolean, nullable=False, default=True)
    is_synthetic = Column(Boolean, nullable=False, default=True)

    order = relationship("Order")
    order_item = relationship("OrderItem")
    product = relationship("Product")
    customer = relationship("Customer")
    warehouse = relationship("Warehouse")
    reason = relationship("ReturnReason")


class OperationalException(Base):
    __tablename__ = "operational_exceptions"

    id = Column(Integer, primary_key=True, index=True)
    exception_code = Column(String(40), unique=True, nullable=False, index=True)
    domain = Column(String(40), nullable=False)
    severity = Column(String(24), nullable=False)
    status = Column(String(32), nullable=False, default="OPEN")
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    po_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True)
    assigned_to = Column(String(120), nullable=False, default="Unassigned")
    assigned_role = Column(String(80), nullable=False, default="Operations Queue")
    root_cause = Column(Text, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    financial_impact_inr = Column(Float, nullable=False, default=0.0)
    detected_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    is_synthetic = Column(Boolean, nullable=False, default=True)

    supplier = relationship("Supplier")
    product = relationship("Product")
    warehouse = relationship("Warehouse")
    purchase_order = relationship("PurchaseOrder")
    order = relationship("Order")
    shipment = relationship("Shipment")


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id = Column(Integer, primary_key=True, index=True)
    event_name = Column(String(80), nullable=False, index=True)
    user_role = Column(String(80), nullable=False)
    workspace = Column(String(64), nullable=False)
    supplier_id = Column(String(48), nullable=True)
    sku_id = Column(String(64), nullable=True)
    warehouse_id = Column(String(48), nullable=True)
    exception_type = Column(String(64), nullable=True)
    action_status = Column(String(48), nullable=False)
    duration_seconds = Column(Integer, nullable=True)
    delivery_channel = Column(String(48), nullable=False, default="LOCAL_POSTGRES_ADAPTER")
    properties_json = Column(Text, nullable=False, default="{}")
    event_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
