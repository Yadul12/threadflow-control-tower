"use client";

import React, { useState, useEffect, useCallback } from "react";
import { apiFetch, trackTelemetry, formatINR, statusBadgeStyle } from "@/lib/api";

interface InventoryProps {
  activeSubTab: "overview" | "replenishment" | "performance";
  userRole: string;
  onNotify: (msg: string, type?: "success" | "error") => void;
}

export default function InventoryWorkspace({ activeSubTab, userRole, onNotify }: InventoryProps) {
  const [loading, setLoading] = useState(false);

  // Overview state
  const [warehouses, setWarehouses] = useState<any[]>([]);
  const [inventoryRows, setInventoryRows] = useState<any[]>([]);
  const [recentMovements, setRecentMovements] = useState<any[]>([]);
  const [selectedWhId, setSelectedWhId] = useState<number | null>(null);
  const [stockFilter, setStockFilter] = useState("ALL");
  const [invSearch, setInvSearch] = useState("");
  const [adjustingItem, setAdjustingItem] = useState<any | null>(null);
  const [adjustDelta, setAdjustDelta] = useState<string>("40");

  // Replenishment state
  const [methodology, setMethodology] = useState<any>(null);
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [repSummary, setRepSummary] = useState<any>({});

  // Performance state
  const [catPerformance, setCatPerformance] = useState<any[]>([]);
  const [excessItems, setExcessItems] = useState<any[]>([]);
  const [stockoutItems, setStockoutItems] = useState<any[]>([]);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      if (activeSubTab === "overview") {
        const q = new URLSearchParams();
        if (selectedWhId) q.set("warehouse_id", String(selectedWhId));
        if (stockFilter !== "ALL") q.set("stock_status", stockFilter);
        if (invSearch) q.set("search", invSearch);
        const data = await apiFetch(`/api/inventory/overview?${q.toString()}`);
        setWarehouses(data.warehouses || []);
        setInventoryRows(data.inventory || []);
        setRecentMovements(data.recent_movements || []);
      } else if (activeSubTab === "replenishment") {
        const q = new URLSearchParams({ only_actionable: "true" });
        if (selectedWhId) q.set("warehouse_id", String(selectedWhId));
        const data = await apiFetch(`/api/inventory/demand-replenishment?${q.toString()}`);
        setMethodology(data.methodology_documentation || null);
        setRecommendations(data.recommendations || []);
        setRepSummary(data.summary || {});
      } else if (activeSubTab === "performance") {
        const data = await apiFetch("/api/inventory/performance");
        setCatPerformance(data.category_performance || []);
        setExcessItems(data.excess_and_slow_moving || []);
        setStockoutItems(data.stockout_analysis || []);
      }
    } catch (e: any) {
      onNotify(e.message, "error");
    } finally {
      setLoading(false);
    }
  }, [activeSubTab, selectedWhId, stockFilter, invSearch, onNotify]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleAdjustStock = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!adjustingItem) return;
    try {
      const res = await apiFetch("/api/inventory/adjust", {
        method: "POST",
        body: JSON.stringify({
          inventory_id: adjustingItem.id,
          quantity_delta: parseInt(adjustDelta, 10),
          movement_type: "CYCLE_COUNT_ADJ",
          notes: `Cycle count adjustment logged by ${userRole}`,
          performed_by: userRole,
        }),
      });
      trackTelemetry({
        event_name: "inventory_alert_opened",
        user_role: userRole,
        workspace: "INVENTORY",
        sku_id: adjustingItem.sku,
        warehouse_id: adjustingItem.warehouse_code,
      });
      onNotify(
        `Adjusted ${adjustingItem.sku} at ${adjustingItem.warehouse_code}: New On-Hand = ${res.on_hand_qty} u (DOC: ${res.days_of_cover}d, Status: ${res.stock_status}).`
      );
      setAdjustingItem(null);
      loadData();
    } catch (err: any) {
      onNotify(err.message, "error");
    }
  };

  const handleConvertToPo = async (rec: any) => {
    try {
      const res = await apiFetch(`/api/inventory/replenishment/${rec.inventory_id}/create-po`, {
        method: "POST",
        body: JSON.stringify({
          override_qty: rec.recommended_order_qty,
          created_by: userRole,
        }),
      });
      trackTelemetry({
        event_name: "replenishment_recommendation_reviewed",
        user_role: userRole,
        workspace: "INVENTORY",
        sku_id: rec.sku,
        warehouse_id: rec.warehouse_code,
        supplier_id: rec.supplier_code,
      });
      onNotify(
        `Replenishment PO ${res.po_number} issued to ${rec.supplier_name} for ${res.ordered_qty} units of ${res.sku} (${formatINR(res.total_value_inr)}).`
      );
      loadData();
    } catch (err: any) {
      onNotify(err.message, "error");
    }
  };

  return (
    <div className="space-y-4">
      {/* ===================================================================
          SUB-TAB 1: INVENTORY OVERVIEW & WAREHOUSE MATRIX
      =================================================================== */}
      {activeSubTab === "overview" && (
        <div className="space-y-4">
          {/* Regional Fulfilment Centre Selector Matrix */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            {warehouses.map((w) => {
              const isSelected = selectedWhId === w.id;
              return (
                <div
                  key={w.id}
                  onClick={() => setSelectedWhId(isSelected ? null : w.id)}
                  className={`p-3 border cursor-pointer transition-colors ${
                    isSelected ? "bg-[#18181B] text-white border-[#18181B]" : "bg-white text-[#18181B] border-[#D6D3CD] hover:bg-[#F6F5F2]"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-xs">{w.code}</span>
                    <span className={`px-1.5 py-0.5 text-[10px] font-mono border ${statusBadgeStyle(w.bottleneck_status)}`}>
                      {w.bottleneck_status}
                    </span>
                  </div>
                  <div className={`text-xs mt-1 truncate ${isSelected ? "text-[#E4E4E7]" : "text-[#3F3F46]"}`}>{w.name}</div>
                  <div className="grid grid-cols-3 gap-2 mt-2.5 pt-2 border-t border-[#D6D3CD]/40 font-mono text-[11px]">
                    <div>
                      <div className="text-[10px] opacity-75">Util %</div>
                      <div className="font-semibold">{w.utilization_pct}%</div>
                    </div>
                    <div>
                      <div className="text-[10px] opacity-75">Stockouts</div>
                      <div className="font-semibold text-[#FCA5A5]">{w.stockout_skus}</div>
                    </div>
                    <div>
                      <div className="text-[10px] opacity-75">Available</div>
                      <div className="font-semibold">{w.total_available.toLocaleString()}</div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Filter Bar */}
          <div className="bg-[#EFECE6] border border-[#D6D3CD] p-3 flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#3F3F46]">Stock Position:</span>
              {["ALL", "STOCKOUT", "LOW_STOCK", "HEALTHY", "EXCESS", "SLOW_MOVING"].map((st) => (
                <button
                  key={st}
                  onClick={() => setStockFilter(st)}
                  className={`px-2.5 py-1 text-xs font-mono border ${
                    stockFilter === st ? "bg-[#18181B] text-white border-[#18181B]" : "bg-white text-[#3F3F46] border-[#D6D3CD]"
                  }`}
                >
                  {st}
                </button>
              ))}
              <input
                type="text"
                placeholder="Search SKU, product name, brand..."
                value={invSearch}
                onChange={(e) => setInvSearch(e.target.value)}
                className="ml-2 px-3 py-1 text-xs bg-white border border-[#D6D3CD] w-60"
              />
            </div>
            {selectedWhId && (
              <button onClick={() => setSelectedWhId(null)} className="text-xs font-mono underline text-[#1E3A8A]">
                Clear Warehouse Filter
              </button>
            )}
          </div>

          {/* SKU-Warehouse Inventory Table */}
          <div className="bg-white border border-[#D6D3CD] overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-[#EFECE6] border-b border-[#D6D3CD] text-[11px] font-semibold uppercase tracking-wider text-[#3F3F46]">
                  <th className="py-2.5 px-3">FC / SKU</th>
                  <th className="py-2.5 px-3">Product & Category</th>
                  <th className="py-2.5 px-3 text-right">On Hand</th>
                  <th className="py-2.5 px-3 text-right">Reserved</th>
                  <th className="py-2.5 px-3 text-right">Available</th>
                  <th className="py-2.5 px-3 text-right">In Transit</th>
                  <th className="py-2.5 px-3 text-right">Safety / ROP</th>
                  <th className="py-2.5 px-3 text-right">Stock Cover</th>
                  <th className="py-2.5 px-3 text-right">Ageing (0-30 / 31-60 / 61-90 / 90+)</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3 text-right">Ledger Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E4E4E7]">
                {loading ? (
                  <tr>
                    <td colSpan={11} className="py-8 text-center text-[#71717A]">
                      Loading multi-warehouse inventory matrix...
                    </td>
                  </tr>
                ) : (
                  inventoryRows.slice(0, 65).map((r) => (
                    <tr key={r.id} className="hover:bg-[#F6F5F2]">
                      <td className="py-2 px-3 font-mono">
                        <div className="font-semibold text-[#18181B]">{r.sku}</div>
                        <div className="text-[11px] text-[#71717A]">{r.warehouse_code}</div>
                      </td>
                      <td className="py-2 px-3">
                        <div className="font-medium text-[#18181B]">{r.product_name}</div>
                        <div className="text-[11px] text-[#71717A]">
                          {r.category_name} • {r.supplier_name}
                        </div>
                      </td>
                      <td className="py-2 px-3 text-right font-mono tabular-nums">{r.on_hand_qty}</td>
                      <td className="py-2 px-3 text-right font-mono tabular-nums text-[#71717A]">{r.reserved_qty}</td>
                      <td className="py-2 px-3 text-right font-mono tabular-nums font-bold">
                        <span className={r.available_qty === 0 ? "text-[#991B1B]" : "text-[#18181B]"}>{r.available_qty}</span>
                      </td>
                      <td className="py-2 px-3 text-right font-mono tabular-nums text-[#1E3A8A]">{r.in_transit_qty}</td>
                      <td className="py-2 px-3 text-right font-mono tabular-nums text-[11px]">
                        {r.safety_stock_qty} / {r.reorder_point_qty}
                      </td>
                      <td className="py-2 px-3 text-right font-mono tabular-nums">{r.days_of_cover}d</td>
                      <td className="py-2 px-3 text-right font-mono text-[11px] tabular-nums">
                        <span>{r.age_bucket_0_30_qty}</span> / <span>{r.age_bucket_31_60_qty}</span> /{" "}
                        <span className="text-[#9A3412]">{r.age_bucket_61_90_qty}</span> /{" "}
                        <span className="text-[#991B1B] font-semibold">{r.age_bucket_90_plus_qty}</span>
                      </td>
                      <td className="py-2 px-3">
                        <span className={`px-2 py-0.5 text-[10px] font-mono border ${statusBadgeStyle(r.stock_status)}`}>
                          {r.stock_status}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-right">
                        <button
                          onClick={() => {
                            setAdjustingItem(r);
                            setAdjustDelta(r.available_qty === 0 ? "60" : "25");
                          }}
                          className="px-2 py-1 bg-[#EFECE6] hover:bg-[#18181B] hover:text-white border border-[#D6D3CD] text-[11px]"
                        >
                          Adjust Stock
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Recent Stock Movements Ledger */}
          <div className="bg-white border border-[#D6D3CD] p-3">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-[#3F3F46] mb-2">
              Recent Warehouse Stock Movement Ledger (GRN, Allocations, Dispatches & Cycle Counts)
            </h4>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-[11px] font-mono">
                <thead>
                  <tr className="bg-[#EFECE6] border-b border-[#D6D3CD] text-[#3F3F46]">
                    <th className="py-1.5 px-2">Timestamp</th>
                    <th className="py-1.5 px-2">Reference</th>
                    <th className="py-1.5 px-2">Movement Type</th>
                    <th className="py-1.5 px-2">Warehouse</th>
                    <th className="py-1.5 px-2">SKU</th>
                    <th className="py-1.5 px-2 text-right">Qty Delta</th>
                    <th className="py-1.5 px-2">Operator / Notes</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E4E4E7]">
                  {recentMovements.slice(0, 10).map((m) => (
                    <tr key={m.id}>
                      <td className="py-1.5 px-2 text-[#71717A]">{m.created_at}</td>
                      <td className="py-1.5 px-2 font-semibold">{m.reference_code}</td>
                      <td className="py-1.5 px-2">{m.movement_type}</td>
                      <td className="py-1.5 px-2">{m.warehouse_code}</td>
                      <td className="py-1.5 px-2">{m.sku}</td>
                      <td className={`py-1.5 px-2 text-right font-bold ${m.quantity_delta >= 0 ? "text-[#166534]" : "text-[#991B1B]"}`}>
                        {m.quantity_delta >= 0 ? `+${m.quantity_delta}` : m.quantity_delta}
                      </td>
                      <td className="py-1.5 px-2 font-sans text-[#3F3F46]">
                        {m.performed_by} — {m.notes}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================
          SUB-TAB 2: TRANSPARENT DEMAND FORECASTING & REPLENISHMENT
      =================================================================== */}
      {activeSubTab === "replenishment" && (
        <div className="space-y-4">
          {methodology && (
            <div className="bg-[#EFECE6] border border-[#D6D3CD] p-4 space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-[#18181B]">
                  Transparent Baseline Forecasting Specification: {methodology.method_name}
                </h3>
                <span className="px-2 py-0.5 bg-white border border-[#D6D3CD] font-mono text-[11px]">
                  Actionable Reorder Nodes: <strong>{repSummary.actionable_sku_count || 0}</strong> | Critical Stockouts:{" "}
                  <strong className="text-[#991B1B]">{repSummary.critical_stockout_count || 0}</strong> | Budget:{" "}
                  <strong>{formatINR(repSummary.total_replenishment_budget_inr || 0)}</strong>
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono bg-white p-3 border border-[#D6D3CD]">
                <div>
                  <div className="text-[#71717A] text-[10px] uppercase">Demand & Safety Stock Equations</div>
                  <div className="mt-0.5">{methodology.forecast_formula}</div>
                  <div className="mt-0.5">{methodology.safety_stock_formula}</div>
                </div>
                <div>
                  <div className="text-[#71717A] text-[10px] uppercase">Reorder Point & Order Quantity Equations</div>
                  <div className="mt-0.5">{methodology.reorder_point_formula}</div>
                  <div className="mt-0.5">{methodology.reorder_qty_formula}</div>
                </div>
              </div>
              <div className="text-[11px] text-[#3F3F46]">
                <strong>Documented Forecasting Limitations:</strong>{" "}
                {methodology.documented_limitations.join(" • ")}
              </div>
            </div>
          )}

          <div className="bg-white border border-[#D6D3CD] overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-[#EFECE6] border-b border-[#D6D3CD] text-[11px] font-semibold uppercase tracking-wider text-[#3F3F46]">
                  <th className="py-2.5 px-3">SKU & Warehouse</th>
                  <th className="py-2.5 px-3">Product & Supplier (LT)</th>
                  <th className="py-2.5 px-3 text-right">Avail / In-Transit</th>
                  <th className="py-2.5 px-3 text-right">7d / 30d ADS</th>
                  <th className="py-2.5 px-3 text-right">WMA Forecast</th>
                  <th className="py-2.5 px-3 text-right">Safety / ROP</th>
                  <th className="py-2.5 px-3 text-right">DOC</th>
                  <th className="py-2.5 px-3 text-right">Recommended Qty</th>
                  <th className="py-2.5 px-3 text-right">Est. PO Cost</th>
                  <th className="py-2.5 px-3">Urgency</th>
                  <th className="py-2.5 px-3 text-right">Execute Replenishment</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E4E4E7]">
                {recommendations.slice(0, 50).map((rec) => (
                  <tr key={rec.inventory_id} className="hover:bg-[#F6F5F2]">
                    <td className="py-2.5 px-3 font-mono">
                      <div className="font-semibold text-[#18181B]">{rec.sku}</div>
                      <div className="text-[11px] text-[#71717A]">{rec.warehouse_code}</div>
                    </td>
                    <td className="py-2.5 px-3">
                      <div className="font-medium">{rec.product_name}</div>
                      <div className="text-[11px] text-[#71717A]">
                        {rec.supplier_name} (LT: {rec.supplier_lead_time_days}d)
                      </div>
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono tabular-nums">
                      <span className={rec.available_qty === 0 ? "text-[#991B1B] font-bold" : ""}>{rec.available_qty}</span> /{" "}
                      <span className="text-[#1E3A8A]">{rec.in_transit_qty}</span>
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono tabular-nums text-[11px]">
                      {rec.avg_daily_sales_7d} / {rec.avg_daily_sales_30d}
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono tabular-nums font-semibold">
                      {rec.forecast_daily_demand}/d
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono tabular-nums text-[11px]">
                      {rec.safety_stock_qty} / {rec.reorder_point_qty}
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono tabular-nums font-semibold">
                      <span className={rec.days_of_cover < 3 ? "text-[#991B1B]" : "text-[#9A3412]"}>{rec.days_of_cover}d</span>
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono tabular-nums font-bold text-[#166534]">
                      +{rec.recommended_order_qty} u
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono tabular-nums">{formatINR(rec.estimated_po_value_inr)}</td>
                    <td className="py-2.5 px-3">
                      <span className={`px-2 py-0.5 text-[10px] font-mono border ${statusBadgeStyle(rec.urgency)}`}>
                        {rec.urgency}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <button
                        onClick={() => handleConvertToPo(rec)}
                        className="px-2.5 py-1 bg-[#166534] hover:bg-[#14532D] text-white text-[11px] font-medium"
                      >
                        Issue PO ({rec.recommended_order_qty}u)
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ===================================================================
          SUB-TAB 3: INVENTORY PERFORMANCE, TURNOVER & AGEING LEDGER
      =================================================================== */}
      {activeSubTab === "performance" && (
        <div className="space-y-4">
          {/* Category-Level Inventory Performance Table */}
          <div className="bg-white border border-[#D6D3CD]">
            <div className="bg-[#EFECE6] border-b border-[#D6D3CD] px-4 py-2.5 font-semibold text-xs uppercase tracking-wider text-[#3F3F46]">
              Category-Level Turnover, Sell-Through & Working Capital Exposure
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-[#F6F5F2] border-b border-[#D6D3CD] text-[11px] font-semibold uppercase text-[#3F3F46]">
                    <th className="py-2 px-3">Category</th>
                    <th className="py-2 px-3">Department</th>
                    <th className="py-2 px-3 text-right">On-Hand Units</th>
                    <th className="py-2 px-3 text-right">Stockout Rate %</th>
                    <th className="py-2 px-3 text-right">Inventory Turnover</th>
                    <th className="py-2 px-3 text-right">Sell-Through %</th>
                    <th className="py-2 px-3 text-right">Total Cost Value</th>
                    <th className="py-2 px-3 text-right">60+ Days Aged Value</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E4E4E7]">
                  {catPerformance.map((c, idx) => (
                    <tr key={idx} className="hover:bg-[#F6F5F2]">
                      <td className="py-2 px-3 font-medium">{c.category_name}</td>
                      <td className="py-2 px-3 font-mono text-[11px] text-[#71717A]">{c.department}</td>
                      <td className="py-2 px-3 text-right font-mono tabular-nums">{c.total_on_hand_units.toLocaleString()}</td>
                      <td className="py-2 px-3 text-right font-mono tabular-nums">
                        <span className={c.stockout_rate_pct > 10 ? "text-[#991B1B] font-semibold" : ""}>{c.stockout_rate_pct}%</span>
                      </td>
                      <td className="py-2 px-3 text-right font-mono tabular-nums font-semibold">{c.avg_turnover_ratio}x</td>
                      <td className="py-2 px-3 text-right font-mono tabular-nums text-[#166534] font-semibold">
                        {c.avg_sell_through_pct}%
                      </td>
                      <td className="py-2 px-3 text-right font-mono tabular-nums">{formatINR(c.total_inventory_value_inr)}</td>
                      <td className="py-2 px-3 text-right font-mono tabular-nums text-[#9A3412] font-semibold">
                        {formatINR(c.aged_60_plus_value_inr)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Split Grids: Excess/Slow-Moving Ageing Table & Stockout Revenue Loss */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="bg-white border border-[#D6D3CD]">
              <div className="bg-[#EFECE6] border-b border-[#D6D3CD] px-3 py-2 text-xs font-semibold uppercase text-[#3F3F46]">
                Excess & Slow-Moving Inventory Ageing Table ({excessItems.length} Nodes)
              </div>
              <div className="overflow-x-auto max-h-96">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-[#F6F5F2] border-b border-[#D6D3CD] text-[10px] font-mono uppercase">
                      <th className="py-2 px-2.5">SKU / FC</th>
                      <th className="py-2 px-2.5 text-right">On Hand / DOC</th>
                      <th className="py-2 px-2.5 text-right">61-90d / 90+d</th>
                      <th className="py-2 px-2.5 text-right">Aged INR</th>
                      <th className="py-2 px-2.5">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#E4E4E7]">
                    {excessItems.slice(0, 25).map((ex) => (
                      <tr key={ex.inventory_id} className="hover:bg-[#F6F5F2]">
                        <td className="py-2 px-2.5">
                          <div className="font-mono font-semibold">{ex.sku}</div>
                          <div className="text-[11px] text-[#71717A]">
                            {ex.warehouse_code} • {ex.category_name}
                          </div>
                        </td>
                        <td className="py-2 px-2.5 text-right font-mono">
                          {ex.on_hand_qty} u / {ex.days_of_cover}d
                        </td>
                        <td className="py-2 px-2.5 text-right font-mono text-[#991B1B]">
                          {ex.age_61_90_qty} / <strong>{ex.age_90_plus_qty}</strong>
                        </td>
                        <td className="py-2 px-2.5 text-right font-mono font-semibold">{formatINR(ex.aged_value_inr)}</td>
                        <td className="py-2 px-2.5">
                          <span className={`px-1.5 py-0.5 text-[10px] font-mono border ${statusBadgeStyle(ex.stock_status)}`}>
                            {ex.stock_status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="bg-white border border-[#D6D3CD]">
              <div className="bg-[#EFECE6] border-b border-[#D6D3CD] px-3 py-2 text-xs font-semibold uppercase text-[#3F3F46]">
                Active Stockout Analysis & Daily Revenue at Risk ({stockoutItems.length} Nodes)
              </div>
              <div className="overflow-x-auto max-h-96">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-[#F6F5F2] border-b border-[#D6D3CD] text-[10px] font-mono uppercase">
                      <th className="py-2 px-2.5">SKU / FC</th>
                      <th className="py-2 px-2.5">Product</th>
                      <th className="py-2 px-2.5 text-right">In Transit</th>
                      <th className="py-2 px-2.5 text-right">Daily Demand</th>
                      <th className="py-2 px-2.5 text-right">Daily Rev Loss</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#E4E4E7]">
                    {stockoutItems.slice(0, 25).map((st) => (
                      <tr key={st.inventory_id} className="hover:bg-[#F6F5F2]">
                        <td className="py-2 px-2.5 font-mono">
                          <div className="font-semibold text-[#991B1B]">{st.sku}</div>
                          <div className="text-[11px] text-[#71717A]">{st.warehouse_code}</div>
                        </td>
                        <td className="py-2 px-2.5">
                          <div className="truncate max-w-[180px]">{st.product_name}</div>
                          <div className="text-[11px] text-[#71717A]">{st.category_name}</div>
                        </td>
                        <td className="py-2 px-2.5 text-right font-mono text-[#1E3A8A]">{st.in_transit_qty} u</td>
                        <td className="py-2 px-2.5 text-right font-mono">{st.forecast_daily_demand}/d</td>
                        <td className="py-2 px-2.5 text-right font-mono font-semibold text-[#991B1B]">
                          {formatINR(st.estimated_daily_revenue_loss_inr)}/d
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

      {/* MODAL: Cycle Count / Stock Adjustment */}
      {adjustingItem && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <form onSubmit={handleAdjustStock} className="bg-white border border-[#18181B] w-full max-w-md p-5 space-y-3">
            <h3 className="text-sm font-semibold uppercase tracking-wider border-b border-[#D6D3CD] pb-2">
              Record Warehouse Stock Adjustment ({adjustingItem.sku} @ {adjustingItem.warehouse_code})
            </h3>
            <div className="text-xs space-y-2">
              <div className="bg-[#F6F5F2] p-2.5 border border-[#D6D3CD] font-mono">
                Current On-Hand: <strong>{adjustingItem.on_hand_qty}</strong> | Reserved: <strong>{adjustingItem.reserved_qty}</strong> | Available:{" "}
                <strong>{adjustingItem.available_qty}</strong>
              </div>
              <div>
                <label className="block font-medium mb-1">Quantity Delta (Positive for Putaway/Found, Negative for Shrinkage)</label>
                <input
                  type="number"
                  required
                  value={adjustDelta}
                  onChange={(e) => setAdjustDelta(e.target.value)}
                  className="w-full px-2.5 py-1.5 border border-[#D6D3CD] font-mono"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-3 border-t border-[#D6D3CD]">
              <button type="button" onClick={() => setAdjustingItem(null)} className="px-3 py-1.5 border border-[#D6D3CD] text-xs">
                Cancel
              </button>
              <button type="submit" className="px-4 py-1.5 bg-[#18181B] text-white text-xs font-medium">
                Commit Adjustment
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
