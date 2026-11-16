# THREADFLOW — Jira, Agile & Scrum Product Delivery Framework

**Project Key:** `TFLOW`  
**Board Type:** Scrum (Two-Week Sprints, Story Point Estimation via Fibonacci Scale)  
**Jira Integration Disclosure:** Live Jira Cloud instance credentials are not connected in this local environment. A complete **Jira-compatible CSV import file (`jira_backlog_import.csv`)** is generated alongside this specification for one-click import via *Jira Settings -> System -> External System Import -> CSV*.

---

## 1. Epics, User Stories, Acceptance Criteria & Task Breakdown

### EPIC 1: Procurement and Catalogue Intelligence (`TFLOW-EP1`)
- **Business Objective:** Eliminate supplier lead-time opacity, track purchase order GRN discrepancies, enforce pre-listing SKU catalogue completeness ($\ge 95\%$), and protect category gross margins.
- **Release Milestone:** `v1.0-M1 (Inbound Control Foundation)`

| Issue Key | User Story | Business Requirement | Acceptance Criteria (Given/When/Then) | Priority | Story Points | Dependencies | Dev Tasks | QA Tasks |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `TFLOW-101` | As a **Procurement Lead**, I want to view a consolidated supplier scorecard with contracted vs actual lead times, OTD %, fill rate, and historical quality issues so that I can hold underperforming mills accountable. | Track supplier SLA variance and log operational quality incidents. | **Given** 12 active/audit suppliers, **When** viewing Supplier Register or logging an incident, **Then** lead-time variance and issue count recalculate and persist in PostgreSQL. | Highest | 5 | Schema `suppliers` | Build `/api/inbound/suppliers` GET/POST/PATCH + Scorecard drawer. | Verify supplier creation, status toggle (`ON_HOLD`), and issue log persistence. |
| `TFLOW-102` | As a **Procurement Lead**, I want to create Purchase Orders, record supplier acknowledgements, and log Goods Receipt Notes (GRN) with partial/rejected quantities so that warehouse inventory and pending quantities stay accurate. | Full PO lifecycle (`ISSUED` -> `ACKNOWLEDGED` -> `DELAYED` / `PARTIALLY_RECEIVED` / `RECEIVED`) linked to `inventory` and `stock_movements`. | **Given** an issued PO, **When** recording a partial or full GRN receipt, **Then** `received_qty`, `pending_qty`, and `discrepancy_qty` update and a `GRN_INBOUND` stock movement increments warehouse `on_hand_qty`. | Highest | 8 | `TFLOW-101`, `warehouses` | Implement `/api/inbound/purchase-orders` & `/status` PATCH with atomic inventory update. | Test PO creation, delay flagging, and GRN stock movement accuracy. |
| `TFLOW-103` | As a **Category Merchandiser**, I want to audit SKU catalogue completeness scores, identify missing size charts/fabric care/images, and clear duplicate SKU flags so that incomplete listings do not inflate customer fit returns. | Automated 0–100% completeness scoring across 240 SKUs with inline remediation. | **Given** an incomplete SKU (<100%), **When** attaching a size chart, fabric care spec, or resolving a duplicate flag, **Then** `completeness_score` and `missing_fields_json` recompute immediately. | High | 5 | `products`, `product_attributes` | Build `compute_completeness()` engine and `/api/inbound/catalogue` PATCH endpoint. | Assert completeness formula weights (25%x4 - 20% duplicate penalty). |
| `TFLOW-104` | As a **Category Merchandiser**, I want to manage SKU-level MRP, discounts, and promotional campaigns with real-time gross margin guardrails so that discounting does not breach category margin targets. | Real-time GST-adjusted gross margin calculation and price history audit log. | **Given** a SKU and category target margin, **When** updating discount % or selling price, **Then** `gross_margin_pct` updates and flags `MARGIN_BREACH` if more than 5% below target. | High | 5 | `TFLOW-103`, `promotions` | Build `/api/inbound/pricing` and `/promotions` endpoints + UI margin badges. | Validate GST net-revenue margin math and promotion uplift calculation. |

---

### EPIC 2: Inventory and Replenishment Intelligence (`TFLOW-EP2`)
- **Business Objective:** Prevent high-velocity core-size stockouts, expose aged 60+ day excess inventory capital, and provide transparent moving-average demand forecasting with one-click PO generation.
- **Release Milestone:** `v1.5-M2 (Inventory & Forecasting Engine)`

| Issue Key | User Story | Business Requirement | Acceptance Criteria (Given/When/Then) | Priority | Story Points | Dependencies | Dev Tasks | QA Tasks |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `TFLOW-201` | **As a warehouse manager, I want to view products at risk of stockout so that I can initiate replenishment before orders are affected.** | Real-time visibility into `on_hand_qty`, `reserved_qty`, `available_qty`, `in_transit_qty`, and `days_of_cover` across all 4 regional warehouses. | **Given** 480 SKU-Warehouse inventory nodes, **When** filtering by `STOCKOUT` or `LOW_STOCK` and clicking *Convert to PO*, **Then** an `ISSUED` PO is created for the supplier and `in_transit_qty` increments. | Highest | 8 | `TFLOW-102` | Build `/api/inventory/overview`, `/demand-replenishment`, and `/replenishment/{id}/create-po`. | Test stockout filtering and one-click replenishment PO creation. |
| `TFLOW-202` | As an **Inventory Planner**, I want transparent 7-day and 30-day weighted moving average demand forecasts, safety stock, and reorder points with documented methodological limitations so that I can trust replenishment recommendations. | Deterministic WMA formula ($0.6 \times \text{ADS}_{7\text{d}} + 0.4 \times \text{ADS}_{30\text{d}}$), safety stock, and explicit limitation banner. | **Given** SKU velocity history, **When** opening Demand & Replenishment, **Then** exact formulas and limitations are displayed alongside recommended order quantities. | High | 5 | `TFLOW-201` | Implement WMA forecast & ROP calculator in `inventory.py`. | Verify safety stock, ROP, and ROQ calculations against unit tests. |
| `TFLOW-203` | As an **Inventory Planner**, I want to analyse inventory turnover, sell-through rates, and ageing buckets (`0-30d`, `31-60d`, `61-90d`, `90d+`) and execute cycle-count adjustments so that aged capital can be cleared. | Category-level performance rollup and auditable `StockMovement` ledger. | **Given** excess/slow-moving SKUs, **When** viewing Inventory Performance or posting `/api/inventory/adjust`, **Then** ageing values and stock statuses update accurately. | Medium | 5 | `TFLOW-201` | Build `/api/inventory/performance` and `/api/inventory/adjust` endpoints. | Test positive/negative cycle count adjustments and status transitions. |

---

### EPIC 3: Fulfilment and Returns Intelligence (`TFLOW-EP3`)
- **Business Objective:** Resolve warehouse picking/packing bottlenecks, monitor carrier on-time delivery SLAs, streamline RMA return/exchange QC and refund simulation, and govern cross-chain operational exceptions.
- **Release Milestone:** `v2.4-GA (Outbound, BI, GenAI & Spreadsheet Control Tower)`

| Issue Key | User Story | Business Requirement | Acceptance Criteria (Given/When/Then) | Priority | Story Points | Dependencies | Dev Tasks | QA Tasks |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `TFLOW-301` | As a **Warehouse Ops Manager**, I want to manage order allocation and advance picking, packing, and dispatch statuses with carrier AWB assignment so that orders meet the 12-hour dispatch SLA. | End-to-end order and shipment state machine with multi-step tracking timelines. | **Given** an order in `PICKING` or `PACKED`, **When** advancing to `DISPATCHED` or `DELIVERED`, **Then** the linked `Shipment` timeline and timestamps update automatically. | Highest | 8 | `TFLOW-201` | Build `/api/outbound/orders`, `/fulfilment`, and `/shipments/{id}` PATCH. | Test order lifecycle transitions, cancellation un-reservation, and shipment updates. |
| `TFLOW-302` | As a **CX & Returns Analyst**, I want to classify customer returns by root cause, record QC inspection outcomes, restock eligible items, and simulate refund or exchange processing so that reverse leakage is minimized. | RMA workflow (`REQUESTED` -> `QC_PASSED`/`QC_FAILED` -> `REFUND_PROCESSED`/`EXCHANGE_DISPATCHED`) linked to `inventory`. | **Given** an open RMA case, **When** marking `QC_PASSED`, **Then** `RETURN_RESTOCK` adds +1 unit to warehouse inventory and initiates refund/exchange status. | High | 5 | `TFLOW-301` | Build `/api/outbound/returns` GET/PATCH + SKU return trend aggregator. | Verify QC_PASSED inventory restock and refund status simulation. |
| `TFLOW-303` | As an **Operations Director**, I want to assign, escalate, and resolve cross-chain operational exceptions and query an evidence-grounded GenAI Assistant so that warehouse or supplier bottlenecks are diagnosed using real records. | Exception queue (`INBOUND_PO`, `CATALOGUE_QUALITY`, `INVENTORY_RISK`, `WAREHOUSE_BOTTLENECK`, `DELIVERY_SLA`, `RETURN_SPIKE`) + SQL-grounded Assistant. | **Given** an active exception or user query (*"Why is the delivery performance of Warehouse A declining?"*), **Then** the system retrieves verified records (`WH-A-BLR`, `EXC-2026-001`) and separates facts from hypotheses. | High | 8 | All Epics | Build `/api/outbound/exceptions`, `/api/ai/assistant`, Mixpanel adapter & XLSX workflows. | Test exception assignment/resolution, AI evidence payload, and CSV/XLSX import/export. |

---

## 2. Three Two-Week Development Sprints (Scrum Execution Log)

### Sprint 1 (Weeks 1–2): Inbound Procurement, Catalogue Quality & Relational Core
- **Sprint Goal:** Deliver the 19-table PostgreSQL/SQLAlchemy relational schema, coherent synthetic fashion dataset, and Workspace A (Suppliers, PO Register, Catalogue Completeness, Pricing & Promotions).
- **Committed Backlog:** `TFLOW-101` (5 SP), `TFLOW-102` (8 SP), `TFLOW-103` (5 SP), `TFLOW-104` (5 SP) — **Total: 23 SP**.
- **Daily Standup Highlights:**
  - *Day 3:* Completed 19-table SQLAlchemy schema and composite indexes; seeded 12 suppliers and 240 fashion SKUs.
  - *Day 6:* Implemented PO creation and GRN partial receipt handler updating `inventory.on_hand_qty` and `stock_movements`.
  - *Day 9:* Completed Catalogue Completeness 0–100% calculator and GST-adjusted Gross Margin guardrail alerts.
- **Sprint Review:** Demonstrated live supplier creation, PO acknowledgement, GRN discrepancy logging, and SKU size-chart remediation raising completeness from 75% to 100%.
- **Sprint Retrospective:**
  - *Went Well:* Enforcing referential integrity in the seed script prevented orphaned PO items.
  - *Improvement Action:* Add inline confirmation feedback banners on every table row action in Sprint 2.

### Sprint 2 (Weeks 3–4): Inventory Intelligence, WMA Forecasting & Outbound Fulfilment
- **Sprint Goal:** Deliver Workspace B (Inventory Overview, Transparent 7d/30d WMA Forecasting, One-Click PO Replenishment, Ageing Analysis) and Workspace C Order/Shipment/Returns workflows.
- **Committed Backlog:** `TFLOW-201` (8 SP), `TFLOW-202` (5 SP), `TFLOW-203` (5 SP), `TFLOW-301` (8 SP), `TFLOW-302` (5 SP) — **Total: 31 SP**.
- **Daily Standup Highlights:**
  - *Day 14:* Implemented weighted moving average demand engine and one-click replenishment-to-PO conversion.
  - *Day 17:* Built Warehouse A (`WH-A-BLR`) bottleneck scenario (14.8h processing time vs 12.0h SLA) and 5-step AWB shipment timeline inspector.
  - *Day 19:* Completed RMA return QC workflow with automatic +1 unit restock on `QC_PASSED`.
- **Sprint Review:** Demonstrated end-to-end flow from a stockout alert at `WH-A-BLR` to PO generation, plus order dispatch and RMA refund simulation.
- **Sprint Retrospective:**
  - *Went Well:* Documenting moving-average forecast limitations directly in the UI clarified planner expectations.
  - *Improvement Action:* Correlate SKU return trends directly with Catalogue Completeness scores in Sprint 3.

### Sprint 3 (Weeks 5–6): Exception Command Queue, Mixpanel Telemetry, Tableau Views, GenAI Assistant & Spreadsheets
- **Sprint Goal:** Deliver the Unified 14-KPI Control Tower, Cross-Chain Exception Queue, Mixpanel + Local Event Adapter, 5 Tableau SQL Views/Extracts, Evidence-Grounded GenAI Assistant, and CSV/XLSX Import/Export Workbench.
- **Committed Backlog:** `TFLOW-303` (8 SP) + Analytics, Tableau, Spreadsheets & Automated QA Suite — **Total: 21 SP**.
- **Sprint Review & Release Notes (`v2.4.0-GA`):**
  - All 14 Control Tower KPIs live with explicit formulas, reporting periods, and source tables.
  - Mixpanel dual-adapter tracking all 11 operational events with role, workspace, SKU, supplier, and warehouse properties.
  - GenAI Operations Assistant answering warehouse decline, supplier complaints, return drivers, and inventory risk queries with strict SQL record citations.
  - Validated CSV/XLSX import templates and export reports live with row-level error diagnostics.
