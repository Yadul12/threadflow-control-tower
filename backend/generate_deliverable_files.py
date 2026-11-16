import os
import csv
import openpyxl
from openpyxl.styles import Font, PatternFill
from app.database import engine, Base, SessionLocal
from app.seed import seed_database
from app.routers.analytics_ai_sheets import (
    TEMPLATE_SPECS,
    download_tableau_extract,
    export_operational_report,
)
from app.models import Supplier, Category, Warehouse, Product, PurchaseOrder, Inventory, Order, Shipment, ReturnRecord, ReturnReason

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(ROOT_DIR, "deliverables", "spreadsheets", "templates")
EXPORTS_DIR = os.path.join(ROOT_DIR, "deliverables", "spreadsheets", "exports")
TABLEAU_DIR = os.path.join(ROOT_DIR, "deliverables", "tableau", "extracts")


def save_csv_and_xlsx(headers, rows, folder, basename):
    os.makedirs(folder, exist_ok=True)
    csv_path = os.path.join(folder, f"{basename}.csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    xlsx_path = os.path.join(folder, f"{basename}.xlsx")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = basename[:31]
    ws.append(headers)
    fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    font = Font(color="FFFFFF", bold=True)
    for idx in range(1, len(headers) + 1):
        c = ws.cell(row=1, column=idx)
        c.fill = fill
        c.font = font
    for r in rows:
        ws.append(r)
    wb.save(xlsx_path)


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        res = seed_database(db, force_reset=True)
        print("Database seeded:", res)

        # 1. Save validated import templates
        for entity, spec in TEMPLATE_SPECS.items():
            save_csv_and_xlsx(spec["headers"], spec["sample_rows"], TEMPLATES_DIR, f"threadflow_{entity}_import_template")

        # 2. Save exported operational scorecards & reports
        sups = {s.id: s.name for s in db.query(Supplier).all()}
        whs = {w.id: w.code for w in db.query(Warehouse).all()}
        prods = {p.id: p for p in db.query(Product).all()}
        crs = {c.id: c.name for c in db.query(Carrier).all()} if False else {}
        ords = {o.id: o.order_number for o in db.query(Order).all()}
        rrs = {r.id: r for r in db.query(ReturnReason).all()}

        # Supplier Scorecard
        s_rows = [[s.code, s.name, s.tier, s.category_specialization, s.city, s.contracted_lead_time_days, s.actual_avg_lead_time_days, s.on_time_delivery_rate, s.fill_rate, s.quality_pass_rate, s.issue_count, s.status] for s in db.query(Supplier).all()]
        save_csv_and_xlsx(["Supplier Code", "Supplier Name", "Tier", "Specialization", "City", "Contracted Lead Time", "Actual Lead Time", "OTD %", "Fill Rate %", "Quality Pass %", "Issues", "Status"], s_rows, EXPORTS_DIR, "supplier_performance_scorecard")
        save_csv_and_xlsx(["supplier_code", "supplier_name", "tier", "category_specialization", "city", "contracted_lead_time_days", "actual_avg_lead_time_days", "on_time_delivery_rate", "fill_rate", "quality_pass_rate", "issue_count", "status"], s_rows, TABLEAU_DIR, "vw_tableau_procurement_scorecard")

        # Procurement Report
        p_rows = [[p.po_number, sups.get(p.supplier_id, ""), whs.get(p.warehouse_id, ""), p.status, p.order_date.isoformat(), p.expected_delivery_date.isoformat(), p.actual_delivery_date.isoformat() if p.actual_delivery_date else "", p.total_ordered_qty, p.total_received_qty, p.pending_qty, p.discrepancy_qty, p.total_value_inr, p.delay_days] for p in db.query(PurchaseOrder).all()]
        save_csv_and_xlsx(["PO Number", "Supplier", "Warehouse", "Status", "Order Date", "Expected Delivery", "Actual Delivery", "Ordered Qty", "Received Qty", "Pending Qty", "Discrepancy Qty", "Total Value INR", "Delay Days"], p_rows, EXPORTS_DIR, "procurement_report")

        # Stockout Report
        st_rows = [[whs.get(i.warehouse_id, ""), prods[i.product_id].sku, prods[i.product_id].name, i.on_hand_qty, i.reserved_qty, i.available_qty, i.in_transit_qty, i.avg_daily_sales_7d, i.forecast_daily_demand, i.reorder_point_qty, i.stock_status] for i in db.query(Inventory).filter(Inventory.stock_status.in_(["STOCKOUT", "LOW_STOCK"])).all() if i.product_id in prods]
        save_csv_and_xlsx(["Warehouse", "SKU", "Product Name", "On Hand", "Reserved", "Available", "In Transit", "7d ADS", "Forecast Daily Demand", "Reorder Point", "Status"], st_rows, EXPORTS_DIR, "stockout_report")

        # Inventory Ageing & Tableau Inventory Extract
        ag_rows = [[whs.get(i.warehouse_id, ""), prods[i.product_id].sku, prods[i.product_id].name, i.on_hand_qty, i.available_qty, i.age_bucket_0_30_qty, i.age_bucket_31_60_qty, i.age_bucket_61_90_qty, i.age_bucket_90_plus_qty, round((i.age_bucket_61_90_qty + i.age_bucket_90_plus_qty) * prods[i.product_id].cost_price, 2), i.days_of_cover, i.sell_through_pct, i.turnover_ratio, i.stock_status] for i in db.query(Inventory).all() if i.product_id in prods]
        save_csv_and_xlsx(["Warehouse", "SKU", "Product Name", "On Hand", "Available", "0-30d Qty", "31-60d Qty", "61-90d Qty", "90+d Qty", "Aged 60+d Value INR", "Days of Cover", "Sell Through %", "Turnover Ratio", "Status"], ag_rows, EXPORTS_DIR, "inventory_ageing_report")
        save_csv_and_xlsx(["warehouse_code", "sku", "product_name", "on_hand_qty", "available_qty", "age_0_30_qty", "age_31_60_qty", "age_61_90_qty", "age_90_plus_qty", "aged_excess_value_inr", "days_of_cover", "sell_through_pct", "turnover_ratio", "stock_status"], ag_rows, TABLEAU_DIR, "vw_tableau_inventory_intelligence")

        # Delivery Performance & Tableau Outbound Extract
        dl_rows = [[sh.awb_number, ords.get(sh.order_id, ""), whs.get(sh.warehouse_id, ""), sh.status, sh.promised_delivery_date.isoformat(), sh.actual_delivery_date.isoformat() if sh.actual_delivery_date else "", sh.dispatch_hours, sh.delay_hours, "YES" if sh.on_time else "NO", sh.current_hub, sh.exception_code or ""] for sh in db.query(Shipment).all()]
        save_csv_and_xlsx(["AWB Number", "Order Number", "Warehouse", "Status", "Promised Date", "Actual Date", "Dispatch Hours", "Delay Hours", "On Time", "Current Hub", "Exception Code"], dl_rows, EXPORTS_DIR, "delivery_performance_report")
        save_csv_and_xlsx(["awb_number", "order_number", "warehouse_code", "shipment_status", "promised_delivery_date", "actual_delivery_date", "dispatch_hours", "delay_hours", "on_time", "current_hub", "exception_code"], dl_rows, TABLEAU_DIR, "vw_tableau_outbound_fulfilment")

        # Return Analysis & Tableau Returns Extract
        ret_rows = [[r.rma_number, ords.get(r.order_id, ""), prods[r.product_id].sku if r.product_id in prods else "", r.request_type, r.status, rrs[r.return_reason_id].code if r.return_reason_id in rrs else "", rrs[r.return_reason_id].category if r.return_reason_id in rrs else "", r.refund_amount_inr, r.refund_status, "YES" if r.restock_eligible else "NO"] for r in db.query(ReturnRecord).all()]
        save_csv_and_xlsx(["RMA Number", "Order Number", "SKU", "Request Type", "Status", "Reason Code", "Reason Category", "Refund INR", "Refund Status", "Restock Eligible"], ret_rows, EXPORTS_DIR, "return_analysis_report")
        save_csv_and_xlsx(["rma_number", "order_number", "sku", "request_type", "status", "reason_code", "reason_category", "refund_amount_inr", "refund_status", "restock_eligible"], ret_rows, TABLEAU_DIR, "vw_tableau_returns_analysis")

        print("All templates, export reports, and Tableau extracts generated successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
