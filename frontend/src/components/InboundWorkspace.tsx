"use client";

import React, { useState, useEffect, useCallback } from "react";
import { apiFetch, trackTelemetry, formatINR, statusBadgeStyle } from "@/lib/api";

interface InboundProps {
  activeSubTab: "suppliers" | "purchase_orders" | "catalogue" | "pricing";
  userRole: string;
  onNotify: (msg: string, type?: "success" | "error") => void;
}

export default function InboundWorkspace({ activeSubTab, userRole, onNotify }: InboundProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Suppliers state
  const [suppliers, setSuppliers] = useState<any[]>([]);
  const [supFilterStatus, setSupFilterStatus] = useState("ALL");
  const [supSearch, setSupSearch] = useState("");
  const [selectedSupplier, setSelectedSupplier] = useState<any | null>(null);
  const [showNewSupplierModal, setShowNewSupplierModal] = useState(false);
  const [newSupForm, setNewSupForm] = useState({
    code: "SUP-CBE-018",
    name: "Kovai Fine Combed Knits Pvt Ltd",
    tier: "TIER_1",
    category_specialization: "Men's Casual Shirts & Polos",
    contact_name: "Muthuvel Rajagopal",
    contact_email: "muthuvel@kovaiknits.example.in",
    contact_phone: "+91-422-2491822",
    city: "Coimbatore",
    state: "Tamil Nadu",
    payment_terms: "NET_45",
    contracted_lead_time_days: 15,
  });
  const [newIssueNote, setNewIssueNote] = useState("");

  // Purchase Orders state
  const [pos, setPos] = useState<any[]>([]);
  const [poSummary, setPoSummary] = useState<any>({});
  const [poFilterStatus, setPoFilterStatus] = useState("ALL");
  const [expandedPoId, setExpandedPoId] = useState<number | null>(null);
  const [showCreatePoModal, setShowCreatePoModal] = useState(false);
  const [newPoForm, setNewPoForm] = useState({
    supplier_id: 1,
    warehouse_id: 1,
    product_id: 1,
    ordered_qty: 160,
    expected_delivery_days: 15,
    notes: "AW26 Mid-Season Core Size Replenishment",
  });

  // Catalogue state
  const [catalogue, setCatalogue] = useState<any[]>([]);
  const [catSummary, setCatSummary] = useState<any>({});
  const [onlyIssues, setOnlyIssues] = useState(true);
  const [catSearch, setCatSearch] = useState("");
  const [editingSku, setEditingSku] = useState<any | null>(null);

  // Pricing & Promotions state
  const [pricingRows, setPricingRows] = useState<any[]>([]);
  const [promotions, setPromotions] = useState<any[]>([]);
  const [pricingSummary, setPricingSummary] = useState<any>({});
  const [belowTargetOnly, setBelowTargetOnly] = useState(false);
  const [editingPriceId, setEditingPriceId] = useState<number | null>(null);
  const [editDiscountVal, setEditDiscountVal] = useState<string>("15");
  const [showNewPromoModal, setShowNewPromoModal] = useState(false);
  const [newPromoForm, setNewPromoForm] = useState({
    code: "PROMO-AW26-DENIM20",
    name: "AW26 Core Denim Fit Event",
    campaign_type: "CATEGORY_SPOTLIGHT",
    discount_pct: 18,
    start_date: "2026-11-18",
    end_date: "2026-12-02",
    baseline_daily_units: 95,
    promo_daily_units: 148,
  });

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (activeSubTab === "suppliers") {
        const q = new URLSearchParams();
        if (supFilterStatus !== "ALL") q.set("status", supFilterStatus);
        if (supSearch) q.set("search", supSearch);
        const data = await apiFetch(`/api/inbound/suppliers?${q.toString()}`);
        setSuppliers(data.suppliers || []);
      } else if (activeSubTab === "purchase_orders") {
        const q = new URLSearchParams();
        if (poFilterStatus !== "ALL") q.set("status", poFilterStatus);
        const data = await apiFetch(`/api/inbound/purchase-orders?${q.toString()}`);
        setPos(data.purchase_orders || []);
        setPoSummary(data.summary || {});
      } else if (activeSubTab === "catalogue") {
        const q = new URLSearchParams();
        if (onlyIssues) q.set("only_issues", "true");
        if (catSearch) q.set("search", catSearch);
        const data = await apiFetch(`/api/inbound/catalogue?${q.toString()}`);
        setCatalogue(data.catalogue || []);
        setCatSummary(data.summary || {});
      } else if (activeSubTab === "pricing") {
        const q = new URLSearchParams();
        if (belowTargetOnly) q.set("below_target_margin", "true");
        const data = await apiFetch(`/api/inbound/pricing?${q.toString()}`);
        setPricingRows(data.pricing_ledger || []);
        setPromotions(data.promotions || []);
        setPricingSummary(data.summary || {});
      }
    } catch (e: any) {
      setError(e.message || "Failed to load Inbound data");
    } finally {
      setLoading(false);
    }
  }, [activeSubTab, supFilterStatus, supSearch, poFilterStatus, onlyIssues, catSearch, belowTargetOnly]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // --- Handlers ---
  const openSupplierProfile = async (supId: number, supCode: string) => {
    try {
      const detail = await apiFetch(`/api/inbound/suppliers/${supId}`);
      setSelectedSupplier(detail);
      trackTelemetry({
        event_name: "supplier_profile_opened",
        user_role: userRole,
        workspace: "INBOUND",
        supplier_id: supCode,
      });
    } catch (e: any) {
      onNotify(e.message, "error");
    }
  };

  const handleCreateSupplier = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await apiFetch("/api/inbound/suppliers", {
        method: "POST",
        body: JSON.stringify(newSupForm),
      });
      onNotify(`Supplier ${res.code} onboarded to directory.`);
      setShowNewSupplierModal(false);
      loadData();
    } catch (err: any) {
      onNotify(err.message, "error");
    }
  };

  const handleSupplierUpdate = async (supId: number, supCode: string, payload: any) => {
    try {
      await apiFetch(`/api/inbound/suppliers/${supId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      onNotify(`Updated supplier ${supCode} record.`);
      setNewIssueNote("");
      openSupplierProfile(supId, supCode);
      loadData();
    } catch (err: any) {
      onNotify(err.message, "error");
    }
  };

  const handleCreatePo = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await apiFetch("/api/inbound/purchase-orders", {
        method: "POST",
        body: JSON.stringify({
          supplier_id: Number(newPoForm.supplier_id),
          warehouse_id: Number(newPoForm.warehouse_id),
          expected_delivery_days: Number(newPoForm.expected_delivery_days),
          notes: newPoForm.notes,
          created_by: userRole,
          items: [{ product_id: Number(newPoForm.product_id), ordered_qty: Number(newPoForm.ordered_qty) }],
        }),
      });
      trackTelemetry({
        event_name: "purchase_order_created",
        user_role: userRole,
        workspace: "INBOUND",
        supplier_id: `SUP-${newPoForm.supplier_id}`,
        warehouse_id: `WH-${newPoForm.warehouse_id}`,
      });
      onNotify(`Purchase Order ${res.po_number} created (${res.total_ordered_qty} units, ${formatINR(res.total_value_inr)}).`);
      setShowCreatePoModal(false);
      loadData();
    } catch (err: any) {
      onNotify(err.message, "error");
    }
  };

  const handlePoStatusAction = async (po: any, newStatus: string, extra?: any) => {
    try {
      const res = await apiFetch(`/api/inbound/purchase-orders/${po.id}/status`, {
        method: "PATCH",
        body: JSON.stringify({
          status: newStatus,
          ...extra,
        }),
      });
      trackTelemetry({
        event_name: "purchase_order_updated",
        user_role: userRole,
        workspace: "INBOUND",
        supplier_id: po.supplier_code,
        warehouse_id: po.warehouse_code,
      });
      onNotify(`PO ${po.po_number} transitioned to ${res.new_status} (Received: ${res.total_received_qty}, Pending: ${res.pending_qty}).`);
      loadData();
    } catch (err: any) {
      onNotify(err.message, "error");
    }
  };

  const handleRemediateSku = async (skuItem: any) => {
    try {
      const res = await apiFetch(`/api/inbound/catalogue/${skuItem.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          description: skuItem.description || `Verified AW26 technical specification for ${skuItem.name} (${skuItem.fabric_composition}, ${skuItem.gsm_or_weight}).`,
          has_description: true,
          image_count: Math.max(5, skuItem.image_count || 5),
          has_size_chart: true,
          has_fabric_care: true,
          is_duplicate_flag: false,
        }),
      });
      trackTelemetry({
        event_name: "catalogue_issue_resolved",
        user_role: userRole,
        workspace: "INBOUND",
        sku_id: skuItem.sku,
      });
      onNotify(`SKU ${skuItem.sku} remediated — Completeness Score updated to ${res.completeness_score}%.`);
      setEditingSku(null);
      loadData();
    } catch (err: any) {
      onNotify(err.message, "error");
    }
  };

  const handleUpdatePricing = async (row: any) => {
    try {
      const res = await apiFetch(`/api/inbound/pricing/${row.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          discount_pct: parseFloat(editDiscountVal),
          reason: `Adjusted by ${userRole} in Pricing Workbench`,
        }),
      });
      onNotify(`SKU ${res.sku} updated: Selling Price ${formatINR(res.selling_price)} (${res.discount_pct}% off) | Gross Margin: ${res.gross_margin_pct}%.`);
      setEditingPriceId(null);
      loadData();
    } catch (err: any) {
      onNotify(err.message, "error");
    }
  };

  const handleCreatePromo = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await apiFetch("/api/inbound/promotions", {
        method: "POST",
        body: JSON.stringify(newPromoForm),
      });
      onNotify(`Promotional campaign ${res.code} scheduled.`);
      setShowNewPromoModal(false);
      loadData();
    } catch (err: any) {
      onNotify(err.message, "error");
    }
  };

  return (
    <div className="space-y-4">
      {error && (
        <div className="bg-[#FEE2E2] border border-[#FCA5A5] text-[#991B1B] px-4 py-2.5 flex items-center justify-between">
          <span>Operational Error: {error}</span>
          <button onClick={loadData} className="underline font-semibold text-xs">
            Retry
          </button>
        </div>
      )}

      {/* ===================================================================
          SUB-TAB 1: SUPPLIER MANAGEMENT & SCORECARD REGISTER
      =================================================================== */}
      {activeSubTab === "suppliers" && (
        <div className="space-y-4">
          <div className="bg-[#EFECE6] border border-[#D6D3CD] p-3 flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#3F3F46]">Status:</span>
              {["ALL", "ACTIVE", "UNDER_AUDIT", "ON_HOLD"].map((st) => (
                <button
                  key={st}
                  onClick={() => setSupFilterStatus(st)}
                  className={`px-2.5 py-1 text-xs font-mono border ${
                    supFilterStatus === st
                      ? "bg-[#18181B] text-white border-[#18181B]"
                      : "bg-white text-[#3F3F46] border-[#D6D3CD] hover:bg-[#F6F5F2]"
                  }`}
                >
                  {st}
                </button>
              ))}
              <input
                type="text"
                placeholder="Filter supplier name, code, city, category..."
                value={supSearch}
                onChange={(e) => setSupSearch(e.target.value)}
                className="ml-2 px-3 py-1 text-xs bg-white border border-[#D6D3CD] w-64 focus:outline-none focus:border-[#18181B]"
              />
            </div>
            <button
              onClick={() => setShowNewSupplierModal(true)}
              className="px-3 py-1.5 bg-[#1E3A8A] text-white text-xs font-medium hover:bg-[#172554]"
            >
              + Onboard Supplier
            </button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className={`${selectedSupplier ? "lg:col-span-2" : "lg:col-span-3"} bg-white border border-[#D6D3CD] overflow-x-auto`}>
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-[#EFECE6] border-b border-[#D6D3CD] text-[11px] font-semibold uppercase tracking-wider text-[#3F3F46]">
                    <th className="py-2.5 px-3">Code / Mill Name</th>
                    <th className="py-2.5 px-3">Category & City</th>
                    <th className="py-2.5 px-3">Tier</th>
                    <th className="py-2.5 px-3 text-right">Lead Time (Act vs SLA)</th>
                    <th className="py-2.5 px-3 text-right">OTD %</th>
                    <th className="py-2.5 px-3 text-right">Fill Rate %</th>
                    <th className="py-2.5 px-3 text-right">Issues</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E4E4E7] text-xs">
                  {loading ? (
                    <tr>
                      <td colSpan={9} className="py-8 text-center text-[#71717A]">
                        Loading supplier scorecard register...
                      </td>
                    </tr>
                  ) : suppliers.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="py-8 text-center text-[#71717A]">
                        No suppliers match the selected filter criteria.
                      </td>
                    </tr>
                  ) : (
                    suppliers.map((s) => (
                      <tr key={s.id} className="hover:bg-[#F6F5F2]">
                        <td className="py-2.5 px-3">
                          <div className="font-mono font-semibold text-[#18181B]">{s.code}</div>
                          <div className="text-[#3F3F46]">{s.name}</div>
                        </td>
                        <td className="py-2.5 px-3">
                          <div>{s.category_specialization}</div>
                          <div className="text-[11px] text-[#71717A]">
                            {s.city}, {s.state} • {s.payment_terms}
                          </div>
                        </td>
                        <td className="py-2.5 px-3">
                          <span className={`px-1.5 py-0.5 text-[10px] font-mono border ${statusBadgeStyle(s.tier)}`}>
                            {s.tier}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums">
                          <span className={s.lead_time_variance_days > 3 ? "text-[#991B1B] font-semibold" : "text-[#18181B]"}>
                            {s.actual_avg_lead_time_days}d
                          </span>{" "}
                          <span className="text-[#71717A]">/ {s.contracted_lead_time_days}d</span>
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums font-medium">
                          <span className={s.on_time_delivery_rate < 82 ? "text-[#991B1B]" : s.on_time_delivery_rate < 90 ? "text-[#9A3412]" : "text-[#166534]"}>
                            {s.on_time_delivery_rate}%
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums">{s.fill_rate}%</td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums">
                          {s.issue_count > 0 ? (
                            <span className="text-[#991B1B] font-semibold">{s.issue_count}</span>
                          ) : (
                            <span className="text-[#71717A]">0</span>
                          )}
                        </td>
                        <td className="py-2.5 px-3">
                          <span className={`px-2 py-0.5 text-[10px] font-mono border ${statusBadgeStyle(s.status)}`}>
                            {s.status}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-right">
                          <button
                            onClick={() => openSupplierProfile(s.id, s.code)}
                            className="px-2.5 py-1 bg-[#EFECE6] hover:bg-[#18181B] hover:text-white text-[#18181B] border border-[#D6D3CD] text-[11px] font-medium"
                          >
                            Scorecard & POs
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {selectedSupplier && (
              <div className="bg-white border border-[#D6D3CD] p-4 space-y-4">
                <div className="flex items-start justify-between border-b border-[#D6D3CD] pb-3">
                  <div>
                    <div className="text-[11px] font-mono text-[#71717A]">{selectedSupplier.supplier.code}</div>
                    <h3 className="text-sm font-semibold text-[#18181B]">{selectedSupplier.supplier.name}</h3>
                    <div className="text-xs text-[#3F3F46] mt-0.5">
                      Contact: {selectedSupplier.supplier.contact_name} ({selectedSupplier.supplier.contact_phone})
                    </div>
                  </div>
                  <button
                    onClick={() => setSelectedSupplier(null)}
                    className="text-xs text-[#71717A] hover:text-[#18181B] font-mono px-1.5 py-0.5 border border-[#D6D3CD]"
                  >
                    CLOSE [X]
                  </button>
                </div>

                <div className="grid grid-cols-3 gap-2 bg-[#F6F5F2] p-2.5 border border-[#D6D3CD] text-center">
                  <div>
                    <div className="text-[10px] uppercase text-[#71717A]">OTD Rate</div>
                    <div className="font-mono font-semibold text-sm">{selectedSupplier.supplier.on_time_delivery_rate}%</div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase text-[#71717A]">Quality Pass</div>
                    <div className="font-mono font-semibold text-sm">{selectedSupplier.supplier.quality_pass_rate}%</div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase text-[#71717A]">Actual LT</div>
                    <div className="font-mono font-semibold text-sm">{selectedSupplier.supplier.actual_avg_lead_time_days}d</div>
                  </div>
                </div>

                {/* Governance Status Toggle */}
                <div className="space-y-1.5">
                  <div className="text-[11px] font-semibold uppercase text-[#3F3F46]">Vendor Governance Action</div>
                  <div className="flex gap-1.5">
                    {["ACTIVE", "UNDER_AUDIT", "ON_HOLD"].map((st) => (
                      <button
                        key={st}
                        onClick={() => handleSupplierUpdate(selectedSupplier.supplier.id, selectedSupplier.supplier.code, { status: st })}
                        className={`px-2 py-1 text-[11px] font-mono border ${
                          selectedSupplier.supplier.status === st
                            ? "bg-[#18181B] text-white border-[#18181B]"
                            : "bg-[#F6F5F2] text-[#3F3F46] border-[#D6D3CD]"
                        }`}
                      >
                        Set {st}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Log new supplier quality/delivery issue */}
                <div className="space-y-1.5 border-t border-[#D6D3CD] pt-3">
                  <div className="text-[11px] font-semibold uppercase text-[#3F3F46]">
                    Supplier Issue History ({selectedSupplier.supplier.issue_history.length})
                  </div>
                  <div className="flex gap-1.5">
                    <input
                      type="text"
                      placeholder="Log new AQL defect or lead-time incident..."
                      value={newIssueNote}
                      onChange={(e) => setNewIssueNote(e.target.value)}
                      className="flex-1 px-2 py-1 text-xs border border-[#D6D3CD]"
                    />
                    <button
                      onClick={() => {
                        if (!newIssueNote.trim()) return;
                        handleSupplierUpdate(selectedSupplier.supplier.id, selectedSupplier.supplier.code, {
                          new_issue_note: newIssueNote,
                          new_issue_severity: "HIGH",
                        });
                      }}
                      className="px-2.5 py-1 bg-[#991B1B] text-white text-xs font-medium"
                    >
                      Log Issue
                    </button>
                  </div>
                  <div className="max-h-36 overflow-y-auto space-y-1.5 mt-2">
                    {selectedSupplier.supplier.issue_history.length === 0 ? (
                      <div className="text-xs text-[#71717A] italic">Zero compliance issues recorded.</div>
                    ) : (
                      selectedSupplier.supplier.issue_history.map((iss: any, idx: number) => (
                        <div key={idx} className="p-2 bg-[#F6F5F2] border border-[#D6D3CD] text-xs">
                          <div className="flex justify-between font-mono text-[10px] text-[#71717A]">
                            <span>{iss.date}</span>
                            <span className="text-[#991B1B] font-semibold">{iss.severity}</span>
                          </div>
                          <div className="text-[#18181B] mt-0.5">{iss.summary}</div>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Historical Purchase Orders */}
                <div className="space-y-1.5 border-t border-[#D6D3CD] pt-3">
                  <div className="text-[11px] font-semibold uppercase text-[#3F3F46]">
                    Historical Purchase Orders ({selectedSupplier.historical_purchase_orders.length})
                  </div>
                  <div className="max-h-44 overflow-y-auto divide-y divide-[#E4E4E7] border border-[#D6D3CD]">
                    {selectedSupplier.historical_purchase_orders.map((po: any) => (
                      <div key={po.id} className="p-2 flex items-center justify-between text-xs">
                        <div>
                          <div className="font-mono font-medium">{po.po_number}</div>
                          <div className="text-[11px] text-[#71717A]">
                            Exp: {po.expected_delivery_date} | Rcvd: {po.total_received_qty}/{po.total_ordered_qty}
                          </div>
                        </div>
                        <span className={`px-1.5 py-0.5 text-[10px] font-mono border ${statusBadgeStyle(po.status)}`}>
                          {po.status}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ===================================================================
          SUB-TAB 2: PURCHASE ORDER REGISTER & GRN WORKBENCH
      =================================================================== */}
      {activeSubTab === "purchase_orders" && (
        <div className="space-y-4">
          <div className="bg-[#EFECE6] border border-[#D6D3CD] p-3 flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#3F3F46]">PO Lifecycle:</span>
              {["ALL", "ISSUED", "ACKNOWLEDGED", "DELAYED", "PARTIALLY_RECEIVED", "RECEIVED", "CLOSED"].map((st) => (
                <button
                  key={st}
                  onClick={() => setPoFilterStatus(st)}
                  className={`px-2.5 py-1 text-xs font-mono border ${
                    poFilterStatus === st
                      ? "bg-[#18181B] text-white border-[#18181B]"
                      : "bg-white text-[#3F3F46] border-[#D6D3CD]"
                  }`}
                >
                  {st}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-4">
              <div className="text-xs font-mono text-[#3F3F46]">
                Delayed POs: <strong className="text-[#991B1B]">{poSummary.delayed_count || 0}</strong> | Pending Units:{" "}
                <strong>{poSummary.total_pending_units || 0}</strong> | Discrepancies:{" "}
                <strong className="text-[#9A3412]">{poSummary.total_discrepancy_units || 0}</strong>
              </div>
              <button
                onClick={() => setShowCreatePoModal(true)}
                className="px-3 py-1.5 bg-[#1E3A8A] text-white text-xs font-medium hover:bg-[#172554]"
              >
                + Create Purchase Order
              </button>
            </div>
          </div>

          <div className="bg-white border border-[#D6D3CD] overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-[#EFECE6] border-b border-[#D6D3CD] text-[11px] font-semibold uppercase tracking-wider text-[#3F3F46]">
                  <th className="py-2.5 px-3">PO Number</th>
                  <th className="py-2.5 px-3">Supplier & Category</th>
                  <th className="py-2.5 px-3">FC Dest</th>
                  <th className="py-2.5 px-3">Dates (Ord / Exp / Act)</th>
                  <th className="py-2.5 px-3 text-right">Ordered / Rcvd / Pend</th>
                  <th className="py-2.5 px-3 text-right">Discrepancy</th>
                  <th className="py-2.5 px-3 text-right">PO Value</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3 text-right">Operational Workflow Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E4E4E7] text-xs">
                {pos.map((po) => (
                  <React.Fragment key={po.id}>
                    <tr className="hover:bg-[#F6F5F2]">
                      <td className="py-2.5 px-3">
                        <button
                          onClick={() => setExpandedPoId(expandedPoId === po.id ? null : po.id)}
                          className="font-mono font-semibold text-[#1E3A8A] hover:underline flex items-center gap-1"
                        >
                          <span>{expandedPoId === po.id ? "▼" : "▶"}</span>
                          <span>{po.po_number}</span>
                        </button>
                        <div className="text-[10px] font-mono text-[#71717A]">
                          {po.supplier_acknowledged ? "ACK: Verified" : "ACK: Pending Vendor"}
                        </div>
                      </td>
                      <td className="py-2.5 px-3">
                        <div className="font-medium text-[#18181B]">{po.supplier_name}</div>
                        <div className="text-[11px] text-[#71717A]">{po.category_name}</div>
                      </td>
                      <td className="py-2.5 px-3 font-mono">{po.warehouse_code}</td>
                      <td className="py-2.5 px-3 font-mono text-[11px]">
                        <div>Ord: {po.order_date}</div>
                        <div>Exp: {po.expected_delivery_date}</div>
                        {po.delay_days > 0 && (
                          <div className="text-[#991B1B] font-semibold">Slippage: +{po.delay_days}d</div>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono tabular-nums">
                        <span className="font-semibold">{po.total_ordered_qty}</span> /{" "}
                        <span className="text-[#166534]">{po.total_received_qty}</span> /{" "}
                        <span className="text-[#9A3412]">{po.pending_qty}</span>
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono tabular-nums">
                        {po.discrepancy_qty > 0 ? (
                          <span className="text-[#991B1B] font-semibold">-{po.discrepancy_qty} u</span>
                        ) : (
                          <span className="text-[#71717A]">0</span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono tabular-nums font-medium">
                        {formatINR(po.total_value_inr)}
                      </td>
                      <td className="py-2.5 px-3">
                        <span className={`px-2 py-0.5 text-[10px] font-mono border ${statusBadgeStyle(po.status)}`}>
                          {po.status}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right space-x-1">
                        {!po.supplier_acknowledged && (
                          <button
                            onClick={() => handlePoStatusAction(po, "ACKNOWLEDGED", { supplier_acknowledged: true })}
                            className="px-2 py-1 bg-[#DBEAFE] text-[#1E3A8A] border border-[#93C5FD] text-[11px] font-medium hover:bg-[#1E3A8A] hover:text-white"
                          >
                            Ack PO
                          </button>
                        )}
                        {po.status !== "RECEIVED" && po.status !== "CLOSED" && (
                          <>
                            <button
                              onClick={() => handlePoStatusAction(po, "PARTIALLY_RECEIVED", { received_ratio: 0.65, discrepancy_qty: 8 })}
                              className="px-2 py-1 bg-[#FFEDD5] text-[#9A3412] border border-[#FDBA74] text-[11px] font-medium hover:bg-[#9A3412] hover:text-white"
                            >
                              Partial GRN
                            </button>
                            <button
                              onClick={() => handlePoStatusAction(po, "RECEIVED", { received_ratio: 1.0, discrepancy_qty: 0 })}
                              className="px-2 py-1 bg-[#DCFCE7] text-[#166534] border border-[#86EFAC] text-[11px] font-medium hover:bg-[#166534] hover:text-white"
                            >
                              Full GRN
                            </button>
                          </>
                        )}
                        {po.status !== "DELAYED" && po.status !== "RECEIVED" && (
                          <button
                            onClick={() => handlePoStatusAction(po, "DELAYED", { delay_days: 5, delay_reason: "Production line bottleneck flagged by procurement desk" })}
                            className="px-2 py-1 bg-[#FEE2E2] text-[#991B1B] border border-[#FCA5A5] text-[11px] font-medium"
                          >
                            Flag Delay
                          </button>
                        )}
                      </td>
                    </tr>
                    {expandedPoId === po.id && (
                      <tr className="bg-[#F6F5F2]">
                        <td colSpan={9} className="p-3 border-l-4 border-[#1E3A8A]">
                          <div className="text-xs font-semibold mb-2 text-[#18181B]">
                            Line Items for {po.po_number} {po.delay_reason ? `• Delay Reason: ${po.delay_reason}` : ""}
                          </div>
                          <table className="w-full text-left bg-white border border-[#D6D3CD] text-[11px]">
                            <thead>
                              <tr className="bg-[#EFECE6] border-b border-[#D6D3CD] font-mono uppercase">
                                <th className="py-1.5 px-2">SKU</th>
                                <th className="py-1.5 px-2">Product Description</th>
                                <th className="py-1.5 px-2 text-right">Ordered</th>
                                <th className="py-1.5 px-2 text-right">Received</th>
                                <th className="py-1.5 px-2 text-right">Pending</th>
                                <th className="py-1.5 px-2 text-right">Rejected / Disc</th>
                                <th className="py-1.5 px-2 text-right">Unit Cost</th>
                                <th className="py-1.5 px-2 text-right">Line Total</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-[#E4E4E7] font-mono">
                              {po.items.map((it: any) => (
                                <tr key={it.id}>
                                  <td className="py-1.5 px-2 font-semibold">{it.sku}</td>
                                  <td className="py-1.5 px-2 font-sans">{it.product_name}</td>
                                  <td className="py-1.5 px-2 text-right">{it.ordered_qty}</td>
                                  <td className="py-1.5 px-2 text-right text-[#166534]">{it.received_qty}</td>
                                  <td className="py-1.5 px-2 text-right text-[#9A3412]">{it.pending_qty}</td>
                                  <td className="py-1.5 px-2 text-right text-[#991B1B]">{it.rejected_qty}</td>
                                  <td className="py-1.5 px-2 text-right">{formatINR(it.unit_cost_inr)}</td>
                                  <td className="py-1.5 px-2 text-right font-semibold">{formatINR(it.line_total_inr)}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ===================================================================
          SUB-TAB 3: CATALOGUE QUALITY & COMPLETENESS QUEUE
      =================================================================== */}
      {activeSubTab === "catalogue" && (
        <div className="space-y-4">
          <div className="bg-[#EFECE6] border border-[#D6D3CD] p-3 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setOnlyIssues(!onlyIssues)}
                className={`px-3 py-1 text-xs font-mono border ${
                  onlyIssues ? "bg-[#991B1B] text-white border-[#991B1B]" : "bg-white text-[#18181B] border-[#D6D3CD]"
                }`}
              >
                {onlyIssues ? "Showing Incomplete & Duplicate SKUs Only" : "Showing All 240 SKUs"}
              </button>
              <input
                type="text"
                placeholder="Search SKU, style code, brand..."
                value={catSearch}
                onChange={(e) => setCatSearch(e.target.value)}
                className="px-3 py-1 text-xs bg-white border border-[#D6D3CD] w-64"
              />
            </div>
            <div className="text-xs font-mono text-[#3F3F46]">
              Avg Completeness: <strong>{catSummary.avg_completeness_score || 0}%</strong> | Incomplete SKUs:{" "}
              <strong className="text-[#991B1B]">{catSummary.incomplete_sku_count || 0}</strong> | Missing Size Charts:{" "}
              <strong className="text-[#9A3412]">{catSummary.missing_size_chart_count || 0}</strong> | Duplicates:{" "}
              <strong>{catSummary.duplicate_listing_count || 0}</strong>
            </div>
          </div>

          <div className="bg-white border border-[#D6D3CD] overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-[#EFECE6] border-b border-[#D6D3CD] text-[11px] font-semibold uppercase tracking-wider text-[#3F3F46]">
                  <th className="py-2.5 px-3">SKU / Style</th>
                  <th className="py-2.5 px-3">Product & Brand</th>
                  <th className="py-2.5 px-3">Size / Colour / Spec</th>
                  <th className="py-2.5 px-3">Missing Merchandising Attributes</th>
                  <th className="py-2.5 px-3 text-right">Images</th>
                  <th className="py-2.5 px-3 text-right">Completeness</th>
                  <th className="py-2.5 px-3 text-right">Remediation Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E4E4E7] text-xs">
                {catalogue.slice(0, 60).map((item) => (
                  <tr key={item.id} className="hover:bg-[#F6F5F2]">
                    <td className="py-2.5 px-3 font-mono">
                      <div className="font-semibold text-[#18181B]">{item.sku}</div>
                      <div className="text-[11px] text-[#71717A]">{item.style_code}</div>
                    </td>
                    <td className="py-2.5 px-3">
                      <div className="font-medium text-[#18181B]">{item.name}</div>
                      <div className="text-[11px] text-[#71717A]">
                        {item.brand} • {item.category_name} • {item.supplier_name}
                      </div>
                    </td>
                    <td className="py-2.5 px-3">
                      <div className="flex items-center gap-1.5">
                        <span
                          className="w-3 h-3 inline-block border border-[#D6D3CD]"
                          style={{ backgroundColor: item.color_hex }}
                        />
                        <span className="font-mono">{item.size}</span>
                        <span>• {item.color}</span>
                      </div>
                      <div className="text-[11px] text-[#71717A]">
                        {item.gsm_or_weight} • {item.fabric_composition}
                      </div>
                    </td>
                    <td className="py-2.5 px-3">
                      {item.missing_fields.length === 0 ? (
                        <span className="px-2 py-0.5 text-[10px] font-mono bg-[#DCFCE7] text-[#166534] border border-[#86EFAC]">
                          100% READY FOR STOREFRONT
                        </span>
                      ) : (
                        <div className="flex flex-wrap gap-1">
                          {item.missing_fields.map((mf: string, i: number) => (
                            <span
                              key={i}
                              className="px-1.5 py-0.5 text-[10px] font-mono bg-[#FEE2E2] text-[#991B1B] border border-[#FCA5A5]"
                            >
                              {mf}
                            </span>
                          ))}
                          {item.is_duplicate_flag && (
                            <span className="px-1.5 py-0.5 text-[10px] font-mono bg-[#FFEDD5] text-[#9A3412] border border-[#FDBA74]">
                              Dup of {item.duplicate_of_sku}
                            </span>
                          )}
                        </div>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono">{item.image_count} shots</td>
                    <td className="py-2.5 px-3 text-right font-mono tabular-nums">
                      <span
                        className={`font-semibold ${
                          item.completeness_score >= 95
                            ? "text-[#166534]"
                            : item.completeness_score >= 75
                            ? "text-[#9A3412]"
                            : "text-[#991B1B]"
                        }`}
                      >
                        {item.completeness_score}%
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      {item.completeness_score < 100 || item.is_duplicate_flag ? (
                        <button
                          onClick={() => {
                            trackTelemetry({
                              event_name: "catalogue_issue_opened",
                              user_role: userRole,
                              workspace: "INBOUND",
                              sku_id: item.sku,
                            });
                            handleRemediateSku(item);
                          }}
                          className="px-2.5 py-1 bg-[#166534] text-white text-[11px] font-medium hover:bg-[#14532D]"
                        >
                          Attach Specs & Fix (100%)
                        </button>
                      ) : (
                        <span className="text-[11px] font-mono text-[#71717A]">Verified</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ===================================================================
          SUB-TAB 4: PRICING, GROSS MARGIN & PROMOTIONAL CALENDAR
      =================================================================== */}
      {activeSubTab === "pricing" && (
        <div className="space-y-4">
          {/* Active Promotional Calendar */}
          <div className="bg-white border border-[#D6D3CD] p-4">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="text-sm font-semibold text-[#18181B]">Promotional Campaign Calendar & Margin Impact</h3>
                <p className="text-xs text-[#71717A]">
                  Tracks baseline vs promo daily unit velocity, uplift %, and gross margin dilution across active markdown events.
                </p>
              </div>
              <button
                onClick={() => setShowNewPromoModal(true)}
                className="px-3 py-1.5 bg-[#1E3A8A] text-white text-xs font-medium"
              >
                + Schedule Promotion
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse border border-[#D6D3CD] text-xs">
                <thead>
                  <tr className="bg-[#EFECE6] border-b border-[#D6D3CD] text-[11px] font-semibold uppercase text-[#3F3F46]">
                    <th className="py-2 px-3">Code / Campaign</th>
                    <th className="py-2 px-3">Type & Category</th>
                    <th className="py-2 px-3">Window</th>
                    <th className="py-2 px-3 text-right">Discount</th>
                    <th className="py-2 px-3 text-right">Baseline / Promo Units</th>
                    <th className="py-2 px-3 text-right">Unit Uplift</th>
                    <th className="py-2 px-3 text-right">GM Impact</th>
                    <th className="py-2 px-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E4E4E7]">
                  {promotions.map((pr) => (
                    <tr key={pr.id} className="hover:bg-[#F6F5F2]">
                      <td className="py-2 px-3">
                        <div className="font-mono font-semibold">{pr.code}</div>
                        <div>{pr.name}</div>
                      </td>
                      <td className="py-2 px-3">
                        <div className="font-mono text-[11px]">{pr.campaign_type}</div>
                        <div className="text-[#71717A]">{pr.category_name}</div>
                      </td>
                      <td className="py-2 px-3 font-mono text-[11px]">
                        {pr.start_date} → {pr.end_date}
                      </td>
                      <td className="py-2 px-3 text-right font-mono font-semibold text-[#9A3412]">{pr.discount_pct}%</td>
                      <td className="py-2 px-3 text-right font-mono">
                        {pr.baseline_daily_units}/d → <strong>{pr.promo_daily_units}/d</strong>
                      </td>
                      <td className="py-2 px-3 text-right font-mono text-[#166534] font-semibold">+{pr.uplift_pct}%</td>
                      <td className="py-2 px-3 text-right font-mono text-[#991B1B]">{pr.gross_margin_impact_pct}%</td>
                      <td className="py-2 px-3">
                        <span className={`px-2 py-0.5 text-[10px] font-mono border ${statusBadgeStyle(pr.status)}`}>
                          {pr.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* SKU Pricing & Gross Margin Guardrail Ledger */}
          <div className="bg-white border border-[#D6D3CD]">
            <div className="bg-[#EFECE6] border-b border-[#D6D3CD] p-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-xs font-semibold uppercase tracking-wider text-[#3F3F46]">
                  SKU Pricing & Gross Margin Guardrail Ledger
                </span>
                <button
                  onClick={() => setBelowTargetOnly(!belowTargetOnly)}
                  className={`px-2.5 py-1 text-xs font-mono border ${
                    belowTargetOnly ? "bg-[#991B1B] text-white border-[#991B1B]" : "bg-white text-[#18181B] border-[#D6D3CD]"
                  }`}
                >
                  {belowTargetOnly ? "Showing Below-Target Margin SKUs" : "Filter: Below Target Margin Only"}
                </button>
              </div>
              <div className="text-xs font-mono text-[#3F3F46]">
                Realized Avg Margin: <strong>{pricingSummary.avg_realized_margin_pct || 0}%</strong> | Margin Breaches:{" "}
                <strong className="text-[#991B1B]">{pricingSummary.margin_breach_count || 0}</strong>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-[#EFECE6] border-b border-[#D6D3CD] text-[11px] font-semibold uppercase text-[#3F3F46]">
                    <th className="py-2.5 px-3">SKU</th>
                    <th className="py-2.5 px-3">Product & Category</th>
                    <th className="py-2.5 px-3 text-right">Landed Cost</th>
                    <th className="py-2.5 px-3 text-right">MRP</th>
                    <th className="py-2.5 px-3 text-right">Discount %</th>
                    <th className="py-2.5 px-3 text-right">Selling Price</th>
                    <th className="py-2.5 px-3 text-right">Realized GM % (vs Target)</th>
                    <th className="py-2.5 px-3">Guardrail</th>
                    <th className="py-2.5 px-3 text-right">Update Price</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E4E4E7]">
                  {pricingRows.slice(0, 50).map((r) => (
                    <tr key={r.id} className="hover:bg-[#F6F5F2]">
                      <td className="py-2.5 px-3 font-mono font-semibold">{r.sku}</td>
                      <td className="py-2.5 px-3">
                        <div className="font-medium">{r.name}</div>
                        <div className="text-[11px] text-[#71717A]">{r.category_name}</div>
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono">{formatINR(r.cost_price)}</td>
                      <td className="py-2.5 px-3 text-right font-mono">{formatINR(r.mrp)}</td>
                      <td className="py-2.5 px-3 text-right font-mono">
                        {editingPriceId === r.id ? (
                          <input
                            type="number"
                            min={0}
                            max={75}
                            value={editDiscountVal}
                            onChange={(e) => setEditDiscountVal(e.target.value)}
                            className="w-16 px-1.5 py-0.5 border border-[#18181B] text-right font-mono"
                          />
                        ) : (
                          <span>{r.discount_pct}%</span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono font-semibold">{formatINR(r.selling_price)}</td>
                      <td className="py-2.5 px-3 text-right font-mono">
                        <span className={r.margin_variance_pct < 0 ? "text-[#991B1B] font-semibold" : "text-[#166534] font-semibold"}>
                          {r.gross_margin_pct}%
                        </span>{" "}
                        <span className="text-[#71717A]">/ {r.target_gross_margin_pct}%</span>
                      </td>
                      <td className="py-2.5 px-3">
                        <span className={`px-2 py-0.5 text-[10px] font-mono border ${statusBadgeStyle(r.margin_status)}`}>
                          {r.margin_status}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        {editingPriceId === r.id ? (
                          <div className="inline-flex gap-1">
                            <button
                              onClick={() => handleUpdatePricing(r)}
                              className="px-2 py-0.5 bg-[#166534] text-white text-[11px]"
                            >
                              Save
                            </button>
                            <button
                              onClick={() => setEditingPriceId(null)}
                              className="px-2 py-0.5 bg-[#EFECE6] text-[#18181B] text-[11px]"
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => {
                              setEditingPriceId(r.id);
                              setEditDiscountVal(String(r.discount_pct));
                            }}
                            className="px-2 py-1 bg-[#EFECE6] hover:bg-[#18181B] hover:text-white border border-[#D6D3CD] text-[11px]"
                          >
                            Edit Discount
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: Create Supplier */}
      {showNewSupplierModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <form onSubmit={handleCreateSupplier} className="bg-white border border-[#18181B] w-full max-w-lg p-5 space-y-3">
            <h3 className="text-sm font-semibold uppercase tracking-wider border-b border-[#D6D3CD] pb-2">
              Onboard New Garment / Apparel Supplier
            </h3>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <label className="block font-medium mb-1">Supplier Code</label>
                <input
                  required
                  value={newSupForm.code}
                  onChange={(e) => setNewSupForm({ ...newSupForm, code: e.target.value })}
                  className="w-full px-2.5 py-1.5 border border-[#D6D3CD] font-mono"
                />
              </div>
              <div>
                <label className="block font-medium mb-1">Supplier Name</label>
                <input
                  required
                  value={newSupForm.name}
                  onChange={(e) => setNewSupForm({ ...newSupForm, name: e.target.value })}
                  className="w-full px-2.5 py-1.5 border border-[#D6D3CD]"
                />
              </div>
              <div>
                <label className="block font-medium mb-1">Category Specialization</label>
                <input
                  required
                  value={newSupForm.category_specialization}
                  onChange={(e) => setNewSupForm({ ...newSupForm, category_specialization: e.target.value })}
                  className="w-full px-2.5 py-1.5 border border-[#D6D3CD]"
                />
              </div>
              <div>
                <label className="block font-medium mb-1">Contracted Lead Time (Days)</label>
                <input
                  type="number"
                  required
                  value={newSupForm.contracted_lead_time_days}
                  onChange={(e) => setNewSupForm({ ...newSupForm, contracted_lead_time_days: Number(e.target.value) })}
                  className="w-full px-2.5 py-1.5 border border-[#D6D3CD] font-mono"
                />
              </div>
              <div>
                <label className="block font-medium mb-1">Contact Name</label>
                <input
                  required
                  value={newSupForm.contact_name}
                  onChange={(e) => setNewSupForm({ ...newSupForm, contact_name: e.target.value })}
                  className="w-full px-2.5 py-1.5 border border-[#D6D3CD]"
                />
              </div>
              <div>
                <label className="block font-medium mb-1">Contact Email</label>
                <input
                  type="email"
                  required
                  value={newSupForm.contact_email}
                  onChange={(e) => setNewSupForm({ ...newSupForm, contact_email: e.target.value })}
                  className="w-full px-2.5 py-1.5 border border-[#D6D3CD]"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-3 border-t border-[#D6D3CD]">
              <button
                type="button"
                onClick={() => setShowNewSupplierModal(false)}
                className="px-3 py-1.5 border border-[#D6D3CD] text-xs"
              >
                Cancel
              </button>
              <button type="submit" className="px-4 py-1.5 bg-[#1E3A8A] text-white text-xs font-medium">
                Confirm Onboarding
              </button>
            </div>
          </form>
        </div>
      )}

      {/* MODAL: Create Purchase Order */}
      {showCreatePoModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <form onSubmit={handleCreatePo} className="bg-white border border-[#18181B] w-full max-w-md p-5 space-y-3">
            <h3 className="text-sm font-semibold uppercase tracking-wider border-b border-[#D6D3CD] pb-2">
              Issue New Purchase Order
            </h3>
            <div className="space-y-2.5 text-xs">
              <div>
                <label className="block font-medium mb-1">Supplier ID (1 = Kaveri Knits, 2 = Deccan Loom, 3 = Tapi Silk)</label>
                <input
                  type="number"
                  min={1}
                  max={12}
                  value={newPoForm.supplier_id}
                  onChange={(e) => setNewPoForm({ ...newPoForm, supplier_id: Number(e.target.value) })}
                  className="w-full px-2.5 py-1.5 border border-[#D6D3CD] font-mono"
                />
              </div>
              <div>
                <label className="block font-medium mb-1">Destination Warehouse (1=WH-A-BLR, 2=WH-B-DEL, 3=WH-C-BOM, 4=WH-D-CCU)</label>
                <input
                  type="number"
                  min={1}
                  max={4}
                  value={newPoForm.warehouse_id}
                  onChange={(e) => setNewPoForm({ ...newPoForm, warehouse_id: Number(e.target.value) })}
                  className="w-full px-2.5 py-1.5 border border-[#D6D3CD] font-mono"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block font-medium mb-1">Product ID (1–240)</label>
                  <input
                    type="number"
                    min={1}
                    max={240}
                    value={newPoForm.product_id}
                    onChange={(e) => setNewPoForm({ ...newPoForm, product_id: Number(e.target.value) })}
                    className="w-full px-2.5 py-1.5 border border-[#D6D3CD] font-mono"
                  />
                </div>
                <div>
                  <label className="block font-medium mb-1">Order Quantity (Units)</label>
                  <input
                    type="number"
                    min={20}
                    value={newPoForm.ordered_qty}
                    onChange={(e) => setNewPoForm({ ...newPoForm, ordered_qty: Number(e.target.value) })}
                    className="w-full px-2.5 py-1.5 border border-[#D6D3CD] font-mono"
                  />
                </div>
              </div>
              <div>
                <label className="block font-medium mb-1">Procurement Notes</label>
                <input
                  value={newPoForm.notes}
                  onChange={(e) => setNewPoForm({ ...newPoForm, notes: e.target.value })}
                  className="w-full px-2.5 py-1.5 border border-[#D6D3CD]"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-3 border-t border-[#D6D3CD]">
              <button type="button" onClick={() => setShowCreatePoModal(false)} className="px-3 py-1.5 border border-[#D6D3CD] text-xs">
                Cancel
              </button>
              <button type="submit" className="px-4 py-1.5 bg-[#1E3A8A] text-white text-xs font-medium">
                Issue PO
              </button>
            </div>
          </form>
        </div>
      )}

      {/* MODAL: Create Promotion */}
      {showNewPromoModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <form onSubmit={handleCreatePromo} className="bg-white border border-[#18181B] w-full max-w-md p-5 space-y-3">
            <h3 className="text-sm font-semibold uppercase tracking-wider border-b border-[#D6D3CD] pb-2">
              Schedule Promotional Campaign
            </h3>
            <div className="space-y-2.5 text-xs">
              <div>
                <label className="block font-medium mb-1">Promo Code</label>
                <input
                  required
                  value={newPromoForm.code}
                  onChange={(e) => setNewPromoForm({ ...newPromoForm, code: e.target.value })}
                  className="w-full px-2.5 py-1.5 border border-[#D6D3CD] font-mono"
                />
              </div>
              <div>
                <label className="block font-medium mb-1">Campaign Name</label>
                <input
                  required
                  value={newPromoForm.name}
                  onChange={(e) => setNewPromoForm({ ...newPromoForm, name: e.target.value })}
                  className="w-full px-2.5 py-1.5 border border-[#D6D3CD]"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block font-medium mb-1">Discount %</label>
                  <input
                    type="number"
                    value={newPromoForm.discount_pct}
                    onChange={(e) => setNewPromoForm({ ...newPromoForm, discount_pct: Number(e.target.value) })}
                    className="w-full px-2.5 py-1.5 border border-[#D6D3CD] font-mono"
                  />
                </div>
                <div>
                  <label className="block font-medium mb-1">Expected Daily Units</label>
                  <input
                    type="number"
                    value={newPromoForm.promo_daily_units}
                    onChange={(e) => setNewPromoForm({ ...newPromoForm, promo_daily_units: Number(e.target.value) })}
                    className="w-full px-2.5 py-1.5 border border-[#D6D3CD] font-mono"
                  />
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-3 border-t border-[#D6D3CD]">
              <button type="button" onClick={() => setShowNewPromoModal(false)} className="px-3 py-1.5 border border-[#D6D3CD] text-xs">
                Cancel
              </button>
              <button type="submit" className="px-4 py-1.5 bg-[#1E3A8A] text-white text-xs font-medium">
                Save Campaign
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
