export const API_BASE = "";

export async function apiFetch<T = any>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(options?.headers || {}),
    },
  });
  if (!res.ok) {
    let errText = `HTTP ${res.status}`;
    try {
      const errJson = await res.json();
      errText = errJson.detail || JSON.stringify(errJson);
    } catch {
      errText = await res.text();
    }
    throw new Error(errText);
  }
  return res.json();
}

export async function trackTelemetry(params: {
  event_name: string;
  user_role: string;
  workspace: string;
  supplier_id?: string;
  sku_id?: string;
  warehouse_id?: string;
  exception_type?: string;
  action_status?: string;
  duration_seconds?: number;
  properties?: Record<string, any>;
}) {
  try {
    await fetch(`${API_BASE}/api/analytics/track`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action_status: "COMPLETED",
        duration_seconds: 38,
        ...params,
      }),
    });
  } catch {
    // Non-blocking telemetry
  }
}

export function formatINR(val: number): string {
  if (val === undefined || val === null || isNaN(val)) return "₹0";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(val);
}

export function statusBadgeStyle(status: string): string {
  const s = (status || "").toUpperCase();
  if (
    [
      "HEALTHY",
      "ACTIVE",
      "RECEIVED",
      "DELIVERED",
      "QC_PASSED",
      "RESOLVED",
      "PROCESSED",
      "ABOVE_TARGET",
      "COMPLETED",
      "NORMAL",
    ].includes(s)
  ) {
    return "bg-[#DCFCE7] text-[#166534] border-[#86EFAC]";
  }
  if (
    [
      "ISSUED",
      "ACKNOWLEDGED",
      "IN_TRANSIT",
      "DISPATCHED",
      "PICKED_UP",
      "MANIFESTED",
      "ALLOCATED",
      "IN_PROGRESS",
      "APPROVED",
      "EXCHANGE_DISPATCHED",
      "SCHEDULED",
      "STRATEGIC",
      "TIER_1",
    ].includes(s)
  ) {
    return "bg-[#DBEAFE] text-[#1E3A8A] border-[#93C5FD]";
  }
  if (
    [
      "WARNING",
      "LOW_STOCK",
      "PARTIALLY_RECEIVED",
      "EXCESS",
      "SLOW_MOVING",
      "PICKING",
      "PACKED",
      "ELEVATED",
      "UNDER_AUDIT",
      "GUARDRAIL_WARN",
      "HIGH",
      "MEDIUM",
      "REQUESTED",
      "PENDING",
      "INITIATED",
      "HIGH_BELOW_SAFETY",
      "REPLENISH_AT_ROP",
    ].includes(s)
  ) {
    return "bg-[#FFEDD5] text-[#9A3412] border-[#FDBA74]";
  }
  if (
    [
      "CRITICAL",
      "STOCKOUT",
      "DELAYED",
      "DELIVERY_EXCEPTION",
      "QC_FAILED",
      "ON_HOLD",
      "CANCELLED",
      "MARGIN_BREACH",
      "ESCALATED",
      "CRITICAL_BACKLOG",
      "CRITICAL_STOCKOUT",
      "OPEN",
      "ABANDONED",
    ].includes(s)
  ) {
    return "bg-[#FEE2E2] text-[#991B1B] border-[#FCA5A5]";
  }
  return "bg-[#EFECE6] text-[#3F3F46] border-[#D6D3CD]";
}
