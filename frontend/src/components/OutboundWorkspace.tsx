"use client";

import React, { useState, useEffect, useCallback } from "react";
import { apiFetch, trackTelemetry, formatINR, statusBadgeStyle } from "@/lib/api";

interface OutboundProps {
  activeSubTab: "orders" | "fulfilment" | "delivery" | "returns" | "exceptions";
  userRole: string;
  onNotify: (msg: string, type?: "success" | "error") => void;
}

export default function OutboundWorkspace({ activeSubTab, userRole, onNotify }: OutboundProps) {
  const [loading, setLoading] = useState(false);

  // Orders state
  const [orders, setOrders] = useState<any[]>([]);
  const [orderSummary, setOrderSummary] = useState<any>({});
  const [orderStatusFilter, setOrderStatusFilter] = useState("ALL");

  // Fulfilment state
  const [whFulfilment, setWhFulfilment] = useState<any[]>([]);
  const [carriers, setCarriers] = useState<any[]>([]);
  const [shipments, setShipments] = useState<any[]>([]);
  const [expandedShipmentId, setExpandedShipmentId] = useState<number | null>(null);

  // Delivery Intelligence state
  const [whSlaBreakdown, setWhSlaBreakdown] = useState<any[]>([]);
  const [delayedShipments, setDelayedShipments] = useState<any[]>([]);

  // Returns state
  const [returnsList, setReturnsList] = useState<any[]>([]);
  const [reasonBreakdown, setReasonBreakdown] = useState<any[]>([]);
  const [skuReturnTrends, setSkuReturnTrends] = useState<any[]>([]);
  const [returnStatusFilter, setReturnStatusFilter] = useState("ALL");

  // Exceptions state
  const [exceptions, setExceptions] = useState<any[]>([]);
  const [excSummary, setExcSummary] = useState<any>({});
  const [excDomainFilter, setExcDomainFilter] = useState("ALL");
  const [excStatusFilter, setExcStatusFilter] = useState("ALL");
  const [editingException, setEditingException] = useState<any | null>(null);
  const [excOwnerInput, setExcOwnerInput] = useState("");
  const [excResolutionInput, setExcResolutionInput] = useState("");

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      if (activeSubTab === "orders") {
        const q = new URLSearchParams();
        if (orderStatusFilter !== "ALL") q.set("status", orderStatusFilter);
        const data = await apiFetch(`/api/outbound/orders?${q.toString()}`);
        setOrders(data.orders || []);
        setOrderSummary(data.summary || {});
      } else if (activeSubTab === "fulfilment") {
        const data = await apiFetch("/api/outbound/fulfilment");
        setWhFulfilment(data.warehouses || []);
        setCarriers(data.carriers || []);
        setShipments(data.shipments || []);
      } else if (activeSubTab === "delivery") {
        const data = await apiFetch("/api/outbound/delivery-intelligence");
        setWhSlaBreakdown(data.warehouse_sla_breakdown || []);
        setDelayedShipments(data.delayed_and_exception_shipments || []);
      } else if (activeSubTab === "returns") {
        const q = new URLSearchParams();
        if (returnStatusFilter !== "ALL") q.set("status", returnStatusFilter);
        const data = await apiFetch(`/api/outbound/returns?${q.toString()}`);
        setReturnsList(data.returns || []);
        setReasonBreakdown(data.reason_breakdown || []);
        setSkuReturnTrends(data.product_return_trends || []);
      } else if (activeSubTab === "exceptions") {
        const q = new URLSearchParams();
        if (excDomainFilter !== "ALL") q.set("domain", excDomainFilter);
        if (excStatusFilter !== "ALL") q.set("status", excStatusFilter);
        const data = await apiFetch(`/api/outbound/exceptions?${q.toString()}`);
        setExceptions(data.exceptions || []);
        setExcSummary(data.summary || {});
      }
    } catch (e: any) {
      onNotify(e.message, "error");
    } finally {
      setLoading(false);
    }
  }, [activeSubTab, orderStatusFilter, returnStatusFilter, excDomainFilter, excStatusFilter, onNotify]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleOrderTransition = async (order: any, nextStatus: string) => {
    try {
      const res = await apiFetch(`/api/outbound/orders/${order.id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: nextStatus, carrier_id: 1 }),
      });
      onNotify(`Order ${res.order_number} transitioned from ${res.previous_status} to ${res.new_status}.`);
      loadData();
    } catch (err: any) {
      onNotify(err.message, "error");
    }
  };

  const handleShipmentUpdate = async (sh: any, nextStatus: string, delayHrs: number) => {
    try {
      const res = await apiFetch(`/api/outbound/shipments/${sh.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          status: nextStatus,
          delay_hours: delayHrs,
          current_hub: nextStatus === "DELIVERED" ? "Customer Doorstep POD" : sh.current_hub,
          note: `Operational update by ${userRole}: ${nextStatus}`,
        }),
      });
      onNotify(`Shipment ${res.awb_number} updated to ${res.shipment_status}.`);
      loadData();
    } catch (err: any) {
      onNotify(err.message, "error");
    }
  };

  const handleReturnAction = async (ret: any, nextStatus: string, refundSt?: string) => {
    try {
      trackTelemetry({
        event_name: nextStatus === "APPROVED" ? "return_case_reviewed" : "return_case_resolved",
        user_role: userRole,
        workspace: "OUTBOUND",
        sku_id: ret.sku,
        warehouse_id: ret.warehouse_code,
      });
      const res = await apiFetch(`/api/outbound/returns/${ret.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          status: nextStatus,
          refund_status: refundSt,
        }),
      });
      onNotify(
        `RMA ${res.rma_number} updated to ${res.new_status} (Refund Status: ${res.refund_status}${
          res.exchange_order_number ? `, Exchange: ${res.exchange_order_number}` : ""
        }).`
      );
      loadData();
    } catch (err: any) {
      onNotify(err.message, "error");
    }
  };

  const handleExceptionSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingException) return;
    try {
      const res = await apiFetch(`/api/outbound/exceptions/${editingException.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          status: editingException.status,
          assigned_to: excOwnerInput,
          resolution_notes: excResolutionInput,
        }),
      });
      trackTelemetry({
        event_name: "delivery_exception_assigned",
        user_role: userRole,
        workspace: "OUTBOUND",
        warehouse_id: editingException.warehouse_code || "WH-A-BLR",
        exception_type: editingException.domain,
      });
      onNotify(`Exception ${res.exception_code} updated (${res.new_status}, Owner: ${res.assigned_to}).`);
      setEditingException(null);
      loadData();
    } catch (err: any) {
      onNotify(err.message, "error");
    }
  };

  return (
    <div className="space-y-4">
      {/* ===================================================================
          SUB-TAB 1: ORDER MANAGEMENT & ALLOCATION REGISTER
      =================================================================== */}
      {activeSubTab === "orders" && (
        <div className="space-y-4">
          <div className="bg-[#EFECE6] border border-[#D6D3CD] p-3 flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#3F3F46] mr-1">Order Lifecycle:</span>
              {["ALL", "PENDING", "ALLOCATED", "PICKING", "PACKED", "DISPATCHED", "IN_TRANSIT", "DELAYED", "DELIVERED", "CANCELLED"].map(
                (st) => (
                  <button
                    key={st}
                    onClick={() => setOrderStatusFilter(st)}
                    className={`px-2 py-1 text-[11px] font-mono border ${
                      orderStatusFilter === st ? "bg-[#18181B] text-white border-[#18181B]" : "bg-white text-[#3F3F46] border-[#D6D3CD]"
                    }`}
                  >
                    {st}
                  </button>
                )
              )}
            </div>
            <div className="text-xs font-mono text-[#3F3F46]">
              Avg Processing: <strong>{orderSummary.avg_processing_hours || 0}h</strong> | SLA Breached:{" "}
              <strong className="text-[#991B1B]">{orderSummary.sla_breached_count || 0}</strong> | Pending Wave:{" "}
              <strong>{orderSummary.pending_fulfilment_count || 0}</strong>
            </div>
          </div>

          <div className="bg-white border border-[#D6D3CD] overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-[#EFECE6] border-b border-[#D6D3CD] text-[11px] font-semibold uppercase tracking-wider text-[#3F3F46]">
                  <th className="py-2.5 px-3">Order Number</th>
                  <th className="py-2.5 px-3">Customer & City</th>
                  <th className="py-2.5 px-3">Allocated FC</th>
                  <th className="py-2.5 px-3">Order Timestamp</th>
                  <th className="py-2.5 px-3 text-right">Cycle Time</th>
                  <th className="py-2.5 px-3 text-right">Order Value</th>
                  <th className="py-2.5 px-3">Promised / Actual Deliv</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3 text-right">Advance Fulfilment State</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E4E4E7]">
                {orders.slice(0, 55).map((o) => (
                  <tr key={o.id} className="hover:bg-[#F6F5F2]">
                    <td className="py-2.5 px-3 font-mono">
                      <div className="font-semibold text-[#18181B]">{o.order_number}</div>
                      {o.awb_number && <div className="text-[10px] text-[#1E3A8A]">{o.awb_number}</div>}
                    </td>
                    <td className="py-2.5 px-3">
                      <div className="font-medium">{o.customer_name}</div>
                      <div className="text-[11px] text-[#71717A]">
                        {o.customer_city} • {o.customer_tier} • {o.payment_mode}
                      </div>
                    </td>
                    <td className="py-2.5 px-3 font-mono font-semibold">{o.warehouse_code}</td>
                    <td className="py-2.5 px-3 font-mono text-[11px]">{o.order_date}</td>
                    <td className="py-2.5 px-3 text-right font-mono tabular-nums">
                      <span className={o.sla_breached ? "text-[#991B1B] font-bold" : "text-[#166534]"}>{o.processing_hours}h</span>
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono tabular-nums font-medium">{formatINR(o.total_amount_inr)}</td>
                    <td className="py-2.5 px-3 font-mono text-[11px]">
                      <div>Prom: {o.promised_delivery_date}</div>
                      {o.actual_delivery_date && <div className="text-[#166534]">Act: {o.actual_delivery_date}</div>}
                    </td>
                    <td className="py-2.5 px-3">
                      <span className={`px-2 py-0.5 text-[10px] font-mono border ${statusBadgeStyle(o.status)}`}>{o.status}</span>
                    </td>
                    <td className="py-2.5 px-3 text-right space-x-1">
                      {o.status === "PENDING" && (
                        <button
                          onClick={() => handleOrderTransition(o, "PICKING")}
                          className="px-2 py-1 bg-[#1E3A8A] text-white text-[11px]"
                        >
                          Release to Pick
                        </button>
                      )}
                      {(o.status === "ALLOCATED" || o.status === "PICKING") && (
                        <button
                          onClick={() => handleOrderTransition(o, "PACKED")}
                          className="px-2 py-1 bg-[#1E3A8A] text-white text-[11px]"
                        >
                          Mark Packed
                        </button>
                      )}
                      {o.status === "PACKED" && (
                        <button
                          onClick={() => handleOrderTransition(o, "DISPATCHED")}
                          className="px-2 py-1 bg-[#166534] text-white text-[11px]"
                        >
                          Dispatch AWB
                        </button>
                      )}
                      {(o.status === "DISPATCHED" || o.status === "IN_TRANSIT" || o.status === "DELAYED") && (
                        <button
                          onClick={() => handleOrderTransition(o, "DELIVERED")}
                          className="px-2 py-1 bg-[#166534] text-white text-[11px]"
                        >
                          Confirm POD
                        </button>
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
          SUB-TAB 2: WAREHOUSE FULFILMENT, PICKING & CARRIER DISPATCH
      =================================================================== */}
      {activeSubTab === "fulfilment" && (
        <div className="space-y-4">
          {/* Warehouse & Carrier Scorecards */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="bg-white border border-[#D6D3CD] p-3">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-[#3F3F46] mb-2">
                Regional Fulfilment Centre Processing & Picker Capacity
              </h4>
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-[#EFECE6] border-b border-[#D6D3CD] text-[10px] font-mono uppercase">
                    <th className="py-1.5 px-2">Warehouse</th>
                    <th className="py-1.5 px-2 text-right">Active Pickers</th>
                    <th className="py-1.5 px-2 text-right">Avg Cycle (vs 12h SLA)</th>
                    <th className="py-1.5 px-2">Bottleneck Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E4E4E7]">
                  {whFulfilment.map((w) => (
                    <tr key={w.id}>
                      <td className="py-2 px-2">
                        <div className="font-mono font-semibold">{w.code}</div>
                        <div className="text-[11px] text-[#71717A]">{w.name}</div>
                      </td>
                      <td className="py-2 px-2 text-right font-mono">{w.active_pickers} staff</td>
                      <td className="py-2 px-2 text-right font-mono">
                        <span className={w.avg_processing_hours > w.sla_dispatch_hours ? "text-[#991B1B] font-bold" : "text-[#166534]"}>
                          {w.avg_processing_hours}h
                        </span>{" "}
                        / {w.sla_dispatch_hours}h
                      </td>
                      <td className="py-2 px-2">
                        <span className={`px-2 py-0.5 text-[10px] font-mono border ${statusBadgeStyle(w.bottleneck_status)}`}>
                          {w.bottleneck_status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="bg-white border border-[#D6D3CD] p-3">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-[#3F3F46] mb-2">
                Logistics Carrier Allocation & SLA Performance
              </h4>
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-[#EFECE6] border-b border-[#D6D3CD] text-[10px] font-mono uppercase">
                    <th className="py-1.5 px-2">Carrier Partner</th>
                    <th className="py-1.5 px-2">Service Mode</th>
                    <th className="py-1.5 px-2 text-right">Transit Days</th>
                    <th className="py-1.5 px-2 text-right">OTD %</th>
                    <th className="py-1.5 px-2 text-right">RTO %</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E4E4E7]">
                  {carriers.map((c) => (
                    <tr key={c.id}>
                      <td className="py-2 px-2 font-medium">{c.name}</td>
                      <td className="py-2 px-2 font-mono text-[11px] text-[#71717A]">{c.service_type}</td>
                      <td className="py-2 px-2 text-right font-mono">{c.avg_transit_days}d</td>
                      <td className="py-2 px-2 text-right font-mono text-[#166534] font-semibold">{c.on_time_rate_pct}%</td>
                      <td className="py-2 px-2 text-right font-mono text-[#9A3412]">{c.rto_rate_pct}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Shipment Register & Expandable Timeline */}
          <div className="bg-white border border-[#D6D3CD] overflow-x-auto">
            <div className="bg-[#EFECE6] border-b border-[#D6D3CD] px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-[#3F3F46]">
              Manifested & In-Transit Shipment Register (Click AWB to Inspect Multi-Hop Tracking Timeline)
            </div>
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-[#F6F5F2] border-b border-[#D6D3CD] text-[11px] font-semibold uppercase text-[#3F3F46]">
                  <th className="py-2 px-3">AWB / Order</th>
                  <th className="py-2 px-3">Origin FC & Carrier</th>
                  <th className="py-2 px-3">Current Hub Location</th>
                  <th className="py-2 px-3 text-right">Dispatch / Delay Hrs</th>
                  <th className="py-2 px-3">Status</th>
                  <th className="py-2 px-3 text-right">Shipment Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E4E4E7]">
                {shipments.slice(0, 45).map((sh) => (
                  <React.Fragment key={sh.id}>
                    <tr className="hover:bg-[#F6F5F2]">
                      <td className="py-2.5 px-3 font-mono">
                        <button
                          onClick={() => setExpandedShipmentId(expandedShipmentId === sh.id ? null : sh.id)}
                          className="font-semibold text-[#1E3A8A] hover:underline flex items-center gap-1"
                        >
                          <span>{expandedShipmentId === sh.id ? "▼" : "▶"}</span>
                          <span>{sh.awb_number}</span>
                        </button>
                        <div className="text-[11px] text-[#71717A]">{sh.order_number}</div>
                      </td>
                      <td className="py-2.5 px-3">
                        <div className="font-mono font-semibold">{sh.warehouse_code}</div>
                        <div className="text-[11px] text-[#71717A]">{sh.carrier_name}</div>
                      </td>
                      <td className="py-2.5 px-3">
                        <div>{sh.current_hub}</div>
                        {sh.exception_code && (
                          <span className="text-[10px] font-mono text-[#991B1B] font-semibold">EXC: {sh.exception_code}</span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono">
                        <div>Disp: {sh.dispatch_hours}h</div>
                        {sh.delay_hours > 0 && <div className="text-[#991B1B] font-semibold">Delay: +{sh.delay_hours}h</div>}
                      </td>
                      <td className="py-2.5 px-3">
                        <span className={`px-2 py-0.5 text-[10px] font-mono border ${statusBadgeStyle(sh.status)}`}>{sh.status}</span>
                      </td>
                      <td className="py-2.5 px-3 text-right space-x-1">
                        {sh.status !== "DELIVERED" && (
                          <button
                            onClick={() => handleShipmentUpdate(sh, "DELIVERED", 0)}
                            className="px-2 py-1 bg-[#166534] text-white text-[11px]"
                          >
                            Mark Delivered
                          </button>
                        )}
                        {sh.status !== "DELIVERY_EXCEPTION" && sh.status !== "DELIVERED" && (
                          <button
                            onClick={() => handleShipmentUpdate(sh, "DELIVERY_EXCEPTION", 24)}
                            className="px-2 py-1 bg-[#FEE2E2] text-[#991B1B] border border-[#FCA5A5] text-[11px]"
                          >
                            Flag Hub Hold
                          </button>
                        )}
                      </td>
                    </tr>
                    {expandedShipmentId === sh.id && (
                      <tr className="bg-[#F6F5F2]">
                        <td colSpan={6} className="p-3 border-l-4 border-[#18181B]">
                          <div className="text-xs font-semibold mb-2">
                            Shipment Event Timeline — {sh.awb_number} (Promised Delivery: {sh.promised_delivery_date})
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {sh.tracking_timeline.map((step: any, idx: number) => (
                              <div key={idx} className="bg-white border border-[#D6D3CD] p-2.5 min-w-[200px] flex-1">
                                <div className="font-mono text-[10px] font-bold text-[#1E3A8A]">{step.step}</div>
                                <div className="font-mono text-[11px] text-[#71717A]">{step.timestamp}</div>
                                <div className="text-xs font-medium mt-1">{step.location}</div>
                                <div className="text-[11px] text-[#3F3F46]">{step.note}</div>
                              </div>
                            ))}
                          </div>
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
          SUB-TAB 3: DELIVERY INTELLIGENCE & SLA SCORECARD
      =================================================================== */}
      {activeSubTab === "delivery" && (
        <div className="space-y-4">
          <div className="bg-white border border-[#D6D3CD]">
            <div className="bg-[#EFECE6] border-b border-[#D6D3CD] px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-[#3F3F46]">
              Fulfilment Centre On-Time Delivery & Dispatch Latency Comparison
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-[#F6F5F2] border-b border-[#D6D3CD] text-[11px] font-semibold uppercase text-[#3F3F46]">
                    <th className="py-2.5 px-3">Warehouse</th>
                    <th className="py-2.5 px-3">Bottleneck Status</th>
                    <th className="py-2.5 px-3 text-right">Total Shipments</th>
                    <th className="py-2.5 px-3 text-right">On-Time Delivery %</th>
                    <th className="py-2.5 px-3 text-right">Delayed Shipments</th>
                    <th className="py-2.5 px-3 text-right">Avg Dispatch Time</th>
                    <th className="py-2.5 px-3 text-right">Avg SLA Delay</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E4E4E7]">
                  {whSlaBreakdown.map((w) => (
                    <tr key={w.warehouse_code} className="hover:bg-[#F6F5F2]">
                      <td className="py-2.5 px-3">
                        <div className="font-mono font-semibold">{w.warehouse_code}</div>
                        <div className="text-[11px] text-[#71717A]">{w.warehouse_name}</div>
                      </td>
                      <td className="py-2.5 px-3">
                        <span className={`px-2 py-0.5 text-[10px] font-mono border ${statusBadgeStyle(w.bottleneck_status)}`}>
                          {w.bottleneck_status}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono">{w.total_shipments}</td>
                      <td className="py-2.5 px-3 text-right font-mono font-bold">
                        <span className={w.on_time_delivery_pct < 75 ? "text-[#991B1B]" : "text-[#166534]"}>
                          {w.on_time_delivery_pct}%
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-[#991B1B] font-semibold">{w.delayed_count}</td>
                      <td className="py-2.5 px-3 text-right font-mono">{w.avg_dispatch_hours}h</td>
                      <td className="py-2.5 px-3 text-right font-mono">{w.avg_delay_hours}h</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="bg-white border border-[#D6D3CD] overflow-x-auto">
            <div className="bg-[#EFECE6] border-b border-[#D6D3CD] px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-[#3F3F46]">
              Delayed & Exception Shipment Escalation Ledger ({delayedShipments.length} Active Breaches)
            </div>
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-[#F6F5F2] border-b border-[#D6D3CD] text-[11px] font-semibold uppercase text-[#3F3F46]">
                  <th className="py-2 px-3">AWB / Order</th>
                  <th className="py-2 px-3">Origin FC & Carrier</th>
                  <th className="py-2 px-3">Promised vs Actual Date</th>
                  <th className="py-2 px-3 text-right">Dispatch / Delay Hrs</th>
                  <th className="py-2 px-3">Current Hub & Exception Code</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E4E4E7]">
                {delayedShipments.slice(0, 35).map((ds) => (
                  <tr key={ds.shipment_id} className="hover:bg-[#F6F5F2]">
                    <td className="py-2 px-3 font-mono">
                      <div className="font-semibold">{ds.awb_number}</div>
                      <div className="text-[11px] text-[#71717A]">{ds.order_number}</div>
                    </td>
                    <td className="py-2 px-3">
                      <div className="font-mono font-semibold">{ds.warehouse_code}</div>
                      <div className="text-[11px] text-[#71717A]">{ds.carrier_name}</div>
                    </td>
                    <td className="py-2 px-3 font-mono text-[11px]">
                      <div>Prom: {ds.promised_delivery_date}</div>
                      <div className="text-[#991B1B]">Act: {ds.actual_delivery_date}</div>
                    </td>
                    <td className="py-2 px-3 text-right font-mono">
                      <div>{ds.dispatch_hours}h disp</div>
                      <div className="text-[#991B1B] font-bold">+{ds.delay_hours}h delay</div>
                    </td>
                    <td className="py-2 px-3">
                      <div>{ds.current_hub}</div>
                      <span className="px-1.5 py-0.5 text-[10px] font-mono bg-[#FEE2E2] text-[#991B1B] border border-[#FCA5A5]">
                        {ds.exception_code}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ===================================================================
          SUB-TAB 4: RETURNS, EXCHANGES & REFUND SIMULATION REGISTER
      =================================================================== */}
      {activeSubTab === "returns" && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="bg-white border border-[#D6D3CD] p-3">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-[#3F3F46] mb-2">
                Return Reason Classification Breakdown
              </h4>
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-[#EFECE6] border-b border-[#D6D3CD] text-[10px] font-mono uppercase">
                    <th className="py-1.5 px-2">Reason Category</th>
                    <th className="py-1.5 px-2 text-right">RMA Cases</th>
                    <th className="py-1.5 px-2 text-right">Share %</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E4E4E7]">
                  {reasonBreakdown.map((rb) => (
                    <tr key={rb.category}>
                      <td className="py-1.5 px-2 font-mono font-semibold">{rb.category}</td>
                      <td className="py-1.5 px-2 text-right font-mono">{rb.count}</td>
                      <td className="py-1.5 px-2 text-right font-mono font-bold text-[#991B1B]">{rb.share_pct}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="bg-white border border-[#D6D3CD] p-3">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-[#3F3F46] mb-2">
                High-Return SKUs & Catalogue Completeness Correlation
              </h4>
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-[#EFECE6] border-b border-[#D6D3CD] text-[10px] font-mono uppercase">
                    <th className="py-1.5 px-2">SKU</th>
                    <th className="py-1.5 px-2">Primary Driver</th>
                    <th className="py-1.5 px-2 text-right">Completeness</th>
                    <th className="py-1.5 px-2 text-right">Returns</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E4E4E7]">
                  {skuReturnTrends.slice(0, 6).map((tr) => (
                    <tr key={tr.sku}>
                      <td className="py-1.5 px-2">
                        <span className="font-mono font-semibold">{tr.sku}</span>
                        <span className="text-[11px] text-[#71717A] ml-2">{tr.category_name}</span>
                      </td>
                      <td className="py-1.5 px-2 font-mono text-[11px] text-[#9A3412]">{tr.top_reason}</td>
                      <td className="py-1.5 px-2 text-right font-mono">
                        <span className={tr.completeness_score < 85 ? "text-[#991B1B] font-semibold" : "text-[#166534]"}>
                          {tr.completeness_score}%
                        </span>
                      </td>
                      <td className="py-1.5 px-2 text-right font-mono font-bold">{tr.return_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* RMA Case Register */}
          <div className="bg-white border border-[#D6D3CD] overflow-x-auto">
            <div className="bg-[#EFECE6] border-b border-[#D6D3CD] p-3 flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="text-xs font-semibold uppercase tracking-wider text-[#3F3F46] mr-1">RMA Status:</span>
                {["ALL", "REQUESTED", "APPROVED", "QC_PASSED", "QC_FAILED", "EXCHANGE_DISPATCHED", "REFUND_PROCESSED"].map((st) => (
                  <button
                    key={st}
                    onClick={() => setReturnStatusFilter(st)}
                    className={`px-2 py-1 text-[11px] font-mono border ${
                      returnStatusFilter === st ? "bg-[#18181B] text-white border-[#18181B]" : "bg-white text-[#3F3F46] border-[#D6D3CD]"
                    }`}
                  >
                    {st}
                  </button>
                ))}
              </div>
            </div>
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-[#F6F5F2] border-b border-[#D6D3CD] text-[11px] font-semibold uppercase text-[#3F3F46]">
                  <th className="py-2.5 px-3">RMA / Order</th>
                  <th className="py-2.5 px-3">SKU & Product</th>
                  <th className="py-2.5 px-3">Type & Reason Classification</th>
                  <th className="py-2.5 px-3 text-right">Refund Value</th>
                  <th className="py-2.5 px-3">RMA & Refund Status</th>
                  <th className="py-2.5 px-3 text-right">QC & Refund / Exchange Simulation</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E4E4E7]">
                {returnsList.map((r) => (
                  <tr key={r.id} className="hover:bg-[#F6F5F2]">
                    <td className="py-2.5 px-3 font-mono">
                      <div className="font-semibold text-[#18181B]">{r.rma_number}</div>
                      <div className="text-[11px] text-[#71717A]">
                        {r.order_number} • {r.warehouse_code}
                      </div>
                    </td>
                    <td className="py-2.5 px-3">
                      <div className="font-mono font-medium">{r.sku}</div>
                      <div className="text-[11px] text-[#71717A]">{r.product_name}</div>
                    </td>
                    <td className="py-2.5 px-3">
                      <div className="font-mono text-[11px] font-semibold text-[#1E3A8A]">
                        {r.request_type} • {r.reason_category}
                      </div>
                      <div className="text-[11px] text-[#3F3F46]">{r.reason_description}</div>
                      <div className="text-[10px] text-[#71717A] italic mt-0.5">QC: {r.qc_notes}</div>
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono tabular-nums font-semibold">
                      {formatINR(r.refund_amount_inr)}
                    </td>
                    <td className="py-2.5 px-3 space-y-1">
                      <div>
                        <span className={`px-2 py-0.5 text-[10px] font-mono border ${statusBadgeStyle(r.status)}`}>{r.status}</span>
                      </div>
                      <div className="text-[10px] font-mono text-[#71717A]">Refund: {r.refund_status}</div>
                    </td>
                    <td className="py-2.5 px-3 text-right space-x-1">
                      {r.status === "REQUESTED" && (
                        <button
                          onClick={() => handleReturnAction(r, "APPROVED")}
                          className="px-2 py-1 bg-[#DBEAFE] text-[#1E3A8A] border border-[#93C5FD] text-[11px]"
                        >
                          Approve Pickup
                        </button>
                      )}
                      {r.status !== "QC_PASSED" && r.status !== "REFUND_PROCESSED" && r.status !== "CLOSED" && (
                        <button
                          onClick={() => handleReturnAction(r, "QC_PASSED", "INITIATED")}
                          className="px-2 py-1 bg-[#DCFCE7] text-[#166534] border border-[#86EFAC] text-[11px] font-medium"
                        >
                          Pass QC (+Restock)
                        </button>
                      )}
                      {r.request_type === "RETURN_REFUND" && r.refund_status !== "PROCESSED" && (
                        <button
                          onClick={() => handleReturnAction(r, "REFUND_PROCESSED", "PROCESSED")}
                          className="px-2 py-1 bg-[#18181B] text-white text-[11px] font-medium"
                        >
                          Simulate Refund
                        </button>
                      )}
                      {r.request_type !== "RETURN_REFUND" && r.status !== "EXCHANGE_DISPATCHED" && (
                        <button
                          onClick={() => handleReturnAction(r, "EXCHANGE_DISPATCHED", "NOT_APPLICABLE")}
                          className="px-2 py-1 bg-[#1E3A8A] text-white text-[11px] font-medium"
                        >
                          Dispatch Exchange
                        </button>
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
          SUB-TAB 5: OPERATIONS EXCEPTIONS COMMAND QUEUE
      =================================================================== */}
      {activeSubTab === "exceptions" && (
        <div className="space-y-4">
          <div className="bg-[#EFECE6] border border-[#D6D3CD] p-3 flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#3F3F46] mr-1">Domain:</span>
              {[
                "ALL",
                "WAREHOUSE_BOTTLENECK",
                "INBOUND_PO",
                "CATALOGUE_QUALITY",
                "INVENTORY_RISK",
                "DISPATCH_DELAY",
                "DELIVERY_SLA",
                "RETURN_SPIKE",
              ].map((d) => (
                <button
                  key={d}
                  onClick={() => setExcDomainFilter(d)}
                  className={`px-2 py-1 text-[10px] font-mono border ${
                    excDomainFilter === d ? "bg-[#18181B] text-white border-[#18181B]" : "bg-white text-[#3F3F46] border-[#D6D3CD]"
                  }`}
                >
                  {d}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-2">
              {["ALL", "OPEN", "IN_PROGRESS", "ESCALATED", "RESOLVED"].map((st) => (
                <button
                  key={st}
                  onClick={() => setExcStatusFilter(st)}
                  className={`px-2 py-1 text-[10px] font-mono border ${
                    excStatusFilter === st ? "bg-[#1E3A8A] text-white border-[#1E3A8A]" : "bg-white text-[#3F3F46] border-[#D6D3CD]"
                  }`}
                >
                  {st}
                </button>
              ))}
            </div>
          </div>

          <div className="bg-white border border-[#D6D3CD] overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-[#EFECE6] border-b border-[#D6D3CD] text-[11px] font-semibold uppercase tracking-wider text-[#3F3F46]">
                  <th className="py-2.5 px-3">Code / Domain / Severity</th>
                  <th className="py-2.5 px-3">Exception Summary & Root Cause</th>
                  <th className="py-2.5 px-3">Linked Entities</th>
                  <th className="py-2.5 px-3">Assigned Owner</th>
                  <th className="py-2.5 px-3 text-right">Financial Exposure</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3 text-right">Governance Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E4E4E7]">
                {exceptions.map((ex) => (
                  <tr key={ex.id} className="hover:bg-[#F6F5F2]">
                    <td className="py-2.5 px-3 font-mono">
                      <div className="font-bold text-[#18181B]">{ex.exception_code}</div>
                      <div className="text-[10px] text-[#71717A]">{ex.domain}</div>
                      <span className={`inline-block mt-1 px-1.5 py-0.5 text-[10px] border ${statusBadgeStyle(ex.severity)}`}>
                        {ex.severity}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 max-w-md">
                      <div className="font-semibold text-[#18181B]">{ex.title}</div>
                      <div className="text-[11px] text-[#3F3F46] mt-0.5">{ex.description}</div>
                      <div className="text-[11px] text-[#71717A] mt-1">
                        <strong>Root Cause:</strong> {ex.root_cause}
                      </div>
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px]">
                      {ex.warehouse_code && <div>FC: {ex.warehouse_code}</div>}
                      {ex.sku && <div>SKU: {ex.sku}</div>}
                      {ex.po_number && <div>PO: {ex.po_number}</div>}
                      {ex.awb_number && <div>AWB: {ex.awb_number}</div>}
                    </td>
                    <td className="py-2.5 px-3">
                      <div className="font-medium">{ex.assigned_to}</div>
                      <div className="text-[11px] text-[#71717A]">{ex.assigned_role}</div>
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono tabular-nums font-semibold">
                      {formatINR(ex.financial_impact_inr)}
                    </td>
                    <td className="py-2.5 px-3">
                      <span className={`px-2 py-0.5 text-[10px] font-mono border ${statusBadgeStyle(ex.status)}`}>{ex.status}</span>
                    </td>
                    <td className="py-2.5 px-3 text-right space-x-1">
                      <button
                        onClick={() => {
                          trackTelemetry({
                            event_name: "fulfilment_exception_opened",
                            user_role: userRole,
                            workspace: "OUTBOUND",
                            warehouse_id: ex.warehouse_code || "WH-A-BLR",
                            exception_type: ex.domain,
                          });
                          setEditingException(ex);
                          setExcOwnerInput(ex.assigned_to);
                          setExcResolutionInput(ex.resolution_notes || "");
                        }}
                        className="px-2.5 py-1 bg-[#18181B] text-white text-[11px] font-medium"
                      >
                        Assign / Resolve
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* MODAL: Assign / Update / Resolve Operational Exception */}
      {editingException && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <form onSubmit={handleExceptionSave} className="bg-white border border-[#18181B] w-full max-w-lg p-5 space-y-3">
            <h3 className="text-sm font-semibold uppercase tracking-wider border-b border-[#D6D3CD] pb-2">
              Manage Operational Exception — {editingException.exception_code}
            </h3>
            <div className="text-xs space-y-2.5">
              <div className="bg-[#F6F5F2] p-2.5 border border-[#D6D3CD]">
                <div className="font-semibold">{editingException.title}</div>
                <div className="text-[#3F3F46] mt-0.5">{editingException.description}</div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium mb-1">Exception Status</label>
                  <select
                    value={editingException.status}
                    onChange={(e) => setEditingException({ ...editingException, status: e.target.value })}
                    className="w-full px-2.5 py-1.5 border border-[#D6D3CD] font-mono bg-white"
                  >
                    <option value="OPEN">OPEN</option>
                    <option value="IN_PROGRESS">IN_PROGRESS</option>
                    <option value="ESCALATED">ESCALATED</option>
                    <option value="RESOLVED">RESOLVED</option>
                  </select>
                </div>
                <div>
                  <label className="block font-medium mb-1">Assigned Owner</label>
                  <input
                    required
                    value={excOwnerInput}
                    onChange={(e) => setExcOwnerInput(e.target.value)}
                    className="w-full px-2.5 py-1.5 border border-[#D6D3CD]"
                  />
                </div>
              </div>
              <div>
                <label className="block font-medium mb-1">Action Plan / Resolution Verification Notes</label>
                <textarea
                  rows={3}
                  value={excResolutionInput}
                  onChange={(e) => setExcResolutionInput(e.target.value)}
                  className="w-full px-2.5 py-1.5 border border-[#D6D3CD]"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-3 border-t border-[#D6D3CD]">
              <button type="button" onClick={() => setEditingException(null)} className="px-3 py-1.5 border border-[#D6D3CD] text-xs">
                Cancel
              </button>
              <button type="submit" className="px-4 py-1.5 bg-[#166534] text-white text-xs font-medium">
                Save & Update Exception
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
