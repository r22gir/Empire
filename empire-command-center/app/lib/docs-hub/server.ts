/**
 * Final Docs hub — server-side index (Next.js route handlers only).
 *
 * Indexes the documents that already live on the Dell. Nothing is moved or
 * copied; files are only read. Sources:
 *   ~/empire-data/quotes/pdf/*.pdf            system estimate PDFs
 *   <repo>/backend/data/quotes/pdf/*.pdf      system estimate PDFs (backend data dir)
 *   ~/empire-data/presentations/*.pdf         presentations
 *   <repo>/backend/data/invoices/pdf/*.pdf    invoice PDFs
 *   drawing_versions.file_path (DB)           shop drawings
 *   ~/jobs/<client>/**                        job folders (estimate revisions,
 *                                             presentations, drawings, photos)
 *   job_documents (DB, photos)                quote photos served by the backend
 *   invoices (DB) without a stored PDF        previewed via the backend PDF endpoint
 * DB rows come from scripts/docs_hub_db.py (SQLite opened read-only).
 */
import { execFile } from 'child_process';
import { createHash } from 'crypto';
import { promises as fs } from 'fs';
import os from 'os';
import path from 'path';
import type { DocEntry, DocGroup, DocType, JobContext } from './types';

const HOME = os.homedir();
const APP_DIR = process.cwd();                      // .../empire-command-center
const REPO = path.resolve(APP_DIR, '..');
const DATA = process.env.EMPIRE_DATA_HOME || path.join(HOME, 'empire-data');
const JOBS = process.env.EMPIRE_JOBS_DIR || path.join(HOME, 'jobs');
export const UPSTREAM = process.env.NEXT_PUBLIC_BACKEND_UPSTREAM || 'http://127.0.0.1:8000';
export const CACHE_DIR = process.env.DOCS_HUB_CACHE || path.join(os.tmpdir(), 'docs-hub');

const ROOTS: { dir: string; type: DocType; source: string; system?: boolean }[] = [
  { dir: path.join(DATA, 'quotes', 'pdf'), type: 'estimate', source: 'Quote PDFs (empire-data)', system: true },
  { dir: path.join(REPO, 'backend', 'data', 'quotes', 'pdf'), type: 'estimate', source: 'Quote PDFs (backend data)', system: true },
  { dir: path.join(DATA, 'presentations'), type: 'presentation', source: 'Presentations' },
  { dir: path.join(REPO, 'backend', 'data', 'invoices', 'pdf'), type: 'invoice', source: 'Invoice PDFs' },
];
/** Only files under these roots can ever be served. */
export const ALLOWED_ROOTS = [...ROOTS.map(r => r.dir), JOBS, path.join(REPO, 'backend', 'data', 'drawings')];

const PDF_RE = /\.pdf$/i;
const IMG_RE = /\.(png|jpe?g|webp|gif)$/i;
const QN_RE = /\b(EST-\d{4}-\d{3,4})\b/i;
const INV_RE = /\b(INV-\d{4}-\d{3,4})\b/i;

export const sha = (s: string) => createHash('sha1').update(s).digest('hex').slice(0, 16);

type Row = Record<string, any>;
interface Db { quotes: Row[]; invoices: Row[]; jobs: Row[]; drawings: Row[]; job_documents: Row[]; error?: string }

function loadDb(): Promise<Db> {
  const empty: Db = { quotes: [], invoices: [], jobs: [], drawings: [], job_documents: [] };
  return new Promise(resolve => {
    execFile('python3', [path.join(APP_DIR, 'scripts', 'docs_hub_db.py')], { timeout: 15000, maxBuffer: 64 * 1024 * 1024 }, (err, stdout) => {
      if (err) return resolve({ ...empty, error: String(err.message || err) });
      try {
        const j = JSON.parse(stdout);
        const pick = (k: string) => (j[k] && Array.isArray(j[k].rows) ? j[k].rows : []);
        resolve({ quotes: pick('quotes'), invoices: pick('invoices'), jobs: pick('jobs'), drawings: pick('drawings'), job_documents: pick('job_documents'), error: j.error });
      } catch (e) { resolve({ ...empty, error: 'bad db json' }); }
    });
  });
}

async function walk(dir: string, depth: number, out: string[]) {
  let ents: import('fs').Dirent[];
  try { ents = await fs.readdir(dir, { withFileTypes: true }); } catch { return; }
  for (const e of ents) {
    if (e.name.startsWith('.') || e.name === '__pycache__' || e.name === 'node_modules' || e.name === 'src') continue;
    const p = path.join(dir, e.name);
    if (e.isDirectory()) { if (depth > 0) await walk(p, depth - 1, out); }
    else if (PDF_RE.test(e.name) || IMG_RE.test(e.name)) out.push(p);
  }
}

function versionOf(name: string, system?: boolean): { label: string; rank: number; explicitFinal: boolean } {
  const base = name.replace(/\.[a-z0-9]+$/i, '');
  if (/(^|[-_ ])final([-_ ]|$)/i.test(base)) return { label: 'final', rank: 100000, explicitFinal: true };
  const rev = base.match(/(?:^|[-_ ])rev[-_ ]?([A-Z]{1,2})(?=$|[-_ ])/i);
  if (rev) { const l = rev[1].toUpperCase(); const r = l.length === 1 ? l.charCodeAt(0) - 64 : 26 + (l.charCodeAt(1) - 64); return { label: `rev ${l}`, rank: 1000 + r, explicitFinal: false }; }
  const v = base.match(/(?:^|[-_ ])v(\d{1,3})(?=$|[-_ ])/i);
  if (v) return { label: `v${v[1]}`, rank: Number(v[1]), explicitFinal: false };
  if (system) return { label: 'system PDF', rank: 1, explicitFinal: false };
  return { label: 'original', rank: 1, explicitFinal: false };
}

function titleCase(slug: string) {
  return slug.replace(/[-_]+/g, ' ').replace(/\b\w/g, c => c.toUpperCase()).trim();
}

/** "Nehal Elrefai — Phase 2: Upstairs" -> "Nehal Elrefai" */
function clientFromProject(project?: string | null): string | null {
  if (!project) return null;
  const head = String(project).split(/\s+[—–-]\s+/)[0].trim();
  return head && head.length <= 60 ? head : null;
}

function classifyJobFile(rel: string): { type: DocType; variant: string } {
  const lower = rel.toLowerCase();
  const name = path.basename(lower);
  if (IMG_RE.test(name)) return { type: 'photo', variant: name };
  if (/(^|\/)ref\//.test(lower)) return { type: 'other', variant: name };
  if (/(^|\/)pres\/hdr\//.test(lower) || /header-option/.test(name)) return { type: 'other', variant: name.replace(/\.pdf$/, '') };
  if (/ripplefold|drawing|shop|elevation|(^|\/)rf\//.test(lower)) {
    const variant = name.replace(QN_RE, '').replace(/\.pdf$/, '').replace(/(^|[-_ ])rev[-_ ]?[a-z]{1,2}(?=$|[-_ ])/i, '').replace(/(^|[-_ ])v\d{1,3}(?=$|[-_ ])/i, '').replace(/^[-_ ]+|[-_ ]+$/g, '');
    return { type: 'drawing', variant: variant || 'drawing' };
  }
  if (/present|(^|\/)pres\//.test(lower)) return { type: 'presentation', variant: 'presentation' };
  if (INV_RE.test(name) || /invoice/.test(name)) return { type: 'invoice', variant: 'invoice' };
  if (QN_RE.test(name) || /estimate|quote|phase\d|preliminary/.test(name)) return { type: 'estimate', variant: 'estimate' };
  return { type: 'other', variant: name };
}

const TYPE_LABEL: Record<DocType, string> = { estimate: 'Estimate', presentation: 'Presentation', invoice: 'Invoice', drawing: 'Drawing', photo: 'Photo', other: 'File' };

export interface DocsIndex {
  builtAt: string;
  tookMs: number;
  docs: DocEntry[];
  roots: { dir: string; files: number }[];
  dbError?: string;
  quotes: Row[];
  invoices: Row[];
  jobs: Row[];
}

let CACHE: { at: number; idx: DocsIndex } | null = null;
let BUILDING: Promise<DocsIndex> | null = null;
const TTL_MS = 60_000;

export async function getIndex(refresh = false): Promise<DocsIndex> {
  if (!refresh && CACHE && Date.now() - CACHE.at < TTL_MS) return CACHE.idx;
  if (BUILDING) return BUILDING;
  BUILDING = buildIndex().then(idx => { CACHE = { at: Date.now(), idx }; BUILDING = null; persist(idx); return idx; })
    .catch(e => { BUILDING = null; throw e; });
  return BUILDING;
}

async function persist(idx: DocsIndex) {
  try {
    await fs.mkdir(CACHE_DIR, { recursive: true });
    await fs.writeFile(path.join(CACHE_DIR, 'index.json'), JSON.stringify({ builtAt: idx.builtAt, roots: idx.roots, count: idx.docs.length, docs: idx.docs }, null, 1));
  } catch { /* snapshot is best-effort */ }
}

async function buildIndex(): Promise<DocsIndex> {
  const t0 = Date.now();
  const db = await loadDb();
  const quotes = db.quotes.filter(q => !q.is_test);
  const qByNum = new Map<string, Row>();
  const qById = new Map<string, Row>();
  for (const q of quotes) { if (q.quote_number) qByNum.set(String(q.quote_number).toUpperCase(), q); qById.set(String(q.id), q); }
  const jobsById = new Map<string, Row>(db.jobs.map(j => [String(j.id), j]));
  const jobByQuote = new Map<string, Row>();
  for (const j of db.jobs) if (j.quote_id) jobByQuote.set(String(j.quote_id), j);
  const invByNum = new Map<string, Row>(db.invoices.filter(i => i.invoice_number).map(i => [String(i.invoice_number).toUpperCase(), i]));

  const docs: DocEntry[] = [];
  const roots: { dir: string; files: number }[] = [];

  const enrichFromQuote = (d: Partial<DocEntry>, q?: Row | null) => {
    if (!q) return d;
    const job = (q.job_id && jobsById.get(String(q.job_id))) || jobByQuote.get(String(q.id));
    d.quoteNumber = q.quote_number; d.quoteId = q.id;
    d.designer = q.customer_name || null;
    d.project = q.project_name || null;
    d.client = d.client || clientFromProject(q.project_name) || q.customer_name || null;
    d.businessUnit = q.business_unit || null;
    if (job) { d.jobId = job.id; d.jobNumber = job.job_number || null; }
    return d;
  };

  const push = async (abs: string, type: DocType, source: string, extra: Partial<DocEntry> = {}, system = false) => {
    let st: import('fs').Stats;
    try { st = await fs.stat(abs); } catch { return; }
    const filename = path.basename(abs);
    const v = versionOf(filename, system);
    const d: Partial<DocEntry> = {
      id: sha(abs), type, kind: IMG_RE.test(filename) ? 'image' : 'pdf', filename,
      version: v.label, versionRank: v.rank, isFinal: false, source,
      location: abs.replace(HOME, '~'), modified: st.mtime.toISOString(), size: st.size, ...extra,
    };
    if (v.explicitFinal) (d as any)._explicitFinal = true;
    const qn = (filename.match(QN_RE)?.[1] || extra.quoteNumber || '').toUpperCase();
    if (qn) enrichFromQuote(d, qByNum.get(qn) || null), d.quoteNumber = d.quoteNumber || qn;
    const inv = filename.match(INV_RE)?.[1];
    if (inv) {
      const row = invByNum.get(inv.toUpperCase());
      d.invoiceNumber = inv.toUpperCase();
      if (row) { d.invoiceId = row.id; d.client = d.client || row.client_name; if (row.quote_id) enrichFromQuote(d, qById.get(String(row.quote_id)) || null); }
    }
    docs.push(d as DocEntry);
  };

  // 1) fixed roots
  for (const r of ROOTS) {
    const files: string[] = [];
    await walk(r.dir, 0, files);
    roots.push({ dir: r.dir.replace(HOME, '~'), files: files.length });
    for (const f of files) {
      const extra: Partial<DocEntry> = {};
      if (r.type === 'presentation') {
        // e.g. 260926_2017_lindsey-draft.pdf -> client hint "Lindsey"
        const m = path.basename(f).replace(/\.pdf$/i, '').replace(/^\d{6}_\d{4}_/, '');
        if (m && !/^presentation$/i.test(m)) extra.client = titleCase(m.replace(/[-_](draft|presentation|construction.*)$/i, ''));
      }
      await push(f, r.type, r.source, extra, !!r.system);
    }
  }

  // 2) drawings recorded in the DB
  for (const dv of db.drawings) {
    if (!dv.file_path) continue;
    const abs = path.resolve(String(dv.file_path));
    if (!ALLOWED_ROOTS.some(root => abs.startsWith(root + path.sep))) continue;
    const q = dv.quote_id ? qById.get(String(dv.quote_id)) : null;
    await push(abs, 'drawing', 'Drawing versions (DB)', enrichFromQuote({ title: dv.item_name || undefined }, q) as Partial<DocEntry>);
    const last = docs[docs.length - 1];
    if (last && last.location.endsWith(path.basename(abs))) {
      last.version = `v${dv.version ?? 1}`; last.versionRank = Number(dv.version) || 1;
      last.groupKey = `drawing|${dv.quote_id || 'none'}|${String(dv.item_type || 'drawing')}`;
    }
  }

  // 3) job folders (~/jobs/<slug>)
  let jobDirs: string[] = [];
  try { jobDirs = (await fs.readdir(JOBS, { withFileTypes: true })).filter(d => d.isDirectory() && !d.name.startsWith('.')).map(d => d.name); } catch { /* no jobs dir */ }
  for (const slug of jobDirs) {
    const base = path.join(JOBS, slug);
    const files: string[] = [];
    await walk(base, 3, files);
    const relevant = files.filter(f => !/-page-\d+\.png$/i.test(f));
    if (relevant.length === 0) continue;
    roots.push({ dir: base.replace(HOME, '~'), files: relevant.length });
    // which quotes does this folder belong to?
    const folderQns = new Set<string>();
    for (const f of relevant) { const m = path.basename(f).match(QN_RE); if (m) folderQns.add(m[1].toUpperCase()); }
    for (const qidFile of ['p1/quote_id.txt', 'p2/quote_id.txt', 'max/quote_id.txt', 'quote_id.txt']) {
      try { const t = await fs.readFile(path.join(base, qidFile), 'utf8'); const m = t.match(QN_RE); if (m) folderQns.add(m[1].toUpperCase()); } catch { /* optional */ }
    }
    const folderClient = titleCase(slug);
    const primaryQn = [...folderQns].sort().pop() || null;
    for (const f of relevant) {
      const rel = path.relative(base, f);
      const { type, variant } = classifyJobFile(rel);
      const qn = path.basename(f).match(QN_RE)?.[1]?.toUpperCase() || null;
      await push(f, type, `Job folder ~/jobs/${slug}`, { jobFolder: slug, client: folderClient, quoteNumber: qn });
      const d = docs[docs.length - 1];
      if (!d || !d.location.endsWith(rel)) continue;
      if (!qn && primaryQn) { enrichFromQuote(d, qByNum.get(primaryQn) || null); d.quoteNumber = null; d.client = folderClient; }
      d.client = folderClient;
      d.groupKey = type === 'photo' || type === 'other'
        ? `${type}|${slug}|${rel}`
        : type === 'drawing' ? `drawing|${qn || slug}|${variant}` : `${type}|${qn || slug}`;
      if (rel.includes('/')) d.version = d.version === 'original' ? path.dirname(rel) : `${d.version} (${path.dirname(rel)})`;
    }
  }

  // 4) photos referenced by job_documents (served by the backend)
  for (const jd of db.job_documents) {
    if (!jd.url || !/^\/api\/v1\//.test(String(jd.url))) continue;
    const type: DocType = jd.document_type === 'photo' ? 'photo' : jd.document_type === 'drawing' ? 'drawing' : 'other';
    const q = jd.quote_id ? qById.get(String(jd.quote_id)) : null;
    if (!q && !jd.job_id) continue; // unassigned uploads stay out of the hub
    let src = String(jd.url);
    // drawing PDFs recorded as /api/v1/drawings/files/<name>.pdf (that backend path 404s):
    // index the file on disk instead, unless the DB drawing pass already did.
    const dm = src.match(/^\/api\/v1\/drawings\/files\/([\w.-]+\.pdf)$/i);
    if (dm) {
      const abs = path.join(REPO, 'backend', 'data', 'drawings', dm[1]);
      if (docs.some(x => x.location === abs || x.location.endsWith(path.sep + dm[1]))) continue;
      try { await fs.access(abs); } catch { continue; }
      await push(abs, 'drawing', `Job documents (${jd.source_channel || 'db'})`, enrichFromQuote({}, q) as Partial<DocEntry>);
      continue;
    }
    // photos stored as /api/v1/photos/<type>/<id>/<file>; the backend serves them under /serve/
    const pm = src.match(/^\/api\/v1\/photos\/(?!serve\/)([\w-]+)\/([\w-]+)\/([\w.-]+)$/);
    if (pm) src = `/api/v1/photos/serve/${pm[1]}/${pm[2]}/${pm[3]}`;
    const d: Partial<DocEntry> = {
      id: sha(src), type, kind: IMG_RE.test(src) ? 'image' : 'pdf', filename: jd.filename || path.basename(src),
      version: jd.revision ? `rev ${jd.revision}` : 'original', versionRank: Number(jd.revision) || 1, isFinal: false,
      source: `Job documents (${jd.source_channel || 'db'})`, location: src, modified: String(jd.created_at || ''), src,
      groupKey: `${type}|db|${jd.id}`,
    };
    enrichFromQuote(d, q);
    docs.push(d as DocEntry);
  }

  // 5) invoices without a stored PDF -> preview through the backend endpoint
  const stored = new Set(docs.filter(d => d.type === 'invoice' && d.invoiceNumber).map(d => d.invoiceNumber));
  for (const inv of db.invoices) {
    if (!inv.invoice_number || stored.has(String(inv.invoice_number).toUpperCase())) continue;
    const src = `/api/v1/finance/invoices/${inv.id}/pdf`;
    const d: Partial<DocEntry> = {
      id: sha(src), type: 'invoice', kind: 'pdf', filename: `${inv.invoice_number}.pdf`, version: 'generated', versionRank: 0, isFinal: false,
      source: 'Invoice (generated on preview)', location: `backend ${src}`, modified: String(inv.updated_at || inv.created_at || ''), generated: true, src,
      invoiceId: inv.id, invoiceNumber: inv.invoice_number, client: inv.client_name || null,
    };
    if (inv.quote_id) enrichFromQuote(d, qById.get(String(inv.quote_id)) || null);
    if (inv.client_name) d.designer = d.designer || inv.client_name;
    docs.push(d as DocEntry);
  }

  // titles, group keys, finals
  for (const d of docs) {
    if (!d.groupKey) {
      if (d.type === 'invoice') d.groupKey = `invoice|${d.invoiceNumber || d.id}`;
      else if (d.type === 'photo' || d.type === 'other') d.groupKey = `${d.type}|${d.id}`;
      else d.groupKey = `${d.type}|${d.quoteNumber || d.client || d.id}`;
    }
    if (!d.title) {
      const ref = d.type === 'invoice' ? (d.invoiceNumber || d.quoteNumber) : d.quoteNumber;
      const variant = d.type === 'drawing' ? d.groupKey.split('|')[2] : '';
      d.title = d.type === 'photo' || d.type === 'other'
        ? d.filename
        : [TYPE_LABEL[d.type], ref, variant && variant !== 'drawing' ? `· ${variant.replace(/[-_]+/g, ' ')}` : ''].filter(Boolean).join(' ');
    }
  }
  // de-duplicate identical system copies (same size, same mtime second) inside a group
  const seen = new Map<string, DocEntry>();
  const deduped: DocEntry[] = [];
  for (const d of docs) {
    const k = `${d.groupKey}|${d.size}|${d.modified.slice(0, 19)}`;
    const prev = seen.get(k);
    if (prev && d.size) {
      if (prev.version === 'system PDF' && d.version !== 'system PDF') { deduped[deduped.indexOf(prev)] = d; seen.set(k, d); }
      continue;
    }
    seen.set(k, d); deduped.push(d);
  }
  const groups = new Map<string, DocEntry[]>();
  for (const d of deduped) { const g = groups.get(d.groupKey) || []; g.push(d); groups.set(d.groupKey, g); }
  for (const g of groups.values()) {
    g.sort((a, b) => (b.modified || '').localeCompare(a.modified || '') || b.versionRank - a.versionRank);
    const explicit = g.find(d => (d as any)._explicitFinal);
    // Hand-made / versioned files (job folders, presentations) win over auto-generated system PDFs,
    // which the quote PDF endpoint rewrites every time someone previews or downloads a quote.
    const curated = g.filter(d => d.version !== 'system PDF' && !d.generated);
    const fin = explicit || (curated.length ? curated[0] : g[0]);
    fin.isFinal = true; fin.finalReason = explicit ? 'explicit' : g.length === 1 ? 'single' : 'latest';
  }
  for (const d of deduped) delete (d as any)._explicitFinal;

  return {
    builtAt: new Date().toISOString(), tookMs: Date.now() - t0, docs: deduped, roots, dbError: db.error,
    quotes, invoices: db.invoices, jobs: db.jobs,
  };
}

/** Group a flat doc list into final + older versions. */
export function groupDocs(docs: DocEntry[]): DocGroup[] {
  const m = new Map<string, DocEntry[]>();
  for (const d of docs) { const g = m.get(d.groupKey) || []; g.push(d); m.set(d.groupKey, g); }
  const out: DocGroup[] = [];
  for (const [key, g] of m) {
    const fin = g.find(d => d.isFinal) || g[0];
    out.push({ key, type: fin.type, title: fin.title, final: fin, older: g.filter(d => d !== fin).sort((a, b) => (b.modified || '').localeCompare(a.modified || '')) });
  }
  const order: DocType[] = ['estimate', 'presentation', 'invoice', 'drawing', 'photo', 'other'];
  return out.sort((a, b) => order.indexOf(a.type) - order.indexOf(b.type) || (b.final.modified || '').localeCompare(a.final.modified || ''));
}

const STOP = new Set(['show', 'me', 'the', 'open', 'final', 'latest', 'last', 'newest', 'please', 'pull', 'up', 'for', 'of', 'a', 'an', 'doc', 'docs', 'document', 'file', 'pdf', 'can', 'you', 'i', 'want', 'see', 'view', 'get', 'my', 's', 'version', 'current', 'muestrame', 'muéstrame', 'abre', 'el', 'la', 'de', 'del', 'final', 'ultimo', 'último']);
const TYPE_WORDS: [RegExp, DocType][] = [
  [/^(estimate|estimates|quote|quotes|estimado|cotizacion|cotización|presupuesto)$/, 'estimate'],
  [/^(presentation|presentations|deck|presentacion|presentación)$/, 'presentation'],
  [/^(invoice|invoices|bill|factura)$/, 'invoice'],
  [/^(drawing|drawings|shop|elevation|dibujo|plano)$/, 'drawing'],
  [/^(photo|photos|picture|pictures|foto|fotos|image|images)$/, 'photo'],
];

export function parseQuery(q: string): { type: DocType | null; terms: string[]; qn: string | null } {
  // bare "2026-297" means an estimate number, but not when it is part of an invoice number (INV-2026-123)
  const bare = /\binv-?\d{4}-\d{3}/i.test(q) ? null : q.match(/\b(\d{4}-\d{3})\b/)?.[1];
  const qn = q.match(QN_RE)?.[1]?.toUpperCase() || (bare ? `EST-${bare}` : null);
  let type: DocType | null = null;
  const terms: string[] = [];
  for (const raw of q.toLowerCase().replace(QN_RE, ' ').split(/[^a-z0-9áéíóúñ]+/i)) {
    const w = raw.replace(/'s$/, '');
    if (!w || STOP.has(w)) continue;
    const t = TYPE_WORDS.find(([re]) => re.test(w));
    if (t) { type = type || t[1]; continue; }
    if (w.length >= 2) terms.push(w);
  }
  return { type, terms, qn };
}

export function haystack(d: DocEntry) {
  return [d.title, d.filename, d.client, d.designer, d.project, d.quoteNumber, d.jobNumber, d.invoiceNumber, d.jobFolder, d.type].filter(Boolean).join(' ').toLowerCase();
}

export function searchDocs(docs: DocEntry[], opts: { q?: string; type?: string | null; client?: string | null; quote?: string | null; job?: string | null; finalOnly?: boolean }) {
  const p = parseQuery(opts.q || '');
  const type = (opts.type as DocType) || null;
  return docs.filter(d => {
    if (type && d.type !== type) return false;
    if (opts.finalOnly && !d.isFinal) return false;
    if (opts.client && !((d.client || '') + ' ' + (d.designer || '')).toLowerCase().includes(opts.client.toLowerCase())) return false;
    if (opts.quote && !(d.quoteId === opts.quote || (d.quoteNumber || '').toUpperCase() === opts.quote.toUpperCase())) return false;
    if (opts.job && !(d.jobId === opts.job || d.jobNumber === opts.job || d.jobFolder === opts.job)) return false;
    if (p.qn && (d.quoteNumber || '').toUpperCase() !== p.qn) return false;
    if (!opts.q) return true;
    const h = haystack(d);
    const typeFromQ = !type && p.type ? d.type === p.type : true;
    return typeFromQ && p.terms.every(t => h.includes(t));
  });
}

/** Docs that belong to a quote: its own files + job-folder files tied to it. */
export function docsForQuote(idx: DocsIndex, quoteIdOrNumber: string) {
  const q = idx.quotes.find(x => x.id === quoteIdOrNumber || String(x.quote_number).toUpperCase() === quoteIdOrNumber.toUpperCase());
  const qn = q ? String(q.quote_number).toUpperCase() : quoteIdOrNumber.toUpperCase();
  const folders = new Set(idx.docs.filter(d => d.jobFolder && (d.quoteNumber || '').toUpperCase() === qn).map(d => d.jobFolder!));
  return {
    quote: q || null,
    docs: idx.docs.filter(d => (d.quoteNumber || '').toUpperCase() === qn || (q && d.quoteId === q.id) || (d.jobFolder && folders.has(d.jobFolder) && !d.quoteNumber)),
  };
}

const money = (n: number) => `$${n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export function jobContext(idx: DocsIndex, opts: { quote?: string | null; job?: string | null; invoice?: string | null }): JobContext | null {
  let inv = opts.invoice ? idx.invoices.find(i => i.id === opts.invoice || i.invoice_number === opts.invoice) : null;
  let job = opts.job ? idx.jobs.find(j => j.id === opts.job || j.job_number === opts.job) : null;
  let q = opts.quote ? idx.quotes.find(x => x.id === opts.quote || x.quote_number === opts.quote) : null;
  if (!q && inv?.quote_id) q = idx.quotes.find(x => x.id === inv!.quote_id) || null;
  if (!q && job?.quote_id) q = idx.quotes.find(x => x.id === job!.quote_id) || null;
  if (!job && q) job = idx.jobs.find(j => j.quote_id === q!.id || (q!.job_id && j.id === q!.job_id)) || null;
  if (!q && !job && !inv) return null;
  const invoices = idx.invoices.filter(i => (q && i.quote_id === q.id) || (job && i.job_id === job.id) || (inv && i.id === inv.id));
  if (!inv && invoices.length) inv = invoices[0];
  const depositRequired = Number(q?.deposit_required ?? inv?.deposit_required ?? 0) || 0;
  const depositPaid = Math.max(Number(q?.deposit_paid ?? 0) || 0, Number(inv?.deposit_received ?? 0) || 0);
  const balanceDue = invoices.length ? invoices.reduce((t, i) => t + (Number(i.balance_due) || 0), 0) : (Number(q?.balance_due ?? 0) || null);
  const status = String(job?.status && job.status !== 'pending' ? job.status : q?.status || job?.status || inv?.status || '');
  const installDate = job?.install_date || job?.scheduled_date || null;
  let nextStep = '';
  const qs = String(q?.status || '');
  if (qs === 'draft' || qs === 'founder_review') nextStep = 'Approve and send the quote';
  else if (qs === 'sent' || qs === 'viewed') {
    const d = q?.sent_at ? Math.floor((Date.now() - new Date(q.sent_at).getTime()) / 86400000) : null;
    nextStep = d != null && d >= 0 ? `Follow up: sent ${d} day${d === 1 ? '' : 's'} ago, waiting on approval` : 'Waiting on client approval';
  } else if (qs === 'accepted' && depositRequired > depositPaid) nextStep = `Collect deposit (${money(depositRequired - depositPaid)} owed)`;
  else if (qs === 'accepted' && !installDate) nextStep = 'Schedule the install';
  else if (installDate && new Date(installDate).getTime() > Date.now()) nextStep = `Install on ${new Date(installDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`;
  else if ((balanceDue || 0) > 0 && invoices.length) nextStep = `Collect balance (${money(balanceDue || 0)})`;
  return {
    quoteId: q?.id || null, quoteNumber: q?.quote_number || null, jobId: job?.id || null, jobNumber: job?.job_number || null,
    client: clientFromProject(q?.project_name) || job?.client_name || q?.customer_name || inv?.client_name || null,
    designer: q?.customer_name || null, project: q?.project_name || job?.title || null,
    address: q?.project_address || job?.address || job?.client_address || q?.customer_address || null,
    phone: q?.customer_phone || job?.client_phone || inv?.client_phone || null,
    email: q?.customer_email || job?.client_email || inv?.client_email || null,
    status: status || null, total: Number(q?.total ?? inv?.total ?? 0) || null,
    depositRequired: depositRequired || null, depositPaid, depositOwed: Math.max(0, depositRequired - depositPaid),
    balanceDue, installDate, nextStep: nextStep || null,
    invoices: invoices.map(i => ({ id: i.id, number: i.invoice_number, status: i.status, total: Number(i.total) || 0, paid: Number(i.amount_paid) || 0, balance: Number(i.balance_due) || 0 })),
  };
}

/** Resolve a doc id to an absolute file path that is inside an allowed root. */
export async function resolveDocFile(id: string): Promise<{ doc: DocEntry; abs: string | null } | null> {
  const idx = await getIndex();
  const doc = idx.docs.find(d => d.id === id);
  if (!doc) return null;
  if (doc.src) return { doc, abs: null };
  const abs = path.resolve(doc.location.replace(/^~/, HOME));
  if (!ALLOWED_ROOTS.some(r => abs.startsWith(r + path.sep))) return null;
  return { doc, abs };
}

/** Backend sources the viewer may fetch on the user's behalf (same auth perimeter). */
export const SRC_ALLOW = [
  /^\/api\/v1\/quotes-v2\/[\w-]+\/pdf$/,
  /^\/api\/v1\/finance\/invoices\/[\w-]+\/pdf$/,
  /^\/api\/v1\/photos\/[\w./-]+\.(png|jpe?g|webp|gif)$/i,
  /^\/api\/v1\/patterns\/saved\/[\w-]+\/pdf$/,
];
export const srcAllowed = (src: string) => !src.includes('..') && SRC_ALLOW.some(re => re.test(src));

/** Fetch a backend-generated PDF into the cache (5 min freshness). */
export async function cachedSrc(src: string, ver?: string | null): Promise<{ abs: string; type: string } | { error: string; status: number }> {
  if (!srcAllowed(src)) return { error: 'source not allowed', status: 400 };
  await fs.mkdir(CACHE_DIR, { recursive: true });
  const isImg = IMG_RE.test(src);
  // `ver` (e.g. the quote's updated_at) busts the cache right after a save
  const abs = path.join(CACHE_DIR, `src-${sha(src + (ver ? `|${ver}` : ''))}${isImg ? path.extname(src) : '.pdf'}`);
  try { const st = await fs.stat(abs); if (Date.now() - st.mtimeMs < 5 * 60_000 && st.size > 0) return { abs, type: isImg ? 'image' : 'application/pdf' }; } catch { /* miss */ }
  const res = await fetch(`${UPSTREAM}${src}`, { cache: 'no-store' });
  if (!res.ok) return { error: `upstream ${res.status}`, status: res.status === 404 ? 404 : 502 };
  const buf = Buffer.from(await res.arrayBuffer());
  await fs.writeFile(abs, buf);
  return { abs, type: res.headers.get('content-type') || (isImg ? 'image' : 'application/pdf') };
}
