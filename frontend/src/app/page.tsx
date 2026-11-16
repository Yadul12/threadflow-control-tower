"use client";

import React, { useState, useEffect, useCallback } from "react";
import { apiFetch, formatINR, statusBadgeStyle } from "@/lib/api";
import InboundWorkspace from "@/components/InboundWorkspace";
import InventoryWorkspace from "@/components/InventoryWorkspace";
import OutboundWorkspace from "@/components/OutboundWorkspace";
import EnterpriseEnablementWorkspace from "@/components/EnterpriseEnablementWorkspace";
import AssistantDrawer from "@/components/AssistantDrawer";

type NavSection =
  | "control_tower"
  | "inbound_suppliers"
  | "inbound_pos"
  | "inbound_catalogue"
  | "inbound_pricing"
  | "inventory_overview"
  | "inventory_replenishment"
  | "inventory_performance"
  | "outbound_orders"
  | "outbound_fulfilment"
  | "outbound_delivery"
  | "outbound_returns"
  | "outbound_exceptions"
  | "bi_mixpanel"
  | "bi_tableau"
  | "bi_spreadsheets"
  | "bi_agile_figma";

const ROLES = [
  "Operations Director",
  "Procurement Lead",
  "Category Merchandiser",
  "Inventory Planner",
  "Warehouse Ops Manager",
  "CX & Returns Analyst",
];

export default function ThreadflowControlTowerPage() {
  const [activeNav, setActiveNav] = useState<NavSection>("control_tower");
  const [userRole, setUserRole] = useState<string>("Operations Director");
  const [assistantOpen, setAssistantOpen] = useState<boolean>(false);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  // Control Tower KPI & System Status State
  const [systemStatus, setSystemStatus] = useState<any>(null);
  const [kpis, setKpis] = useState<any[]>([]);
  const [excSummary, setExcSummary] = useState<any>({});
  const [kpiDomainFilter, setKpiDomainFilter] = useState<string>("ALL");
  const [selectedKpiFormula, setSelectedKpiFormula] = useState<any | null>(null);

  const notify = useCallback((message: string, type: "success" | "error" = "success") => {
    setToast({ message, type });
    setTimeout(() => {
      setToast((prev) => (prev?.message === message ? null : prev));
    }, 4500);
  }, []);

  const loadControlTower = useCallback(async () => {
    try {
      const [sys, kpiData] = await Promise.all([
        apiFetch("/api/system/status"),
        apiFetch("/api/control-tower/kpis"),
      ]);
      setSystemStatus(sys);
      setKpis(kpiData.kpis || []);
      setExcSummary(kpiData.exception_summary || {});
    } catch (e: any) {
      notify(e.message || "Failed to load Control Tower telemetry", "error");
    }
  }, [notify]);

  useEffect(() => {
    loadControlTower();
  }, [loadControlTower, activeNav]);

  const handleResetSeed = async () => {
    try {
      await apiFetch("/api/system/reset-seed", { method: "POST" });
      notify("Synthetic operational database reset to baseline seed state.");
      loadControlTower();
    } catch (e: any) {
      notify(e.message, "error");
    }
  };

  const navGroups = [
    {
      group: "UNIFIED COMMAND",
      items: [{ id: "control_tower", label: "Control Tower & 14 KPIs", code: "CT-00" }],
    },
    {
      group: "A. INBOUND & CATALOGUE",
      items: [
        { id: "inbound_suppliers", label: "Supplier Management", code: "IN-01" },
        { id: "inbound_pos", label: "Purchase Order Register", code: "IN-02" },
        { id: "inbound_catalogue", label: "Catalogue Quality Queue", code: "IN-03" },
        { id: "inbound_pricing", label: "Pricing & Promotions", code: "IN-04" },
      ],
    },
    {
      group: "B. INVENTORY INTELLIGENCE",
      items: [
        { id: "inventory_overview", label: "Inventory Overview", code: "IV-01" },
        { id: "inventory_replenishment", label: "Demand & Replenishment", code: "IV-02" },
        { id: "inventory_performance", label: "Turnover & Ageing Ledger", code: "IV-03" },
      ],
    },
    {
      group: "C. OUTBOUND & FULFILMENT",
      items: [
        { id: "outbound_orders", label: "Order Management", code: "OB-01" },
        { id: "outbound_fulfilment", label: "Warehouse Fulfilment", code: "OB-02" },
        { id: "outbound_delivery", label: "Delivery Intelligence", code: "OB-03" },
        { id: "outbound_returns", label: "Returns & Exchanges", code: "OB-04" },
        { id: "outbound_exceptions", label: "Operations Exceptions", code: "OB-05" },
      ],
    },
    {
      group: "BI, SHEETS & PRODUCT OPS",
      items: [
        { id: "bi_mixpanel", label: "Mixpanel & Event Telemetry", code: "BI-01" },
        { id: "bi_tableau", label: "SQL Views & Tableau Layer", code: "BI-02" },
        { id: "bi_spreadsheets", label: "Excel / Sheets Workflows", code: "BI-03" },
        { id: "bi_agile_figma", label: "Jira Scrum & Figma Spec", code: "PM-04" },
      ],
    },
  ];

  const activeItemLabel =
    navGroups.flatMap((g) => g.items).find((i) => i.id === activeNav)?.label || "Control Tower";

  const filteredKpis = kpis.filter((k) => kpiDomainFilter === "ALL" || k.domain === kpiDomainFilter);

  return (
    <div className="min-h-screen flex bg-[#F6F5F2] text-[#18181B]">
      {/* =====================================================================
          COMPACT ENTERPRISE LEFT NAVIGATION RAIL
      ===================================================================== */}
      <aside className="w-60 bg-[#18181B] text-[#F4F4F5] shrink-0 flex flex-col border-r border-[#27272A] select-none">
        <div className="px-4 py-3.5 border-b border-[#27272A]">
          <div className="flex items-center justify-between">
            <span className="font-mono font-bold text-sm tracking-widest text-white">THREADFLOW</span>
            <span className="px-1.5 py-0.5 text-[10px] font-mono bg-[#27272A] text-[#A1A1AA] border border-[#3F3F46]">
              v2.4
            </span>
          </div>
          <div className="text-[11px] text-[#A1A1AA] mt-0.5">
            Supply Chain & Merchandising Control Tower
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-4">
          {navGroups.map((grp) => (
            <div key={grp.group}>
              <div className="px-2 mb-1 text-[10px] font-mono font-semibold uppercase tracking-wider text-[#71717A]">
                {grp.group}
              </div>
              <div className="space-y-0.5">
                {grp.items.map((item) => {
                  const active = activeNav === item.id;
                  return (
                    <button
                      key={item.id}
                      onClick={() => setActiveNav(item.id as NavSection)}
                      className={`w-full flex items-center justify-between px-2.5 py-1.5 text-xs text-left transition-colors ${
                        active
                          ? "bg-[#F6F5F2] text-[#18181B] font-semibold"
                          : "text-[#D4D4D8] hover:bg-[#27272A] hover:text-white"
                      }`}
                    >
                      <span className="truncate">{item.label}</span>
                      <span
                        className={`font-mono text-[10px] ${
                          active ? "text-[#1E3A8A] font-bold" : "text-[#71717A]"
                        }`}
                      >
                        {item.code}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        <div className="p-3 border-t border-[#27272A] bg-[#121214] text-[11px] space-y-2">
          <div className="font-mono text-[10px] text-[#A1A1AA]">
            DB: {systemStatus?.database?.connection_scheme?.toUpperCase() || "RELATIONAL"} •{" "}
            {systemStatus?.entity_counts?.products || 240} SKUs
          </div>
          <button
            onClick={handleResetSeed}
            className="w-full py-1 px-2 bg-[#27272A] hover:bg-[#3F3F46] text-[#E4E4E7] text-[11px] font-mono border border-[#3F3F46]"
          >
            Reset Synthetic Baseline
          </button>
        </div>
      </aside>

      {/* =====================================================================
          MAIN OPERATIONAL WORKSPACE AREA
      ===================================================================== */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Command Header */}
        <header className="h-12 bg-white border-b border-[#D6D3CD] px-4 flex items-center justify-between gap-3 shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <h1 className="text-sm font-semibold text-[#18181B] truncate">{activeItemLabel}</h1>
            <span className="hidden md:inline-block px-2 py-0.5 text-[10px] font-mono bg-[#FFEDD5] text-[#9A3412] border border-[#FDBA74]">
              SYNTHETIC OPERATIONAL DATA
            </span>
          </div>

          <div className="flex items-center gap-2.5">
            <div className="flex items-center gap-1.5 text-xs">
              <span className="text-[11px] text-[#71717A] hidden sm:inline">Active Role:</span>
              <select
                value={userRole}
                onChange={(e) => setUserRole(e.target.value)}
                className="px-2 py-1 text-xs bg-[#F6F5F2] border border-[#D6D3CD] font-medium focus:outline-none"
              >
                {ROLES.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={() => setAssistantOpen(true)}
              className="px-3 py-1 bg-[#18181B] hover:bg-[#3F3F46] text-white text-xs font-mono font-medium flex items-center gap-1.5"
            >
              <span>[AI] Ops Evidence Assistant</span>
            </button>
          </div>
        </header>

        {/* Action Confirmation / Notification Banner */}
        {toast && (
          <div
            className={`px-4 py-2 text-xs font-mono flex items-center justify-between border-b ${
              toast.type === "error"
                ? "bg-[#FEE2E2] text-[#991B1B] border-[#FCA5A5]"
                : "bg-[#DCFCE7] text-[#166534] border-[#86EFAC]"
            }`}
          >
            <span>
              <strong>{toast.type === "error" ? "ACTION ERROR:" : "WORKFLOW CONFIRMED:"}</strong> {toast.message}
            </span>
            <button onClick={() => setToast(null)} className="underline text-[11px]">
              Dismiss
            </button>
          </div>
        )}

        {/* Workspace Content */}
        <main className="flex-1 p-4 overflow-y-auto">
          {/* =================================================================
              CONTROL TOWER UNIFIED KPI & EXCEPTION LEDGER
          ================================================================= */}
          {activeNav === "control_tower" && (
            <div className="space-y-4">
              {/* Operational Context & Quick Triage Bar */}
              <div className="bg-white border border-[#D6D3CD] p-3.5 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="text-xs font-bold uppercase tracking-wider text-[#18181B]">
                    Unified Supply Chain & Merchandising Control Tower — 14 Audited KPIs
                  </div>
                  <p className="text-xs text-[#3F3F46] mt-0.5">
                    Every metric below is computed live from the relational schema with documented formulas, reporting windows, and source tables.
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    onClick={() => setActiveNav("outbound_exceptions")}
                    className="px-2.5 py-1 bg-[#FEE2E2] text-[#991B1B] border border-[#FCA5A5] text-xs font-mono font-semibold hover:bg-[#991B1B] hover:text-white"
                  >
                    Active Exceptions: {excSummary.total_active || 0} ({excSummary.critical_count || 0} Critical) →
                  </button>
                  <button
                    onClick={() => setAssistantOpen(true)}
                    className="px-2.5 py-1 bg-[#DBEAFE] text-[#1E3A8A] border border-[#93C5FD] text-xs font-mono font-medium"
                  >
                    Diagnose Warehouse A Decline →
                  </button>
                </div>
              </div>

              {/* Domain Filter */}
              <div className="flex flex-wrap items-center justify-between gap-2 bg-[#EFECE6] border border-[#D6D3CD] px-3 py-2">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-semibold uppercase tracking-wider text-[#3F3F46] mr-1">
                    Filter KPI Horizon:
                  </span>
                  {["ALL", "PROCUREMENT", "INVENTORY", "OUTBOUND"].map((dom) => (
                    <button
                      key={dom}
                      onClick={() => setKpiDomainFilter(dom)}
                      className={`px-2.5 py-1 text-xs font-mono border ${
                        kpiDomainFilter === dom
                          ? "bg-[#18181B] text-white border-[#18181B]"
                          : "bg-white text-[#3F3F46] border-[#D6D3CD]"
                      }`}
                    >
                      {dom}
                    </button>
                  ))}
                </div>
                <div className="text-[11px] font-mono text-[#3F3F46]">
                  Click any KPI row to inspect its full SQL calculation methodology
                </div>
              </div>

              {/* Unified 14-KPI Data Table (No superficial card clutter — high-density operational register) */}
              <div className="bg-white border border-[#D6D3CD] overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-[#EFECE6] border-b border-[#D6D3CD] text-[11px] font-semibold uppercase tracking-wider text-[#3F3F46]">
                      <th className="py-2.5 px-3">Domain</th>
                      <th className="py-2.5 px-3">KPI Name</th>
                      <th className="py-2.5 px-3 text-right">Current Value</th>
                      <th className="py-2.5 px-3 text-right">Target SLA</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3">Mathematical Formula</th>
                      <th className="py-2.5 px-3">Reporting Window</th>
                      <th className="py-2.5 px-3">Source Tables</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#E4E4E7]">
                    {filteredKpis.map((k) => (
                      <tr
                        key={k.id}
                        onClick={() => setSelectedKpiFormula(selectedKpiFormula?.id === k.id ? null : k)}
                        className="hover:bg-[#F6F5F2] cursor-pointer"
                      >
                        <td className="py-2.5 px-3 font-mono text-[11px] font-semibold text-[#3F3F46]">{k.domain}</td>
                        <td className="py-2.5 px-3 font-semibold text-[#18181B]">{k.name}</td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums font-bold text-sm">
                          {k.unit === "INR" ? formatINR(k.value) : `${k.value} ${k.unit}`}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums text-[#71717A]">
                          {k.unit === "INR" ? formatINR(k.target) : `${k.target} ${k.unit}`}
                        </td>
                        <td className="py-2.5 px-3">
                          <span className={`px-2 py-0.5 text-[10px] font-mono border ${statusBadgeStyle(k.status)}`}>
                            {k.status}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 font-mono text-[11px] text-[#1E3A8A]">{k.formula}</td>
                        <td className="py-2.5 px-3 text-[11px] text-[#3F3F46]">{k.reporting_period}</td>
                        <td className="py-2.5 px-3 font-mono text-[11px] text-[#71717A]">
                          {k.source_tables.join(", ")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {selectedKpiFormula && (
                <div className="bg-[#EFECE6] border border-[#18181B] p-3.5 text-xs space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold uppercase text-[#18181B]">
                      KPI Calculation Specification — {selectedKpiFormula.name} ({selectedKpiFormula.domain})
                    </span>
                    <button
                      onClick={() => setSelectedKpiFormula(null)}
                      className="font-mono text-[11px] underline"
                    >
                      Close
                    </button>
                  </div>
                  <div>
                    <strong>Formula:</strong> <code className="font-mono">{selectedKpiFormula.formula}</code>
                  </div>
                  <div>
                    <strong>Calculation Method:</strong> {selectedKpiFormula.calculation_method}
                  </div>
                  <div>
                    <strong>Source Relational Tables:</strong>{" "}
                    <span className="font-mono">{selectedKpiFormula.source_tables.join(", ")}</span> |{" "}
                    <strong>Reporting Window:</strong> {selectedKpiFormula.reporting_period}
                  </div>
                </div>
              )}

              {/* Cross-Workspace Operational Navigation Matrix */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-white border border-[#D6D3CD] p-4 space-y-2.5">
                  <div className="flex items-center justify-between border-b border-[#D6D3CD] pb-2">
                    <span className="font-mono text-xs font-bold text-[#1E3A8A]">WORKSPACE A: INBOUND</span>
                    <span className="font-mono text-[11px] text-[#71717A]">
                      {systemStatus?.entity_counts?.suppliers || 12} Suppliers •{" "}
                      {systemStatus?.entity_counts?.purchase_orders || 48} POs
                    </span>
                  </div>
                  <p className="text-xs text-[#3F3F46]">
                    Manage garment mill lead times, acknowledge POs, record partial/full GRN receipts, remediate incomplete SKU size charts, and govern promotional margins.
                  </p>
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    <button
                      onClick={() => setActiveNav("inbound_suppliers")}
                      className="px-2.5 py-1 bg-[#EFECE6] hover:bg-[#18181B] hover:text-white border border-[#D6D3CD] text-xs font-medium"
                    >
                      Supplier Scorecard
                    </button>
                    <button
                      onClick={() => setActiveNav("inbound_pos")}
                      className="px-2.5 py-1 bg-[#EFECE6] hover:bg-[#18181B] hover:text-white border border-[#D6D3CD] text-xs font-medium"
                    >
                      PO Register
                    </button>
                    <button
                      onClick={() => setActiveNav("inbound_catalogue")}
                      className="px-2.5 py-1 bg-[#EFECE6] hover:bg-[#18181B] hover:text-white border border-[#D6D3CD] text-xs font-medium"
                    >
                      Catalogue Queue
                    </button>
                  </div>
                </div>

                <div className="bg-white border border-[#D6D3CD] p-4 space-y-2.5">
                  <div className="flex items-center justify-between border-b border-[#D6D3CD] pb-2">
                    <span className="font-mono text-xs font-bold text-[#166534]">WORKSPACE B: INVENTORY</span>
                    <span className="font-mono text-[11px] text-[#71717A]">
                      {systemStatus?.entity_counts?.warehouses || 4} FCs •{" "}
                      {systemStatus?.entity_counts?.inventory_records || 480} Nodes
                    </span>
                  </div>
                  <p className="text-xs text-[#3F3F46]">
                    Inspect multi-warehouse stock cover, review transparent 7d/30d moving average demand forecasts, convert stockout alerts into POs, and audit 90+d aged stock.
                  </p>
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    <button
                      onClick={() => setActiveNav("inventory_overview")}
                      className="px-2.5 py-1 bg-[#EFECE6] hover:bg-[#18181B] hover:text-white border border-[#D6D3CD] text-xs font-medium"
                    >
                      Stock Overview
                    </button>
                    <button
                      onClick={() => setActiveNav("inventory_replenishment")}
                      className="px-2.5 py-1 bg-[#EFECE6] hover:bg-[#18181B] hover:text-white border border-[#D6D3CD] text-xs font-medium"
                    >
                      Demand & Replenish
                    </button>
                    <button
                      onClick={() => setActiveNav("inventory_performance")}
                      className="px-2.5 py-1 bg-[#EFECE6] hover:bg-[#18181B] hover:text-white border border-[#D6D3CD] text-xs font-medium"
                    >
                      Ageing & Turnover
                    </button>
                  </div>
                </div>

                <div className="bg-white border border-[#D6D3CD] p-4 space-y-2.5">
                  <div className="flex items-center justify-between border-b border-[#D6D3CD] pb-2">
                    <span className="font-mono text-xs font-bold text-[#9A3412]">WORKSPACE C: OUTBOUND</span>
                    <span className="font-mono text-[11px] text-[#71717A]">
                      {systemStatus?.entity_counts?.orders || 180} Orders •{" "}
                      {systemStatus?.entity_counts?.returns || 52} RMAs
                    </span>
                  </div>
                  <p className="text-xs text-[#3F3F46]">
                    Advance order picking/packing/dispatch waves, inspect carrier AWB timelines, process RMA QC & refund simulations, and resolve warehouse SLA exceptions.
                  </p>
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    <button
                      onClick={() => setActiveNav("outbound_fulfilment")}
                      className="px-2.5 py-1 bg-[#EFECE6] hover:bg-[#18181B] hover:text-white border border-[#D6D3CD] text-xs font-medium"
                    >
                      Fulfilment & AWBs
                    </button>
                    <button
                      onClick={() => setActiveNav("outbound_returns")}
                      className="px-2.5 py-1 bg-[#EFECE6] hover:bg-[#18181B] hover:text-white border border-[#D6D3CD] text-xs font-medium"
                    >
                      Returns & QC
                    </button>
                    <button
                      onClick={() => setActiveNav("outbound_exceptions")}
                      className="px-2.5 py-1 bg-[#EFECE6] hover:bg-[#18181B] hover:text-white border border-[#D6D3CD] text-xs font-medium"
                    >
                      Exception Queue
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* WORKSPACE A: INBOUND */}
          {activeNav === "inbound_suppliers" && (
            <InboundWorkspace activeSubTab="suppliers" userRole={userRole} onNotify={notify} />
          )}
          {activeNav === "inbound_pos" && (
            <InboundWorkspace activeSubTab="purchase_orders" userRole={userRole} onNotify={notify} />
          )}
          {activeNav === "inbound_catalogue" && (
            <InboundWorkspace activeSubTab="catalogue" userRole={userRole} onNotify={notify} />
          )}
          {activeNav === "inbound_pricing" && (
            <InboundWorkspace activeSubTab="pricing" userRole={userRole} onNotify={notify} />
          )}

          {/* WORKSPACE B: INVENTORY */}
          {activeNav === "inventory_overview" && (
            <InventoryWorkspace activeSubTab="overview" userRole={userRole} onNotify={notify} />
          )}
          {activeNav === "inventory_replenishment" && (
            <InventoryWorkspace activeSubTab="replenishment" userRole={userRole} onNotify={notify} />
          )}
          {activeNav === "inventory_performance" && (
            <InventoryWorkspace activeSubTab="performance" userRole={userRole} onNotify={notify} />
          )}

          {/* WORKSPACE C: OUTBOUND */}
          {activeNav === "outbound_orders" && (
            <OutboundWorkspace activeSubTab="orders" userRole={userRole} onNotify={notify} />
          )}
          {activeNav === "outbound_fulfilment" && (
            <OutboundWorkspace activeSubTab="fulfilment" userRole={userRole} onNotify={notify} />
          )}
          {activeNav === "outbound_delivery" && (
            <OutboundWorkspace activeSubTab="delivery" userRole={userRole} onNotify={notify} />
          )}
          {activeNav === "outbound_returns" && (
            <OutboundWorkspace activeSubTab="returns" userRole={userRole} onNotify={notify} />
          )}
          {activeNav === "outbound_exceptions" && (
            <OutboundWorkspace activeSubTab="exceptions" userRole={userRole} onNotify={notify} />
          )}

          {/* BI, SHEETS & PRODUCT OPS */}
          {activeNav === "bi_mixpanel" && (
            <EnterpriseEnablementWorkspace activeSubTab="mixpanel" userRole={userRole} onNotify={notify} />
          )}
          {activeNav === "bi_tableau" && (
            <EnterpriseEnablementWorkspace activeSubTab="sql_tableau" userRole={userRole} onNotify={notify} />
          )}
          {activeNav === "bi_spreadsheets" && (
            <EnterpriseEnablementWorkspace activeSubTab="spreadsheets" userRole={userRole} onNotify={notify} />
          )}
          {activeNav === "bi_agile_figma" && (
            <EnterpriseEnablementWorkspace activeSubTab="agile_figma" userRole={userRole} onNotify={notify} />
          )}
        </main>
      </div>

      {/* GenAI Evidence-Grounded Operations Assistant Drawer */}
      <AssistantDrawer isOpen={assistantOpen} onClose={() => setAssistantOpen(false)} />
    </div>
  );
}
