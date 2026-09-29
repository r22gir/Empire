"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { API } from "../../lib/api";

const JOB_TYPES = [
  ["drapery_romans", "Drapery / Romans"],
  ["banquette", "Banquette"],
  ["soft_seating", "Soft seating"],
  ["headboard", "Headboard"],
  ["mixed", "Mixed"],
  ["other", "Other"],
] as const;

const SOURCES = [
  ["meta_ad", "Meta ad"],
  ["instagram", "Instagram"],
  ["houzz", "Houzz"],
  ["outreach", "Outreach"],
  ["web", "Web"],
  ["referral", "Referral"],
  ["other", "Other"],
] as const;

const STATUSES = ["new", "needs_info", "quoting", "quoted", "won", "lost", "hold"] as const;

const GMAIL_SEARCH =
  "https://mail.google.com/mail/u/0/#search/to%3Aworkroom%40empirebox.store";

type Intake = {
  id: number;
  received_at: string;
  full_name: string;
  email: string;
  phone?: string | null;
  firm_name?: string | null;
  city_region?: string | null;
  job_type: string;
  message: string;
  photo_urls: string[];
  source: string;
  utm_campaign?: string | null;
  consent_contact: string;
  business: string;
  campaign: string;
  owner?: string | null;
  status: string;
  last_contacted_at?: string | null;
  next_action?: string | null;
  crm_contact_id?: string | null;
  lead_id?: number | null;
  quote_id?: string | null;
  notes?: string | null;
};

const EMPTY_FORM = {
  full_name: "",
  email: "",
  phone: "",
  firm_name: "",
  city_region: "",
  job_type: "",
  message: "",
  photo_urls: "",
  source: "",
  utm_campaign: "",
  consent_contact: "",
  owner: "Rafael",
  notes: "",
};

async function readError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) {
      return data.detail.map((item: { msg?: string }) => item.msg || "Invalid field").join(", ");
    }
  } catch {
    /* response was not JSON */
  }
  return `Request failed (${res.status})`;
}

export default function WorkroomCapturePage() {
  const [form, setForm] = useState(EMPTY_FORM);
  const [intakes, setIntakes] = useState<Intake[]>([]);
  const [focusId, setFocusId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await fetch(`${API}/workroom-capture/intake?limit=50`);
      if (!res.ok) throw new Error(await readError(res));
      const data = await res.json();
      setIntakes(data.intakes || []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load captures");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const id = Number(new URLSearchParams(window.location.search).get("intake"));
    if (Number.isFinite(id) && id > 0) setFocusId(id);
    load();
  }, [load]);

  function setField(name: keyof typeof EMPTY_FORM, value: string) {
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setNotice(null);
    const photo_urls = form.photo_urls
      .split(/\n|,/)
      .map((item) => item.trim())
      .filter(Boolean);
    try {
      const res = await fetch(`${API}/workroom-capture/intake`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          full_name: form.full_name,
          email: form.email,
          phone: form.phone || null,
          firm_name: form.firm_name || null,
          city_region: form.city_region || null,
          job_type: form.job_type,
          message: form.message,
          photo_urls,
          source: form.source,
          utm_campaign: form.utm_campaign || null,
          consent_contact: form.consent_contact,
          business: "workroom",
          campaign: "workroom_national_48h",
          owner: form.owner || "Rafael",
          notes: form.notes || null,
        }),
      });
      if (!res.ok) throw new Error(await readError(res));
      const data = await res.json();
      setFocusId(data.intake.id);
      setNotice(
        data.crm_outcome === "matched"
          ? `Saved lead #${data.lead_id} on existing contact ${data.customer_id}. No email sent.`
          : `Saved lead #${data.lead_id} and new contact ${data.customer_id}. No email sent.`
      );
      setForm({ ...EMPTY_FORM, owner: form.owner || "Rafael" });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the capture");
    } finally {
      setSaving(false);
    }
  }

  async function openQuote(intake: Intake) {
    setBusyId(intake.id);
    setError(null);
    try {
      const res = await fetch(`${API}/workroom-capture/intake/${intake.id}/quote`, { method: "POST" });
      if (!res.ok) throw new Error(await readError(res));
      const data = await res.json();
      setNotice(
        data.quote_outcome === "already_open"
          ? `Quote ${data.quote.quote_number} is already open. No email sent.`
          : `Opened draft ${data.quote.quote_number}. No email sent.`
      );
      setFocusId(intake.id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not open the quote");
    } finally {
      setBusyId(null);
    }
  }

  async function saveRow(intake: Intake, patch: Record<string, string>) {
    setBusyId(intake.id);
    setError(null);
    try {
      const res = await fetch(`${API}/workroom-capture/intake/${intake.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      });
      if (!res.ok) throw new Error(await readError(res));
      setNotice("Row updated. No email sent.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update the row");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="min-h-screen" style={{ backgroundColor: "#f5f3ef", fontFamily: "'Outfit', 'Segoe UI', sans-serif" }}>
      <header className="px-6 py-10 md:px-12" style={{ background: "linear-gradient(135deg, #1a1a2e 0%, #2d2d44 100%)" }}>
        <div className="max-w-5xl mx-auto">
          <p className="text-xs font-bold tracking-[0.2em] uppercase mb-2" style={{ color: "#d4af37" }}>
            Empire Workroom — Stage 0
          </p>
          <h1 className="text-3xl md:text-4xl font-extrabold text-white">Inbox capture</h1>
          <p className="text-white/70 mt-3 max-w-2xl text-sm leading-relaxed">
            Log mail to workroom@empirebox.store into LeadForge and ForgeCRM, then open a Workroom quote draft.
            This page does not send email.
          </p>
          <div className="flex flex-wrap gap-4 mt-5 text-sm">
            <a href={GMAIL_SEARCH} target="_blank" rel="noreferrer" className="font-semibold" style={{ color: "#d4af37" }}>
              Open Gmail search
            </a>
            <a href="/workroom/ops" className="font-semibold text-white/80">
              Daily ops
            </a>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 md:px-12 py-8 space-y-8">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">{error}</div>
        )}
        {notice && (
          <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg px-4 py-3 text-sm">{notice}</div>
        )}

        <section className="bg-white rounded-xl shadow-sm border border-black/5 p-5 md:p-6">
          <h2 className="text-xs font-bold tracking-[0.15em] uppercase mb-3" style={{ color: "#1a1a2e" }}>
            Triage the inbox
          </h2>
          <ol className="text-sm text-gray-700 space-y-2 list-decimal pl-5">
            <li>Public address workroom@empirebox.store routes to empirebox2026@gmail.com.</li>
            <li>Read the new thread, then log it here the same day. Leave unknown fields blank.</li>
            <li>Reply yourself from that mailbox. Then record the contact time on the row. Recording does not send the reply.</li>
            <li>Create the Workroom quote when you are ready to price. The draft is not sent.</li>
          </ol>
          <p className="text-xs text-gray-500 mt-3">
            Business stays workroom. Campaign tag for this sprint is workroom_national_48h. Owner defaults to Rafael.
          </p>
        </section>

        <section className="bg-white rounded-xl shadow-sm border border-black/5 p-5 md:p-6">
          <h2 className="text-xs font-bold tracking-[0.15em] uppercase mb-4" style={{ color: "#1a1a2e" }}>
            New capture
          </h2>
          <form onSubmit={onSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label className="text-sm font-medium text-gray-700">
              Full name
              <input required value={form.full_name} onChange={(e) => setField("full_name", e.target.value)} className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2" />
            </label>
            <label className="text-sm font-medium text-gray-700">
              Email
              <input required type="email" value={form.email} onChange={(e) => setField("email", e.target.value)} className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2" />
            </label>
            <label className="text-sm font-medium text-gray-700">
              Phone
              <input value={form.phone} onChange={(e) => setField("phone", e.target.value)} className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2" />
            </label>
            <label className="text-sm font-medium text-gray-700">
              Firm
              <input value={form.firm_name} onChange={(e) => setField("firm_name", e.target.value)} className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2" />
            </label>
            <label className="text-sm font-medium text-gray-700">
              City / region
              <input value={form.city_region} onChange={(e) => setField("city_region", e.target.value)} className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2" />
            </label>
            <label className="text-sm font-medium text-gray-700">
              Owner
              <input value={form.owner} onChange={(e) => setField("owner", e.target.value)} className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2" />
            </label>
            <label className="text-sm font-medium text-gray-700">
              Job type
              <select required value={form.job_type} onChange={(e) => setField("job_type", e.target.value)} className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 bg-white">
                <option value="">Select job type</option>
                {JOB_TYPES.map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </label>
            <label className="text-sm font-medium text-gray-700">
              Source
              <select required value={form.source} onChange={(e) => setField("source", e.target.value)} className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 bg-white">
                <option value="">Select source</option>
                {SOURCES.map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </label>
            <label className="text-sm font-medium text-gray-700 md:col-span-2">
              Message
              <textarea required rows={4} value={form.message} onChange={(e) => setField("message", e.target.value)} className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2" />
            </label>
            <label className="text-sm font-medium text-gray-700">
              Photo links
              <textarea rows={3} value={form.photo_urls} onChange={(e) => setField("photo_urls", e.target.value)} placeholder="One link per line" className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2" />
            </label>
            <div className="space-y-4">
              <label className="text-sm font-medium text-gray-700 block">
                UTM campaign
                <input value={form.utm_campaign} onChange={(e) => setField("utm_campaign", e.target.value)} className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2" />
              </label>
              <fieldset className="text-sm font-medium text-gray-700">
                <legend>Consent to contact</legend>
                <div className="mt-2 flex flex-wrap gap-4 font-normal">
                  {(["yes", "no", "unknown"] as const).map((value) => (
                    <label key={value} className="inline-flex items-center gap-2">
                      <input
                        required
                        type="radio"
                        name="consent_contact"
                        value={value}
                        checked={form.consent_contact === value}
                        onChange={() => setField("consent_contact", value)}
                      />
                      {value}
                    </label>
                  ))}
                </div>
              </fieldset>
            </div>
            <label className="text-sm font-medium text-gray-700 md:col-span-2">
              Notes
              <textarea rows={2} value={form.notes} onChange={(e) => setField("notes", e.target.value)} className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2" />
            </label>
            <div className="md:col-span-2">
              <button
                type="submit"
                disabled={saving}
                className="rounded-lg px-5 py-2.5 text-sm font-bold text-white disabled:opacity-60"
                style={{ background: "#1a1a2e" }}
              >
                {saving ? "Saving…" : "Save prospect"}
              </button>
            </div>
          </form>
        </section>

        <section>
          <h2 className="text-xs font-bold tracking-[0.15em] uppercase mb-3" style={{ color: "#1a1a2e" }}>
            Recent captures
          </h2>
          {loading ? (
            <p className="text-sm text-gray-500">Loading captures…</p>
          ) : intakes.length === 0 ? (
            <div className="bg-white rounded-xl p-8 shadow-sm border border-black/5 text-center text-gray-400 text-sm">
              No captures yet. The inbox row you save will show up here.
            </div>
          ) : (
            <div className="space-y-3">
              {intakes.map((intake) => (
                <article
                  key={intake.id}
                  id={`intake-${intake.id}`}
                  className="bg-white rounded-xl shadow-sm border p-5"
                  style={{ borderColor: focusId === intake.id ? "#d4af37" : "rgba(0,0,0,0.06)" }}
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h3 className="font-bold" style={{ color: "#1a1a2e" }}>{intake.full_name}</h3>
                      <p className="text-sm text-gray-600">
                        {intake.email}
                        {intake.phone ? ` · ${intake.phone}` : ""}
                        {intake.firm_name ? ` · ${intake.firm_name}` : ""}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {intake.job_type} · {intake.source}
                        {intake.utm_campaign ? ` · utm ${intake.utm_campaign}` : ""}
                        {intake.city_region ? ` · ${intake.city_region}` : ""}
                        {" · "}consent {intake.consent_contact}
                        {" · "}lead #{intake.lead_id} · contact {intake.crm_contact_id}
                      </p>
                    </div>
                    <span className="text-xs font-bold uppercase tracking-wide px-2 py-1 rounded-full bg-gray-100 text-gray-700">
                      {intake.status}
                    </span>
                  </div>
                  <p className="text-sm text-gray-800 mt-3 whitespace-pre-wrap">{intake.message}</p>
                  {intake.photo_urls?.length > 0 && (
                    <ul className="mt-2 text-xs text-gray-500 space-y-1">
                      {intake.photo_urls.map((url) => (
                        <li key={url}><a href={url} className="underline" target="_blank" rel="noreferrer">{url}</a></li>
                      ))}
                    </ul>
                  )}
                  <p className="text-xs text-gray-500 mt-2">Next: {intake.next_action || "—"}</p>
                  <div className="flex flex-wrap items-center gap-2 mt-4">
                    <label className="text-xs text-gray-500">
                      Status
                      <select
                        value={intake.status}
                        onChange={(e) => saveRow(intake, { status: e.target.value })}
                        className="ml-2 rounded-lg border border-gray-200 px-2 py-1 text-sm bg-white"
                      >
                        {STATUSES.map((status) => (
                          <option key={status} value={status}>{status}</option>
                        ))}
                      </select>
                    </label>
                    <button
                      type="button"
                      disabled={busyId === intake.id}
                      onClick={() => openQuote(intake)}
                      className="rounded-lg px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-60"
                      style={{ background: "#1a1a2e" }}
                    >
                      {intake.quote_id ? "Open quote draft" : "Create Workroom quote"}
                    </button>
                    {intake.quote_id && (
                      <a href={`/quote/${intake.quote_id}`} className="text-sm font-semibold" style={{ color: "#8a6d12" }}>
                        View {intake.quote_id}
                      </a>
                    )}
                    <button
                      type="button"
                      disabled={busyId === intake.id}
                      onClick={() => saveRow(intake, { last_contacted_at: new Date().toISOString() })}
                      className="rounded-lg px-3 py-1.5 text-sm font-semibold border border-gray-200"
                    >
                      Record that I replied
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
