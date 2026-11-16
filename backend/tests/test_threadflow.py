import io
import csv
import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal, Base, engine
from app.seed import seed_database


@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_database(db, force_reset=True)
    db.close()
    with TestClient(app) as c:
        yield c


def test_01_supplier_creation_and_updates(client: TestClient):
    # Create a new supplier
    resp = client.post("/api/inbound/suppliers", json={
        "code": "SUP-TEST-099",
        "name": "Madurai Organic Twill Mills",
        "tier": "TIER_1",
        "category_specialization": "Men's Casual Shirts",
        "contact_name": "Senthil Kumar",
        "contact_email": "senthil@maduraitwill.example.in",
        "contact_phone": "+91-452-2345678",
        "city": "Madurai",
        "state": "Tamil Nadu",
        "payment_terms": "NET_45",
        "contracted_lead_time_days": 15,
    })
    assert resp.status_code == 200
    data = resp.json()
    sup_id = data["supplier_id"]

    # Update supplier status and log an issue
    patch_resp = client.patch(f"/api/inbound/suppliers/{sup_id}", json={
        "status": "UNDER_AUDIT",
        "actual_avg_lead_time_days": 18.5,
        "new_issue_note": "Fabric shrinkage exceeded 3% tolerance on initial lot.",
        "new_issue_severity": "HIGH",
    })
    assert patch_resp.status_code == 200
    p_data = patch_resp.json()
    assert p_data["supplier_status"] == "UNDER_AUDIT"
    assert p_data["issue_count"] == 1

    # Verify detail retrieval
    det = client.get(f"/api/inbound/suppliers/{sup_id}").json()
    assert det["supplier"]["code"] == "SUP-TEST-099"
    assert len(det["supplier"]["issue_history"]) == 1


def test_02_purchase_order_status_changes_and_grn(client: TestClient):
    # Create PO
    create_resp = client.post("/api/inbound/purchase-orders", json={
        "supplier_id": 1,
        "warehouse_id": 1,
        "expected_delivery_days": 14,
        "notes": "Automated test replenishment PO",
        "created_by": "QA Engineer",
        "items": [{"product_id": 1, "ordered_qty": 100}],
    })
    assert create_resp.status_code == 200
    po_id = create_resp.json()["po_id"]
    assert create_resp.json()["total_ordered_qty"] == 100

    # Acknowledge PO
    ack_resp = client.patch(f"/api/inbound/purchase-orders/{po_id}/status", json={
        "status": "ACKNOWLEDGED",
        "supplier_acknowledged": True,
    })
    assert ack_resp.status_code == 200
    assert ack_resp.json()["new_status"] == "ACKNOWLEDGED"

    # Receive goods with discrepancy (GRN reconciliation)
    grn_resp = client.patch(f"/api/inbound/purchase-orders/{po_id}/status", json={
        "status": "RECEIVED",
        "received_ratio": 1.0,
        "discrepancy_qty": 5,
        "discrepancy_reason": "5 units rejected for seam stain at gate-in",
    })
    assert grn_resp.status_code == 200
    g_data = grn_resp.json()
    assert g_data["total_received_qty"] == 95
    assert g_data["discrepancy_qty"] == 5
    assert g_data["pending_qty"] == 0


def test_03_catalogue_validation_and_remediation(client: TestClient):
    cat_resp = client.get("/api/inbound/catalogue?only_issues=true")
    assert cat_resp.status_code == 200
    issues = cat_resp.json()["catalogue"]
    assert len(issues) > 0

    target = issues[0]
    prod_id = target["id"]
    assert target["completeness_score"] < 100.0

    # Remediate all missing catalogue attributes
    fix_resp = client.patch(f"/api/inbound/catalogue/{prod_id}", json={
        "description": "Complete verified garment specification with chest, shoulder, and length grading.",
        "has_description": True,
        "image_count": 6,
        "has_size_chart": True,
        "has_fabric_care": True,
        "is_duplicate_flag": False,
    })
    assert fix_resp.status_code == 200
    f_data = fix_resp.json()
    assert f_data["completeness_score"] == 100.0
    assert f_data["missing_fields"] == []


def test_04_pricing_calculations_and_promotions(client: TestClient):
    pricing_list = client.get("/api/inbound/pricing").json()["pricing_ledger"]
    sku_item = pricing_list[0]
    prod_id = sku_item["id"]

    # Update MRP and Discount % and verify GST-adjusted Gross Margin %
    upd = client.patch(f"/api/inbound/pricing/{prod_id}", json={
        "mrp": 2000.0,
        "cost_price": 750.0,
        "discount_pct": 10.0,
        "reason": "QA Margin Test Update",
    })
    assert upd.status_code == 200
    u_data = upd.json()
    assert u_data["selling_price"] == 1800.0
    # Net revenue = 1800 / 1.12 = 1607.1428; GM% = (1607.1428 - 750) / 1607.1428 * 100 = 53.33%
    assert 53.0 <= u_data["gross_margin_pct"] <= 53.6

    # Create promotion
    promo_resp = client.post("/api/inbound/promotions", json={
        "code": "PROMO-QA-TEST",
        "name": "QA Winter Preview Sale",
        "campaign_type": "SEASONAL_SALE",
        "category_id": 1,
        "discount_pct": 15.0,
        "start_date": "2026-11-18",
        "end_date": "2026-11-30",
        "status": "ACTIVE",
        "baseline_daily_units": 100.0,
        "promo_daily_units": 155.0,
    })
    assert promo_resp.status_code == 200


def test_05_inventory_calculations_and_adjustments(client: TestClient):
    ov = client.get("/api/inventory/overview").json()
    assert len(ov["warehouses"]) == 4
    inv_item = ov["inventory"][0]
    inv_id = inv_item["id"]
    initial_on_hand = inv_item["on_hand_qty"]

    adj_resp = client.post("/api/inventory/adjust", json={
        "inventory_id": inv_id,
        "quantity_delta": 50,
        "movement_type": "CYCLE_COUNT_ADJ",
        "notes": "Found 50 units in secondary reserve rack",
        "performed_by": "QA Auditor",
    })
    assert adj_resp.status_code == 200
    assert adj_resp.json()["on_hand_qty"] == initial_on_hand + 50


def test_06_replenishment_suggestions_and_po_conversion(client: TestClient):
    rep = client.get("/api/inventory/demand-replenishment?only_actionable=true").json()
    assert "methodology_documentation" in rep
    assert len(rep["methodology_documentation"]["documented_limitations"]) >= 3
    recs = rep["recommendations"]
    assert len(recs) > 0

    target_rec = recs[0]
    inv_id = target_rec["inventory_id"]
    conv_resp = client.post(f"/api/inventory/replenishment/{inv_id}/create-po", json={
        "override_qty": 120,
        "created_by": "QA Inventory Planner",
    })
    assert conv_resp.status_code == 200
    c_data = conv_resp.json()
    assert c_data["status"] == "po_created"
    assert c_data["ordered_qty"] == 120
    assert c_data["new_in_transit_qty"] >= 120


def test_07_order_lifecycle_transitions(client: TestClient):
    orders = client.get("/api/outbound/orders").json()["orders"]
    picking_order = next((o for o in orders if o["status"] in ("PENDING", "ALLOCATED", "PICKING", "PACKED")), orders[0])
    ord_id = picking_order["id"]

    disp_resp = client.patch(f"/api/outbound/orders/{ord_id}/status", json={
        "status": "DISPATCHED",
        "carrier_id": 1,
    })
    assert disp_resp.status_code == 200
    assert disp_resp.json()["new_status"] == "DISPATCHED"


def test_08_shipment_status_updates(client: TestClient):
    fulf = client.get("/api/outbound/fulfilment").json()
    sh = fulf["shipments"][0]
    sh_id = sh["id"]

    upd = client.patch(f"/api/outbound/shipments/{sh_id}", json={
        "status": "DELIVERED",
        "current_hub": "Customer Doorstep POD",
        "delay_hours": 0.0,
        "note": "Delivered during QA test run",
    })
    assert upd.status_code == 200
    assert upd.json()["shipment_status"] == "DELIVERED"
    assert upd.json()["on_time"] is True


def test_09_delivery_sla_calculations(client: TestClient):
    deliv = client.get("/api/outbound/delivery-intelligence").json()
    wh_breakdown = deliv["warehouse_sla_breakdown"]
    assert len(wh_breakdown) == 4
    wh_a = next(w for w in wh_breakdown if w["warehouse_code"] == "WH-A-BLR")
    assert wh_a["avg_dispatch_hours"] > 10.0


def test_10_returns_and_exchanges_workflow(client: TestClient):
    ret_data = client.get("/api/outbound/returns").json()
    assert len(ret_data["returns"]) > 0
    assert len(ret_data["reason_breakdown"]) > 0

    open_ret = next((r for r in ret_data["returns"] if r["status"] in ("REQUESTED", "APPROVED")), ret_data["returns"][0])
    ret_id = open_ret["id"]

    qc_resp = client.patch(f"/api/outbound/returns/{ret_id}", json={
        "status": "QC_PASSED",
        "qc_notes": "Garment verified clean and tags intact",
        "refund_status": "PROCESSED",
    })
    assert qc_resp.status_code == 200
    assert qc_resp.json()["new_status"] == "QC_PASSED"
    assert qc_resp.json()["refund_status"] == "PROCESSED"


def test_11_exception_assignment_and_resolution(client: TestClient):
    ex_list = client.get("/api/outbound/exceptions").json()["exceptions"]
    assert len(ex_list) >= 25
    target_ex = ex_list[0]
    ex_id = target_ex["id"]

    upd = client.patch(f"/api/outbound/exceptions/{ex_id}", json={
        "status": "RESOLVED",
        "assigned_to": "Siddharth Nair (Verified)",
        "resolution_notes": "Zone-C belt motor replaced and backlog cleared.",
    })
    assert upd.status_code == 200
    assert upd.json()["new_status"] == "RESOLVED"


def test_12_sql_kpi_calculations_and_tableau_views(client: TestClient):
    kpi_resp = client.get("/api/control-tower/kpis").json()
    kpis = kpi_resp["kpis"]
    assert len(kpis) == 14
    for k in kpis:
        assert "formula" in k and len(k["formula"]) > 5
        assert "reporting_period" in k
        assert "source_tables" in k and len(k["source_tables"]) >= 1
        assert "calculation_method" in k

    sql_views = client.get("/api/analytics/sql-views").json()
    assert len(sql_views["sql_views_catalog"]) == 5

    # Test Tableau CSV extract download
    ext_resp = client.get("/api/analytics/tableau/extract/vw_tableau_inventory_intelligence?format=csv")
    assert ext_resp.status_code == 200
    assert "warehouse_code" in ext_resp.text


def test_13_export_import_mixpanel_and_genai_workflows(client: TestClient):
    # 1. Export XLSX report
    exp_resp = client.get("/api/spreadsheets/export/supplier_scorecard?format=xlsx")
    assert exp_resp.status_code == 200
    assert len(exp_resp.content) > 1000

    # 2. Import CSV with a valid supplier row and an invalid row to test row-level validation
    csv_buf = io.StringIO()
    writer = csv.writer(csv_buf)
    writer.writerow(["code", "name", "tier", "category_specialization", "contact_name", "contact_email", "contact_phone", "city", "state", "payment_terms", "contracted_lead_time_days"])
    writer.writerow(["SUP-IMP-201", "Valid Imported Mills", "TIER_1", "Knits", "Rajesh", "rajesh@validmills.example.in", "+91-9900112233", "Surat", "Gujarat", "NET_45", "16"])
    writer.writerow(["SUP-IMP-BAD", "Invalid Email Mill", "TIER_2", "Denim", "Suresh", "not-an-email", "+91-9900112244", "Mumbai", "Maharashtra", "NET_30", "-5"])

    imp_resp = client.post(
        "/api/spreadsheets/import/suppliers",
        files={"file": ("suppliers_upload.csv", csv_buf.getvalue().encode("utf-8"), "text/csv")},
    )
    assert imp_resp.status_code == 200
    imp_data = imp_resp.json()
    assert imp_data["imported_count"] == 1
    assert imp_data["error_count"] == 1
    assert imp_data["errors"][0]["row"] == 3

    # 3. Mixpanel / Local Analytics Tracking
    tr_resp = client.post("/api/analytics/track", json={
        "event_name": "supplier_profile_opened",
        "user_role": "Procurement Lead",
        "workspace": "INBOUND",
        "supplier_id": "SUP-TIR-001",
        "action_status": "COMPLETED",
    })
    assert tr_resp.status_code == 200
    assert tr_resp.json()["delivery_channel"] in ("LOCAL_POSTGRES_ADAPTER", "MIXPANEL_AND_LOCAL")

    # 4. GenAI Evidence-Grounded Assistant (Warehouse A Decline Query)
    ai_resp = client.post("/api/ai/assistant", json={
        "question": "Why is the delivery performance of Warehouse A declining?",
    })
    assert ai_resp.status_code == 200
    ai_data = ai_resp.json()
    assert "WH-A-BLR" in json.dumps(ai_data["relevant_records"])
    assert len(ai_data["observed_patterns"]) >= 2
    assert len(ai_data["investigation_steps"]) >= 2
