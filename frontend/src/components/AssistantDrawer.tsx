"use client";

import React, { useState, useEffect } from "react";
import { apiFetch, statusBadgeStyle } from "@/lib/api";

interface AssistantDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

const PRESET_QUESTIONS = [
  {
    label: "Warehouse A Decline",
    question: "Why is the delivery performance of Warehouse A declining?",
    focus_area: "WAREHOUSE_DELIVERY",
  },
  {
    label: "Supplier Performance & Complaints",
    question: "Summarise supplier performance and categorise supplier complaints.",
    focus_area: "SUPPLIER_PERFORMANCE",
  },
  {
    label: "Recurring Return Reasons",
    question: "Identify recurring return reasons and their link to catalogue completeness.",
    focus_area: "RETURNS_ANALYSIS",
  },
  {
    label: "Stockout & Excess Inventory Risks",
    question: "Explain potential inventory problems across stockouts and aged excess stock.",
    focus_area: "INVENTORY_RISK",
  },
  {
    label: "Catalogue Improvement Plan",
    question: "Generate catalogue improvement suggestions for incomplete and duplicate SKUs.",
    focus_area: "CATALOGUE_QUALITY",
  },
  {
    label: "Weekly Ops Digest",
    question: "Summarise weekly operational performance across Inbound, Inventory, and Outbound.",
    focus_area: "WEEKLY_SUMMARY",
  },
];

export default function AssistantDrawer({ isOpen, onClose }: AssistantDrawerProps) {
  const [question, setQuestion] = useState("Why is the delivery performance of Warehouse A declining?");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<any | null>(null);

  const runQuery = async (qText: string, focus?: string) => {
    setLoading(true);
    try {
      const res = await apiFetch("/api/ai/assistant", {
        method: "POST",
        body: JSON.stringify({ question: qText, focus_area: focus }),
      });
      setResponse(res);
    } catch (e: any) {
      setResponse({
        error: e.message || "Failed to query operations assistant",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && !response) {
      runQuery("Why is the delivery performance of Warehouse A declining?", "WAREHOUSE_DELIVERY");
    }
  }, [isOpen, response]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex justify-end">
      <div className="w-full max-w-2xl bg-[#F6F5F2] border-l border-[#18181B] h-full flex flex-col">
        {/* Header */}
        <div className="bg-[#18181B] text-white px-4 py-3 flex items-center justify-between">
          <div>
            <div className="text-xs font-mono uppercase tracking-wider text-[#A1A1AA]">
              THREADFLOW Evidence-Grounded GenAI Assistant
            </div>
            <h3 className="text-sm font-semibold">Operational Diagnostic & SQL Evidence Synthesis</h3>
          </div>
          <button
            onClick={onClose}
            className="px-2.5 py-1 bg-[#27272A] hover:bg-[#3F3F46] text-xs font-mono border border-[#52525B]"
          >
            CLOSE [ESC]
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Preset Investigation Prompts */}
          <div className="space-y-1.5">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-[#3F3F46]">
              Select Evidence-Grounded Operational Investigation:
            </div>
            <div className="flex flex-wrap gap-1.5">
              {PRESET_QUESTIONS.map((pq) => (
                <button
                  key={pq.label}
                  onClick={() => {
                    setQuestion(pq.question);
                    runQuery(pq.question, pq.focus_area);
                  }}
                  className="px-2.5 py-1 bg-white hover:bg-[#18181B] hover:text-white text-[#18181B] border border-[#D6D3CD] text-xs font-medium transition-colors"
                >
                  {pq.label}
                </button>
              ))}
            </div>
          </div>

          {/* Custom Query Bar */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (question.trim()) runQuery(question);
            }}
            className="flex gap-2"
          >
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask an operational question (e.g., Why is the delivery performance of Warehouse A declining?)..."
              className="flex-1 px-3 py-1.5 bg-white border border-[#18181B] text-xs"
            />
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-1.5 bg-[#1E3A8A] text-white text-xs font-medium hover:bg-[#172554]"
            >
              {loading ? "Retrieving SQL..." : "Run Analysis"}
            </button>
          </form>

          {/* Response Output */}
          {response && !response.error && (
            <div className="space-y-3">
              {/* Execution Mode & Guardrail Banner */}
              <div className="bg-[#EFECE6] border border-[#D6D3CD] p-3 text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-[#1E3A8A]">ENGINE: {response.execution_mode}</span>
                  <span className="font-mono text-[11px] text-[#3F3F46]">Window: {response.time_period}</span>
                </div>
                <div className="text-[11px] text-[#52525B]">{response.guardrail_notice}</div>
              </div>

              {/* Executive Summary */}
              <div className="bg-white border border-[#D6D3CD] p-3.5">
                <div className="text-[10px] font-mono uppercase tracking-wider text-[#71717A]">
                  Evidence-Grounded Executive Summary
                </div>
                <div className="text-xs font-semibold text-[#18181B] mt-1 leading-relaxed">
                  {response.executive_summary}
                </div>
              </div>

              {/* Relevant Database Records */}
              <div className="bg-white border border-[#D6D3CD] p-3.5">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-[#3F3F46] mb-2">
                  1. Retrieved Relational Records (Ground-Truth SQL Evidence)
                </div>
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-[#EFECE6] border-b border-[#D6D3CD] text-[10px] font-mono uppercase">
                      <th className="py-1.5 px-2">Record ID</th>
                      <th className="py-1.5 px-2">Entity</th>
                      <th className="py-1.5 px-2">Verified Operational Metric</th>
                      <th className="py-1.5 px-2">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#E4E4E7] font-mono text-[11px]">
                    {response.relevant_records?.map((rec: any, i: number) => (
                      <tr key={i}>
                        <td className="py-1.5 px-2 font-bold text-[#18181B]">{rec.record_id}</td>
                        <td className="py-1.5 px-2 text-[#71717A]">{rec.entity}</td>
                        <td className="py-1.5 px-2 font-sans text-[#18181B]">{rec.metric}</td>
                        <td className="py-1.5 px-2">
                          <span className={`px-1.5 py-0.5 text-[10px] border ${statusBadgeStyle(rec.status)}`}>
                            {rec.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Observed Patterns */}
              <div className="bg-white border border-[#D6D3CD] p-3.5 space-y-1.5">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-[#3F3F46]">
                  2. Observed Operational Patterns
                </div>
                <ul className="list-disc list-inside text-xs text-[#18181B] space-y-1">
                  {response.observed_patterns?.map((pat: string, idx: number) => (
                    <li key={idx}>{pat}</li>
                  ))}
                </ul>
              </div>

              {/* Possible Contributing Factors (Facts vs Hypotheses) */}
              <div className="bg-white border border-[#D6D3CD] p-3.5 space-y-1.5">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-[#3F3F46]">
                  3. Contributing Factors (Recorded Facts vs Unconfirmed Hypotheses)
                </div>
                <ul className="space-y-1.5 text-xs">
                  {response.contributing_factors?.map((cf: string, idx: number) => (
                    <li key={idx} className="p-2 bg-[#F6F5F2] border border-[#D6D3CD]">
                      {cf}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Suggested Investigation Steps */}
              <div className="bg-white border border-[#D6D3CD] p-3.5 space-y-1.5">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-[#166534]">
                  4. Recommended Investigation & Remediation Steps
                </div>
                <ol className="list-decimal list-inside text-xs text-[#18181B] space-y-1 font-medium">
                  {response.investigation_steps?.map((st: string, idx: number) => (
                    <li key={idx}>{st}</li>
                  ))}
                </ol>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
