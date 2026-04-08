"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { API } from '../../lib/api';

/* ── Types ─────────────────────────────────────────────────────────── */

interface LineItem {
  description: string;
  qty: number;
  unit_price: number;
  subtotal: number;
}

interface Quote {
  id: number;
  project_name: string;
  status: string;
  line_items: LineItem[];
  subtotal: number;
  tax: number;
  total: number;
}

interface WorkOrderItem {
  description: string;
  stage: string;
  overdue?: boolean;
}

interface ProductionLog {
  date: string;
  status: string;
  notes?: string;
}

interface Production {
  work_order_items: WorkOrderItem[];
  production_log: ProductionLog[];
}

interface Payment {
  date: string;
  amount: number;
  method?: string;
}

interface Invoice {
  invoice_number: string;
  total: number;
  amount_paid: number;
  balance_due: number;
  payments: Payment[];
}

interface PortalData {
  client_name: string;
  project_name: string;
  status: string;
  quote?: Quote;
  production?: Production;
  invoice?: Invoice;
  can_approve_quote?: boolean;
  can_pay?: boolean;
}

/* ── Constants ─────────────────────────────────────────────────────── */

const PORTAL_API = `${API}/portal`;

const STAGES = [
  "Pending",
  "Fabric Ordered",
  "Cutting",
  "Sewing",
  "QC",
  "Complete",
];

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-gray-400 text-white",
  sent: "bg-yellow-500 text-white",
  approved: "bg-green-600 text-white",
  in_production: "bg-blue-600 text-white",
  complete: "bg-emerald-700 text-white",
};

/* ── Helpers ───────────────────────────────────────────────────────── */

function fmt(n: number) {
  return n.toLocaleString("en-US", { style: "currency", currency: "USD" });
}

function statusLabel(s: string) {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function stageIndex(stage: string) {
  const idx = STAGES.findIndex(
    (s) => s.toLowerCase() === stage.toLowerCase()
  );
  return idx === -1 ? 0 : idx;
}

/* ── Component ─────────────────────────────────────────────────────── */

export default function PortalPage() {
  const params = useParams();
  const token = params.token as string;

  const [data, setData] = useState<PortalData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [approving, setApproving] = useState(false);

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    fetch(`${PORTAL_API}/${token}`)
      .then((r) => {
        if (r.status === 404) throw new Error("expired");
        if (!r.ok) throw new Error("failed");
        return r.json();
      })
      .then((d) => {
        setData(d);
        setError(null);
      })
      .catch((e) => {
        setError(e.message === "expired" ? "expired" : "failed");
      })
      .finally(() => setLoading(false));
  }, [token]);

  async function handleApprove() {
    if (!confirm("Are you sure you want to approve this quote?")) return;
    setApproving(true);
    try {
      const r = await fetch(`${PORTAL_API}/${token}/approve`, { method: "POST" });
      if (!r.ok) throw new Error();
      const updated = await r.json();
      setData((prev) => (prev ? { ...prev, ...updated } : prev));
    } catch {
      alert("Unable to approve at this time. Please try again or call us.");
    } finally {
      setApproving(false);
    }
  }

  /* ── Loading ──────────────────────────────────────────────────────── */

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "#f5f3ef" }}>
        <div className="text-center">
          <div
            className="w-10 h-10 border-4 rounded-full animate-spin mx-auto mb-4"
            style={{ borderColor: "#e5e5e5", borderTopColor: "#b8960c" }}
          />
          <p className="text-lg" style={{ color: "#1a1a2e" }}>
            Loading your project details...
          </p>
        </div>
      </div>
    );
  }

  /* ── Error / expired ──────────────────────────────────────────────── */

  if (error || !data) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "#f5f3ef" }}>
        <div className="text-center max-w-md px-6">
          <div className="text-5xl mb-4">🔒</div>
          <h1 className="text-2xl font-bold mb-2" style={{ color: "#1a1a2e" }}>
            {error === "expired" ? "Link Expired" : "Something Went Wrong"}
          </h1>
          <p className="text-gray-600 mb-6">
            {error === "expired"
              ? "This portal link is no longer valid. Please contact us for an updated link."
              : "We couldn\u2019t load your project details. Please try again or contact us."}
          </p>
          <p className="text-sm text-gray-500">
            Call (703) 213-6484 or visit{" "}
            <a
              href="https://studio.empirebox.store"
              className="underline"
              style={{ color: "#b8960c" }}
            >
              studio.empirebox.store
            </a>
          </p>
        </div>
      </div>
    );
  }

  const { quote, production, invoice } = data;

  /* ── Main portal ──────────────────────────────────────────────────── */

  return (
    <div className="min-h-screen" style={{ background: "#f5f3ef" }}>
      {/* Header */}
      <header className="border-b" style={{ borderColor: "#e0ddd6" }}>
        <div className="max-w-4xl mx-auto px-4 py-6 sm:px-6">
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight" style={{ color: "#1a1a2e" }}>
            Empire Workroom
          </h1>
          <p className="mt-1 text-sm sm:text-base" style={{ color: "#b8960c" }}>
            Your Project Details
          </p>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8 sm:px-6 space-y-8">
        {/* ── Client Info ────────────────────────────────────────────── */}
        <section className="bg-white rounded-xl shadow-sm p-5 sm:p-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <h2 className="text-xl font-semibold" style={{ color: "#1a1a2e" }}>
                {data.client_name}
              </h2>
              <p className="text-gray-500 text-sm mt-1">{data.project_name}</p>
            </div>
            <span
              className={`inline-block self-start px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wide ${
                STATUS_COLORS[data.status] || "bg-gray-300 text-gray-800"
              }`}
            >
              {statusLabel(data.status)}
            </span>
          </div>
        </section>

        {/* ── Quote ──────────────────────────────────────────────────── */}
        {quote && (
          <section className="bg-white rounded-xl shadow-sm overflow-hidden">
            <div className="px-5 sm:px-6 py-4 border-b" style={{ borderColor: "#eae7e0" }}>
              <h3 className="text-lg font-semibold" style={{ color: "#b8960c" }}>
                Quote
              </h3>
            </div>

            {/* Line items table */}
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left" style={{ background: "#faf8f5" }}>
                    <th className="px-5 py-3 font-medium text-gray-500 w-10">#</th>
                    <th className="px-5 py-3 font-medium text-gray-500">Description</th>
                    <th className="px-5 py-3 font-medium text-gray-500 text-right">Qty</th>
                    <th className="px-5 py-3 font-medium text-gray-500 text-right">Unit Price</th>
                    <th className="px-5 py-3 font-medium text-gray-500 text-right">Subtotal</th>
                  </tr>
                </thead>
                <tbody>
                  {quote.line_items.map((item, i) => (
                    <tr key={i} className="border-t" style={{ borderColor: "#f0ede7" }}>
                      <td className="px-5 py-3 text-gray-400">{i + 1}</td>
                      <td className="px-5 py-3" style={{ color: "#1a1a2e" }}>
                        {item.description}
                      </td>
                      <td className="px-5 py-3 text-right text-gray-600">{item.qty}</td>
                      <td className="px-5 py-3 text-right text-gray-600">{fmt(item.unit_price)}</td>
                      <td className="px-5 py-3 text-right font-medium" style={{ color: "#1a1a2e" }}>
                        {fmt(item.subtotal)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Totals */}
            <div className="px-5 sm:px-6 py-4 border-t" style={{ borderColor: "#eae7e0", background: "#faf8f5" }}>
              <div className="flex flex-col items-end gap-1 text-sm">
                <div className="flex justify-between w-48">
                  <span className="text-gray-500">Subtotal</span>
                  <span style={{ color: "#1a1a2e" }}>{fmt(quote.subtotal)}</span>
                </div>
                <div className="flex justify-between w-48">
                  <span className="text-gray-500">Tax</span>
                  <span style={{ color: "#1a1a2e" }}>{fmt(quote.tax)}</span>
                </div>
                <div className="flex justify-between w-48 pt-2 border-t font-bold text-base" style={{ borderColor: "#e0ddd6" }}>
                  <span style={{ color: "#1a1a2e" }}>Total</span>
                  <span style={{ color: "#1a1a2e" }}>{fmt(quote.total)}</span>
                </div>
              </div>
            </div>

            {/* Approve button */}
            {data.can_approve_quote && quote.status === "sent" && (
              <div className="px-5 sm:px-6 py-4 border-t" style={{ borderColor: "#eae7e0" }}>
                <button
                  onClick={handleApprove}
                  disabled={approving}
                  className="w-full sm:w-auto px-8 rounded-lg font-semibold text-white transition-opacity disabled:opacity-50"
                  style={{ background: "#b8960c", minHeight: 44 }}
                >
                  {approving ? "Approving..." : "Approve Quote"}
                </button>
              </div>
            )}

            {quote.status === "approved" && (
              <div className="px-5 sm:px-6 py-4 border-t" style={{ borderColor: "#eae7e0" }}>
                <div className="flex items-center gap-2 text-green-700 text-sm font-medium">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Quote Approved
                </div>
              </div>
            )}
          </section>
        )}

        {/* ── Production Status ──────────────────────────────────────── */}
        {production && (
          <section className="bg-white rounded-xl shadow-sm overflow-hidden">
            <div className="px-5 sm:px-6 py-4 border-b" style={{ borderColor: "#eae7e0" }}>
              <h3 className="text-lg font-semibold" style={{ color: "#b8960c" }}>
                Production Status
              </h3>
            </div>

            <div className="px-5 sm:px-6 py-6 space-y-6">
              {/* Progress bar */}
              <div>
                {/* Stage labels */}
                <div className="hidden sm:flex justify-between mb-2 text-xs text-gray-500">
                  {STAGES.map((s) => (
                    <span key={s} className="text-center flex-1">
                      {s}
                    </span>
                  ))}
                </div>
                {/* Bar — uses the most-advanced item to show overall progress */}
                {(() => {
                  const maxStage = Math.max(
                    ...production.work_order_items.map((w) => stageIndex(w.stage)),
                    0
                  );
                  const pct = ((maxStage + 1) / STAGES.length) * 100;
                  return (
                    <div className="w-full h-3 rounded-full overflow-hidden" style={{ background: "#e8e5de" }}>
                      <div
                        className="h-full rounded-full transition-all duration-700"
                        style={{ width: `${pct}%`, background: "#b8960c" }}
                      />
                    </div>
                  );
                })()}
                {/* Current stage label (mobile) */}
                <p className="sm:hidden mt-2 text-xs text-gray-500 text-center">
                  {(() => {
                    const maxStage = Math.max(
                      ...production.work_order_items.map((w) => stageIndex(w.stage)),
                      0
                    );
                    return STAGES[maxStage];
                  })()}
                </p>
              </div>

              {/* Work order items */}
              <div className="space-y-3">
                <h4 className="text-sm font-semibold text-gray-700">Work Order Items</h4>
                {production.work_order_items.map((item, i) => {
                  const isComplete = item.stage.toLowerCase() === "complete";
                  const isOverdue = item.overdue === true;
                  const dot = isComplete ? "\uD83D\uDFE2" : isOverdue ? "\uD83D\uDD34" : "\uD83D\uDFE1";
                  return (
                    <div
                      key={i}
                      className="flex items-center justify-between py-2 px-3 rounded-lg"
                      style={{ background: "#faf8f5" }}
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-base leading-none">{dot}</span>
                        <span className="text-sm" style={{ color: "#1a1a2e" }}>
                          {item.description}
                        </span>
                      </div>
                      <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                        {item.stage}
                      </span>
                    </div>
                  );
                })}
              </div>

              {/* Timeline */}
              {production.production_log && production.production_log.length > 0 && (
                <div className="space-y-3">
                  <h4 className="text-sm font-semibold text-gray-700">Timeline</h4>
                  <div className="relative pl-6 space-y-4">
                    {/* Vertical line */}
                    <div
                      className="absolute left-[7px] top-2 bottom-2 w-px"
                      style={{ background: "#ddd8ce" }}
                    />
                    {production.production_log.map((entry, i) => (
                      <div key={i} className="relative">
                        {/* Dot */}
                        <div
                          className="absolute -left-6 top-1.5 w-3.5 h-3.5 rounded-full border-2 border-white"
                          style={{ background: "#b8960c" }}
                        />
                        <div>
                          <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-3">
                            <span className="text-xs text-gray-400 font-mono whitespace-nowrap">
                              {entry.date}
                            </span>
                            <span className="text-sm font-medium" style={{ color: "#1a1a2e" }}>
                              {statusLabel(entry.status)}
                            </span>
                          </div>
                          {entry.notes && (
                            <p className="text-xs text-gray-500 mt-0.5">{entry.notes}</p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </section>
        )}

        {/* ── Invoice ────────────────────────────────────────────────── */}
        {invoice && (
          <section className="bg-white rounded-xl shadow-sm overflow-hidden">
            <div className="px-5 sm:px-6 py-4 border-b" style={{ borderColor: "#eae7e0" }}>
              <h3 className="text-lg font-semibold" style={{ color: "#b8960c" }}>
                Invoice
              </h3>
            </div>

            <div className="px-5 sm:px-6 py-5 space-y-5">
              {/* Summary grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div>
                  <p className="text-xs text-gray-400 uppercase tracking-wide">Invoice #</p>
                  <p className="text-sm font-semibold mt-0.5" style={{ color: "#1a1a2e" }}>
                    {invoice.invoice_number}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 uppercase tracking-wide">Total</p>
                  <p className="text-sm font-semibold mt-0.5" style={{ color: "#1a1a2e" }}>
                    {fmt(invoice.total)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 uppercase tracking-wide">Paid</p>
                  <p className="text-sm font-semibold mt-0.5 text-green-700">
                    {fmt(invoice.amount_paid)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 uppercase tracking-wide">Balance Due</p>
                  <p
                    className="text-sm font-semibold mt-0.5"
                    style={{ color: invoice.balance_due > 0 ? "#e94560" : "#1a1a2e" }}
                  >
                    {fmt(invoice.balance_due)}
                  </p>
                </div>
              </div>

              {/* Payments list */}
              {invoice.payments && invoice.payments.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">Payments</h4>
                  <div className="space-y-2">
                    {invoice.payments.map((p, i) => (
                      <div
                        key={i}
                        className="flex items-center justify-between py-2 px-3 rounded-lg text-sm"
                        style={{ background: "#faf8f5" }}
                      >
                        <div className="flex items-center gap-3">
                          <span className="text-gray-400 font-mono text-xs">{p.date}</span>
                          {p.method && (
                            <span className="text-gray-500 text-xs capitalize">{p.method}</span>
                          )}
                        </div>
                        <span className="font-medium text-green-700">{fmt(p.amount)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Pay Now */}
              {data.can_pay && invoice.balance_due > 0 && (
                <button
                  onClick={() => alert("Payment coming soon")}
                  className="w-full sm:w-auto px-8 rounded-lg font-semibold text-white transition-opacity"
                  style={{ background: "#e94560", minHeight: 44 }}
                >
                  Pay Now &mdash; {fmt(invoice.balance_due)}
                </button>
              )}
            </div>
          </section>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t mt-12" style={{ borderColor: "#e0ddd6" }}>
        <div className="max-w-4xl mx-auto px-4 py-6 sm:px-6 text-center text-sm text-gray-400">
          Questions? Call{" "}
          <a href="tel:+17032136484" className="underline" style={{ color: "#b8960c" }}>
            (703) 213-6484
          </a>{" "}
          |{" "}
          <a href="https://studio.empirebox.store" className="underline" style={{ color: "#b8960c" }}>
            studio.empirebox.store
          </a>
        </div>
      </footer>
    </div>
  );
}
