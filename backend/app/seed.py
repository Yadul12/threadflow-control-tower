import json
import math
import random
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
from .models import (
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
    Customer,
    Carrier,
    Order,
    OrderItem,
    Shipment,
    ReturnReason,
    ReturnRecord,
    OperationalException,
    AnalyticsEvent,
)

REFERENCE_NOW = datetime(2026, 11, 16, 13, 30, 0)
REFERENCE_TODAY = date(2026, 11, 16)


def compute_completeness(has_desc: bool, img_count: int, has_size_chart: bool, has_fabric_care: bool, is_dup: bool):
    score = 0.0
    missing = []
    if has_desc:
        score += 25.0
    else:
        missing.append("Product Description")

    if img_count >= 4:
        score += 25.0
    elif img_count >= 1:
        score += 12.0
        missing.append("Full Image Gallery (<4 shots)")
    else:
        missing.append("Product Images (0 uploaded)")

    if has_size_chart:
        score += 25.0
    else:
        missing.append("Garment Size Chart")

    if has_fabric_care:
        score += 25.0
    else:
        missing.append("Fabric & Wash Care Spec")

    if is_dup:
        score = max(0.0, score - 20.0)
        missing.append("Duplicate Listing Flag")

    return round(score, 1), missing


def seed_database(db: Session, force_reset: bool = False):
    existing = db.query(Supplier).count()
    if existing > 0 and not force_reset:
        return {"seeded": False, "message": "Database already contains synthetic operational data."}

    if force_reset:
        for model in [
            AnalyticsEvent,
            OperationalException,
            ReturnRecord,
            ReturnReason,
            Shipment,
            OrderItem,
            Order,
            Carrier,
            Customer,
            Promotion,
            StockMovement,
            Inventory,
            PurchaseOrderItem,
            PurchaseOrder,
            ProductAttribute,
            Product,
            Warehouse,
            Category,
            Supplier,
        ]:
            db.query(model).delete()
        db.commit()

    rng = random.Random(20261116)

    # -------------------------------------------------------------------------
    # 1. SUPPLIERS (12 Realistic Fashion & Apparel Manufacturers)
    # -------------------------------------------------------------------------
    supplier_specs = [
        ("SUP-TIR-001", "Kaveri Knitwear Exports Pvt Ltd", "STRATEGIC", "Men's Casual Shirts & Knits", "Aravind Subramanian", "aravind@kaveriknits.example.in", "+91-421-2489102", "Tiruppur", "Tamil Nadu", "NET_45", 14, 15.2, 94.5, 96.8, 98.1, 1, "ACTIVE", [
            {"date": "2026-10-12", "type": "MINOR_SHADE_VARIATION", "severity": "LOW", "summary": "Lot #KK-892 olive pique polo showed 0.4 Delta-E shade variance; accepted under concession."}
        ]),
        ("SUP-BLR-002", "Deccan Loom & Apparel Works", "TIER_1", "Men's Stretch Denim & Chinos", "Vikramaditya Rao", "v.rao@deccanloom.example.in", "+91-80-41298301", "Bengaluru", "Karnataka", "NET_60", 18, 22.4, 81.2, 88.5, 94.0, 4, "ACTIVE", [
            {"date": "2026-10-28", "type": "LEAD_TIME_SLIPPAGE", "severity": "HIGH", "summary": "Indigo enzyme wash line bottleneck delayed 3 POs by 5-7 days."},
            {"date": "2026-11-04", "type": "SHORT_SHIPMENT", "severity": "MEDIUM", "summary": "PO-2026-1018 short-shipped by 110 units across waist 32 and 34."}
        ]),
        ("SUP-SUR-003", "Tapi Silk & Georgette Mills", "STRATEGIC", "Women's Ethnic Kurtas & Sarees", "Harshadbhai Desai", "h.desai@tapisilk.example.in", "+91-261-2339011", "Surat", "Gujarat", "NET_45", 16, 16.5, 93.0, 95.4, 97.2, 1, "ACTIVE", [
            {"date": "2026-09-19", "type": "PACKAGING_BARCODE", "severity": "LOW", "summary": "Polybag EAN stickers smudged on 24 units; relabelled at WH-C-BOM."}
        ]),
        ("SUP-JAI-004", "Rajputana Craft & Block Prints", "TIER_2", "Women's Ethnic Kurtas & Fusion", "Meenakshi Rathore", "m.rathore@rajputanacraft.example.in", "+91-141-2781209", "Jaipur", "Rajasthan", "NET_30", 20, 27.8, 72.5, 83.0, 91.5, 6, "UNDER_AUDIT", [
            {"date": "2026-10-15", "type": "COLOR_FASTNESS_FAILURE", "severity": "HIGH", "summary": "Azo-free indigo block print bled during lab wash test; 320 units quarantined."},
            {"date": "2026-11-02", "type": "UNACKNOWLEDGED_PO", "severity": "HIGH", "summary": "PO-2026-1031 remained unacknowledged for 96 hours past SLA."},
            {"date": "2026-11-09", "type": "SIZE_SPEC_DRIFT", "severity": "MEDIUM", "summary": "Bust grading on Anarkali style narrower than tech-pack by 2.2 cm."}
        ]),
        ("SUP-GGN-005", "Atelier Moda NCR Pvt Ltd", "TIER_1", "Women's Western Dresses & Tops", "Sonalika Kapur", "sonalika@ateliermoda.example.in", "+91-124-4902188", "Gurugram", "Haryana", "NET_45", 15, 16.1, 91.8, 94.2, 96.9, 2, "ACTIVE", [
            {"date": "2026-10-22", "type": "TRIM_SUBSTITUTION", "severity": "LOW", "summary": "Concealed zipper puller substituted with matte nickel without prior approval."}
        ]),
        ("SUP-LUD-006", "Sutlej Merino & Fleece Co", "TIER_1", "Winter Knitwear & Sweatshirts", "Gurpreet Singh Gill", "gsgill@sutlejmerino.example.in", "+91-161-5018290", "Ludhiana", "Punjab", "NET_60", 21, 26.5, 76.4, 86.0, 93.8, 5, "ACTIVE", [
            {"date": "2026-10-30", "type": "YARN_SHORTAGE_DELAY", "severity": "HIGH", "summary": "320 GSM brushed fleece yarn delay pushed AW26 hoodie delivery by 8 days."},
            {"date": "2026-11-08", "type": "PILLING_COMPLAINT", "severity": "MEDIUM", "summary": "Elevated pilling noted on acrylic-blend crewnecks in customer returns."}
        ]),
        ("SUP-NOI-007", "Kinetic Performance Apparel", "STRATEGIC", "Activewear & Athleisure", "Rohan Malhotra", "rohan@kineticactive.example.in", "+91-120-4319822", "Noida", "Uttar Pradesh", "NET_45", 14, 14.4, 96.2, 97.5, 98.6, 0, "ACTIVE", []),
        ("SUP-AGR-008", "Braj Footwear & Vulcanized Sole Ltd", "TIER_1", "Footwear & Sneakers", "Anurag Bansal", "a.bansal@brajfootwear.example.in", "+91-562-2521904", "Agra", "Uttar Pradesh", "NET_45", 22, 24.0, 85.0, 91.2, 94.5, 3, "ACTIVE", [
            {"date": "2026-10-18", "type": "SOLE_BONDING_QC", "severity": "MEDIUM", "summary": "TPR sole edge delamination found in 1.8% of random AQL 2.5 inspection."}
        ]),
        ("SUP-TIR-009", "LittleStar Organic Cottons", "TIER_1", "Kids Apparel & Infantwear", "revathi@littlestar.example.in", "Revathi Krishnan", "+91-421-2209871", "Tiruppur", "Tamil Nadu", "NET_30", 15, 15.8, 92.4, 95.0, 97.8, 1, "ACTIVE", []),
        ("SUP-BOM-010", "Konkan Intimates & Lounge Studio", "TIER_2", "Loungewear & Innerwear", "Nikhil Sawant", "nikhil@konkanintimates.example.in", "+91-22-28910455", "Mumbai", "Maharashtra", "NET_45", 16, 19.2, 84.5, 90.1, 95.2, 2, "ACTIVE", [
            {"date": "2026-11-01", "type": "ELASTIC_WAISTBAND_SPEC", "severity": "MEDIUM", "summary": "Modal lounge pant waistband tension variance reported on Size M."}
        ]),
        ("SUP-CCU-011", "Hooghly Leather & Canvas Craft", "TIER_2", "Accessories & Bags", "Subhashis Chatterjee", "s.chatterjee@hooghlycraft.example.in", "+91-33-24890123", "Kolkata", "West Bengal", "NET_30", 18, 25.1, 74.0, 82.5, 90.4, 5, "ON_HOLD", [
            {"date": "2026-10-20", "type": "HARDWARE_TARNISH", "severity": "HIGH", "summary": "Brass D-rings showed oxidation spots due to missing silica gel packets in transit."},
            {"date": "2026-11-05", "type": "SEVERE_PO_DELAY", "severity": "CRITICAL", "summary": "PO-2026-1029 delayed 11 days; supplier placed ON_HOLD pending CAPA audit."}
        ]),
        ("SUP-CHN-012", "Coromandel Woven Poplin Mills", "STRATEGIC", "Men's Formal & Casual Shirts", "Karthik Narayanan", "karthik@coromandelmills.example.in", "+91-44-28194022", "Chennai", "Tamil Nadu", "NET_60", 14, 14.8, 95.1, 96.4, 98.0, 1, "ACTIVE", []),
    ]

    suppliers = []
    for spec in supplier_specs:
        sup = Supplier(
            code=spec[0],
            name=spec[1],
            tier=spec[2],
            category_specialization=spec[3],
            contact_name=spec[4] if "@" not in spec[4] else spec[5],
            contact_email=spec[5] if "@" in spec[5] else spec[4],
            contact_phone=spec[6],
            city=spec[7],
            state=spec[8],
            payment_terms=spec[9],
            contracted_lead_time_days=spec[10],
            actual_avg_lead_time_days=spec[11],
            on_time_delivery_rate=spec[12],
            fill_rate=spec[13],
            quality_pass_rate=spec[14],
            issue_count=spec[15],
            status=spec[16],
            issue_history_json=json.dumps(spec[17]),
            is_synthetic=True,
        )
        db.add(sup)
        suppliers.append(sup)
    db.flush()

    # -------------------------------------------------------------------------
    # 2. CATEGORIES (10 Fashion & Apparel Merchandising Categories)
    # -------------------------------------------------------------------------
    category_specs = [
        ("CAT-MCS", "Men's Casual Shirts", "MENSWEAR", "Topwear", "AW26", 54.0, 15.5, 0),
        ("CAT-MSD", "Men's Stretch Denim", "MENSWEAR", "Bottomwear", "AW26", 51.0, 19.0, 1),
        ("CAT-WEK", "Women's Ethnic Kurtas", "WOMENSWEAR", "Indianwear", "AW26", 56.0, 21.5, 2),
        ("CAT-WWD", "Women's Western Dresses", "WOMENSWEAR", "Westernwear", "AW26", 58.0, 24.0, 4),
        ("CAT-WKN", "Winter Knitwear & Hoodies", "UNISEX_APPAREL", "Winterwear", "AW26", 53.0, 16.0, 5),
        ("CAT-ACT", "Activewear & Athleisure", "ACTIVEWEAR", "Sports", "AW26", 55.0, 14.0, 6),
        ("CAT-FTW", "Footwear & Sneakers", "FOOTWEAR", "Casual Footwear", "AW26", 49.0, 22.0, 7),
        ("CAT-KID", "Kids Apparel Sets", "KIDS", "Kids Clothing", "AW26", 52.0, 13.5, 8),
        ("CAT-LNG", "Loungewear & Innerwear", "INTIMATES", "Sleep & Lounge", "AW26", 57.0, 11.0, 9),
        ("CAT-ACC", "Accessories & Crossbody Bags", "ACCESSORIES", "Bags & Belts", "AW26", 60.0, 10.5, 10),
    ]

    categories = []
    for cspec in category_specs:
        cat = Category(
            code=cspec[0],
            name=cspec[1],
            department=cspec[2],
            parent_category=cspec[3],
            season=cspec[4],
            target_gross_margin_pct=cspec[5],
            return_benchmark_pct=cspec[6],
        )
        db.add(cat)
        categories.append(cat)
    db.flush()

    # -------------------------------------------------------------------------
    # 3. WAREHOUSES (4 Regional Fulfilment Centres: WH-A-BLR, WH-B-DEL, WH-C-BOM, WH-D-CCU)
    # -------------------------------------------------------------------------
    warehouse_specs = [
        ("WH-A-BLR", "Warehouse A — Bengaluru Peenya Fulfilment Hub", "Bengaluru", "SOUTH", 140000, 129500, 22, 14.8, 12.0, "CRITICAL_BACKLOG", "Siddharth Nair"),
        ("WH-B-DEL", "Warehouse B — Bilaspur NCR Mega Fulfilment Centre", "Gurugram", "NORTH", 180000, 142000, 38, 5.6, 12.0, "NORMAL", "Priyanka Shergill"),
        ("WH-C-BOM", "Warehouse C — Bhiwandi West Regional FC", "Mumbai", "WEST", 160000, 138400, 30, 8.9, 12.0, "ELEVATED", "Mandar Kulkarni"),
        ("WH-D-CCU", "Warehouse D — Dankuni East Fulfilment Centre", "Kolkata", "EAST", 110000, 78200, 24, 5.1, 12.0, "NORMAL", "Anirban Sen"),
    ]

    warehouses = []
    for wspec in warehouse_specs:
        wh = Warehouse(
            code=wspec[0],
            name=wspec[1],
            city=wspec[2],
            region=wspec[3],
            capacity_units=wspec[4],
            utilized_units=wspec[5],
            active_pickers=wspec[6],
            avg_processing_hours=wspec[7],
            sla_dispatch_hours=wspec[8],
            bottleneck_status=wspec[9],
            manager_name=wspec[10],
            is_synthetic=True,
        )
        db.add(wh)
        warehouses.append(wh)
    db.flush()

    # -------------------------------------------------------------------------
    # 4. PRODUCTS & PRODUCT ATTRIBUTES (240 Realistic Fashion SKUs)
    # -------------------------------------------------------------------------
    brands_by_cat = {
        "CAT-MCS": ["Vero Thread", "Harbour Loom", "Northbound Studio"],
        "CAT-MSD": ["Indigo Foundry", "Raw Selvedge Co", "Denim Republic"],
        "CAT-WEK": ["Aurelia Weaves", "Saanjh Heritage", "Zari & Co"],
        "CAT-WWD": ["atelier Lune", "Maison Verve", "Solstice Femme"],
        "CAT-WKN": ["Alpine Knit", "Nordic Fleece", "Warmth & Co"],
        "CAT-ACT": ["Kinetix Pro", "Pulse Stride", "AeroFlex"],
        "CAT-FTW": ["UrbanSole", "StrideCraft", "Veloce Kicks"],
        "CAT-KID": ["Little Acorn", "CloudHopper Kids", "Sunbeam Junior"],
        "CAT-LNG": ["Serene Modal", "CloudRest", "Hush Cotton"],
        "CAT-ACC": ["Tanner & Loom", "Nomad Carry", "Vanguard Goods"],
    }

    style_templates = {
        "CAT-MCS": [("Oxford Button-Down Shirt", "165 GSM", "100% Combed Organic Cotton", "Regular Fit"), ("Linen-Cotton Mandarin Shirt", "150 GSM", "55% Linen 45% Cotton", "Slim Fit"), ("Brushed Twill Overshirt", "220 GSM", "100% Cotton Twill", "Relaxed Fit"), ("Slub Pique Resort Shirt", "180 GSM", "100% Cotton Pique", "Tailored Fit")],
        "CAT-MSD": [("Selvedge Tapered Jeans", "12.5 oz", "98% Cotton 2% Elastane", "Slim Tapered"), ("Athletic Stretch Denim", "11.5 oz", "95% Cotton 3% Elastomultiester 2% Elastane", "Athletic Fit"), ("Vintage Wash Straight Jeans", "13.0 oz", "100% Ring-Spun Cotton", "Straight Fit"), ("Garment-Dyed Stretch Chino", "260 GSM", "97% Cotton 3% Spandex", "Slim Fit")],
        "CAT-WEK": [("Chanderi Embroidered Straight Kurta", "140 GSM", "70% Silk 30% Cotton Chanderi", "Straight Fit"), ("Handblock Indigo Anarkali Kurta", "130 GSM", "100% Mulmul Cotton", "Flared Anarkali"), ("Festive Zari A-Line Kurta Set", "160 GSM", "Viscose Muslin Blend", "A-Line Fit"), ("Schiffli Cotton Everyday Kurta", "145 GSM", "100% Cambric Cotton", "Regular Fit")],
        "CAT-WWD": [("Pleated Georgette Midi Dress", "125 GSM", "100% Recycled Polyester Georgette", "Fit & Flare"), ("Linen Wrap Shirt Dress", "165 GSM", "60% European Flax Linen 40% Viscose", "Wrap Fit"), ("Satin Bias-Cut Evening Slip Dress", "135 GSM", "100% Matte Viscose Satin", "Bias Slim Fit"), ("Tiered Poplin Smocked Day Dress", "150 GSM", "100% Crisp Cotton Poplin", "Relaxed Midi")],
        "CAT-WKN": [("Heavyweight French Terry Hoodie", "340 GSM", "85% Organic Cotton 15% Recycled Poly", "Oversized Fit"), ("Merino Blend Quarter-Zip Pullover", "280 GSM", "50% Merino Wool 50% Combed Acrylic", "Regular Fit"), ("Cable-Knit Crewneck Sweater", "310 GSM", "80% Lambswool 20% Nylon", "Classic Fit"), ("Brushed Fleece Track Sweatshirt", "320 GSM", "80% Cotton 20% Polyester Fleece", "Relaxed Fit")],
        "CAT-ACT": [("4-Way Stretch Training Tee", "155 GSM", "88% Nylon 12% Lycra Moisture-Wicking", "Compression Fit"), ("High-Waist Sculpt Leggings", "240 GSM", "78% Recycled Polyamide 22% Elastane", "Sculpt High-Rise"), ("Perforated Running Joggers", "190 GSM", "90% Polyester 10% Spandex Woven", "Tapered Active"), ("Seamless Studio Quarter-Zip", "210 GSM", "92% Polyamide 8% Elastane Seamless", "Contoured Fit")],
        "CAT-FTW": [("Vulcanized Suede Low-Top Sneaker", "680 g/pair", "Suede Upper + Natural Rubber Cupsole", "Standard D-Width"), ("Knit-Mesh Runner Trainer", "540 g/pair", "Engineered Knit + EVA Phylon Midsole", "Neutral Arch Fit"), ("Leather Court Classic Sneaker", "720 g/pair", "Full-Grain Nappa Leather + TPR Sole", "Regular Fit"), ("Slip-On Canvas Espadrille Mule", "490 g/pair", "14oz Organic Canvas + Jute-Wrapped Sole", "Relaxed Fit")],
        "CAT-KID": [("Organic Interlock Graphic Co-ord", "190 GSM", "100% GOTS Organic Cotton Interlock", "Comfort Fit"), ("Brushed Jersey Jogger & Tee Set", "210 GSM", "95% Cotton 5% Elastane", "Play Fit"), ("Quilted Reversible Gilet & Top", "250 GSM", "100% Cotton Shell + Recycled Poly Fill", "Regular Layer Fit"), ("Soft Chambray Dungaree Set", "175 GSM", "100% Washed Cotton Chambray", "Relaxed Toddler Fit")],
        "CAT-LNG": [("Micro-Modal Ribbed Lounge Set", "185 GSM", "93% Lenzing Micro-Modal 7% Elastane", "Relaxed Lounge"), ("Pima Cotton Pyjama Trouser", "160 GSM", "100% Supima Cotton Poplin", "Wide-Leg Comfort"), ("Seamless Bamboo Everyday Briefs 2-Pack", "170 GSM", "70% Bamboo Viscose 22% Nylon 8% Spandex", "Second-Skin Fit"), ("Waffle-Knit Thermal Lounge Henleys", "220 GSM", "60% Cotton 40% Modal Waffle", "Relaxed Fit")],
        "CAT-ACC": [("Full-Grain Vegetable Tanned Crossbody", "420 g", "100% Vegetable-Tanned Buff Calf Leather", "Structured One-Size"), ("Waxed Canvas Commuter Tote", "580 g", "16oz Paraffin-Waxed Cotton Canvas", "15-Inch Laptop Fit"), ("Reversible Italian Leather Dress Belt", "210 g", "Full-Grain Leather + Brushed Brass Buckle", "Waist 30-38"), ("Quilted Nylon Weekender Duffel", "740 g", "Water-Repellent Ballistic Ripstop Nylon", "35L Cabin Size")],
    }

    colors = [
        ("Midnight Navy", "#1E293B"),
        ("Olive Drab", "#3F4E38"),
        ("Raw Indigo", "#1E3A5F"),
        ("Burnt Terracotta", "#9A3412"),
        ("Charcoal Slate", "#334155"),
        ("Ecru Sand", "#E7E2D8"),
        ("Burgundy Wine", "#5B1924"),
        ("Forest Pine", "#14532D"),
    ]
    sizes_general = ["XS", "S", "M", "L", "XL", "XXL"]
    sizes_ftw = ["UK6", "UK7", "UK8", "UK9", "UK10", "UK11"]

    products = []
    sku_counter = 1001

    for cat_idx, cat in enumerate(categories):
        sup_idx = category_specs[cat_idx][7]
        primary_sup = suppliers[sup_idx]
        alt_sup = suppliers[(sup_idx + 1) % len(suppliers)]
        templates = style_templates[cat.code]
        cat_brands = brands_by_cat[cat.code]

        # 24 SKUs per category = 240 SKUs total
        for i in range(24):
            tmpl = templates[i % len(templates)]
            brand = cat_brands[i % len(cat_brands)]
            color_name, color_hex = colors[(cat_idx + i) % len(colors)]
            size_list = sizes_ftw if cat.code == "CAT-FTW" else sizes_general
            size_val = size_list[i % len(size_list)]

            style_code = f"STY-{cat.code[-3:]}-{100 + (i // 3)}"
            sku_code = f"TF-{cat.code[-3:]}-{sku_counter}"
            sku_counter += 1

            base_mrp = round(rng.choice([1299, 1499, 1799, 1999, 2299, 2499, 2999, 3499, 3999]), 2)
            discount_pct = rng.choice([0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0])
            selling_price = round(base_mrp * (1.0 - discount_pct / 100.0), 2)
            # Cost price around 38% to 52% of selling price
            cost_ratio = rng.uniform(0.38, 0.56)
            cost_price = round(selling_price * cost_ratio, 2)
            net_rev = selling_price / 1.12
            gross_margin_pct = round(((net_rev - cost_price) / net_rev) * 100.0, 2)

            # Intentional catalogue completeness issues on ~42 SKUs
            has_desc = True
            img_count = 5
            has_size_chart = True
            has_fabric_care = True
            is_dup = False
            dup_of = None

            if i in (2, 9, 17, 22) or (cat_idx in (2, 3, 6) and i in (5, 13)):
                if i % 3 == 0:
                    has_size_chart = False
                if i % 2 == 1:
                    has_fabric_care = False
                if i in (9, 22):
                    img_count = rng.choice([0, 2])
                if i == 17:
                    has_desc = False
                if i == 22 and len(products) > 0:
                    is_dup = True
                    dup_of = products[-1].sku

            comp_score, missing_list = compute_completeness(
                has_desc, img_count, has_size_chart, has_fabric_care, is_dup
            )

            chosen_sup = primary_sup if i % 4 != 3 else alt_sup
            lifecycle = "CORE" if i < 14 else ("NEW_LAUNCH" if i < 19 else ("SEASONAL" if i < 22 else "CLEARANCE"))

            prod_name = f"{brand} {tmpl[0]} — {color_name} ({size_val})"
            desc_text = (
                f"Engineered in {tmpl[2]} ({tmpl[1]}) with {tmpl[3]} construction for AW26 retail merchandising."
                if has_desc
                else ""
            )

            price_hist = [
                {"date": "2026-09-15", "mrp": base_mrp, "selling_price": base_mrp, "discount_pct": 0.0, "reason": "AW26 Initial Launch Price"},
            ]
            if discount_pct > 0:
                price_hist.append({
                    "date": "2026-10-25",
                    "mrp": base_mrp,
                    "selling_price": selling_price,
                    "discount_pct": discount_pct,
                    "reason": "Festive Merchandising Markdown",
                })

            prod = Product(
                sku=sku_code,
                style_code=style_code,
                name=prod_name,
                brand=brand,
                category_id=cat.id,
                supplier_id=chosen_sup.id,
                season="AW26",
                cost_price=cost_price,
                mrp=base_mrp,
                selling_price=selling_price,
                discount_pct=discount_pct,
                tax_rate_pct=12.0,
                gross_margin_pct=gross_margin_pct,
                description=desc_text,
                has_description=has_desc,
                has_images=img_count > 0,
                image_count=img_count,
                has_size_chart=has_size_chart,
                has_fabric_care=has_fabric_care,
                is_duplicate_flag=is_dup,
                duplicate_of_sku=dup_of,
                completeness_score=comp_score,
                missing_fields_json=json.dumps(missing_list),
                lifecycle_stage=lifecycle,
                price_history_json=json.dumps(price_hist),
                is_synthetic=True,
            )
            db.add(prod)
            db.flush()

            attr = ProductAttribute(
                product_id=prod.id,
                size=size_val,
                color=color_name,
                color_hex=color_hex,
                ean_barcode=f"8904{sku_counter:09d}",
                gsm_or_weight=tmpl[1],
                fabric_composition=tmpl[2],
                fit_type=tmpl[3],
                wash_care="Machine wash cold 30C gentle cycle, do not bleach, dry flat in shade" if has_fabric_care else "Not specified",
                hsn_code="64039900" if cat.code == "CAT-FTW" else ("42022100" if cat.code == "CAT-ACC" else "61091000"),
            )
            db.add(attr)
            products.append(prod)

    db.flush()

    # -------------------------------------------------------------------------
    # 5. PURCHASE ORDERS & PO ITEMS (48 POs with Coherent Quantities & Statuses)
    # -------------------------------------------------------------------------
    po_statuses = [
        "RECEIVED", "RECEIVED", "RECEIVED", "PARTIALLY_RECEIVED", "PARTIALLY_RECEIVED",
        "DELAYED", "DELAYED", "ACKNOWLEDGED", "ACKNOWLEDGED", "ISSUED", "ISSUED", "CLOSED"
    ]

    purchase_orders = []
    for po_idx in range(48):
        sup = suppliers[po_idx % len(suppliers)]
        wh = warehouses[po_idx % len(warehouses)]
        sup_prods = [p for p in products if p.supplier_id == sup.id]
        if not sup_prods:
            sup_prods = products[:10]
        cat_id = sup_prods[0].category_id

        st = po_statuses[po_idx % len(po_statuses)]
        if sup.status in ("UNDER_AUDIT", "ON_HOLD") and po_idx % 2 == 0:
            st = "DELAYED"

        days_ago = rng.randint(6, 42)
        ord_date = REFERENCE_TODAY - timedelta(days=days_ago)
        exp_date = ord_date + timedelta(days=sup.contracted_lead_time_days)

        act_date = None
        delay_days = 0
        delay_reason = None
        sup_ack = True
        ack_at = datetime.combine(ord_date + timedelta(days=1), datetime.min.time())

        if st == "ISSUED":
            ord_date = REFERENCE_TODAY - timedelta(days=rng.randint(1, 4))
            exp_date = ord_date + timedelta(days=sup.contracted_lead_time_days)
            sup_ack = False
            ack_at = None
        elif st == "ACKNOWLEDGED":
            ord_date = REFERENCE_TODAY - timedelta(days=rng.randint(3, 9))
            exp_date = ord_date + timedelta(days=sup.contracted_lead_time_days)
        elif st == "DELAYED":
            ord_date = REFERENCE_TODAY - timedelta(days=rng.randint(20, 32))
            exp_date = REFERENCE_TODAY - timedelta(days=rng.randint(3, 11))
            delay_days = (REFERENCE_TODAY - exp_date).days
            delay_reason = rng.choice([
                "Dyeing & enzyme wash batch bottleneck at tier-2 mill",
                "Fabric GSM inspection hold awaiting lab re-test",
                "Inter-state logistics truck shortage at dispatch hub",
                "Trim & YKK zipper import clearance delay",
                "Unacknowledged schedule drift by supplier production floor",
            ])
            if sup.code == "SUP-JAI-004":
                sup_ack = False
                ack_at = None
        elif st in ("RECEIVED", "CLOSED"):
            delay_days = rng.choice([0, 0, 0, 2, 4])
            act_date = exp_date + timedelta(days=delay_days)
            if act_date > REFERENCE_TODAY:
                act_date = REFERENCE_TODAY - timedelta(days=1)
        elif st == "PARTIALLY_RECEIVED":
            delay_days = rng.choice([1, 3, 5])
            act_date = REFERENCE_TODAY - timedelta(days=1)
            delay_reason = "Partial lot delivered; balance units held in finishing QC"

        po = PurchaseOrder(
            po_number=f"PO-2026-{1001 + po_idx}",
            supplier_id=sup.id,
            warehouse_id=wh.id,
            category_id=cat_id,
            status=st,
            order_date=ord_date,
            expected_delivery_date=exp_date,
            actual_delivery_date=act_date,
            supplier_acknowledged=sup_ack,
            acknowledged_at=ack_at,
            delay_days=delay_days,
            delay_reason=delay_reason,
            notes=f"AW26 Replenishment PO for {wh.code} ({sup.name})",
            created_by=rng.choice(["Ananya Sharma (Procurement)", "Vikram Patel (Sourcing Lead)", "Ritu Verma (Category Buyer)"]),
            is_synthetic=True,
        )
        db.add(po)
        db.flush()

        # Add 3 to 5 PO Line Items
        chosen_items = rng.sample(sup_prods, k=min(len(sup_prods), rng.randint(3, 5)))
        tot_ord = 0
        tot_rec = 0
        tot_pend = 0
        tot_disc = 0
        tot_val = 0.0

        for prod in chosen_items:
            o_qty = rng.choice([80, 120, 150, 200, 250, 300])
            if st in ("RECEIVED", "CLOSED"):
                disc = rng.choice([0, 0, 0, 8, 15])
                r_qty = o_qty - disc
                p_qty = 0
                rej_qty = disc
                disc_reason = "Minor stitching/shade reject during GRN AQL check" if disc > 0 else None
            elif st == "PARTIALLY_RECEIVED":
                r_qty = int(o_qty * 0.65)
                disc = rng.choice([0, 10])
                p_qty = o_qty - r_qty - disc
                rej_qty = disc
                disc_reason = "Short-shipped split batch; balance pending"
            else:
                r_qty = 0
                p_qty = o_qty
                disc = 0
                rej_qty = 0
                disc_reason = None

            line_val = round(o_qty * prod.cost_price, 2)
            po_item = PurchaseOrderItem(
                po_id=po.id,
                product_id=prod.id,
                ordered_qty=o_qty,
                received_qty=r_qty,
                pending_qty=p_qty,
                rejected_qty=rej_qty,
                unit_cost_inr=prod.cost_price,
                line_total_inr=line_val,
                discrepancy_reason=disc_reason,
            )
            db.add(po_item)

            tot_ord += o_qty
            tot_rec += r_qty
            tot_pend += p_qty
            tot_disc += disc
            tot_val += line_val

        po.total_ordered_qty = tot_ord
        po.total_received_qty = tot_rec
        po.pending_qty = tot_pend
        po.discrepancy_qty = tot_disc
        po.total_value_inr = round(tot_val, 2)
        purchase_orders.append(po)

    db.flush()

    # -------------------------------------------------------------------------
    # 6. INVENTORY & STOCK MOVEMENTS (480 Warehouse x SKU Records + Ledger)
    # -------------------------------------------------------------------------
    inventory_records = []
    supplier_map = {s.id: s for s in suppliers}

    for idx, prod in enumerate(products):
        # Place each SKU in 2 regional warehouses (240 * 2 = 480 inventory records)
        wh_pair = [warehouses[idx % 4], warehouses[(idx + 2) % 4]]
        sup = supplier_map[prod.supplier_id]

        for w_i, wh in enumerate(wh_pair):
            # Create realistic distributions of STOCKOUT, LOW_STOCK, HEALTHY, EXCESS, SLOW_MOVING
            scenario_roll = (idx + w_i * 7) % 20
            ads_30 = round(rng.uniform(2.2, 9.5), 2)
            ads_7 = round(ads_30 * rng.uniform(0.82, 1.28), 2)

            if scenario_roll in (0, 1):
                # STOCKOUT
                on_hand = rng.choice([0, 3, 5])
                reserved = on_hand
                in_transit = rng.choice([0, 60, 120])
                stock_status = "STOCKOUT"
            elif scenario_roll in (2, 3, 4):
                # LOW_STOCK
                on_hand = rng.randint(14, 38)
                reserved = rng.randint(4, 10)
                in_transit = rng.choice([0, 40, 80])
                stock_status = "LOW_STOCK"
            elif scenario_roll in (5, 6):
                # EXCESS
                ads_30 = round(rng.uniform(1.0, 2.4), 2)
                ads_7 = round(ads_30 * 0.85, 2)
                on_hand = rng.randint(240, 420)
                reserved = rng.randint(5, 18)
                in_transit = 0
                stock_status = "EXCESS"
            elif scenario_roll == 7:
                # SLOW_MOVING
                ads_30 = round(rng.uniform(0.3, 0.9), 2)
                ads_7 = round(ads_30 * 0.7, 2)
                on_hand = rng.randint(95, 175)
                reserved = rng.randint(0, 4)
                in_transit = 0
                stock_status = "SLOW_MOVING"
            else:
                # HEALTHY
                on_hand = rng.randint(85, 210)
                reserved = rng.randint(8, 28)
                in_transit = rng.choice([0, 0, 50])
                stock_status = "HEALTHY"

            avail = max(0, on_hand - reserved)
            # Transparent Weighted Moving Average Forecast: 0.6 * ADS_7d + 0.4 * ADS_30d
            forecast_dd = round(0.60 * ads_7 + 0.40 * ads_30, 2)
            lead_time = sup.actual_avg_lead_time_days
            safety_stock = int(math.ceil(forecast_dd * max(5.0, 0.35 * lead_time)))
            reorder_point = int(math.ceil((forecast_dd * lead_time) + safety_stock))
            doc = round(avail / max(forecast_dd, 0.1), 1)

            sold_30d = forecast_dd * 30.0
            sell_through = round(min(98.5, (sold_30d / max(sold_30d + avail, 1.0)) * 100.0), 1)
            turnover = round((sold_30d * 12.0) / max((on_hand + avail) / 2.0, 10.0), 2)

            # Ageing buckets summing exactly to on_hand
            if stock_status in ("EXCESS", "SLOW_MOVING"):
                b_0_30 = int(on_hand * 0.15)
                b_31_60 = int(on_hand * 0.25)
                b_61_90 = int(on_hand * 0.30)
                b_90_p = on_hand - (b_0_30 + b_31_60 + b_61_90)
            else:
                b_0_30 = int(on_hand * 0.60)
                b_31_60 = int(on_hand * 0.28)
                b_61_90 = int(on_hand * 0.09)
                b_90_p = on_hand - (b_0_30 + b_31_60 + b_61_90)

            inv = Inventory(
                product_id=prod.id,
                warehouse_id=wh.id,
                on_hand_qty=on_hand,
                reserved_qty=reserved,
                available_qty=avail,
                damaged_qty=rng.choice([0, 0, 2, 4]),
                in_transit_qty=in_transit,
                safety_stock_qty=safety_stock,
                reorder_point_qty=reorder_point,
                avg_daily_sales_7d=ads_7,
                avg_daily_sales_30d=ads_30,
                forecast_daily_demand=forecast_dd,
                days_of_cover=doc,
                sell_through_pct=sell_through,
                turnover_ratio=turnover,
                age_bucket_0_30_qty=b_0_30,
                age_bucket_31_60_qty=b_31_60,
                age_bucket_61_90_qty=b_61_90,
                age_bucket_90_plus_qty=b_90_p,
                stock_status=stock_status,
                last_received_date=REFERENCE_TODAY - timedelta(days=rng.randint(4, 38)),
                last_sold_date=REFERENCE_TODAY - timedelta(days=rng.randint(0, 6)),
                is_synthetic=True,
            )
            db.add(inv)
            inventory_records.append(inv)

            # Create Stock Movement history for first 220 inventory rows
            if len(inventory_records) <= 220:
                db.add(StockMovement(
                    product_id=prod.id,
                    warehouse_id=wh.id,
                    movement_type="GRN_INBOUND",
                    quantity_delta=on_hand + 45,
                    reference_code=f"GRN-2026-{2000 + len(inventory_records)}",
                    performed_by="Inbound Dock Scanner",
                    notes="Initial AW26 lot putaway",
                    created_at=REFERENCE_NOW - timedelta(days=18),
                ))
                db.add(StockMovement(
                    product_id=prod.id,
                    warehouse_id=wh.id,
                    movement_type="ORDER_DISPATCH",
                    quantity_delta=-45,
                    reference_code=f"BATCH-DSP-{500 + len(inventory_records)}",
                    performed_by="WMS Auto-Allocation",
                    notes="Customer order wave dispatch",
                    created_at=REFERENCE_NOW - timedelta(days=4),
                ))

    db.flush()

    # -------------------------------------------------------------------------
    # 7. PROMOTIONS (12 Promotional Campaigns)
    # -------------------------------------------------------------------------
    promo_specs = [
        ("PROMO-AW26-FEST", "AW26 Festive Wardrobe Edit", "SEASONAL_SALE", categories[2].id, None, 20.0, date(2026, 10, 20), date(2026, 11, 22), "ACTIVE", 145.0, 238.0, 64.1, 1845000.0, -4.2),
        ("PROMO-DENIM-FIT", "Stretch Denim Try-On Spotlight", "CATEGORY_SPOTLIGHT", categories[1].id, None, 15.0, date(2026, 11, 1), date(2026, 11, 25), "ACTIVE", 92.0, 134.0, 45.7, 1120000.0, -2.8),
        ("PROMO-WINTER-EARLY", "Early Winter Fleece & Merino Drop", "SEASONAL_SALE", categories[4].id, None, 12.0, date(2026, 11, 5), date(2026, 11, 30), "ACTIVE", 80.0, 118.0, 47.5, 980000.0, -1.9),
        ("PROMO-AGED-CLEAR", "90+ Day Aged Inventory Clearance", "CLEARANCE_MARKDOWN", categories[3].id, None, 35.0, date(2026, 11, 10), date(2026, 11, 28), "ACTIVE", 44.0, 96.0, 118.2, 640000.0, -9.4),
        ("PROMO-ATHLEISURE-2X", "Activewear Twin-Pack Bundle", "BUNDLE_OFFER", categories[5].id, None, 18.0, date(2026, 11, 18), date(2026, 12, 5), "SCHEDULED", 110.0, 165.0, 50.0, 0.0, -3.1),
        ("PROMO-SHIRT-WORK", "Smart Casual Office Edit", "CATEGORY_SPOTLIGHT", categories[0].id, None, 10.0, date(2026, 10, 1), date(2026, 10, 31), "EXPIRED", 130.0, 172.0, 32.3, 1490000.0, -1.5),
    ]
    for pspec in promo_specs:
        db.add(Promotion(
            code=pspec[0],
            name=pspec[1],
            campaign_type=pspec[2],
            category_id=pspec[3],
            product_id=pspec[4],
            discount_pct=pspec[5],
            start_date=pspec[6],
            end_date=pspec[7],
            status=pspec[8],
            baseline_daily_units=pspec[9],
            promo_daily_units=pspec[10],
            uplift_pct=pspec[11],
            revenue_generated_inr=pspec[12],
            gross_margin_impact_pct=pspec[13],
            is_synthetic=True,
        ))

    # -------------------------------------------------------------------------
    # 8. CUSTOMERS (60 Customers) & CARRIERS (6 Logistics Partners)
    # -------------------------------------------------------------------------
    customer_cities = [
        ("Bengaluru", "Karnataka", "560034"),
        ("Mumbai", "Maharashtra", "400050"),
        ("New Delhi", "Delhi", "110016"),
        ("Gurugram", "Haryana", "122002"),
        ("Hyderabad", "Telangana", "500033"),
        ("Pune", "Maharashtra", "411007"),
        ("Chennai", "Tamil Nadu", "600018"),
        ("Kolkata", "West Bengal", "700019"),
        ("Ahmedabad", "Gujarat", "380015"),
        ("Jaipur", "Rajasthan", "302001"),
    ]
    first_names = ["Aarav", "Diya", "Kabir", "Neha", "Rohan", "Ishita", "Vivaan", "Ananya", "Aditya", "Meera", "Siddharth", "Tanvi"]
    last_names = ["Mehta", "Iyer", "Sharma", "Kulkarni", "Reddy", "Nair", "Chatterjee", "Kapoor", "Verma", "Joshi"]

    customers = []
    for c_i in range(60):
        fn = first_names[c_i % len(first_names)]
        ln = last_names[(c_i * 3) % len(last_names)]
        city, state, pin = customer_cities[c_i % len(customer_cities)]
        cust = Customer(
            code=f"CUST-{1001 + c_i}",
            full_name=f"{fn} {ln}",
            email=f"{fn.lower()}.{ln.lower()}{c_i}@customer.example.in",
            phone=f"+91-98{10000000 + c_i * 13579:08d}",
            city=city,
            state=state,
            pin_code=pin,
            tier="VIP" if c_i % 5 == 0 else ("INSIDER" if c_i % 3 == 0 else "STANDARD"),
            total_orders=rng.randint(2, 14),
            return_count=rng.randint(0, 3),
            is_synthetic=True,
        )
        db.add(cust)
        customers.append(cust)
    db.flush()

    carrier_specs = [
        ("CR-DELHIVERY", "Delhivery Surface Express", "SURFACE_EXPRESS", 3.4, 91.2, 4.1, 48, "enterprise-desk@delhivery.example.in"),
        ("CR-BLUEDART", "BlueDart Apex Air Priority", "AIR_PRIORITY", 2.1, 95.8, 2.3, 36, "controltower@bluedart.example.in"),
        ("CR-SHADOWFAX", "Shadowfax Hyperlocal & Metro", "SAME_DAY_METRO", 1.6, 89.4, 4.8, 29, "ops-escalation@shadowfax.example.in"),
        ("CR-XPRESSBEES", "XpressBees Regional Surface", "SURFACE_EXPRESS", 3.9, 84.6, 6.2, 34, "keyaccounts@xpressbees.example.in"),
        ("CR-ECOMEXP", "Ecom Express Tier-2 Reach", "SURFACE_EXPRESS", 4.3, 82.1, 7.4, 25, "sla-support@ecomexpress.example.in"),
        ("CR-DTDC", "DTDC Plus Parcel Network", "SURFACE_EXPRESS", 3.8, 87.5, 5.1, 18, "corp-ops@dtdc.example.in"),
    ]
    carriers = []
    for cr_spec in carrier_specs:
        cr = Carrier(
            code=cr_spec[0],
            name=cr_spec[1],
            service_type=cr_spec[2],
            avg_transit_days=cr_spec[3],
            on_time_rate_pct=cr_spec[4],
            rto_rate_pct=cr_spec[5],
            active_shipments=cr_spec[6],
            escalation_contact=cr_spec[7],
        )
        db.add(cr)
        carriers.append(cr)
    db.flush()

    # -------------------------------------------------------------------------
    # 9. ORDERS, ORDER ITEMS & SHIPMENTS (180 Orders with Coherent Shipments)
    # -------------------------------------------------------------------------
    order_status_pool = (
        ["DELIVERED"] * 88
        + ["IN_TRANSIT"] * 24
        + ["DELAYED"] * 18
        + ["DISPATCHED"] * 14
        + ["PACKED"] * 10
        + ["PICKING"] * 10
        + ["ALLOCATED"] * 6
        + ["PENDING"] * 4
        + ["CANCELLED"] * 6
    )

    orders = []
    delivered_order_items = []
    shipments = []

    for o_idx in range(180):
        cust = customers[o_idx % len(customers)]
        # Weight orders heavily so WH-A-BLR gets realistic bottleneck data
        wh = warehouses[0] if o_idx % 3 == 0 else warehouses[o_idx % len(warehouses)]
        st = order_status_pool[o_idx % len(order_status_pool)]

        # If assigned to WH-A-BLR, higher chance of DELAYED or elevated processing hours
        if wh.code == "WH-A-BLR" and o_idx % 5 == 0 and st == "IN_TRANSIT":
            st = "DELAYED"

        days_back = rng.randint(5, 25) if st == "DELIVERED" else rng.randint(1, 7)
        ord_dt = REFERENCE_NOW - timedelta(days=days_back, hours=rng.randint(1, 18))
        prom_disp = ord_dt + timedelta(hours=12)
        prom_deliv = (ord_dt + timedelta(days=4)).date()

        if wh.code == "WH-A-BLR":
            proc_hrs = round(rng.uniform(11.5, 21.4), 1)
        elif wh.code == "WH-C-BOM":
            proc_hrs = round(rng.uniform(6.5, 13.8), 1)
        else:
            proc_hrs = round(rng.uniform(3.2, 8.8), 1)

        sla_breached = proc_hrs > wh.sla_dispatch_hours or st == "DELAYED"
        act_disp = ord_dt + timedelta(hours=proc_hrs) if st in ("DISPATCHED", "IN_TRANSIT", "DELIVERED", "DELAYED") else None

        act_deliv = None
        if st == "DELIVERED":
            # In WH-A-BLR, ~36% of delivered orders arrived 1-3 days late
            if wh.code == "WH-A-BLR" and o_idx % 3 != 0:
                late_d = rng.randint(1, 3)
                act_deliv = prom_deliv + timedelta(days=late_d)
                sla_breached = True
            elif o_idx % 9 == 0:
                act_deliv = prom_deliv + timedelta(days=1)
                sla_breached = True
            else:
                act_deliv = prom_deliv - timedelta(days=rng.choice([0, 1]))

        cancel_reason = None
        if st == "CANCELLED":
            cancel_reason = rng.choice([
                "Customer cancelled due to dispatch SLA delay (>18h)",
                "Inventory bin short-pick during warehouse wave",
                "COD verification timeout",
            ])

        item_count = rng.choice([1, 1, 2, 2, 3])
        chosen_prods = rng.sample(products, k=item_count)
        sub_inr = 0.0
        disc_inr = 0.0

        order_obj = Order(
            order_number=f"ORD-2026-{50001 + o_idx}",
            customer_id=cust.id,
            warehouse_id=wh.id,
            order_date=ord_dt,
            status=st,
            payment_mode=rng.choice(["PREPAID_UPI", "PREPAID_UPI", "PREPAID_CARD", "COD"]),
            total_items=item_count,
            subtotal_inr=0.0,
            discount_inr=0.0,
            total_amount_inr=0.0,
            promised_dispatch_at=prom_disp,
            actual_dispatch_at=act_disp,
            promised_delivery_date=prom_deliv,
            actual_delivery_date=act_deliv,
            processing_hours=proc_hrs,
            sla_breached=sla_breached,
            cancellation_reason=cancel_reason,
            is_synthetic=True,
        )
        db.add(order_obj)
        db.flush()

        for p in chosen_prods:
            qty = 1
            u_mrp = p.mrp
            u_sell = p.selling_price
            u_disc = round(u_mrp - u_sell, 2)
            sub_inr += u_mrp * qty
            disc_inr += u_disc * qty

            oi = OrderItem(
                order_id=order_obj.id,
                product_id=p.id,
                quantity=qty,
                unit_price_inr=u_mrp,
                discount_inr=u_disc,
                net_price_inr=u_sell,
                cost_price_inr=p.cost_price,
                fulfilment_status=st,
            )
            db.add(oi)
            db.flush()
            if st == "DELIVERED":
                delivered_order_items.append((order_obj, oi, p))

        order_obj.subtotal_inr = round(sub_inr, 2)
        order_obj.discount_inr = round(disc_inr, 2)
        order_obj.total_amount_inr = round(sub_inr - disc_inr, 2)
        orders.append(order_obj)

        # Create coherent Shipment record for all post-packing / active fulfilment orders
        if st in ("PACKED", "DISPATCHED", "IN_TRANSIT", "DELIVERED", "DELAYED"):
            carrier = carriers[o_idx % len(carriers)]
            pick_dt = ord_dt + timedelta(hours=max(1.0, proc_hrs * 0.35))
            pack_dt = ord_dt + timedelta(hours=max(2.0, proc_hrs * 0.80))
            disp_dt = act_disp

            if st == "PACKED":
                sh_status = "MANIFESTED"
                delay_hrs = 0.0
                on_time = not sla_breached
                hub = f"{wh.city} Fulfilment Outbound Dock"
                exc_code = None
            elif st == "DISPATCHED":
                sh_status = "PICKED_UP"
                delay_hrs = max(0.0, round(proc_hrs - wh.sla_dispatch_hours, 1))
                on_time = delay_hrs == 0
                hub = f"{wh.city} Origin Sortation Hub"
                exc_code = None
            elif st == "IN_TRANSIT":
                sh_status = rng.choice(["IN_TRANSIT", "HUB_REACHED", "OUT_FOR_DELIVERY"])
                delay_hrs = max(0.0, round(proc_hrs - wh.sla_dispatch_hours, 1))
                on_time = delay_hrs == 0
                hub = f"{cust.city} Regional Transit Hub"
                exc_code = None
            elif st == "DELAYED":
                sh_status = "DELIVERY_EXCEPTION"
                delay_hrs = round(rng.uniform(18.0, 56.0), 1)
                on_time = False
                hub = f"{cust.city} Linehaul Hub (Held)"
                exc_code = rng.choice([
                    "WH_SORTATION_BACKLOG",
                    "CARRIER_LINEHAUL_MISROUTE",
                    "WEATHER_OR_HIGHWAY_CONGESTION",
                    "CONSIGNEE_ADDRESS_UNREACHABLE",
                ])
            else:
                # DELIVERED
                sh_status = "DELIVERED"
                if act_deliv and act_deliv > prom_deliv:
                    delay_hrs = float((act_deliv - prom_deliv).days * 24)
                    on_time = False
                    exc_code = "SLA_LATE_DELIVERY"
                else:
                    delay_hrs = 0.0
                    on_time = True
                    exc_code = None
                hub = f"{cust.city} Last-Mile Delivery Centre"

            timeline = [
                {"step": "ORDER_ALLOCATED", "timestamp": ord_dt.strftime("%Y-%m-%d %H:%M"), "location": wh.code, "note": "Allocated to warehouse wave"},
                {"step": "PICK_COMPLETED", "timestamp": pick_dt.strftime("%Y-%m-%d %H:%M"), "location": wh.code, "note": "Bin picking verified via barcode scan"},
                {"step": "PACK_MANIFESTED", "timestamp": pack_dt.strftime("%Y-%m-%d %H:%M"), "location": wh.code, "note": f"Assigned to {carrier.name}"},
            ]
            if disp_dt:
                timeline.append({"step": "DISPATCHED_FROM_FC", "timestamp": disp_dt.strftime("%Y-%m-%d %H:%M"), "location": wh.city, "note": f"Handed over to carrier ({proc_hrs}h processing)"})
            if st == "DELAYED":
                timeline.append({"step": "DELIVERY_EXCEPTION", "timestamp": (REFERENCE_NOW - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M"), "location": hub, "note": f"Exception flagged: {exc_code}"})
            elif st == "DELIVERED" and act_deliv:
                timeline.append({"step": "DELIVERED_POD", "timestamp": f"{act_deliv.isoformat()} 16:15", "location": cust.city, "note": "Delivered with OTP confirmation"})

            sh = Shipment(
                awb_number=f"AWB{carrier.code[-4:]}{800001 + o_idx}",
                order_id=order_obj.id,
                warehouse_id=wh.id,
                carrier_id=carrier.id,
                status=sh_status,
                pick_started_at=pick_dt,
                pack_completed_at=pack_dt,
                dispatched_at=disp_dt,
                promised_delivery_date=prom_deliv,
                actual_delivery_date=act_deliv,
                dispatch_hours=proc_hrs,
                delay_hours=delay_hrs,
                on_time=on_time,
                current_hub=hub,
                exception_code=exc_code,
                tracking_timeline_json=json.dumps(timeline),
                is_synthetic=True,
            )
            db.add(sh)
            shipments.append(sh)

    db.flush()

    # -------------------------------------------------------------------------
    # 10. RETURN REASONS & RETURNS/EXCHANGES (52 Coherent Returns from Delivered Orders)
    # -------------------------------------------------------------------------
    reason_specs = [
        ("RET-SIZE-SMALL", "SIZE_FIT", "Garment runs smaller/tighter than size chart across chest or waist", True, "Audit supplier grading spec & add garment measurement table to SKU catalogue"),
        ("RET-SIZE-LARGE", "SIZE_FIT", "Garment fit looser/longer than expected for standard size", True, "Update fit advisory badge (Relaxed vs Regular) on product page"),
        ("RET-CAT-COLOR", "CATALOGUE_MISMATCH", "Delivered shade or fabric texture differs from studio imagery", True, "Recalibrate studio lighting & add fabric macro shot + GSM details"),
        ("RET-QC-STITCH", "QUALITY_DEFECT", "Seam opening, button detachment, or fabric pilling after unpack", True, "Trigger supplier AQL 1.5 inspection hold & debit note"),
        ("RET-LATE-ARRIVAL", "LATE_DELIVERY", "Order arrived after festive/occasion date due to SLA delay", True, "Investigate FC dispatch backlog and carrier linehaul SLA"),
        ("RET-TRANSIT-DMG", "DAMAGED_IN_TRANSIT", "Outer polybag/shoebox crushed and garment stained in transit", True, "Escalate packaging spec with carrier & enforce 70-micron tamper bag"),
        ("RET-MIND-CHANGE", "CHANGED_MIND", "Customer style preference changed; no product defect", False, "Standard restock after steam-press QC verification"),
    ]
    return_reasons = []
    for rspec in reason_specs:
        rr = ReturnReason(
            code=rspec[0],
            category=rspec[1],
            description=rspec[2],
            controllable_by_ops=rspec[3],
            recommended_action=rspec[4],
        )
        db.add(rr)
        return_reasons.append(rr)
    db.flush()

    return_statuses = [
        "REQUESTED", "APPROVED", "IN_TRANSIT_RETURN", "QC_PASSED",
        "QC_FAILED", "EXCHANGE_DISPATCHED", "REFUND_PROCESSED", "CLOSED"
    ]

    # Prioritize delivered items where product has incomplete catalogue or supplier issues, plus normal delivered items
    delivered_sorted = sorted(
        delivered_order_items,
        key=lambda x: (0 if x[2].completeness_score < 85 else 1, x[0].id)
    )

    for r_idx in range(min(52, len(delivered_sorted))):
        ord_obj, oi_obj, prod_obj = delivered_sorted[r_idx]
        # Correlate reason with catalogue/supplier realities
        if not prod_obj.has_size_chart or r_idx % 4 == 0:
            reason = return_reasons[0] if r_idx % 2 == 0 else return_reasons[1]
        elif prod_obj.completeness_score < 85:
            reason = return_reasons[2]
        elif r_idx % 5 == 0:
            reason = return_reasons[3]
        elif ord_obj.sla_breached:
            reason = return_reasons[4]
        else:
            reason = return_reasons[r_idx % len(return_reasons)]

        req_type = "SIZE_EXCHANGE" if reason.category == "SIZE_FIT" and r_idx % 2 == 0 else ("RETURN_REFUND" if r_idx % 5 != 0 else "STYLE_EXCHANGE")
        r_status = return_statuses[r_idx % len(return_statuses)]

        req_at = datetime.combine(ord_obj.actual_delivery_date or REFERENCE_TODAY - timedelta(days=4), datetime.min.time()) + timedelta(days=1, hours=10)
        if req_at > REFERENCE_NOW:
            req_at = REFERENCE_NOW - timedelta(hours=14)

        res_at = req_at + timedelta(days=2, hours=5) if r_status in ("QC_PASSED", "QC_FAILED", "EXCHANGE_DISPATCHED", "REFUND_PROCESSED", "CLOSED") else None
        if res_at and res_at > REFERENCE_NOW:
            res_at = REFERENCE_NOW - timedelta(hours=2)

        if req_type in ("SIZE_EXCHANGE", "STYLE_EXCHANGE"):
            ref_status = "NOT_APPLICABLE"
            exch_ord = f"EXCH-2026-{9001 + r_idx}" if r_status in ("EXCHANGE_DISPATCHED", "CLOSED") else None
        else:
            ref_status = "PROCESSED" if r_status in ("REFUND_PROCESSED", "CLOSED") else ("INITIATED" if r_status == "QC_PASSED" else "PENDING")
            exch_ord = None

        restock = r_status != "QC_FAILED" and reason.category != "QUALITY_DEFECT"
        qc_notes = (
            "Garment tags intact, passed steam & barcode check; restocked to prime bin."
            if restock and res_at
            else ("Failed QC: seam defect verified; moved to Supplier Debit Quarantine." if r_status == "QC_FAILED" else "Awaiting reverse hub scan & QC table inspection.")
        )

        ret_rec = ReturnRecord(
            rma_number=f"RMA-2026-{3001 + r_idx}",
            order_id=ord_obj.id,
            order_item_id=oi_obj.id,
            product_id=prod_obj.id,
            customer_id=ord_obj.customer_id,
            warehouse_id=ord_obj.warehouse_id,
            return_reason_id=reason.id,
            request_type=req_type,
            status=r_status,
            requested_at=req_at,
            resolved_at=res_at,
            qc_notes=qc_notes,
            refund_amount_inr=oi_obj.net_price_inr,
            refund_status=ref_status,
            exchange_order_number=exch_ord,
            restock_eligible=restock,
            is_synthetic=True,
        )
        db.add(ret_rec)

    db.flush()

    # -------------------------------------------------------------------------
    # 11. OPERATIONAL EXCEPTIONS (30 Cross-Chain Exceptions across Inbound, Inventory & Outbound)
    # -------------------------------------------------------------------------
    delayed_pos = [po for po in purchase_orders if po.status == "DELAYED"]
    incomplete_prods = [p for p in products if p.completeness_score < 80]
    stockout_invs = [inv for inv in inventory_records if inv.stock_status in ("STOCKOUT", "LOW_STOCK")]
    delayed_shipments = [sh for sh in shipments if sh.status == "DELIVERY_EXCEPTION" or sh.delay_hours > 12]

    exceptions_data = [
        ("EXC-2026-001", "WAREHOUSE_BOTTLENECK", "CRITICAL", "IN_PROGRESS", "WH-A-BLR Dispatch SLA Degradation (14.8h Avg Processing vs 12.0h SLA)", "Warehouse A (Bengaluru Peenya) order processing time surged +46% over the last 7 days due to Zone-C automated sorter belt maintenance and a 19% picker shift deficit during AW26 ethnicwear peak wave.", None, None, warehouses[0].id, None, None, None, "Siddharth Nair", "Warehouse Ops Manager", "Zone-C conveyor motor replacement + high multi-item ethnicwear pick density", "Reallocated 8 pickers from inbound putaway to Zone-C wave picking; temporary bypass chute active.", 485000.0),
        ("EXC-2026-002", "INBOUND_PO", "CRITICAL", "OPEN", f"Unacknowledged & Delayed PO ({delayed_pos[0].po_number}) — Rajputana Craft", f"Purchase Order {delayed_pos[0].po_number} is {delayed_pos[0].delay_days} days past expected delivery date with colour-fastness hold on indigo block-print lot.", suppliers[3].id, None, warehouses[0].id, delayed_pos[0].id, None, None, "Ananya Sharma", "Procurement Lead", "Azo-free indigo wash bleeding failed lab test at Jaipur facility", "Supplier quality audit scheduled; alternate allocation initiated with Tapi Silk Mills.", 342000.0),
        ("EXC-2026-003", "INBOUND_PO", "HIGH", "IN_PROGRESS", f"Yarn Shortage Delay on Winter Knitwear ({delayed_pos[1].po_number if len(delayed_pos) > 1 else 'PO-2026-1006'})", "320 GSM brushed fleece lot from Sutlej Merino delayed 8 days ahead of North India winter demand surge.", suppliers[5].id, None, warehouses[1].id, delayed_pos[1].id if len(delayed_pos) > 1 else purchase_orders[5].id, None, None, "Vikram Patel", "Procurement Lead", "Upstream combed cotton-fleece yarn mill backlog in Ludhiana", "Partial air-cargo split shipment of 400 core M/L units approved.", 290000.0),
        ("EXC-2026-004", "CATALOGUE_QUALITY", "HIGH", "OPEN", f"Missing Size Chart Driving 26% Size-Fit Returns on {incomplete_prods[0].sku}", f"SKU {incomplete_prods[0].sku} ({incomplete_prods[0].name}) has completeness score {incomplete_prods[0].completeness_score}% and lacks garment chest/waist measurements.", incomplete_prods[0].supplier_id, incomplete_prods[0].id, None, None, None, None, "Meera Joshi", "Category Merchandiser", "Tech-pack grading table omitted during bulk ERP upload", "Awaiting garment measurement spec upload in Catalogue Quality queue.", 118000.0),
        ("EXC-2026-005", "CATALOGUE_QUALITY", "MEDIUM", "OPEN", f"Duplicate Style Listing & Zero Studio Images on {incomplete_prods[1].sku}", f"SKU {incomplete_prods[1].sku} flagged as duplicate listing with missing front/back studio shots.", incomplete_prods[1].supplier_id, incomplete_prods[1].id, None, None, None, None, "Meera Joshi", "Category Merchandiser", "Vendor portal double submission under secondary EAN barcode", "Merge SKU attribute record and attach 4-angle studio imagery.", 64000.0),
        ("EXC-2026-006", "INVENTORY_RISK", "CRITICAL", "OPEN", f"Core Size Stockout at WH-A-BLR on {products[stockout_invs[0].product_id - 1].sku}", f"Available stock dropped to {stockout_invs[0].available_qty} units while 7-day daily demand is {stockout_invs[0].avg_daily_sales_7d} units/day.", products[stockout_invs[0].product_id - 1].supplier_id, stockout_invs[0].product_id, stockout_invs[0].warehouse_id, None, None, None, "Karan Malhotra", "Inventory Planner", "Festive demand spike (+34% over 30d baseline) combined with supplier lead-time drift", "Emergency replenishment PO recommended via Demand & Replenishment workbench.", 215000.0),
        ("EXC-2026-007", "INVENTORY_RISK", "HIGH", "IN_PROGRESS", f"Low Days of Cover (<3 Days) at WH-B-DEL on {products[stockout_invs[1].product_id - 1].sku}", f"Stock cover at {stockout_invs[1].days_of_cover} days; below safety stock threshold of {stockout_invs[1].safety_stock_qty} units.", products[stockout_invs[1].product_id - 1].supplier_id, stockout_invs[1].product_id, stockout_invs[1].warehouse_id, None, None, None, "Karan Malhotra", "Inventory Planner", "Delayed inbound GRN putaway", "Inter-warehouse transfer of 45 units initiated from WH-D-CCU.", 142000.0),
        ("EXC-2026-008", "DISPATCH_DELAY", "HIGH", "OPEN", "Bhiwandi FC (WH-C-BOM) Carrier Dock Congestion", "18 packed manifests awaiting XpressBees & Ecom Express evening linehaul pickup past 20:00 cutoff.", None, None, warehouses[2].id, None, None, None, "Mandar Kulkarni", "Warehouse Ops Manager", "Carrier feeder vehicle breakdown on NH-48", "Re-manifested 12 priority prepaid parcels to BlueDart Air & Delhivery.", 165000.0),
        ("EXC-2026-009", "DELIVERY_SLA", "HIGH", "OPEN", f"Linehaul Hub Hold on Shipment {delayed_shipments[0].awb_number}", f"Shipment {delayed_shipments[0].awb_number} delayed by {delayed_shipments[0].delay_hours} hours at {delayed_shipments[0].current_hub}.", None, None, delayed_shipments[0].warehouse_id, None, delayed_shipments[0].order_id, delayed_shipments[0].id, "Rohan Iyer", "CX & Returns Analyst", "Feeder hub mis-sort during night wave", "Escalated to carrier control desk; proactive SMS sent to VIP customer.", 28500.0),
        ("EXC-2026-010", "RETURN_SPIKE", "HIGH", "IN_PROGRESS", "Elevated Fit & Sizing Returns (24.8%) in Women's Western Dresses", "Bias-cut and wrap dresses from Atelier Moda showing 6.8% above-benchmark return rate due to bust/hip fit variance.", suppliers[4].id, products[72].id, warehouses[0].id, None, None, None, "Rohan Iyer", "CX & Returns Analyst", "Lack of model height/size-worn callout and rigid non-stretch viscose lining", "Added fit recommendation banner and updated size chart tolerance.", 195000.0),
    ]

    # Add 20 more programmatic exceptions across domains to reach 30 rich operational exceptions
    for extra_i in range(20):
        dom_choice = ["INBOUND_PO", "CATALOGUE_QUALITY", "INVENTORY_RISK", "DELIVERY_SLA", "DISPATCH_DELAY"][extra_i % 5]
        sev_choice = ["HIGH", "MEDIUM", "MEDIUM", "LOW", "CRITICAL"][extra_i % 5]
        st_choice = ["OPEN", "IN_PROGRESS", "RESOLVED", "ESCALATED"][extra_i % 4]
        wh_ref = warehouses[extra_i % len(warehouses)]
        prod_ref = products[(extra_i * 9) % len(products)]
        sup_ref = suppliers[extra_i % len(suppliers)]
        po_ref = purchase_orders[extra_i % len(purchase_orders)]
        sh_ref = delayed_shipments[extra_i % len(delayed_shipments)] if delayed_shipments else shipments[0]

        exceptions_data.append((
            f"EXC-2026-{11 + extra_i:03d}",
            dom_choice,
            sev_choice,
            st_choice,
            f"{dom_choice.replace('_', ' ').title()} Alert — {prod_ref.sku} at {wh_ref.code}",
            f"Automated control tower rule triggered on {prod_ref.name} ({prod_ref.sku}) linked to {sup_ref.name} at {wh_ref.name}.",
            sup_ref.id,
            prod_ref.id,
            wh_ref.id,
            po_ref.id if dom_choice == "INBOUND_PO" else None,
            sh_ref.order_id if dom_choice in ("DELIVERY_SLA", "DISPATCH_DELAY") else None,
            sh_ref.id if dom_choice in ("DELIVERY_SLA", "DISPATCH_DELAY") else None,
            rng.choice(["Siddharth Nair", "Ananya Sharma", "Karan Malhotra", "Meera Joshi", "Rohan Iyer", "Unassigned"]),
            rng.choice(["Warehouse Ops Manager", "Procurement Lead", "Inventory Planner", "Category Merchandiser", "CX & Returns Analyst"]),
            "Identified via automated daily SLA and stock-cover control tower sweep",
            "Resolution verified and closed in control tower ledger." if st_choice == "RESOLVED" else "Investigation underway with cross-functional owner.",
            round(rng.uniform(22000, 185000), 2),
        ))

    for ex in exceptions_data:
        det_at = REFERENCE_NOW - timedelta(days=rng.randint(1, 10), hours=rng.randint(1, 12))
        res_at = det_at + timedelta(hours=rng.randint(4, 28)) if ex[3] == "RESOLVED" else None
        db.add(OperationalException(
            exception_code=ex[0],
            domain=ex[1],
            severity=ex[2],
            status=ex[3],
            title=ex[4],
            description=ex[5],
            supplier_id=ex[6],
            product_id=ex[7],
            warehouse_id=ex[8],
            po_id=ex[9],
            order_id=ex[10],
            shipment_id=ex[11],
            assigned_to=ex[12],
            assigned_role=ex[13],
            root_cause=ex[14],
            resolution_notes=ex[15],
            financial_impact_inr=ex[16],
            detected_at=det_at,
            updated_at=res_at or (det_at + timedelta(hours=2)),
            resolved_at=res_at,
            is_synthetic=True,
        ))

    db.flush()

    # -------------------------------------------------------------------------
    # 12. PRODUCT ANALYTICS & MIXPANEL TELEMETRY SEED (330 Events across 11 Event Types)
    # -------------------------------------------------------------------------
    tracked_event_specs = [
        ("supplier_profile_opened", "Procurement Lead", "INBOUND", "COMPLETED", 45),
        ("purchase_order_created", "Procurement Lead", "INBOUND", "COMPLETED", 140),
        ("purchase_order_updated", "Procurement Lead", "INBOUND", "COMPLETED", 65),
        ("catalogue_issue_opened", "Category Merchandiser", "INBOUND", "IN_PROGRESS", 55),
        ("catalogue_issue_resolved", "Category Merchandiser", "INBOUND", "COMPLETED", 110),
        ("inventory_alert_opened", "Inventory Planner", "INVENTORY", "COMPLETED", 40),
        ("replenishment_recommendation_reviewed", "Inventory Planner", "INVENTORY", "COMPLETED", 95),
        ("fulfilment_exception_opened", "Warehouse Ops Manager", "OUTBOUND", "IN_PROGRESS", 60),
        ("delivery_exception_assigned", "Warehouse Ops Manager", "OUTBOUND", "COMPLETED", 85),
        ("return_case_reviewed", "CX & Returns Analyst", "OUTBOUND", "COMPLETED", 70),
        ("return_case_resolved", "CX & Returns Analyst", "OUTBOUND", "COMPLETED", 125),
    ]

    # Weight counts realistically so adoption, funnels, and abandonment rates are meaningful
    event_weights = [38, 29, 34, 42, 33, 46, 39, 35, 28, 36, 30]
    for ev_idx, (ev_name, role, ws, status_default, avg_dur) in enumerate(tracked_event_specs):
        count = event_weights[ev_idx]
        for k in range(count):
            sup_code = suppliers[(ev_idx + k) % len(suppliers)].code
            sku_code = products[(ev_idx * 7 + k) % len(products)].sku
            wh_code = warehouses[(ev_idx + k) % len(warehouses)].code
            act_status = "ABANDONED" if (k % 11 == 0 and "opened" in ev_name) else status_default
            dur = int(avg_dur * rng.uniform(0.6, 1.6))
            ts = REFERENCE_NOW - timedelta(days=rng.randint(0, 13), hours=rng.randint(0, 22), minutes=rng.randint(1, 58))

            db.add(AnalyticsEvent(
                event_name=ev_name,
                user_role=role,
                workspace=ws,
                supplier_id=sup_code if ws == "INBOUND" else None,
                sku_id=sku_code,
                warehouse_id=wh_code,
                exception_type="SLA_BREACH" if "exception" in ev_name else ("CATALOGUE_GAP" if "catalogue" in ev_name else "STOCK_COVER"),
                action_status=act_status,
                duration_seconds=dur,
                delivery_channel="LOCAL_POSTGRES_ADAPTER",
                properties_json=json.dumps({
                    "synthetic_seed": True,
                    "session_id": f"sess-{1000 + (k % 40)}",
                    "browser": "Chrome 131 Enterprise",
                }),
                event_timestamp=ts,
            ))

    db.commit()
    return {
        "seeded": True,
        "counts": {
            "suppliers": len(suppliers),
            "categories": len(categories),
            "warehouses": len(warehouses),
            "products": len(products),
            "purchase_orders": len(purchase_orders),
            "inventory_records": len(inventory_records),
            "orders": len(orders),
            "shipments": len(shipments),
            "returns": 52,
            "exceptions": len(exceptions_data),
        },
    }
