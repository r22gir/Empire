'use client';

import { useEffect, useMemo, useState } from 'react';
import type { CSSProperties } from 'react';
import { API } from '../../lib/api';

const STUDIO = 'https://studio.empirebox.store';
const STUDIO_SESSION = '__studio_access_session__';
const TAGS = ['visual/theme', 'bug', 'missing feature', 'keep', 'remove', 'priority 1', 'priority 2', 'priority 3'];

const CATEGORY_DEFS = [
  ['core', 'Core & Max', 'Owner shell, Max, channels and shared platform services.'],
  ['sales', 'Sales & CRM', 'Leads, customers, intake, jobs and vendor relationships.'],
  ['money', 'Quotes, Estimates, Invoices & Payments', 'Revenue workflow from quote through payment and portal.'],
  ['design', 'Design & Production', 'Workroom, drawings, vision, fabrication and shipping.'],
  ['growth', 'Marketing & Commerce', 'Social, storefronts, marketplaces and listing operations.'],
  ['comms', 'Communication & Support', 'Inbox, channels, support and cross-channel continuity.'],
  ['docs', 'Documents & Files', 'Archive, Drive, PDFs, reports and transcripts.'],
  ['industry', 'Industry Packs', 'Workroom, ConstructionForge, AMP, Cibernettic and vertical packs.'],
  ['admin', 'Admin, Usage & Platform', 'Edition gates, caps, health, recovery and developer controls.'],
] as const;

type CategoryId = typeof CATEGORY_DEFS[number][0];
type Module = { id: string; category: CategoryId; name: string; description: string; status: 'live' | 'partial' | 'stub'; href?: string };
type AppliesTo = { all?: boolean; modules?: string[]; categories?: string[] };
type Comment = { id: string; module_id: string; category: string; scope: string; tags: string[]; applies_to: AppliesTo; text: string; status: 'open' | 'done'; created_at: string };

const M = (id: string, category: CategoryId, name: string, description: string, status: Module['status'], path?: string): Module => ({ id, category, name, description, status, href: path ? `${STUDIO}${path}` : undefined });

const MODULES: Module[] = [
  M('command-center', 'core', 'Command Center shell and edition-aware navigation', 'One operator shell for chat, products, desks, files, tickets, voice and settings.', 'partial', '/'),
  M('max-chat', 'core', 'Max text chat and Desks', 'Max conversation, desk routing and daily operator actions.', 'live', '/?product=owner'),
  M('max-tools', 'core', 'Max capability and tool registry', 'Image, drawing, quote, PDF, fabric, portal, finance, production and report skills.', 'partial', '/?product=owner'),
  M('voice', 'core', 'Voice, STT/TTS and voice-to-document', 'Voice capture, transcription, speech output and structured drafts.', 'partial', '/?screen=voice'),
  M('simli', 'core', 'Simli avatar / live face', 'Edition-specific face selection, sessions and usage meter.', 'partial', '/?screen=presentation'),
  M('memory', 'core', 'Conversation history, memory bank and continuity', 'Web, Telegram and cross-channel history, search, pins and backups.', 'live', '/?screen=memory-bank'),
  M('auth', 'core', 'Authentication, roles, guardrails and approval gates', 'Sessions, family-edition access, rate limits and approval-before-send/publish.', 'live'),
  M('ops', 'core', 'Notifications, tasks, orchestration and Daily Summary', 'Action items, task queue, scheduled loops and operational summaries.', 'live', '/?screen=dashboard'),
  M('reports', 'core', 'Web research, reports and presentation generation', 'Research-backed reports, verified charts and PDF presentation output.', 'live', '/?screen=report'),
  M('code-mode', 'core', 'Code mode, Git and developer controls', 'Founder code tasks, Git reads, bounded self-heal and developer panels.', 'partial', '/?screen=dev'),

  M('crm', 'sales', 'ForgeCRM and Contacts', 'Shared customer/contact records, types, tags, search and detail.', 'live', '/?product=crm'),
  M('leadforge', 'sales', 'LeadForge', 'Lead pipeline, prospecting, campaigns, follow-ups and conversion reports.', 'live', '/?product=lead'),
  M('capture', 'sales', 'Workroom manual capture and public lead intake', 'Capture leads into CRM and LeadForge without automatically sending mail.', 'live', '/workroom/capture'),
  M('intake', 'sales', 'Customer/project intake portal (LuxeForge intake)', 'Customer projects, measurements, photos, scans, messages and quote conversion.', 'live', '/intake'),
  M('business-profile', 'sales', 'Business Profile, onboarding and Nueva empresa', 'Business setup, profile, registry and EasyStep-style company interview.', 'live', '/?screen=business-profile'),
  M('jobs', 'sales', 'Scheduling, jobs and lifecycle', 'Unified jobs, stages, calendars, work orders and quote-to-job lifecycle.', 'live', '/?screen=jobs'),
  M('contractor', 'sales', 'ContractorForge', 'Contractor/installer contacts, assignments and desk workflows.', 'partial', '/?product=contractor'),
  M('vendorops', 'sales', 'VendorOps', 'Vendor accounts, approvals, renewal alerts, audit and tiered activation.', 'partial', '/?product=vendorops'),

  M('quotes', 'money', 'Quotes and Quote Engine', 'Structured, quick, tiered and photo-assisted quotes with verification.', 'live', '/?screen=quote'),
  M('estimates', 'money', 'Estimates and estimate PDFs', 'Client-safe estimates, line items, totals and PDF output.', 'live', '/?screen=quote'),
  M('pricing', 'money', 'Pricing Studio', 'Pricing tables, dimensions, rate cards, market ranges and recalculation.', 'live', '/?screen=pricing-studio'),
  M('finance', 'money', 'Finance, invoices, collections and profitability', 'P&L, invoices, statements, AR aging, expenses and job profitability.', 'live', '/workroom/finance'),
  M('stripe', 'money', 'EmpirePay / Stripe', 'Checkout, invoice links, PaymentIntents, subscriptions and signed webhooks.', 'partial', '/?product=pay'),
  M('crypto', 'money', 'Crypto payments', 'Invoice/order addresses, QR/status, confirmation and ledger.', 'partial', '/?product=pay'),
  M('client-portal', 'money', 'Client Portal and payment button', 'Secure links for quotes, photos, production, invoices and payment.', 'live'),
  M('apost-billing', 'money', 'ApostApp order billing', 'Apostille orders, fees, shipping and optional Stripe checkout.', 'partial', '/apostille'),

  M('luxe', 'design', 'LuxeForge design and measurement surface', 'Window-treatment/furniture intake, catalogs, measurements and fabric selection.', 'partial', '/luxe'),
  M('craft', 'design', 'WoodCraft / CraftForge', 'Fabrication jobs, designs, inventory, machine status and quote builder.', 'live', '/?product=craft'),
  M('drawings', 'design', 'Drawing Studio', 'Parametric and AI-assisted drawings with PDF, DXF and inline SVG output.', 'partial', '/?product=drawings'),
  M('patterns', 'design', 'Pattern Templates', 'Drapery, upholstery, pillow and fabrication pattern math with PDF export.', 'live', '/tools/patterns'),
  M('custom-shapes', 'design', 'Custom Shapes', 'Calculate, save and retrieve custom shape geometry and measurements.', 'live', '/?product=drawings'),
  M('fabrics', 'design', 'Fabrics and drapery hardware', 'Fabric registry, hardware data and selection surfaces.', 'live', '/?product=workroom'),
  M('photo-analyzer', 'design', 'Photo Analyzer / Smart Analyzer', 'Photo upload, furniture/room understanding, notes and photo-to-quote inputs.', 'partial', '/?product=vision'),
  M('ai-vision', 'design', 'AI Vision and mockups', 'Furniture analysis, image understanding, mockups and approval flow.', 'partial', '/?product=vision'),
  M('production', 'design', 'Production board, work orders, inventory and cost tracking', 'Kanban stages, materials, low-stock checks, costs and production operations.', 'live', '/workroom/production'),
  M('shipforge', 'design', 'ShipForge', 'Rates, label generation, shipment history and tracking.', 'partial', '/?product=ship'),

  M('socialforge', 'growth', 'SocialForge', 'Post drafts, campaigns, calendar, account connections and approval.', 'partial', '/?product=social'),
  M('marketforge', 'growth', 'MarketForge / marketplace', 'Product catalog, listings, sellers, orders, reviews and integrations.', 'partial', '/?product=market'),
  M('storefront', 'growth', 'StoreFront Forge', 'Retail/POS CRUD for products, inventory, transactions and suppliers.', 'live', '/?product=storefront'),
  M('relistapp', 'growth', 'RelistApp', 'Imports, cross-posting, listing management, profit analysis and analytics.', 'partial', '/?product=relist'),
  M('archiveforge', 'growth', 'ArchiveForge', 'Photo-first LIFE magazine archive intake, condition scoring and listing drafts.', 'partial', '/archiveforge'),
  M('apostapp', 'growth', 'ApostApp public service', 'Public apostille intake, order tracking, pricing and return shipping.', 'partial', '/apostille'),

  M('inbox', 'comms', 'Inbox and email', 'Unified inbox, Gmail read capability and SendGrid/SMTP sending helpers.', 'partial', '/?screen=inbox'),
  M('whatsapp', 'comms', 'WhatsApp', 'Cloud webhook, inbound media and channel handling.', 'partial', '/channels'),
  M('telegram', 'comms', 'Telegram', 'Text/voice transport and Max bot surface.', 'partial', '/channels'),
  M('supportforge', 'comms', 'SupportForge', 'Tickets, customer records, knowledge base and AI suggestions.', 'partial', '/?product=support'),
  M('messages', 'comms', 'Messages and notifications', 'Read/unread messages and system, quote, desk and shipping alerts.', 'live', '/?screen=inbox'),
  M('client-notifier', 'comms', 'Client notifier', 'Job-stage updates, progress photos and outbound client communication.', 'partial', '/?screen=chat'),
  M('chat-backup', 'comms', 'Chat backup and cross-channel search', 'Backup sessions, import/export and search across channels.', 'live', '/?screen=memory-bank'),
  M('channels', 'comms', 'Channel status and transport matrix', 'Surface identity, channel health and output transport selection.', 'partial', '/channels'),

  M('files', 'docs', 'Local Files / instance archive', 'Safe upload/serve, working copies, generated documents, logs and browsing.', 'live'),
  M('drive', 'docs', 'Google Drive archive', 'Per-user Drive connection, structured folders and nightly export preparation.', 'partial', '/archivo'),
  M('photos-sync', 'docs', 'Google Photos sync', 'No separate Google Photos API/sync page was found in the current code.', 'stub'),
  M('product-docs', 'docs', 'Product docs and document registry', 'Searchable module READMEs, specs, guides and documentation.', 'live', '/?screen=docs'),
  M('pdfs', 'docs', 'PDF/document generation', 'Quote, estimate, invoice, drawing, report and presentation PDFs.', 'live', '/?screen=docs'),
  M('qr', 'docs', 'Presentations and QR', 'Structured presentations/reports and QR generation.', 'live', '/?screen=report'),
  M('notes', 'docs', 'Notes extraction', 'Extract notes from photos and route them into customer, inventory or quote contexts.', 'partial', '/?product=vision'),
  M('transcriptforge', 'docs', 'TranscriptForge', 'Audio jobs, chunks, reviewer auth, transcription, approval and audit.', 'partial', '/transcriptforge-review'),

  M('workroom', 'industry', 'Empire Workroom / Drapery & Upholstery pack', 'Soft-furnishings workroom with window treatments, fabrics, upholstery and production.', 'live', '/workroom'),
  M('construction', 'industry', 'ConstructionForge / Real Estate Development', 'Projects, phases, lots, buyers, payment plans, progress, materials and reports.', 'live', '/?product=construction'),
  M('amp', 'industry', 'AMP coaching', 'Affirmations, meditations, mood, journal, courses, lessons, audio and progress.', 'partial', '/amp'),
  M('cibernettic', 'industry', 'Cibernettic IT Services', 'Cybersecurity, data/BI, GIS, networks/VoIP and ERP/CRM starters.', 'partial', '/amp/empresas/cibernettic'),
  M('llcfactory', 'industry', 'LLCFactory', 'Business formation and service workflow.', 'partial', '/services/llc'),
  M('vet-pet', 'industry', 'VetForge and PetForge', 'Future vertical labels only; no product implementation found.', 'stub'),

  M('edition', 'admin', 'Edition manifest and route gate', 'Workroom/AMP/Maxine profiles, shared modules and isolated data roots.', 'live'),
  M('usage', 'admin', 'Usage caps and token/cost meters', 'Instance usage, monthly caps, token tracker, budgets and Simli usage.', 'partial', '/?screen=costs'),
  M('licenses', 'admin', 'Licenses, tiers and subscriptions', 'License status, service tiers and subscription state.', 'partial', '/pricing'),
  M('system', 'admin', 'Platform/System monitor', 'Health, disk/resource, provider status and startup probes.', 'live', '/?product=system'),
  M('recovery', 'admin', 'RecoveryForge', 'Recovery status, controls, progress and image analysis.', 'partial', '/?product=recovery'),
  M('maintenance', 'admin', 'Maintenance, accuracy and quality controls', 'Accuracy checks, maintenance routes, grounding and audit support.', 'partial', '/?product=system'),
  M('platform', 'admin', 'Docker/Ollama/provider controls', 'Container and local provider status/management surfaces.', 'partial', '/platform'),
  M('empire-assist', 'admin', 'EmpireAssist automation', 'Automation/workflow panel with paused examples.', 'partial', '/?product=assist'),
  M('hardware', 'admin', 'Hardware / Developer Panel', 'Local hardware and developer diagnostics.', 'stub', '/?product=hardware'),
];

const CATEGORY_BY_ID = Object.fromEntries(CATEGORY_DEFS.map(([id, name]) => [id, { id, name }])) as Record<CategoryId, { id: CategoryId; name: string }>;

function authHeaders(token: string | null): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token && token !== STUDIO_SESSION) headers.Authorization = `Bearer ${token}`;
  return headers;
}

function targetKey(scope: string, moduleId?: string, category?: string) {
  return `${scope}:${moduleId || category || 'general'}`;
}

function appliesToComment(comment: Comment, moduleId: string, category: CategoryId) {
  if (comment.scope === 'module') return comment.module_id === moduleId;
  if (comment.scope === 'category') return comment.category === category;
  const applies = comment.applies_to || {};
  return Boolean(applies.all) || (applies.modules || []).includes(moduleId) || (applies.categories || []).includes(category);
}

export default function AddonReviewPage() {
  const [token, setToken] = useState<string | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [pin, setPin] = useState('');
  const [authError, setAuthError] = useState('');
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [openCategory, setOpenCategory] = useState<CategoryId | null>('core');
  const [generalText, setGeneralText] = useState('');
  const [generalTags, setGeneralTags] = useState<string[]>(['visual/theme']);
  const [generalAll, setGeneralAll] = useState(true);
  const [generalCategories, setGeneralCategories] = useState<string[]>([]);
  const [generalModules, setGeneralModules] = useState<string[]>([]);

  useEffect(() => {
    let active = true;
    const saved = window.sessionStorage.getItem('review_owner_token');
    if (saved) {
      setToken(saved);
      setAuthChecked(true);
      return () => { active = false; };
    }
    // The Studio page is already behind the owner-only Cloudflare Access
    // session. Let that session load review notes before asking for a PIN.
    (async () => {
      try {
        const res = await fetch(`${API}/review/addons`, { credentials: 'include', cache: 'no-store' });
        if (res.ok) {
          const data = await res.json();
          if (active) { setComments(data.comments || []); setToken(STUDIO_SESSION); }
        }
      } catch { /* fall through to the explicit founder-PIN form */ }
      finally { if (active) { setAuthChecked(true); setLoading(false); } }
    })();
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!token || token === STUDIO_SESSION) return;
    void loadComments(token);
  }, [token]);

  async function loadComments(currentToken: string) {
    setLoading(true); setError('');
    try {
      const res = await fetch(`${API}/review/addons`, { headers: authHeaders(currentToken), credentials: 'include', cache: 'no-store' });
      if (res.status === 401 || res.status === 403) { window.sessionStorage.removeItem('review_owner_token'); setToken(null); throw new Error('Owner session expired. Enter the founder PIN again.'); }
      if (!res.ok) throw new Error(`Could not load review notes (${res.status})`);
      const data = await res.json();
      setComments(data.comments || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load review notes');
    } finally { setLoading(false); }
  }

  async function signIn(e: React.FormEvent) {
    e.preventDefault(); setAuthError('');
    try {
      const res = await fetch(`${API}/auth/founder-token`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include', body: JSON.stringify({ pin }) });
      if (!res.ok) throw new Error('Founder PIN was not accepted.');
      const data = await res.json();
      window.sessionStorage.setItem('review_owner_token', data.access_token);
      setPin(''); setAuthChecked(true); setToken(data.access_token);
    } catch (err) { setAuthError(err instanceof Error ? err.message : 'Owner sign-in failed'); }
  }

  async function addComment(payload: { module_id?: string; category?: string; scope: string; tags: string[]; applies_to?: AppliesTo; text: string }) {
    if (!token || !payload.text.trim()) return;
    try {
      const res = await fetch(`${API}/review/addons`, { method: 'POST', headers: authHeaders(token), credentials: 'include', body: JSON.stringify({ ...payload, status: 'open' }) });
      if (res.status === 401 || res.status === 403) { setToken(null); window.sessionStorage.removeItem('review_owner_token'); throw new Error('Owner access expired.'); }
      if (!res.ok) throw new Error(`Could not save note (${res.status})`);
      const data = await res.json();
      setComments(current => [...current, data.comment]);
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not save note'); }
  }

  async function toggleStatus(comment: Comment) {
    if (!token) return;
    const res = await fetch(`${API}/review/addons/${comment.id}`, { method: 'PATCH', headers: authHeaders(token), credentials: 'include', body: JSON.stringify({ status: comment.status === 'done' ? 'open' : 'done' }) });
    if (res.ok) { const data = await res.json(); setComments(current => [...current.filter(item => item.id !== comment.id), data.comment]); }
  }

  async function deleteComment(comment: Comment) {
    if (!token || !window.confirm('Delete this review note?')) return;
    const res = await fetch(`${API}/review/addons/${comment.id}`, { method: 'DELETE', headers: authHeaders(token), credentials: 'include' });
    if (res.ok) setComments(current => current.filter(item => item.id !== comment.id));
  }

  function exportReview(format: 'json' | 'md') {
    const payload = { exported_at: new Date().toISOString(), categories: CATEGORY_DEFS, modules: MODULES, comments };
    const body = format === 'json' ? JSON.stringify(payload, null, 2) : [
      '# EmpireBox Add-on Review', '',
      ...CATEGORY_DEFS.flatMap(([id, name, desc]) => {
        const mods = MODULES.filter(module => module.category === id);
        return [`## ${name}`, desc, '', ...mods.map(module => {
          const notes = comments.filter(comment => appliesToComment(comment, module.id, module.category));
          return `- **${module.name}** — ${module.status}. ${module.description}${notes.length ? ` Notes: ${notes.map(note => note.text).join(' | ')}` : ''}`;
        }), ''];
      }),
      '## General observations', ...comments.filter(comment => comment.scope === 'general').map(comment => `- [${comment.status}] ${comment.text} (${(comment.tags || []).join(', ')})`), '',
    ].join('\n');
    const blob = new Blob([body], { type: format === 'json' ? 'application/json' : 'text/markdown' });
    const url = URL.createObjectURL(blob); const a = document.createElement('a');
    a.href = url; a.download = `empire-addon-review.${format === 'json' ? 'json' : 'md'}`; a.click(); URL.revokeObjectURL(url);
  }

  const generalComments = comments.filter(comment => comment.scope === 'general');
  const counts = useMemo(() => ({ open: comments.filter(comment => comment.status === 'open').length, done: comments.filter(comment => comment.status === 'done').length }), [comments]);

  if (!authChecked) return <main data-review-page style={styles.page}><section style={styles.authCard}><div style={styles.eyebrow}>PRIVATE OWNER REVIEW</div><h1 style={styles.title}>Checking Studio session…</h1><p style={styles.muted}>Using the existing Studio owner session.</p></section></main>;

  if (!token) return (
    <main data-review-page style={styles.page}><section style={styles.authCard}>
      <div style={styles.eyebrow}>PRIVATE OWNER REVIEW</div><h1 style={styles.title}>EmpireBox add-on review</h1>
      <p style={styles.muted}>Enter the founder PIN to load and save Rafael’s review notes. The PIN is sent only to the existing owner-token endpoint.</p>
      <form onSubmit={signIn} style={styles.authForm}><input aria-label="Founder PIN" type="password" value={pin} onChange={e => setPin(e.target.value)} placeholder="Founder PIN" style={styles.input} autoFocus /><button type="submit" style={styles.primary}>Open review</button></form>
      {authError && <p style={styles.error}>{authError}</p>}
    </section></main>
  );

  return (
    <main data-review-page style={styles.page}>
      <header style={styles.header}><div><div style={styles.eyebrow}>PRIVATE OWNER REVIEW · 73 ADD-ONS</div><h1 style={styles.title}>EmpireBox add-on directory</h1><p style={styles.subtitle}>Review each module, open its live Command Center surface, and leave notes for the next agent.</p></div><div style={styles.actions}><button style={styles.secondary} onClick={() => exportReview('json')}>Export JSON</button><button style={styles.secondary} onClick={() => exportReview('md')}>Export Markdown</button><button style={styles.secondary} onClick={() => { window.sessionStorage.removeItem('review_owner_token'); setAuthChecked(true); setToken(null); }}>Lock</button></div></header>
      <div style={styles.summary}><span>{MODULES.length} modules</span><span>{CATEGORY_DEFS.length} categories</span><span>{counts.open} open notes</span><span>{counts.done} done</span>{loading && <span>Loading…</span>}</div>
      {error && <div style={styles.errorBanner}>{error}</div>}

      <section style={styles.generalCard}><div style={styles.sectionHeading}><div><div style={styles.eyebrow}>GENERAL OBSERVATIONS</div><h2 style={styles.h2}>Notes that apply across the directory</h2></div><span style={styles.count}>{generalComments.length}</span></div>
        {generalComments.map(comment => <CommentItem key={comment.id} comment={comment} onToggle={toggleStatus} onDelete={deleteComment} />)}
        <textarea value={generalText} onChange={e => setGeneralText(e.target.value)} placeholder="Add an observation for several modules or all modules…" style={styles.textarea} />
        <div style={styles.formRow}><TagPicker tags={generalTags} setTags={setGeneralTags} /><label style={styles.check}><input type="checkbox" checked={generalAll} onChange={e => setGeneralAll(e.target.checked)} /> Applies to all</label><select multiple value={[...generalCategories, ...generalModules]} onChange={e => { const values = Array.from(e.target.selectedOptions).map(option => option.value); setGeneralCategories(values.filter(value => value.startsWith('category:')).map(value => value.slice(9))); setGeneralModules(values.filter(value => value.startsWith('module:')).map(value => value.slice(7))); }} style={styles.multiSelect} aria-label="Select categories or modules"><optgroup label="Categories">{CATEGORY_DEFS.map(([id, name]) => <option key={id} value={`category:${id}`}>{name}</option>)}</optgroup><optgroup label="Modules">{MODULES.map(module => <option key={module.id} value={`module:${module.id}`}>{module.name}</option>)}</optgroup></select><button style={styles.primary} disabled={!generalText.trim()} onClick={() => { void addComment({ scope: 'general', tags: generalTags, applies_to: { all: generalAll, categories: generalCategories, modules: generalModules }, text: generalText }); setGeneralText(''); }}>Save observation</button></div>
      </section>

      <div style={styles.categoryList}>{CATEGORY_DEFS.map(([id, name, desc]) => <CategorySection key={id} categoryId={id} name={name} description={desc} modules={MODULES.filter(module => module.category === id)} comments={comments} open={openCategory === id} setOpen={() => setOpenCategory(openCategory === id ? null : id)} addComment={addComment} toggleStatus={toggleStatus} deleteComment={deleteComment} />)}</div>
    </main>
  );
}

function CategorySection({ categoryId, name, description, modules, comments, open, setOpen, addComment, toggleStatus, deleteComment }: { categoryId: CategoryId; name: string; description: string; modules: Module[]; comments: Comment[]; open: boolean; setOpen: () => void; addComment: (payload: any) => Promise<void>; toggleStatus: (comment: Comment) => Promise<void>; deleteComment: (comment: Comment) => Promise<void> }) {
  const categoryComments = comments.filter(comment => comment.scope === 'category' && comment.category === categoryId);
  const [categoryText, setCategoryText] = useState(''); const [tags, setTags] = useState<string[]>([]);
  return <section style={styles.categoryCard}><button onClick={setOpen} style={styles.categoryHeader}><span><strong>{name}</strong><small>{description}</small></span><span style={styles.categoryMeta}>{modules.length} modules · {categoryComments.length} notes · {open ? '−' : '+'}</span></button>{open && <div style={styles.categoryBody}><div style={styles.categoryNote}><h3 style={styles.h3}>Category comment</h3>{categoryComments.map(comment => <CommentItem key={comment.id} comment={comment} onToggle={toggleStatus} onDelete={deleteComment} />)}<textarea value={categoryText} onChange={e => setCategoryText(e.target.value)} placeholder={`Note about ${name}…`} style={styles.textarea} /><div style={styles.formRow}><TagPicker tags={tags} setTags={setTags} /><button style={styles.primary} disabled={!categoryText.trim()} onClick={() => { void addComment({ scope: 'category', category: categoryId, tags, text: categoryText }); setCategoryText(''); }}>Save category note</button></div></div>{modules.map(module => <ModuleRow key={module.id} module={module} comments={comments.filter(comment => comment.scope === 'module' && comment.module_id === module.id)} addComment={addComment} toggleStatus={toggleStatus} deleteComment={deleteComment} />)}</div>}</section>;
}

function ModuleRow({ module, comments, addComment, toggleStatus, deleteComment }: { module: Module; comments: Comment[]; addComment: (payload: any) => Promise<void>; toggleStatus: (comment: Comment) => Promise<void>; deleteComment: (comment: Comment) => Promise<void> }) {
  const [text, setText] = useState(''); const [tags, setTags] = useState<string[]>([]);
  return <article style={styles.moduleRow}><div style={styles.moduleTop}><div style={{ flex: 1 }}><div style={styles.moduleName}>{module.name} <span style={{ ...styles.status, ...(module.status === 'live' ? styles.live : module.status === 'partial' ? styles.partial : styles.stub) }}>{module.status}</span></div><p style={styles.moduleDescription}>{module.description}</p></div>{module.href ? <a href={module.href} target="_blank" rel="noreferrer" style={styles.openLink}>Open live page ↗</a> : <span style={styles.noPage}>no page yet</span>}</div>{comments.map(comment => <CommentItem key={comment.id} comment={comment} onToggle={toggleStatus} onDelete={deleteComment} />)}<div style={styles.commentBox}><textarea value={text} onChange={e => setText(e.target.value)} placeholder="Leave a note for this module…" style={styles.textareaSmall} /><div style={styles.formRow}><TagPicker tags={tags} setTags={setTags} /><button style={styles.secondary} disabled={!text.trim()} onClick={() => { void addComment({ scope: 'module', module_id: module.id, category: module.category, tags, text }); setText(''); }}>Save note</button></div></div></article>;
}

function TagPicker({ tags, setTags }: { tags: string[]; setTags: (tags: string[]) => void }) { return <select multiple value={tags} onChange={e => setTags(Array.from(e.target.selectedOptions).map(option => option.value))} style={styles.tagSelect} aria-label="Tags">{TAGS.map(tag => <option key={tag} value={tag}>{tag}</option>)}</select>; }

function CommentItem({ comment, onToggle, onDelete }: { comment: Comment; onToggle: (comment: Comment) => Promise<void>; onDelete: (comment: Comment) => Promise<void> }) { return <div style={{ ...styles.commentItem, opacity: comment.status === 'done' ? .62 : 1 }}><div style={styles.commentText}>{comment.text}</div><div style={styles.commentMeta}>{(comment.tags || []).map(tag => <span key={tag} style={styles.tag}>{tag}</span>)}<span>{new Date(comment.created_at).toLocaleString()}</span><button style={styles.textButton} onClick={() => void onToggle(comment)}>{comment.status === 'done' ? 'Reopen' : 'Mark done'}</button><button style={styles.textButtonDanger} onClick={() => void onDelete(comment)}>Delete</button></div></div>; }

const styles: Record<string, CSSProperties> = {
  page: { minHeight: '100vh', background: '#f6f7f9', color: '#1f2933', padding: '34px clamp(16px, 4vw, 64px) 80px', fontFamily: 'ui-sans-serif, system-ui, sans-serif' },
  header: { maxWidth: 1220, margin: '0 auto 18px', display: 'flex', justifyContent: 'space-between', gap: 24, alignItems: 'flex-start' },
  eyebrow: { color: '#9a7210', fontSize: 11, fontWeight: 800, letterSpacing: 1.5, textTransform: 'uppercase' },
  title: { margin: '7px 0 6px', color: '#172b4d', fontSize: 'clamp(28px, 4vw, 44px)', lineHeight: 1.05 },
  subtitle: { margin: 0, color: '#637083', maxWidth: 670, fontSize: 15, lineHeight: 1.5 },
  actions: { display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'flex-end' },
  summary: { maxWidth: 1220, margin: '0 auto 18px', display: 'flex', gap: 8, flexWrap: 'wrap', color: '#586579', fontSize: 12 },
  generalCard: { maxWidth: 1220, margin: '0 auto 18px', background: '#fffdf7', border: '1px solid #e8d99f', borderRadius: 16, padding: 20, boxShadow: '0 7px 22px rgba(32,49,74,.05)' },
  categoryList: { maxWidth: 1220, margin: '0 auto', display: 'grid', gap: 10 },
  categoryCard: { background: '#fff', border: '1px solid #dde3ea', borderRadius: 14, overflow: 'hidden', boxShadow: '0 4px 16px rgba(32,49,74,.035)' },
  categoryHeader: { width: '100%', padding: '17px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 14, border: 0, background: 'transparent', textAlign: 'left', cursor: 'pointer', color: '#172b4d', fontSize: 16 },
  categoryMeta: { color: '#7b8797', fontSize: 12, whiteSpace: 'nowrap' },
  categoryBody: { borderTop: '1px solid #e7ecf1' },
  categoryNote: { padding: '16px 20px', background: '#fafbfd', borderBottom: '1px solid #e7ecf1' },
  moduleRow: { padding: '17px 20px', borderBottom: '1px solid #edf0f3' },
  moduleTop: { display: 'flex', gap: 16, alignItems: 'flex-start' },
  moduleName: { color: '#203957', fontSize: 15, fontWeight: 800 },
  moduleDescription: { margin: '6px 0 0', color: '#657286', fontSize: 13, lineHeight: 1.45 },
  openLink: { color: '#1769aa', fontSize: 12, fontWeight: 700, whiteSpace: 'nowrap', textDecoration: 'none', paddingTop: 3 },
  noPage: { color: '#9a6b22', fontSize: 12, fontWeight: 700, whiteSpace: 'nowrap', paddingTop: 3 },
  status: { display: 'inline-block', marginLeft: 7, padding: '3px 7px', borderRadius: 99, fontSize: 10, textTransform: 'uppercase', letterSpacing: .5, verticalAlign: 2 },
  live: { color: '#176b45', background: '#e6f5ed' }, partial: { color: '#8a5a10', background: '#fff3d5' }, stub: { color: '#6c7280', background: '#edf0f4' },
  sectionHeading: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  h2: { margin: '4px 0 0', color: '#263b5a', fontSize: 19 },
  h3: { margin: '0 0 9px', color: '#344862', fontSize: 14 },
  count: { width: 28, height: 28, borderRadius: 99, background: '#f1e4ae', color: '#795d09', display: 'grid', placeItems: 'center', fontSize: 12, fontWeight: 800 },
  textarea: { width: '100%', minHeight: 74, boxSizing: 'border-box', resize: 'vertical', border: '1px solid #ccd5df', borderRadius: 10, padding: 10, font: 'inherit', fontSize: 13, background: '#fff' },
  textareaSmall: { width: '100%', minHeight: 52, boxSizing: 'border-box', resize: 'vertical', border: '1px solid #d5dce5', borderRadius: 9, padding: 9, font: 'inherit', fontSize: 12, background: '#fbfcfd' },
  formRow: { display: 'flex', alignItems: 'center', gap: 9, flexWrap: 'wrap', marginTop: 9 },
  tagSelect: { minWidth: 170, height: 31, border: '1px solid #ccd5df', borderRadius: 7, fontSize: 11, color: '#586579', background: '#fff' },
  multiSelect: { minWidth: 260, height: 60, border: '1px solid #ccd5df', borderRadius: 8, fontSize: 11, color: '#586579', background: '#fff' },
  check: { display: 'flex', alignItems: 'center', gap: 5, color: '#586579', fontSize: 12 },
  primary: { border: 0, borderRadius: 8, background: '#1d6b70', color: '#fff', padding: '9px 13px', fontWeight: 800, fontSize: 12, cursor: 'pointer' },
  secondary: { border: '1px solid #c8d2dc', borderRadius: 8, background: '#fff', color: '#36506c', padding: '8px 11px', fontWeight: 700, fontSize: 12, cursor: 'pointer' },
  input: { border: '1px solid #ccd5df', borderRadius: 9, padding: '11px 12px', font: 'inherit', fontSize: 14, flex: 1 },
  authCard: { maxWidth: 520, margin: '12vh auto', background: '#fff', border: '1px solid #dde3ea', borderRadius: 18, padding: 28, boxShadow: '0 14px 45px rgba(32,49,74,.1)' },
  authForm: { display: 'flex', gap: 9, marginTop: 20 },
  muted: { color: '#68768a', fontSize: 13, lineHeight: 1.5 },
  error: { color: '#9c2c2c', fontSize: 12, marginTop: 9 },
  errorBanner: { maxWidth: 1220, margin: '0 auto 14px', background: '#fff0f0', color: '#9c2c2c', border: '1px solid #efc3c3', borderRadius: 9, padding: 10, fontSize: 12 },
  commentBox: { marginTop: 12, paddingTop: 10, borderTop: '1px dashed #dbe1e8' },
  commentItem: { background: '#f7fafc', border: '1px solid #e0e7ed', borderRadius: 9, padding: '9px 10px', marginBottom: 8 },
  commentText: { color: '#334155', fontSize: 13, lineHeight: 1.45, whiteSpace: 'pre-wrap' },
  commentMeta: { display: 'flex', alignItems: 'center', gap: 7, flexWrap: 'wrap', marginTop: 7, color: '#8a96a6', fontSize: 10 },
  tag: { background: '#e7f0f3', color: '#35656c', borderRadius: 99, padding: '3px 6px', fontWeight: 700 },
  textButton: { border: 0, background: 'transparent', color: '#1769aa', cursor: 'pointer', fontSize: 10, fontWeight: 800, padding: 0 },
  textButtonDanger: { border: 0, background: 'transparent', color: '#a14a4a', cursor: 'pointer', fontSize: 10, fontWeight: 800, padding: 0 },
};
