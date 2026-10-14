'use client';

import { useEffect, useMemo, useState, type CSSProperties, type ReactNode } from 'react';
import {
  Building2, CheckCircle2, ChevronLeft, ChevronRight, Loader2, Save, ShieldAlert,
} from 'lucide-react';
import {
  completeInterview,
  createInvite,
  GUIDE_LINKS,
  loadInterview,
  saveProgress,
  saveSection,
  type CompanyInterview,
  type CompanySectionId,
} from '../../lib/companySetup';
import WhatsAppKeysPanel from './WhatsAppKeysPanel';

const DAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'] as const;

function emptyHours() {
  return Object.fromEntries(DAYS.map((d) => [d, { open: '09:00', close: '17:00', closed: d === 'sun' }]));
}

export default function CompanySetupInterview() {
  const [state, setState] = useState<CompanyInterview | null>(null);
  const [section, setSection] = useState<CompanySectionId>('identity');
  const [form, setForm] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  const [invite, setInvite] = useState({ email: '', name: '', role: 'viewer' });
  const [inviteNote, setInviteNote] = useState('');

  useEffect(() => {
    loadInterview()
      .then((data) => {
        setState(data);
        const current = (data.progress?.current_section || 'identity') as CompanySectionId;
        setSection(current);
        setForm(hydrate(data, current));
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load company setup'))
      .finally(() => setLoading(false));
  }, []);

  const go = (next: CompanySectionId) => {
    setSection(next);
    if (state) setForm(hydrate(state, next));
    saveProgress(next).catch(() => {});
  };

  const persist = async (markComplete: boolean, thenNext = false) => {
    setSaving(true);
    setError('');
    setSaved(false);
    try {
      const next = await saveSection(section, payloadFor(section, form), markComplete);
      setState(next);
      setSaved(true);
      if (thenNext) {
        const nxt = (next.progress.current_section || 'review') as CompanySectionId;
        setSection(nxt);
        setForm(hydrate(next, nxt));
      } else {
        setForm(hydrate(next, section));
      }
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      setError(friendlySetupError(err instanceof Error ? err.message : 'Save failed'));
    } finally {
      setSaving(false);
    }
  };

  const finish = async () => {
    setSaving(true);
    try {
      const next = await completeInterview();
      setState(next);
      setSection('review');
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not complete');
    } finally {
      setSaving(false);
    }
  };

  const onInvite = async () => {
    setInviteNote('');
    try {
      const res = await createInvite(invite.email, invite.role, invite.name);
      setInviteNote(res.sent ? 'Recorded' : 'Invite recorded. Max does not send email.');
      setInvite({ email: '', name: '', role: 'viewer' });
    } catch (err) {
      setInviteNote(err instanceof Error ? err.message : 'Invite failed');
    }
  };

  const pct = useMemo(() => {
    const done = state?.progress.completed_sections?.length || 0;
    const total = Math.max(1, (state?.sections.length || 16) - 1);
    return Math.round((done / total) * 100);
  }, [state]);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center" style={{ background: '#f5f2ed' }}>
        <Loader2 className="animate-spin text-[#b8960c]" />
      </div>
    );
  }

  if (error && !state) {
    return (
      <div className="flex-1 flex items-center justify-center" style={{ background: '#f5f2ed', padding: 24 }}>
        <div style={{ maxWidth: 480, background: '#fff', borderRadius: 16, padding: 24, border: '1px solid #e8e4de' }}>
          <ShieldAlert className="text-[#b8960c] mb-3" />
          <h1 style={{ margin: '0 0 8px', fontSize: 20 }}>Company setup</h1>
          <p style={{ color: '#666', fontSize: 13 }}>{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-hidden" style={{ background: '#f5f2ed', display: 'flex' }}>
      <aside style={{ width: 260, borderRight: '1px solid #e8e4de', background: '#fff', overflowY: 'auto', padding: '20px 14px' }}>
        <div style={{ fontSize: 11, letterSpacing: 1.4, textTransform: 'uppercase', color: '#b8960c', fontWeight: 700 }}>Max Studio</div>
        <h2 style={{ margin: '4px 0 14px', fontSize: 18 }}>Company setup</h2>
        <div style={{ height: 6, background: '#eee8dc', borderRadius: 99, marginBottom: 16 }}>
          <div style={{ width: `${pct}%`, height: 6, background: '#b8960c', borderRadius: 99 }} />
        </div>
        {(state?.sections || []).map((row) => (
          <button
            key={row.id}
            onClick={() => go(row.id)}
            style={{
              display: 'block',
              width: '100%',
              textAlign: 'left',
              padding: '8px 10px',
              marginBottom: 4,
              border: 'none',
              borderRadius: 8,
              background: section === row.id ? '#fdf8eb' : 'transparent',
              color: section === row.id ? '#1a1a1a' : '#666',
              fontWeight: section === row.id ? 700 : 500,
              fontSize: 12,
              cursor: 'pointer',
            }}
          >
            <span style={{ color: row.done ? '#16a34a' : '#bbb', marginRight: 6 }}>{row.done ? '●' : '○'}</span>
            {row.title}
          </button>
        ))}
      </aside>

      <main style={{ flex: 1, overflowY: 'auto', padding: '28px 32px' }}>
        <div style={{ maxWidth: 760 }}>
          <div className="flex items-center gap-3 mb-5">
            <div className="w-10 h-10 rounded-xl bg-[#fdf8eb] flex items-center justify-center">
              <Building2 size={20} className="text-[#b8960c]" />
            </div>
            <div>
              <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>
                {state?.sections.find((s) => s.id === section)?.title}
              </h1>
              <p style={{ margin: 0, fontSize: 12, color: '#888' }}>
                {state?.sections.find((s) => s.id === section)?.summary}
              </p>
            </div>
          </div>

          {state?.status && (
            <div style={{ marginBottom: 16, padding: '10px 12px', background: state.status.configured ? '#f0fdf4' : '#fffbeb', borderRadius: 10, fontSize: 12 }}>
              {state.status.configured
                ? `Configured — ${state.status.default_brand || state.status.legal_name}`
                : `Not configured yet${state.status.missing?.length ? `: missing ${state.status.missing.join(', ')}` : ''}`}
            </div>
          )}

          {section === 'identity' && <IdentityForm form={form} setForm={setForm} defaults={state?.defaults?.brands} />}
          {section === 'contact' && <ContactForm form={form} setForm={setForm} />}
          {section === 'tax' && <TaxForm form={form} setForm={setForm} />}
          {section === 'payments' && <PaymentsForm form={form} setForm={setForm} brands={state?.data?.brands} />}
          {section === 'numbering' && <NumberingForm form={form} setForm={setForm} />}
          {section === 'services' && <ServicesForm form={form} setForm={setForm} />}
          {section === 'measurements' && <MeasurementsForm form={form} setForm={setForm} />}
          {section === 'fabric' && <FabricForm form={form} setForm={setForm} />}
          {section === 'team' && (
            <TeamForm form={form} setForm={setForm} invite={invite} setInvite={setInvite} onInvite={onInvite} note={inviteNote} />
          )}
          {section === 'channels' && (
            <div style={{ display: 'grid', gap: 16 }}>
              <ChannelsForm form={form} setForm={setForm} />
              <WhatsAppKeysPanel />
            </div>
          )}
          {section === 'calendar' && <CalendarForm form={form} setForm={setForm} />}
          {section === 'suppliers' && <ListForm form={form} setForm={setForm} field="suppliers" labels={['name', 'phone', 'notes']} />}
          {section === 'insurance' && <InsuranceForm form={form} setForm={setForm} />}
          {section === 'branding' && <BrandingForm form={form} setForm={setForm} />}
          {section === 'life' && <LifeForm form={form} setForm={setForm} />}
          {section === 'review' && <ReviewPage state={state} />}

          {error && <div style={{ marginTop: 12, color: '#b91c1c', fontSize: 12 }}>{error}</div>}

          <div style={{ display: 'flex', gap: 8, marginTop: 22, flexWrap: 'wrap' }}>
            {section !== 'identity' && (
              <button type="button" onClick={() => go(prevSection(section, state))} style={ghostBtn}>
                <ChevronLeft size={14} /> Back
              </button>
            )}
            {section !== 'review' && (
              <>
                <button type="button" onClick={() => persist(false)} disabled={saving} style={ghostBtn}>
                  <Save size={14} /> {saving ? 'Saving…' : saved ? 'Saved' : 'Save draft'}
                </button>
                <button type="button" onClick={() => persist(true, true)} disabled={saving} style={goldBtn}>
                  {saving ? <Loader2 size={14} className="animate-spin" /> : saved ? <CheckCircle2 size={14} /> : <ChevronRight size={14} />}
                  Save and continue
                </button>
              </>
            )}
            {section === 'review' && (
              <button type="button" onClick={finish} disabled={saving} style={goldBtn}>
                {saving ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
                Confirm setup
              </button>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

function hydrate(state: CompanyInterview, section: CompanySectionId): Record<string, any> {
  const data = state.data || {};
  if (section === 'identity') {
    const identity = data.identity || {};
    return {
      legal_name: identity.legal_name || data.legal_name || '',
      dba: identity.dba || data.dba || data.business_name || '',
      owner_name: identity.owner_name || data.owner_name || '',
      tagline: identity.tagline || data.business_tagline || '',
      brands: data.brands?.length ? data.brands : state.defaults?.brands || [
        { id: 'empire-workroom', name: 'Empire Workroom', dba: 'Empire Workroom', is_default: true },
        { id: 'nelmas-workroom', name: "Nelma's Workroom", dba: "Nelma's Workroom", is_default: false },
      ],
    };
  }
  if (section === 'contact') {
    const c = data.contact || {};
    return {
      address: c.address || data.business_address || '',
      phone: c.phone || data.business_phone || '',
      email: c.email || data.business_email || '',
      website: c.website || data.business_website || '',
      timezone: c.timezone || data.timezone || 'America/New_York',
    };
  }
  if (section === 'tax') {
    const t = data.tax || {};
    return {
      ein: t.ein || '',
      rates: t.rates?.length ? t.rates : [{ state: 'MD', county: 'Prince George\'s', rate: 0.06 }],
      taxable_items: (t.taxable_items || ['labor', 'fabric', 'install']).join(', '),
    };
  }
  if (section === 'payments') {
    const p = data.payments || {};
    return {
      deposit_percent: p.deposit_percent ?? 50,
      deposit_terms: p.deposit_terms || '50% deposit to start. Balance due before install.',
      processors: p.processors?.length ? p.processors : [{ brand: 'Empire Workroom', processor: 'stripe_payment_links' }],
    };
  }
  if (section === 'numbering') {
    const n = data.numbering || {};
    return {
      quote_prefix: n.quote_prefix || 'EST',
      quote_start: n.quote_start || 1,
      invoice_prefix: n.invoice_prefix || 'INV',
      invoice_start: n.invoice_start || 1,
    };
  }
  if (section === 'services') {
    const s = data.services_section || {};
    return {
      catalog_text: (s.catalog || data.services_catalog || []).map((row: any) =>
        typeof row === 'string' ? row : `${row.name || ''}|${row.rate || ''}|${row.unit || 'each'}`,
      ).join('\n') || 'Roman shade|65|window\nPinch pleat drapery|85|width',
      labor_rate: s.labor_rate ?? data.labor_rate ?? 65,
    };
  }
  if (section === 'measurements') {
    const m = data.measurements || {};
    return { fractions_only: m.fractions_only !== false, notes: m.notes || 'Print inches as fractions only. Never decimals on shop or client docs.' };
  }
  if (section === 'fabric') {
    const f = data.fabric || {};
    return {
      code_format: f.code_format || data.fabric_code_format || 'V###-Color',
      next_number: f.next_number ?? data.fabric_next_number ?? 1,
      allowance_text: (f.allowance_by_foam_thickness || [
        { foam_thickness_in: 2, allowance_in: 5, status: 'confirm_with_rafael' },
      ]).map((row: any) => `${row.foam_thickness_in}|${row.allowance_in}|${row.status || 'confirm_with_rafael'}`).join('\n'),
    };
  }
  if (section === 'team') {
    return { users_text: (data.team?.users || []).map((u: any) => `${u.name || ''}|${u.email || ''}|${u.role || 'viewer'}`).join('\n') };
  }
  if (section === 'channels') {
    const c = data.channels || {};
    const phones = c.founder_phones || data.founder_phones || [];
    return {
      whatsapp: c.whatsapp !== false,
      email: c.email !== false,
      phone: c.phone !== false,
      founder_phones: Array.isArray(phones) ? phones.join('\n') : String(phones || ''),
    };
  }
  if (section === 'calendar') {
    return { hours: data.calendar?.hours || emptyHours(), notes: data.calendar?.notes || '' };
  }
  if (section === 'suppliers') {
    return { suppliers: data.suppliers || [] };
  }
  if (section === 'insurance') {
    const i = data.insurance || {};
    return {
      coi_required: i.coi_required !== false,
      coverage: i.coverage || 'General liability',
      min_amount: i.min_amount || '1000000',
      notes: i.notes || '',
    };
  }
  if (section === 'branding') {
    const b = data.branding || {};
    return {
      logo_url: b.logo_url || '',
      primary: b.primary || '#b8960c',
      ink: b.ink || '#20241f',
      paper: b.paper || '#f7f3ea',
      letterhead: b.letterhead || 'Empire Workroom letterhead — gold rule, cream paper.',
    };
  }
  if (section === 'life') {
    const l = data.life || {};
    return {
      areas_text: (l.areas || [
        { name: 'Workroom', privacy: 'workroom' },
        { name: 'Family', privacy: 'shared_family' },
        { name: 'Personal', privacy: 'private' },
      ]).map((a: any) => `${a.name}|${a.privacy}`).join('\n'),
      workroom_sees_family: false,
      family_sees_workroom: false,
      max_covers_whole_life: l.max_covers_whole_life !== false,
    };
  }
  return {};
}

function payloadFor(section: CompanySectionId, form: Record<string, any>): Record<string, unknown> {
  if (section === 'tax') {
    return {
      ein: form.ein,
      rates: form.rates,
      taxable_items: String(form.taxable_items || '').split(',').map((s: string) => s.trim()).filter(Boolean),
    };
  }
  if (section === 'services') {
    const catalog = String(form.catalog_text || '').split('\n').map((line) => {
      const [name, rate, unit] = line.split('|').map((s) => s.trim());
      if (!name) return null;
      return { name, rate: Number(rate) || 0, unit: unit || 'each' };
    }).filter(Boolean);
    return {
      catalog,
      labor_rate: Number(form.labor_rate) || 0,
      rate_cards: { workroom: { labor_rate: Number(form.labor_rate) || 0 } },
    };
  }
  if (section === 'fabric') {
    const allowance = String(form.allowance_text || '').split('\n').map((line) => {
      const [foam, extra, status] = line.split('|').map((s) => s.trim());
      if (!foam) return null;
      return { foam_thickness_in: Number(foam), allowance_in: Number(extra), status: status || 'confirm_with_rafael' };
    }).filter(Boolean);
    return { code_format: form.code_format || 'V###-Color', next_number: Number(form.next_number) || 1, allowance_by_foam_thickness: allowance };
  }
  if (section === 'team') {
    const users = String(form.users_text || '').split('\n').map((line) => {
      const [name, email, role] = line.split('|').map((s) => s.trim());
      if (!name && !email) return null;
      return { name, email, role: role || 'viewer' };
    }).filter(Boolean);
    return { users };
  }
  if (section === 'channels') {
    return {
      whatsapp: !!form.whatsapp,
      email: !!form.email,
      phone: !!form.phone,
      founder_phones: String(form.founder_phones || '').split(/[,\n]/).map((s) => s.trim()).filter(Boolean),
    };
  }
  if (section === 'life') {
    const areas = String(form.areas_text || '').split('\n').map((line) => {
      const [name, privacy] = line.split('|').map((s) => s.trim());
      if (!name) return null;
      return { name, privacy: privacy || 'private' };
    }).filter(Boolean);
    return {
      areas,
      privacy_boundaries: {
        workroom_sees_family: false,
        family_sees_workroom: false,
        max_covers_whole_life: !!form.max_covers_whole_life,
      },
      max_covers_whole_life: !!form.max_covers_whole_life,
    };
  }
  if (section === 'branding') {
    return { logo_url: form.logo_url, primary: form.primary, ink: form.ink, paper: form.paper, letterhead: form.letterhead };
  }
  return form;
}

function prevSection(current: CompanySectionId, state: CompanyInterview | null): CompanySectionId {
  const ids = (state?.sections || []).map((s) => s.id);
  const idx = ids.indexOf(current);
  return (ids[Math.max(0, idx - 1)] || 'identity') as CompanySectionId;
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label style={{ display: 'grid', gap: 4, fontSize: 12, marginBottom: 10 }}>
      <span style={{ fontWeight: 600, color: '#333' }}>{label}</span>
      {children}
    </label>
  );
}

const input: CSSProperties = {
  minHeight: 38,
  border: '1px solid #e5e2dc',
  borderRadius: 8,
  padding: '0 10px',
  fontSize: 13,
  background: '#fff',
};

const goldBtn: CSSProperties = {
  minHeight: 40,
  padding: '0 16px',
  border: 'none',
  borderRadius: 8,
  background: '#b8960c',
  color: '#fff',
  fontWeight: 700,
  cursor: 'pointer',
  display: 'inline-flex',
  alignItems: 'center',
  gap: 8,
};

const ghostBtn: CSSProperties = {
  ...goldBtn,
  background: '#fff',
  color: '#333',
  border: '1px solid #e5e2dc',
};

function IdentityForm({ form, setForm, defaults }: any) {
  const brands = form.brands?.length ? form.brands : defaults || [];
  return (
    <div>
      <Field label="Legal name">
        <input style={input} value={form.legal_name || ''} onChange={(e) => setForm({ ...form, legal_name: e.target.value })} />
      </Field>
      <Field label="DBA">
        <input style={input} value={form.dba || ''} onChange={(e) => setForm({ ...form, dba: e.target.value })} />
      </Field>
      <Field label="Owner">
        <input style={input} value={form.owner_name || ''} onChange={(e) => setForm({ ...form, owner_name: e.target.value })} />
      </Field>
      <Field label="Tagline">
        <input style={input} value={form.tagline || ''} onChange={(e) => setForm({ ...form, tagline: e.target.value })} />
      </Field>
      <div style={{ fontSize: 12, fontWeight: 700, margin: '12px 0 8px' }}>Brands under this owner</div>
      {brands.map((brand: any, i: number) => (
        <div key={brand.id || i} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: 8, marginBottom: 8 }}>
          <input style={input} value={brand.name || ''} placeholder="Brand name" onChange={(e) => {
            const next = [...brands];
            next[i] = { ...brand, name: e.target.value };
            setForm({ ...form, brands: next });
          }} />
          <input style={input} value={brand.dba || ''} placeholder="DBA" onChange={(e) => {
            const next = [...brands];
            next[i] = { ...brand, dba: e.target.value };
            setForm({ ...form, brands: next });
          }} />
          <label style={{ fontSize: 11, display: 'flex', alignItems: 'center', gap: 4 }}>
            <input type="checkbox" checked={!!brand.is_default} onChange={(e) => {
              const next = brands.map((b: any, j: number) => ({ ...b, is_default: j === i ? e.target.checked : false }));
              setForm({ ...form, brands: next });
            }} /> Default
          </label>
        </div>
      ))}
      <button type="button" style={ghostBtn} onClick={() => setForm({ ...form, brands: [...brands, { id: `brand-${brands.length + 1}`, name: '', dba: '', is_default: false }] })}>
        Add brand
      </button>
    </div>
  );
}

function ContactForm({ form, setForm }: any) {
  return (
    <div>
      <Field label="Address for documents"><input style={input} value={form.address || ''} onChange={(e) => setForm({ ...form, address: e.target.value })} /></Field>
      <Field label="Phone"><input style={input} value={form.phone || ''} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></Field>
      <Field label="Email"><input style={input} value={form.email || ''} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
      <Field label="Website"><input style={input} value={form.website || ''} onChange={(e) => setForm({ ...form, website: e.target.value })} /></Field>
      <Field label="Timezone"><input style={input} value={form.timezone || ''} onChange={(e) => setForm({ ...form, timezone: e.target.value })} /></Field>
    </div>
  );
}

function TaxForm({ form, setForm }: any) {
  const rates = form.rates || [];
  return (
    <div>
      <Field label="EIN"><input style={input} value={form.ein || ''} onChange={(e) => setForm({ ...form, ein: e.target.value })} /></Field>
      <Field label="Taxable items (comma-separated)"><input style={input} value={form.taxable_items || ''} onChange={(e) => setForm({ ...form, taxable_items: e.target.value })} /></Field>
      <div style={{ fontSize: 12, fontWeight: 700, margin: '8px 0' }}>Sales tax by state / county</div>
      {rates.map((row: any, i: number) => (
        <div key={i} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 100px', gap: 8, marginBottom: 8 }}>
          <input style={input} value={row.state || ''} placeholder="State" onChange={(e) => {
            const next = [...rates]; next[i] = { ...row, state: e.target.value }; setForm({ ...form, rates: next });
          }} />
          <input style={input} value={row.county || ''} placeholder="County" onChange={(e) => {
            const next = [...rates]; next[i] = { ...row, county: e.target.value }; setForm({ ...form, rates: next });
          }} />
          <input style={input} type="number" step="0.001" value={row.rate ?? ''} placeholder="0.06" onChange={(e) => {
            const next = [...rates]; next[i] = { ...row, rate: Number(e.target.value) }; setForm({ ...form, rates: next });
          }} />
        </div>
      ))}
      <button type="button" style={ghostBtn} onClick={() => setForm({ ...form, rates: [...rates, { state: '', county: '', rate: 0 }] })}>Add rate</button>
    </div>
  );
}

function PaymentsForm({ form, setForm }: any) {
  const processors = form.processors || [];
  return (
    <div>
      <Field label="Deposit percent"><input style={input} type="number" value={form.deposit_percent ?? 50} onChange={(e) => setForm({ ...form, deposit_percent: Number(e.target.value) })} /></Field>
      <Field label="Deposit terms"><textarea style={{ ...input, minHeight: 70, padding: 8 }} value={form.deposit_terms || ''} onChange={(e) => setForm({ ...form, deposit_terms: e.target.value })} /></Field>
      {processors.map((row: any, i: number) => (
        <div key={i} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 8 }}>
          <input style={input} value={row.brand || ''} placeholder="Brand" onChange={(e) => {
            const next = [...processors]; next[i] = { ...row, brand: e.target.value }; setForm({ ...form, processors: next });
          }} />
          <select style={input} value={row.processor || 'stripe_payment_links'} onChange={(e) => {
            const next = [...processors]; next[i] = { ...row, processor: e.target.value }; setForm({ ...form, processors: next });
          }}>
            <option value="stripe_payment_links">Stripe Payment Links</option>
            <option value="square">Square</option>
          </select>
        </div>
      ))}
      <button type="button" style={ghostBtn} onClick={() => setForm({ ...form, processors: [...processors, { brand: '', processor: 'stripe_payment_links' }] })}>Add processor</button>
    </div>
  );
}

function NumberingForm({ form, setForm }: any) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
      <Field label="Quote prefix"><input style={input} value={form.quote_prefix || ''} onChange={(e) => setForm({ ...form, quote_prefix: e.target.value })} /></Field>
      <Field label="Quote start"><input style={input} type="number" value={form.quote_start ?? 1} onChange={(e) => setForm({ ...form, quote_start: Number(e.target.value) })} /></Field>
      <Field label="Invoice prefix"><input style={input} value={form.invoice_prefix || ''} onChange={(e) => setForm({ ...form, invoice_prefix: e.target.value })} /></Field>
      <Field label="Invoice start"><input style={input} type="number" value={form.invoice_start ?? 1} onChange={(e) => setForm({ ...form, invoice_start: Number(e.target.value) })} /></Field>
    </div>
  );
}

function ServicesForm({ form, setForm }: any) {
  return (
    <div>
      <Field label="Labor rate (feeds Pricing Studio)">
        <input style={input} type="number" value={form.labor_rate ?? 65} onChange={(e) => setForm({ ...form, labor_rate: Number(e.target.value) })} />
      </Field>
      <Field label="Catalog — name|rate|unit, one per line">
        <textarea style={{ ...input, minHeight: 140, padding: 8, fontFamily: 'ui-monospace, monospace' }} value={form.catalog_text || ''} onChange={(e) => setForm({ ...form, catalog_text: e.target.value })} />
      </Field>
    </div>
  );
}

function MeasurementsForm({ form, setForm }: any) {
  return (
    <div>
      <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 13, marginBottom: 10 }}>
        <input type="checkbox" checked={form.fractions_only !== false} onChange={(e) => setForm({ ...form, fractions_only: e.target.checked })} />
        Fractions only — print 1 1/2, never 1.5, on shop or client docs
      </label>
      <Field label="Notes"><textarea style={{ ...input, minHeight: 80, padding: 8 }} value={form.notes || ''} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></Field>
    </div>
  );
}

function FabricForm({ form, setForm }: any) {
  return (
    <div>
      <Field label="Fabric code format"><input style={input} value={form.code_format || 'V###-Color'} onChange={(e) => setForm({ ...form, code_format: e.target.value })} /></Field>
      <Field label="Next number"><input style={input} type="number" value={form.next_number ?? 1} onChange={(e) => setForm({ ...form, next_number: Number(e.target.value) })} /></Field>
      <Field label="Allowance by foam thickness — foam|per-side inches|status (sixteenth fractions)">
        <textarea style={{ ...input, minHeight: 140, padding: 8, fontFamily: 'ui-monospace, monospace' }} value={form.allowance_text || ''} onChange={(e) => setForm({ ...form, allowance_text: e.target.value })} />
      </Field>
      <p style={{ fontSize: 12, color: '#666' }}>
        Allowance is per side (fabric = wood + 2 × allowance). Use sixteenth fractions only (1, 1 1/2, 2).
        Rows already in Rafael&apos;s table stay. New thicknesses stay unconfirmed until he approves them.
      </p>
    </div>
  );
}

function TeamForm({ form, setForm, invite, setInvite, onInvite, note }: any) {
  return (
    <div>
      <Field label="Users — name|email|role">
        <textarea style={{ ...input, minHeight: 100, padding: 8 }} value={form.users_text || ''} onChange={(e) => setForm({ ...form, users_text: e.target.value })} />
      </Field>
      <div style={{ background: '#faf9f7', borderRadius: 10, padding: 12 }}>
        <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 8 }}>Invite (recorded only — no email is sent)</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 140px', gap: 8 }}>
          <input style={input} placeholder="Name" value={invite.name} onChange={(e) => setInvite({ ...invite, name: e.target.value })} />
          <input style={input} placeholder="Email" value={invite.email} onChange={(e) => setInvite({ ...invite, email: e.target.value })} />
          <select style={input} value={invite.role} onChange={(e) => setInvite({ ...invite, role: e.target.value })}>
            {['viewer', 'estimator', 'seamstress', 'installer', 'admin'].map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>
        <button type="button" style={{ ...ghostBtn, marginTop: 8 }} onClick={onInvite}>Record invite</button>
        {note && <div style={{ fontSize: 12, marginTop: 6, color: '#666' }}>{note}</div>}
      </div>
    </div>
  );
}

function ChannelsForm({ form, setForm }: any) {
  return (
    <div>
      {(['whatsapp', 'email', 'phone'] as const).map((ch) => (
        <label key={ch} style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 13, marginBottom: 8 }}>
          <input type="checkbox" checked={!!form[ch]} onChange={(e) => setForm({ ...form, [ch]: e.target.checked })} />
          {ch}
        </label>
      ))}
      <Field label="Founder numbers (this edition)">
        <textarea style={{ ...input, minHeight: 80, padding: 8 }} value={form.founder_phones || ''} onChange={(e) => setForm({ ...form, founder_phones: e.target.value })} />
      </Field>
    </div>
  );
}

function CalendarForm({ form, setForm }: any) {
  const hours = form.hours || emptyHours();
  return (
    <div>
      {DAYS.map((day) => (
        <div key={day} style={{ display: 'grid', gridTemplateColumns: '70px 1fr 1fr 80px', gap: 8, marginBottom: 8, alignItems: 'center' }}>
          <span style={{ fontSize: 12, fontWeight: 600, textTransform: 'capitalize' }}>{day}</span>
          <input style={input} type="time" value={hours[day]?.open || '09:00'} onChange={(e) => setForm({ ...form, hours: { ...hours, [day]: { ...hours[day], open: e.target.value } } })} />
          <input style={input} type="time" value={hours[day]?.close || '17:00'} onChange={(e) => setForm({ ...form, hours: { ...hours, [day]: { ...hours[day], close: e.target.value } } })} />
          <label style={{ fontSize: 11 }}><input type="checkbox" checked={!!hours[day]?.closed} onChange={(e) => setForm({ ...form, hours: { ...hours, [day]: { ...hours[day], closed: e.target.checked } } })} /> Closed</label>
        </div>
      ))}
      <Field label="Notes"><input style={input} value={form.notes || ''} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></Field>
    </div>
  );
}

function ListForm({ form, setForm, field, labels }: { form: any; setForm: any; field: string; labels: string[] }) {
  const rows = form[field] || [];
  return (
    <div>
      {rows.map((row: any, i: number) => (
        <div key={i} style={{ display: 'grid', gridTemplateColumns: `repeat(${labels.length}, 1fr)`, gap: 8, marginBottom: 8 }}>
          {labels.map((key) => (
            <input key={key} style={input} placeholder={key} value={row[key] || ''} onChange={(e) => {
              const next = [...rows]; next[i] = { ...row, [key]: e.target.value }; setForm({ ...form, [field]: next });
            }} />
          ))}
        </div>
      ))}
      <button type="button" style={ghostBtn} onClick={() => setForm({ ...form, [field]: [...rows, Object.fromEntries(labels.map((k) => [k, '']))] })}>Add</button>
    </div>
  );
}

function InsuranceForm({ form, setForm }: any) {
  return (
    <div>
      <label style={{ display: 'flex', gap: 8, fontSize: 13, marginBottom: 10 }}>
        <input type="checkbox" checked={form.coi_required !== false} onChange={(e) => setForm({ ...form, coi_required: e.target.checked })} />
        COI required on jobs
      </label>
      <Field label="Coverage"><input style={input} value={form.coverage || ''} onChange={(e) => setForm({ ...form, coverage: e.target.value })} /></Field>
      <Field label="Minimum amount"><input style={input} value={form.min_amount || ''} onChange={(e) => setForm({ ...form, min_amount: e.target.value })} /></Field>
      <Field label="Notes"><textarea style={{ ...input, minHeight: 70, padding: 8 }} value={form.notes || ''} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></Field>
    </div>
  );
}

function BrandingForm({ form, setForm }: any) {
  return (
    <div>
      <Field label="Logo URL"><input style={input} value={form.logo_url || ''} onChange={(e) => setForm({ ...form, logo_url: e.target.value })} /></Field>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
        <Field label="Gold / primary"><input style={input} value={form.primary || ''} onChange={(e) => setForm({ ...form, primary: e.target.value })} /></Field>
        <Field label="Ink"><input style={input} value={form.ink || ''} onChange={(e) => setForm({ ...form, ink: e.target.value })} /></Field>
        <Field label="Paper"><input style={input} value={form.paper || ''} onChange={(e) => setForm({ ...form, paper: e.target.value })} /></Field>
      </div>
      <Field label="PDF letterhead notes"><textarea style={{ ...input, minHeight: 80, padding: 8 }} value={form.letterhead || ''} onChange={(e) => setForm({ ...form, letterhead: e.target.value })} /></Field>
    </div>
  );
}

function LifeForm({ form, setForm }: any) {
  return (
    <div>
      <p style={{ fontSize: 13, color: '#444', marginTop: 0 }}>Max covers whole life, not only the Workroom. Family data stays out of Workroom files.</p>
      <Field label="Life areas — name|privacy (private, shared_family, workroom)">
        <textarea style={{ ...input, minHeight: 100, padding: 8 }} value={form.areas_text || ''} onChange={(e) => setForm({ ...form, areas_text: e.target.value })} />
      </Field>
      <label style={{ display: 'flex', gap: 8, fontSize: 13 }}>
        <input type="checkbox" checked={form.max_covers_whole_life !== false} onChange={(e) => setForm({ ...form, max_covers_whole_life: e.target.checked })} />
        Max covers whole life
      </label>
      <p style={{ fontSize: 12, color: '#888' }}>Workroom never sees family. Family editions never see Workroom quotes or CRM.</p>
    </div>
  );
}

function ReviewPage({ state }: { state: CompanyInterview | null }) {
  const data = state?.data || {};
  const rows = [
    ['Legal / DBA', `${data.legal_name || '—'} / ${data.dba || data.business_name || '—'}`],
    ['Brands', (data.brands || []).map((b: any) => b.name).join(', ') || '—'],
    ['Address', data.business_address || data.contact?.address || '—'],
    ['Phone', data.business_phone || data.contact?.phone || '—'],
    ['Email', data.business_email || data.contact?.email || '—'],
    ['EIN', data.tax?.ein || '—'],
    ['Deposit', data.payments?.deposit_percent != null ? `${data.payments.deposit_percent}%` : '—'],
    ['Quote numbers', `${data.numbering?.quote_prefix || 'EST'}-${data.numbering?.quote_start || 1}`],
    ['Fabric codes', data.fabric?.code_format || data.fabric_code_format || 'V###-Color'],
    ['Fractions only', data.measurements?.fractions_only === false ? 'no' : 'yes'],
    ['Life areas', (data.life?.areas || []).map((a: any) => a.name).join(', ') || '—'],
  ];
  return (
    <div>
      <div style={{ background: '#fff', border: '1px solid #e8e4de', borderRadius: 12, overflow: 'hidden' }}>
        {rows.map(([k, v]) => (
          <div key={k} style={{ display: 'flex', justifyContent: 'space-between', gap: 16, padding: '10px 14px', borderBottom: '1px solid #f3f0ea', fontSize: 13 }}>
            <span style={{ color: '#888' }}>{k}</span>
            <span style={{ fontWeight: 600, textAlign: 'right' }}>{String(v)}</span>
          </div>
        ))}
      </div>
      <div style={{ marginTop: 16, fontSize: 12, color: '#666' }}>Open related screens:</div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 8 }}>
        {GUIDE_LINKS.map((link) => (
          <a key={link.id} href={link.href} style={{ ...ghostBtn, textDecoration: 'none' }}>{link.label}</a>
        ))}
        <a href="/help/company" style={{ ...ghostBtn, textDecoration: 'none' }}>English guide</a>
        <a href="/ayuda/empresa" style={{ ...ghostBtn, textDecoration: 'none' }}>Guía en español</a>
      </div>
    </div>
  );
}

function friendlySetupError(raw: string): string {
  const t = (raw || '').toLowerCase();
  if (t.includes('unknown key')) {
    return 'That field is not part of this step. Services cannot change founder phones or other identity keys.';
  }
  if (t.includes('founder session')) return 'Sign in as the founder to save company setup.';
  if (t.includes('e.164')) return 'Phone numbers must look like +17035551212.';
  return raw || 'Could not save this step.';
}
