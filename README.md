# THREADFLOW — Fashion Supply Chain & Merchandising Control Tower

THREADFLOW is a full-stack enterprise operations platform connecting **Inbound Procurement & Catalogue**, **Inventory & Replenishment Intelligence**, and **Outbound Order Fulfilment, Delivery & Returns** for fashion and apparel retail operations.

> **Synthetic Data Disclosure:** All pre-seeded records (12 garment suppliers, 4 regional fulfilment centres, 10 fashion categories, 240 SKUs, 48 purchase orders, 480 warehouse-SKU inventory records, 180 customer orders, 154 shipments, 52 returns/exchanges, and 30 operational exceptions) are **100% synthetic** (`is_synthetic = true`) and generated with strict referential integrity.

---

## 1. Architecture & Technology Stack

- **Frontend (`frontend/`):** Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS (human-designed warm stone `#F6F5F2` & charcoal `#18181B` enterprise interface).
- **Backend (`backend/`):** Python, FastAPI, SQLAlchemy 2.0 ORM, Pydantic v2, OpenPyXL, HTTPX.
- **Database (`backend/sql/`):** PostgreSQL relational schema (`schema.sql`) and 5 Tableau analytical SQL views (`analytical_views.sql`), with automatic local SQLite relational engine fallback (`threadflow.db`) when a local PostgreSQL daemon is not running.
- **Product Analytics (`analytics_events`):** Mixpanel HTTP API integration paired with a local relational event adapter tracking all 11 operational workflow events.
- **AI Assistant (`/api/ai/assistant`):** Evidence-grounded operations assistant supporting `google-genai` (`gemini-4-hydrogen`) when `GEMINI_API_KEY` is provided and a deterministic SQL-evidence engine fallback.
- **Business Deliverables (`deliverables/`):**
  - PRD & Architecture: `deliverables/prd/THREADFLOW_PRD_AND_ARCHITECTURE.md`
  - KPI Data Dictionary & Tableau Spec: `deliverables/analytics/KPI_DATA_DICTIONARY.md` & `deliverables/tableau/extracts/`
  - Figma Design Tokens & SVG Wireframes: `deliverables/figma/FIGMA_DESIGN_SYSTEM_AND_HANDOFF.md`, `design_tokens.json`, `assets/*.svg`
  - Jira Agile Scrum Backlog & 3-Sprint Plan: `deliverables/jira/JIRA_AGILE_SCRUM_FRAMEWORK.md`, `jira_backlog_import.csv`
  - Validated Excel & Google Sheets Templates & Reports: `deliverables/spreadsheets/templates/` & `deliverables/spreadsheets/exports/`

---

## 2. Quick Start (Local Execution)

### Backend API (Port 8000)
```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -v tests/test_threadflow.py
.\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000
```

### Frontend Application (Port 3000)
```powershell
cd frontend
npm run build
npm run start
```
Open `http://localhost:3000` in your browser.
