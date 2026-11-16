"use client";

import React, { useState, useEffect, useCallback } from "react";
import { apiFetch, trackTelemetry, formatINR, statusBadgeStyle } from "@/lib/api";

interface EnablementProps {
  activeSubTab: "mixpanel" | "sql_tableau" | "spreadsheets" | "agile_figma";
  userRole: string;
  onNotify: (msg: string, type?: "success" | "error") => void;
}

export default function EnterpriseEnablementWorkspace({ activeSubTab, userRole, onNotify }: EnablementProps) {
  const [analyticsData, setAnalyticsData] = useState<any>(null);
  const [sqlViewsData, setSqlViewsData] = useState<any>(null);
  const [importEntity, setImportEntity] = useState("suppliers");
  const [importResult, setImportResult] = useState<any>(null);
  const [uploading, setUploading] = useState(false);

  const loadData = useCallback(async () => {
    try {
      if (activeSubTab === "mixpanel") {
        const d = await apiFetch("/api/analytics/summary");
        setAnalyticsData(d);
      } else if (activeSubTab === "sql_tableau") {
        const d = await apiFetch("/api/analytics/sql-views");
        setSqlViewsData(d);
      }
    } catch (e: any) {
      onNotify(e.message, "error");
    }
  }, [activeSubTab, onNotify]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await apiFetch(`/api/spreadsheets/import/${importEntity}`, {
        method: "POST",
        body: formData,
      });
      setImportResult(res);
      onNotify(
        `Processed ${res.total_rows_processed} rows for '${importEntity}': ${res.imported_count} imported, ${res.error_count} validation errors.`
      );
    } catch (err: any) {
      onNotify(err.message, "error");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const runSimulatedSpreadsheetValidationDemo = async (includeErrorRow: boolean) => {
    setUploading(true);
    try {
      const csvLines = [
        "code,name,tier,category_specialization,contact_name,contact_email,contact_phone,city,state,payment_terms,contracted_lead_time_days",
        "SUP-ERO-022,Erode Sustainable Yarn & Looms,TIER_1,Men's Casual Shirts,Balamurugan S,bala@erodelooms.example.in,+91-424-2289100,Erode,Tamil Nadu,NET_45,14",
      ];
      if (includeErrorRow) {
        csvLines.push("SUP-BAD-999,Invalid Mill Row,TIER_2,Denim,Ramesh,invalid-email-address,+91-000,Surat,Gujarat,NET_30,-10");
      }
      const blob = new Blob([csvLines.join("\n")], { type: "text/csv" });
      const formData = new FormData();
      formData.append("file", blob, "demo_suppliers_batch.csv");

      const res = await apiFetch("/api/spreadsheets/import/suppliers", {
        method: "POST",
        body: formData,
      });
      setImportEntity("suppliers");
      setImportResult(res);
      onNotify(
        includeErrorRow
          ? `Validation caught ${res.error_count} malformed row(s) and committed ${res.imported_count} valid row.`
          : `Successfully imported ${res.imported_count} validated supplier row(s).`
      );
    } catch (err: any) {
      onNotify(err.message, "error");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* ===================================================================
          SUB-TAB 1: PRODUCT ANALYTICS & MIXPANEL TELEMETRY
      =================================================================== */}
      {activeSubTab === "mixpanel" && analyticsData && (
        <div className="space-y-4">
          <div className="bg-[#EFECE6] border border-[#D6D3CD] p-3.5 flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-wider text-[#18181B]">
                  Telemetry Adapter Mode: {analyticsData.adapter_status.active_mode}
                </span>
                <span className="px-2 py-0.5 text-[10px] font-mono bg-[#DBEAFE] text-[#1E3A8A] border border-[#93C5FD]">
                  Local DB Events: {analyticsData.adapter_status.local_event_count} | Mixpanel Cloud:{" "}
                  {analyticsData.adapter_status.mixpanel_cloud_event_count}
                </span>
              </div>
              <p className="text-xs text-[#3F3F46] mt-1">{analyticsData.adapter_status.transparency_notice}</p>
            </div>
            <button
              onClick={async () => {
                await trackTelemetry({
                  event_name: "replenishment_recommendation_reviewed",
                  user_role: userRole,
                  workspace: "INVENTORY",
                  sku_id: "TF-MCS-1001",
                  warehouse_id: "WH-A-BLR",
                  action_status: "COMPLETED",
                });
                onNotify("Recorded live Mixpanel / PostgreSQL telemetry event.");
                loadData();
              }}
              className="px-3 py-1.5 bg-[#18181B] text-white text-xs font-medium"
            >
              + Emit Live Test Event
            </button>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-white border border-[#D6D3CD] p-3">
              <div className="text-[11px] uppercase text-[#71717A]">Total Tracked Events</div>
              <div className="text-lg font-mono font-bold mt-1">{analyticsData.metrics.total_tracked_events}</div>
            </div>
            <div className="bg-white border border-[#D6D3CD] p-3">
              <div className="text-[11px] uppercase text-[#71717A]">Workflow Completion Rate</div>
              <div className="text-lg font-mono font-bold text-[#166534] mt-1">
                {analyticsData.metrics.workflow_completion_rate_pct}%
              </div>
            </div>
            <div className="bg-white border border-[#D6D3CD] p-3">
              <div className="text-[11px] uppercase text-[#71717A]">Workflow Abandonment Rate</div>
              <div className="text-lg font-mono font-bold text-[#9A3412] mt-1">
                {analyticsData.metrics.workflow_abandonment_rate_pct}%
              </div>
            </div>
            <div className="bg-white border border-[#D6D3CD] p-3">
              <div className="text-[11px] uppercase text-[#71717A]">Avg Exception Resolution Time</div>
              <div className="text-lg font-mono font-bold text-[#1E3A8A] mt-1">
                {analyticsData.metrics.avg_exception_action_time_seconds}s
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="bg-white border border-[#D6D3CD] p-3">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-[#3F3F46] mb-2">
                Feature Adoption Across All 11 Instrumented Operational Events
              </h4>
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-[#EFECE6] border-b border-[#D6D3CD] text-[10px] font-mono uppercase">
                    <th className="py-1.5 px-2">Instrumented Event Name</th>
                    <th className="py-1.5 px-2 text-right">Count</th>
                    <th className="py-1.5 px-2 text-right">Share %</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E4E4E7] font-mono">
                  {analyticsData.feature_adoption.map((fa: any) => (
                    <tr key={fa.event_name}>
                      <td className="py-1.5 px-2 font-semibold">{fa.event_name}</td>
                      <td className="py-1.5 px-2 text-right">{fa.count}</td>
                      <td className="py-1.5 px-2 text-right">{fa.adoption_share_pct}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="bg-white border border-[#D6D3CD] p-3">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-[#3F3F46] mb-2">
                Live Operational Event Stream (Most Recent 15 Events)
              </h4>
              <div className="max-h-80 overflow-y-auto">
                <table className="w-full text-left border-collapse text-[11px] font-mono">
                  <thead>
                    <tr className="bg-[#EFECE6] border-b border-[#D6D3CD]">
                      <th className="py-1.5 px-2">Timestamp</th>
                      <th className="py-1.5 px-2">Event</th>
                      <th className="py-1.5 px-2">Role / Workspace</th>
                      <th className="py-1.5 px-2">Entity</th>
                      <th className="py-1.5 px-2">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#E4E4E7]">
                    {analyticsData.recent_events.slice(0, 15).map((ev: any) => (
                      <tr key={ev.id}>
                        <td className="py-1.5 px-2 text-[#71717A]">{ev.timestamp.slice(11)}</td>
                        <td className="py-1.5 px-2 font-semibold">{ev.event_name}</td>
                        <td className="py-1.5 px-2 font-sans">
                          {ev.user_role} ({ev.workspace})
                        </td>
                        <td className="py-1.5 px-2">{ev.sku_id || ev.supplier_id || ev.warehouse_id || "-"}</td>
                        <td className="py-1.5 px-2">
                          <span className={`px-1.5 py-0.5 text-[10px] border ${statusBadgeStyle(ev.action_status)}`}>
                            {ev.action_status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================
          SUB-TAB 2: SQL ANALYTICAL VIEWS & TABLEAU BI LAYER
      =================================================================== */}
      {activeSubTab === "sql_tableau" && sqlViewsData && (
        <div className="space-y-4">
          <div className="bg-[#EFECE6] border border-[#D6D3CD] p-3.5">
            <div className="text-xs font-bold uppercase tracking-wider text-[#18181B]">
              Tableau BI Integration Disclosure & SQL View Layer
            </div>
            <p className="text-xs text-[#3F3F46] mt-1">{sqlViewsData.tableau_integration_status.disclosure}</p>
          </div>

          <div className="grid grid-cols-1 gap-3">
            {sqlViewsData.sql_views_catalog.map((v: any) => (
              <div key={v.view_name} className="bg-white border border-[#D6D3CD] p-3.5 flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-xs text-[#1E3A8A]">{v.view_name}</span>
                    <span className="px-1.5 py-0.5 text-[10px] font-mono bg-[#EFECE6] border border-[#D6D3CD]">{v.domain}</span>
                  </div>
                  <div className="font-semibold text-xs">{v.title}</div>
                  <div className="text-xs text-[#3F3F46]">{v.description}</div>
                  <pre className="text-[11px] font-mono bg-[#F6F5F2] p-2 border border-[#D6D3CD] overflow-x-auto mt-1">
                    {v.sql}
                  </pre>
                </div>
                <div className="flex shrink-0 gap-2">
                  <a
                    href={`/api/analytics/tableau/extract/${v.view_name}?format=csv`}
                    className="px-3 py-1.5 bg-[#18181B] text-white text-xs font-mono hover:bg-[#3F3F46]"
                  >
                    Download Tableau CSV
                  </a>
                  <a
                    href={`/api/analytics/tableau/extract/${v.view_name}?format=xlsx`}
                    className="px-3 py-1.5 bg-[#1E3A8A] text-white text-xs font-mono hover:bg-[#172554]"
                  >
                    Download XLSX Extract
                  </a>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ===================================================================
          SUB-TAB 3: EXCEL & GOOGLE SHEETS IMPORT / EXPORT WORKBENCH
      =================================================================== */}
      {activeSubTab === "spreadsheets" && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Validated Import Pipeline */}
            <div className="bg-white border border-[#D6D3CD] p-4 space-y-3">
              <h3 className="text-sm font-semibold uppercase tracking-wider border-b border-[#D6D3CD] pb-2">
                1. Validated Spreadsheet Import Pipeline (CSV & XLSX)
              </h3>
              <p className="text-xs text-[#3F3F46]">
                Enforces strict schema column names, ISO date formatting (YYYY-MM-DD), positive integer quantities, and foreign-key lookup validation.
              </p>

              <div className="space-y-2">
                <label className="block text-xs font-semibold uppercase text-[#3F3F46]">Select Target Operational Table:</label>
                <div className="flex flex-wrap gap-1.5">
                  {["suppliers", "catalogue", "inventory", "purchase_orders", "returns"].map((ent) => (
                    <button
                      key={ent}
                      onClick={() => setImportEntity(ent)}
                      className={`px-2.5 py-1 text-xs font-mono border ${
                        importEntity === ent ? "bg-[#18181B] text-white border-[#18181B]" : "bg-[#F6F5F2] text-[#3F3F46] border-[#D6D3CD]"
                      }`}
                    >
                      {ent}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2 pt-2">
                <a
                  href={`/api/spreadsheets/templates/${importEntity}?format=xlsx`}
                  className="px-3 py-1.5 bg-[#EFECE6] border border-[#D6D3CD] text-xs font-mono font-medium hover:bg-[#18181B] hover:text-white"
                >
                  Download {importEntity}.xlsx Template
                </a>
                <a
                  href={`/api/spreadsheets/templates/${importEntity}?format=csv`}
                  className="px-3 py-1.5 bg-[#EFECE6] border border-[#D6D3CD] text-xs font-mono font-medium hover:bg-[#18181B] hover:text-white"
                >
                  Download {importEntity}.csv Template
                </a>
              </div>

              <div className="border-t border-[#D6D3CD] pt-3 space-y-2">
                <label className="block text-xs font-semibold uppercase text-[#3F3F46]">
                  Upload Populated CSV / XLSX File or Run Instant Validation Test:
                </label>
                <div className="flex flex-wrap items-center gap-2">
                  <input
                    type="file"
                    accept=".csv,.xlsx"
                    onChange={handleFileUpload}
                    disabled={uploading}
                    className="text-xs file:mr-2 file:py-1 file:px-3 file:border file:border-[#18181B] file:bg-[#18181B] file:text-white file:text-xs"
                  />
                  <button
                    onClick={() => runSimulatedSpreadsheetValidationDemo(false)}
                    className="px-2.5 py-1 bg-[#166534] text-white text-xs font-medium"
                  >
                    Demo Valid Import
                  </button>
                  <button
                    onClick={() => runSimulatedSpreadsheetValidationDemo(true)}
                    className="px-2.5 py-1 bg-[#9A3412] text-white text-xs font-medium"
                  >
                    Demo Row Error Diagnostic
                  </button>
                </div>
              </div>

              {importResult && (
                <div className="p-3 bg-[#F6F5F2] border border-[#D6D3CD] text-xs space-y-2">
                  <div className="font-mono font-semibold">
                    Import Status: {importResult.status.toUpperCase()} | Processed: {importResult.total_rows_processed} | Imported:{" "}
                    <span className="text-[#166534]">{importResult.imported_count}</span> | Errors:{" "}
                    <span className="text-[#991B1B]">{importResult.error_count}</span>
                  </div>
                  {importResult.errors && importResult.errors.length > 0 && (
                    <div className="space-y-1">
                      {importResult.errors.map((err: any, i: number) => (
                        <div key={i} className="p-2 bg-[#FEE2E2] border border-[#FCA5A5] text-[#991B1B] font-mono text-[11px]">
                          Row {err.row} [{err.column}]: {err.error}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Operational Report Exports */}
            <div className="bg-white border border-[#D6D3CD] p-4 space-y-3">
              <h3 className="text-sm font-semibold uppercase tracking-wider border-b border-[#D6D3CD] pb-2">
                2. Enterprise Operational Scorecards & Excel Exports
              </h3>
              <p className="text-xs text-[#3F3F46]">
                Generate live formatted Excel (.xlsx) and Google Sheets compatible (.csv) operational reports directly from the relational database.
              </p>
              <div className="divide-y divide-[#E4E4E7] border border-[#D6D3CD]">
                {[
                  { id: "supplier_scorecard", title: "Supplier Performance Scorecard", desc: "Contracted vs actual lead times, OTD %, PO fill rate, and issue counts." },
                  { id: "procurement_report", title: "Purchase Order & GRN Reconciliation Report", desc: "Ordered, received, pending, and discrepancy quantities across all 48+ POs." },
                  { id: "stockout_report", title: "Stockout & Low-Stock Risk Report", desc: "SKU-Warehouse nodes at zero available stock or below reorder point." },
                  { id: "inventory_ageing", title: "Inventory Ageing & Excess Capital Ledger", desc: "0-30d, 31-60d, 61-90d, and 90+d ageing buckets with landed cost valuation." },
                  { id: "delivery_performance", title: "Outbound Delivery & Carrier SLA Report", desc: "AWB dispatch times, carrier transit delays, and hub exception codes." },
                  { id: "return_analysis", title: "Returns, Exchanges & QC Root-Cause Report", desc: "RMA cases, reason classifications, refund statuses, and restock eligibility." },
                ].map((rep) => (
                  <div key={rep.id} className="p-2.5 flex items-center justify-between gap-2 hover:bg-[#F6F5F2]">
                    <div>
                      <div className="font-semibold text-xs">{rep.title}</div>
                      <div className="text-[11px] text-[#71717A]">{rep.desc}</div>
                    </div>
                    <div className="flex shrink-0 gap-1.5">
                      <a
                        href={`/api/spreadsheets/export/${rep.id}?format=xlsx`}
                        className="px-2.5 py-1 bg-[#1E3A8A] text-white text-[11px] font-mono"
                      >
                        .XLSX
                      </a>
                      <a
                        href={`/api/spreadsheets/export/${rep.id}?format=csv`}
                        className="px-2.5 py-1 bg-[#18181B] text-white text-[11px] font-mono"
                      >
                        .CSV
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================
          SUB-TAB 4: JIRA AGILE SCRUM & FIGMA DESIGN SYSTEM DELIVERABLES
      =================================================================== */}
      {activeSubTab === "agile_figma" && (
        <div className="space-y-4">
          <div className="bg-white border border-[#D6D3CD] p-4 space-y-3">
            <h3 className="text-sm font-semibold uppercase tracking-wider border-b border-[#D6D3CD] pb-2">
              Agile & Scrum Product Management Framework (3 Epics • 3 Two-Week Sprints)
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
              <div className="p-3 bg-[#F6F5F2] border border-[#D6D3CD] space-y-1.5">
                <div className="font-mono font-bold text-[#1E3A8A]">EPIC 1: TFLOW-EP1 (Sprint 1 • 23 SP)</div>
                <div className="font-semibold">Procurement & Catalogue Intelligence</div>
                <ul className="list-disc list-inside text-[11px] text-[#3F3F46] space-y-1">
                  <li>TFLOW-101: Supplier Directory & Lead-Time Scorecard</li>
                  <li>TFLOW-102: PO Lifecycle & GRN Discrepancy Reconciliation</li>
                  <li>TFLOW-103: SKU Catalogue Completeness (0–100%) Engine</li>
                  <li>TFLOW-104: Pricing, Gross Margin Guardrails & Promos</li>
                </ul>
              </div>
              <div className="p-3 bg-[#F6F5F2] border border-[#D6D3CD] space-y-1.5">
                <div className="font-mono font-bold text-[#166534]">EPIC 2: TFLOW-EP2 (Sprint 2 • 18 SP)</div>
                <div className="font-semibold">Inventory & Replenishment Intelligence</div>
                <ul className="list-disc list-inside text-[11px] text-[#3F3F46] space-y-1">
                  <li>TFLOW-201: Stockout Risk View & One-Click PO Conversion</li>
                  <li>TFLOW-202: Transparent 7d/30d WMA Forecast & Safety Stock</li>
                  <li>TFLOW-203: Turnover, Sell-Through & 90+d Ageing Ledger</li>
                </ul>
              </div>
              <div className="p-3 bg-[#F6F5F2] border border-[#D6D3CD] space-y-1.5">
                <div className="font-mono font-bold text-[#9A3412]">EPIC 3: TFLOW-EP3 (Sprint 2–3 • 29 SP)</div>
                <div className="font-semibold">Fulfilment, Returns & Control Tower BI</div>
                <ul className="list-disc list-inside text-[11px] text-[#3F3F46] space-y-1">
                  <li>TFLOW-301: Order Wave Picking, Packing & AWB Timeline</li>
                  <li>TFLOW-302: RMA Returns, QC Grading & Refund Simulation</li>
                  <li>TFLOW-303: Exception Queue, Mixpanel, Tableau & GenAI</li>
                </ul>
              </div>
            </div>
          </div>

          <div className="bg-white border border-[#D6D3CD] p-4 space-y-3">
            <h3 className="text-sm font-semibold uppercase tracking-wider border-b border-[#D6D3CD] pb-2">
              Figma Design System Tokens & Wireframe Handoff Specification
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-6 gap-2 text-xs font-mono">
              <div className="p-2.5 bg-[#F6F5F2] border border-[#D6D3CD]">
                <div className="w-full h-6 bg-[#F6F5F2] border border-[#D6D3CD] mb-1" />
                <div>Canvas #F6F5F2</div>
              </div>
              <div className="p-2.5 bg-[#F6F5F2] border border-[#D6D3CD]">
                <div className="w-full h-6 bg-[#18181B] mb-1" />
                <div>Charcoal #18181B</div>
              </div>
              <div className="p-2.5 bg-[#F6F5F2] border border-[#D6D3CD]">
                <div className="w-full h-6 bg-[#166534] mb-1" />
                <div>Ops Green #166534</div>
              </div>
              <div className="p-2.5 bg-[#F6F5F2] border border-[#D6D3CD]">
                <div className="w-full h-6 bg-[#1E3A8A] mb-1" />
                <div>Ops Navy #1E3A8A</div>
              </div>
              <div className="p-2.5 bg-[#F6F5F2] border border-[#D6D3CD]">
                <div className="w-full h-6 bg-[#9A3412] mb-1" />
                <div>Ops Ochre #9A3412</div>
              </div>
              <div className="p-2.5 bg-[#F6F5F2] border border-[#D6D3CD]">
                <div className="w-full h-6 bg-[#991B1B] mb-1" />
                <div>Ops Brick #991B1B</div>
              </div>
            </div>
            <p className="text-xs text-[#3F3F46]">
              Full design tokens (`deliverables/figma/design_tokens.json`), SVG wireframe boards (`deliverables/figma/assets/*.svg`), and Jira CSV backlog (`deliverables/jira/jira_backlog_import.csv`) are persisted in the workspace deliverables directory.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
