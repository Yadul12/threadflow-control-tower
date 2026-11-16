# THREADFLOW — Unified Control Tower KPI Data Dictionary & Tableau BI Specification

**Status:** Production Verified  
**Tableau Integration Disclosure:** Live Tableau Server credentials are not configured in this local workspace. Instead, THREADFLOW provides **5 production PostgreSQL analytical views** (`backend/sql/analytical_views.sql`) and **pre-extracted CSV and XLSX Tableau data sources** in `deliverables/tableau/extracts/` (also downloadable live via `/api/analytics/tableau/extract/{view_name}`).

---

## 1. Unified Control Tower KPI Dictionary (14 Mandatory KPIs)

### 1.1 Inbound Procurement & Catalogue KPIs

| KPI ID | KPI Name | Formula | Reporting Period | Source Tables | Calculation Method & Operational Target |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `KPI-PROC-01` | **Supplier On-Time Delivery (OTD %)** | $\frac{\text{POs where } \text{actual\_delivery\_date} \le \text{expected\_delivery\_date}}{\text{Total Completed POs}} \times 100$ | Rolling 90 Days (AW26) | `suppliers`, `purchase_orders` | Weighted mean of supplier OTD rates across received/closed PO cohorts. **Target:** $\ge 92.0\%$ |
| `KPI-PROC-02` | **Purchase Order Fulfilment (Fill Rate %)** | $\frac{\sum \text{total\_received\_qty}}{\sum \text{total\_ordered\_qty}} \times 100$ | Rolling 90 Days | `purchase_orders`, `purchase_order_items` | Ratio of QC-accepted GRN units received at regional FCs to contracted PO quantities. **Target:** $\ge 96.0\%$ |
| `KPI-PROC-03` | **Average Supplier Lead Time** | $\text{AVG}(\text{actual\_delivery\_date} - \text{order\_date})$ | Rolling 90 Days | `suppliers`, `purchase_orders` | Arithmetic mean of elapsed days from PO issue date to warehouse gate-in receipt. **Target:** $\le 16.5\text{ Days}$ |
| `KPI-PROC-04` | **Catalogue Completeness Score** | $\text{AVG}(25\%[\text{Desc}] + 25\%[\ge 4\text{ Imgs}] + 25\%[\text{Size Chart}] + 25\%[\text{Fabric Care}] - 20\%[\text{Dup}])$ | Live Snapshot (240 SKUs) | `products`, `product_attributes` | Attribute readiness score across all active SKUs prior to storefront listing. **Target:** $\ge 95.0\%$ |

### 1.2 Inventory Intelligence KPIs

| KPI ID | KPI Name | Formula | Reporting Period | Source Tables | Calculation Method & Operational Target |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `KPI-INV-01` | **Stockout Percentage** | $\frac{\text{COUNT}(\text{SKU-WH nodes with } \text{available\_qty} = 0)}{\text{COUNT}(\text{Total SKU-WH nodes})} \times 100$ | Live Real-Time Snapshot | `inventory`, `warehouses`, `products` | Share of active SKU-Warehouse combinations with zero unreserved sellable units. **Target:** $\le 4.0\%$ |
| `KPI-INV-02` | **Inventory Turnover Ratio** | $\frac{\text{ADS}_{30\text{d}} \times 365}{\text{Average On-Hand Inventory Units}}$ | Annualised from Rolling 30d | `inventory`, `stock_movements` | Annualized unit depletion velocity divided by mean on-hand inventory across FCs. **Target:** $\ge 6.5\times\text{/yr}$ |
| `KPI-INV-03` | **Sell-Through Rate %** | $\frac{\text{Units Sold}_{30\text{d}}}{\text{Units Sold}_{30\text{d}} + \text{Ending Available Qty}} \times 100$ | Rolling 30 Days | `inventory`, `order_items` | 30-day unit sales divided by total merchantable stock exposure. **Target:** $\ge 62.0\%$ |
| `KPI-INV-04` | **Days of Inventory Cover (DOC)** | $\frac{\text{available\_qty}}{0.60 \times \text{ADS}_{7\text{d}} + 0.40 \times \text{ADS}_{30\text{d}}}$ | Live Snapshot vs 7d/30d WMA | `inventory` | Current unreserved stock divided by weighted moving-average daily demand. **Target:** $22\text{–}35\text{ Days}$ |
| `KPI-INV-05` | **Excess Inventory Value (>60d Aged)** | $\sum (\text{age\_61\_90\_qty} + \text{age\_90\_plus\_qty}) \times \text{cost\_price}$ | Live Ageing Ledger | `inventory`, `products` | Total landed cost value of inventory sitting in 61–90d and 90+d ageing buckets. **Target:** $\le \text{INR } 25.0\text{L}$ |

### 1.3 Outbound Fulfilment, Delivery & Returns KPIs

| KPI ID | KPI Name | Formula | Reporting Period | Source Tables | Calculation Method & Operational Target |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `KPI-OUT-01` | **Order Fulfilment Processing Time** | $\text{AVG}(\text{actual\_dispatch\_at} - \text{order\_date})\text{ in hours}$ | Rolling 30 Days | `orders`, `warehouses` | Mean warehouse cycle time from order placement to carrier dock handover. **Target:** $\le 8.0\text{ Hours}$ |
| `KPI-OUT-02` | **On-Time Delivery Percentage** | $\frac{\text{Shipments with } \text{actual\_delivery\_date} \le \text{promised\_delivery\_date}}{\text{Total Delivered & Exception Shipments}} \times 100$ | Rolling 30 Days | `shipments`, `orders`, `carriers` | Share of fulfilled shipments delivered on or before customer-promised SLA date. **Target:** $\ge 90.0\%$ |
| `KPI-OUT-03` | **Warehouse Dispatch Time** | $\text{AVG}(\text{shipments.dispatch\_hours})$ | Rolling 30 Days | `shipments`, `warehouses` | Mean pick-pack-manifest duration across all manifested and dispatched shipments. **Target:** $\le 8.0\text{ Hours}$ |
| `KPI-OUT-04` | **Order Cancellation Rate %** | $\frac{\text{COUNT}(\text{Orders where } \text{status} = \text{'CANCELLED'})}{\text{COUNT}(\text{Total Orders})} \times 100$ | Rolling 30 Days | `orders` | Percentage of orders cancelled due to SLA delay, bin short-pick, or COD timeout. **Target:** $\le 2.5\%$ |
| `KPI-OUT-05` | **Customer Return & Exchange Rate %** | $\frac{\text{COUNT}(\text{Return & Exchange RMA Cases})}{\text{COUNT}(\text{Delivered Order Line Items})} \times 100$ | Rolling 30 Days | `returns`, `order_items`, `return_reasons` | Ratio of RMA requests to delivered order line items. **Target:** $\le 18.0\%$ |

---

## 2. Tableau Dashboard Connection & Workbook Specification

### 2.1 Connecting Tableau Desktop / Tableau Cloud
1. **Direct PostgreSQL Connection:**
   - Open Tableau Desktop -> **Connect -> To a Server -> PostgreSQL**.
   - Host: `localhost` (or production DB host), Port: `5432`, Database: `threadflow`.
   - Drag any of the 5 pre-built views (`vw_tableau_procurement_scorecard`, `vw_tableau_category_merchandising`, `vw_tableau_inventory_intelligence`, `vw_tableau_outbound_fulfilment`, `vw_tableau_returns_analysis`) onto the canvas.
2. **File Extract Connection (Zero-Config):**
   - Open Tableau Desktop -> **Connect -> To a File -> Microsoft Excel / Text File**.
   - Select the pre-generated files in `deliverables/tableau/extracts/`.

### 2.2 Tableau Workbook Sheet Specifications
- **Sheet 1: Supplier Lead-Time Variance & Fill-Rate Bullet Chart (`vw_tableau_procurement_scorecard`)**
  - Columns: `AVG(actual_avg_lead_time_days)` with Reference Line at `AVG(contracted_lead_time_days)`.
  - Rows: `supplier_name` grouped by `supplier_tier`.
  - Color: `on_time_delivery_rate` stepped palette (Red `<80%`, Ochre `80–90%`, Forest Green `>90%`).
- **Sheet 2: Warehouse Stock Cover & Aged Working Capital Treemap (`vw_tableau_inventory_intelligence`)**
  - Size: `SUM(aged_excess_value_inr)`.
  - Color: `stock_status` (`STOCKOUT`, `LOW_STOCK`, `HEALTHY`, `EXCESS`, `SLOW_MOVING`).
  - Detail: `warehouse_code`, `sku`.
- **Sheet 3: Outbound FC Processing Bottleneck & Carrier SLA Matrix (`vw_tableau_outbound_fulfilment` + `vw_tableau_returns_analysis`)**
  - Dual-axis bar/line comparing `AVG(dispatch_hours)` against `SLA (12.0h)` and `Return Rate %` by `reason_category` (`SIZE_FIT`, `CATALOGUE_MISMATCH`, `QUALITY_DEFECT`).
