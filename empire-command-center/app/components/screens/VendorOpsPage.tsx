'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { API } from '../../lib/api';

type Tier = 'free' | 'starter' | 'pro';
type Tab = 'dashboard' | 'accounts' | 'approvals' | 'subscriptions' | 'audit';

interface Plan {
  monthly_price_usd: number;
  approval_limit: number;
  account_limit: number;
  subscription_limit: number;
  automation: string;
  positioning: string;
}

interface DashboardData {
  tier: Tier;
  kpis: {
    total_accounts: number;
    active_subscriptions: number;
    monthly_cost_total_usd: number;
    upcoming_renewals_30d: number;
    pending_approvals: number;
  };
  max_policy: string;
}

interface VendorStatus {
  tier: Tier;
  accounts_used: number;
  subscriptions_used: number;
  pending_approvals: number;
  max_can_query: boolean;
  max_can_write: boolean;
  credential_policy: string;
}

interface AccountRow {
  id: string;
  vendor_name: string;
  category?: string;
  account_status: string;
  credential_owner: string;
  monthly_cost_usd?: number;
  renewal_date?: string | null;
  tier: Tier;
}

interface ApprovalRow {
  id: string;
  vendor_name: string;
  requested_action: string;
  status: string;
  verification_boundary: string;
  assisted_signup_state?: string;
  created_at: string;
  approved_at?: string | null;
}

interface SubscriptionRow {
  id: string;
  vendor_name: string;
  plan_name: string;
  tier: Tier;
  status: string;
  monthly_cost_usd?: number;
  renewal_cadence?: string;
  renewal_date: string;
  cancellation_state: string;
}

interface AuditRow {
  id: number;
  event_type: string;
  entity_type: string;
  entity_id: string;
  actor: string;
  created_at: string;
  metadata?: Record<string, unknown>;
}

const tabs: { id: Tab; label: string }[] = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'accounts', label: 'Accounts' },
  { id: 'approvals', label: 'Approvals' },
  { id: 'subscriptions', label: 'Subscriptions' },
  { id: 'audit', label: 'Audit' },
];

function currency(value?: number | null) {
  return `$${Number(value || 0).toFixed(2)}`;
}

function shortDate(value?: string | null) {
  if (!value) return 'Not recorded';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString();
}

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`VendorOps API ${res.status}: ${path}`);
  return res.json();
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`VendorOps API ${res.status}: ${path}`);
  return res.json();
}

export default function VendorOpsPage() {
  const [tab, setTab] = useState<Tab>('dashboard');
  const [tier, setTier] = useState<Tier>('free');
  const [plans, setPlans] = useState<Record<Tier, Plan> | null>(null);
  const [status, setStatus] = useState<VendorStatus | null>(null);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [accounts, setAccounts] = useState<AccountRow[]>([]);
  const [approvals, setApprovals] = useState<ApprovalRow[]>([]);
  const [subscriptions, setSubscriptions] = useState<SubscriptionRow[]>([]);
  const [renewalAlerts, setRenewalAlerts] = useState<SubscriptionRow[]>([]);
  const [audit, setAudit] = useState<AuditRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [plansRes, statusRes, dashboardRes, accountsRes, approvalsRes, subscriptionsRes, alertsRes, auditRes] = await Promise.all([
        fetchJson<{ tiers: Record<Tier, Plan> }>('/vendorops/plans'),
        fetchJson<VendorStatus>(`/vendorops/status?tier=${tier}`),
        fetchJson<DashboardData>(`/vendorops/dashboard?tier=${tier}`),
        fetchJson<{ accounts: AccountRow[] }>('/vendorops/accounts'),
        fetchJson<{ approvals: ApprovalRow[] }>('/vendorops/approvals'),
        fetchJson<{ subscriptions: SubscriptionRow[] }>('/vendorops/subscriptions'),
        fetchJson<{ alerts: SubscriptionRow[] }>('/vendorops/renewal-alerts?days=30'),
        fetchJson<{ events: AuditRow[] }>('/vendorops/audit?limit=50'),
      ]);
      setPlans(plansRes.tiers);
      setStatus(statusRes);
      setDashboard(dashboardRes);
      setAccounts(accountsRes.accounts || []);
      setApprovals(approvalsRes.approvals || []);
      setSubscriptions(subscriptionsRes.subscriptions || []);
      setRenewalAlerts(alertsRes.alerts || []);
      setAudit(auditRes.events || []);
    } catch (exc: any) {
      setError(exc?.message || 'VendorOps unavailable');
    } finally {
      setLoading(false);
    }
  }, [tier]);

  useEffect(() => {
    load();
  }, [load]);

  const pendingApprovals = useMemo(() => approvals.filter(item => item.status === 'pending'), [approvals]);
  const decisionHistory = useMemo(() => approvals.filter(item => item.status !== 'pending'), [approvals]);

  const decideApproval = async (id: string, decision: 'approve' | 'reject') => {
    setActionMessage(null);
    setError(null);
    try {
      await postJson(`/vendorops/approvals/${id}/${decision}`, { explicit_founder_confirmation: true });
      setActionMessage(`Approval ${decision}d.`);
      await load();
    } catch (exc: any) {
      setError(exc?.message || `Approval ${decision} failed`);
    }
  };

  const currentPlan = plans?.[tier];
  const starterLocked = tier === 'free';
  const proLocked = tier !== 'pro';

  return (
    <div className="min-h-full p-4 md:p-6" style={{ background: '#f8fafc', color: '#111827' }}>
      <div className="mx-auto flex max-w-7xl flex-col gap-5">
        <header className="flex flex-col gap-4 rounded-lg border border-slate-200 bg-white p-5 shadow-sm md:flex-row md:items-start md:justify-between">
          <div>
            <div className="text-xs font-bold uppercase tracking-[0.16em]" style={{ color: '#0d9488' }}>Standalone Add-On</div>
            <h1 className="mt-2 text-2xl font-bold text-slate-950">VendorOps</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              Track vendor accounts, approvals, renewals, credential ownership, and subscription risk without mixing VendorOps into Empire payments or RelistApp.
            </p>
            <div className="mt-3 flex flex-wrap gap-2 text-xs font-semibold">
              <span className="rounded-md bg-slate-100 px-2.5 py-1 text-slate-700">Route: /api/v1/vendorops</span>
              <span className="rounded-md bg-slate-100 px-2.5 py-1 text-slate-700">DB prefix: vo_</span>
              <span className="rounded-md bg-amber-100 px-2.5 py-1 text-amber-800">MAX query-only</span>
            </div>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <label className="text-xs font-bold uppercase tracking-wide text-slate-500">Current Tier</label>
            <select
              value={tier}
              onChange={(event) => setTier(event.target.value as Tier)}
              className="mt-2 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-900"
            >
              <option value="free">Free</option>
              <option value="starter">Starter</option>
              <option value="pro">Pro</option>
            </select>
            <div className="mt-2 text-xs text-slate-600">{currentPlan?.positioning || 'Loading plan truth from VendorOps.'}</div>
          </div>
        </header>

        {error && <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">{error}</div>}
        {actionMessage && <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-700">{actionMessage}</div>}

        <section className="grid gap-3 md:grid-cols-3">
          {plans && (Object.keys(plans) as Tier[]).map(planTier => {
            const plan = plans[planTier];
            const isCurrent = planTier === tier;
            const isLocked = (planTier === 'starter' && starterLocked) || (planTier === 'pro' && proLocked);
            return (
              <div key={planTier} className={`rounded-lg border bg-white p-4 shadow-sm ${isCurrent ? 'border-teal-500' : 'border-slate-200'}`}>
                <div className="flex items-center justify-between gap-3">
                  <h2 className="text-base font-bold capitalize text-slate-950">{planTier}</h2>
                  <span className={`rounded-md px-2 py-1 text-xs font-bold ${isCurrent ? 'bg-teal-100 text-teal-800' : isLocked ? 'bg-slate-100 text-slate-600' : 'bg-emerald-100 text-emerald-800'}`}>
                    {isCurrent ? 'Current' : isLocked ? 'Locked' : 'Available'}
                  </span>
                </div>
                <div className="mt-3 text-2xl font-bold text-slate-950">{currency(plan.monthly_price_usd)}<span className="text-sm font-medium text-slate-500">/mo</span></div>
                <p className="mt-2 min-h-[40px] text-sm text-slate-600">{plan.positioning}</p>
                <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
                  <div className="rounded-md bg-slate-50 p-2"><b>{plan.account_limit}</b><br />accounts</div>
                  <div className="rounded-md bg-slate-50 p-2"><b>{plan.subscription_limit}</b><br />subs</div>
                  <div className="rounded-md bg-slate-50 p-2"><b>{plan.approval_limit}</b><br />approvals</div>
                </div>
              </div>
            );
          })}
        </section>

        <nav className="flex flex-wrap gap-2">
          {tabs.map(item => (
            <button
              key={item.id}
              onClick={() => setTab(item.id)}
              className={`rounded-md border px-4 py-2 text-sm font-bold ${tab === item.id ? 'border-teal-600 bg-teal-600 text-white' : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'}`}
            >
              {item.label}
            </button>
          ))}
        </nav>

        {loading ? (
          <div className="rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-600">Loading VendorOps data from /api/v1/vendorops...</div>
        ) : (
          <>
            {tab === 'dashboard' && (
              <section className="grid gap-4">
                <div className="grid gap-3 md:grid-cols-5">
                  {[
                    ['Total Accounts', dashboard?.kpis.total_accounts ?? 0],
                    ['Active Subscriptions', dashboard?.kpis.active_subscriptions ?? 0],
                    ['Monthly Cost', currency(dashboard?.kpis.monthly_cost_total_usd)],
                    ['Renewals 30d', dashboard?.kpis.upcoming_renewals_30d ?? 0],
                    ['Pending Approvals', dashboard?.kpis.pending_approvals ?? 0],
                  ].map(([label, value]) => (
                    <div key={label} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
                      <div className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</div>
                      <div className="mt-2 text-2xl font-bold text-slate-950">{value}</div>
                    </div>
                  ))}
                </div>
                <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                  MAX can query VendorOps status, renewals, approvals, subscriptions, and monthly cost. MAX cannot approve, provision, cancel, or mutate VendorOps state from chat in this MVP.
                </div>
                <FeatureLocks tier={tier} status={status} />
              </section>
            )}

            {tab === 'accounts' && (
              <DataTable
                empty="No VendorOps accounts have been provisioned yet."
                headers={['Name', 'Category', 'Status', 'Owner', 'Monthly cost', 'Renewal date']}
              >
                {accounts.map(account => (
                  <tr key={account.id}>
                    <td>{account.vendor_name}</td>
                    <td>{account.category || 'Not recorded'}</td>
                    <td>{account.account_status}</td>
                    <td>{account.credential_owner || 'Not recorded'}</td>
                    <td>{currency(account.monthly_cost_usd)}</td>
                    <td>{shortDate(account.renewal_date)}</td>
                  </tr>
                ))}
              </DataTable>
            )}

            {tab === 'approvals' && (
              <section className="grid gap-4">
                <Panel title="Pending approvals">
                  {pendingApprovals.length === 0 ? <Empty text="No pending VendorOps approvals." /> : pendingApprovals.map(approval => (
                    <div key={approval.id} className="flex flex-col gap-3 border-b border-slate-100 py-3 last:border-b-0 md:flex-row md:items-center md:justify-between">
                      <div>
                        <div className="font-bold text-slate-950">{approval.vendor_name}</div>
                        <div className="text-sm text-slate-600">{approval.requested_action}</div>
                        <div className="mt-1 text-xs text-slate-500">{approval.verification_boundary}</div>
                      </div>
                      <div className="flex gap-2">
                        <button onClick={() => decideApproval(approval.id, 'approve')} className="rounded-md bg-emerald-600 px-3 py-2 text-xs font-bold text-white">Approve</button>
                        <button onClick={() => decideApproval(approval.id, 'reject')} className="rounded-md bg-red-600 px-3 py-2 text-xs font-bold text-white">Reject</button>
                      </div>
                    </div>
                  ))}
                </Panel>
                <Panel title="Decision history">
                  {decisionHistory.length === 0 ? <Empty text="No approval decisions recorded." /> : decisionHistory.map(approval => (
                    <div key={approval.id} className="border-b border-slate-100 py-3 text-sm last:border-b-0">
                      <b>{approval.vendor_name}</b> — {approval.status} — {shortDate(approval.approved_at || approval.created_at)}
                    </div>
                  ))}
                </Panel>
              </section>
            )}

            {tab === 'subscriptions' && (
              <section className="grid gap-4">
                <DataTable
                  empty="No VendorOps subscriptions have been tracked yet."
                  headers={['Vendor', 'Plan', 'Status', 'Cadence', 'Monthly cost', 'Renewal date', 'Cancellation state']}
                >
                  {subscriptions.map(subscription => (
                    <tr key={subscription.id}>
                      <td>{subscription.vendor_name}</td>
                      <td>{subscription.plan_name}</td>
                      <td>{subscription.status}</td>
                      <td>{subscription.renewal_cadence || 'Not recorded'}</td>
                      <td>{currency(subscription.monthly_cost_usd)}</td>
                      <td>{shortDate(subscription.renewal_date)}</td>
                      <td>{subscription.cancellation_state}</td>
                    </tr>
                  ))}
                </DataTable>
                <Panel title="Upcoming renewal alerts">
                  {renewalAlerts.length === 0 ? <Empty text="No renewals due in the next 30 days." /> : renewalAlerts.map(item => (
                    <div key={item.id} className="border-b border-slate-100 py-3 text-sm last:border-b-0">
                      <b>{item.vendor_name}</b> renews {shortDate(item.renewal_date)} at {currency(item.monthly_cost_usd)}.
                    </div>
                  ))}
                </Panel>
              </section>
            )}

            {tab === 'audit' && (
              <Panel title="Append-only audit trail">
                {audit.length === 0 ? <Empty text="No VendorOps audit events yet." /> : audit.map(event => (
                  <div key={event.id} className="border-b border-slate-100 py-3 text-sm last:border-b-0">
                    <div className="font-bold text-slate-950">{event.event_type}</div>
                    <div className="text-slate-600">{event.actor} changed {event.entity_type} {event.entity_id}</div>
                    <div className="text-xs text-slate-500">{shortDate(event.created_at)}</div>
                  </div>
                ))}
              </Panel>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function FeatureLocks({ tier, status }: { tier: Tier; status: VendorStatus | null }) {
  const rows = [
    ['Query VendorOps from MAX', true],
    ['Approval workflow', true],
    ['Assisted signup tracking', tier !== 'free'],
    ['Advanced querying and automation policy', tier === 'pro'],
    ['MAX write actions', false],
  ] as const;
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-base font-bold text-slate-950">Activation and locked states</h2>
      <div className="mt-3 grid gap-2 md:grid-cols-2">
        {rows.map(([label, allowed]) => (
          <div key={label} className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2 text-sm">
            <span>{label}</span>
            <span className={`rounded-md px-2 py-1 text-xs font-bold ${allowed ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}`}>
              {allowed ? 'Unlocked' : label === 'MAX write actions' ? 'Blocked by policy' : 'Upgrade required'}
            </span>
          </div>
        ))}
      </div>
      <div className="mt-3 text-xs text-slate-500">
        Credential policy: {status?.credential_policy || 'Loading from VendorOps status.'}
      </div>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-base font-bold text-slate-950">{title}</h2>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function Empty({ text }: { text: string }) {
  return <div className="rounded-md bg-slate-50 p-4 text-sm text-slate-600">{text}</div>;
}

function DataTable({ children, empty, headers }: { children: ReactNode; empty: string; headers: string[] }) {
  const rows = Array.isArray(children) ? children.filter(Boolean) : children ? [children] : [];
  if (!rows.length) return <Empty text={empty} />;
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full text-left text-sm">
        <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
          <tr>
            {headers.map(header => <th key={header} className="px-4 py-3 font-bold">{header}</th>)}
          </tr>
        </thead>
        <tbody className="[&_td]:border-b [&_td]:border-slate-100 [&_td]:px-4 [&_td]:py-3 [&_td]:align-top">
          {children}
        </tbody>
      </table>
    </div>
  );
}
