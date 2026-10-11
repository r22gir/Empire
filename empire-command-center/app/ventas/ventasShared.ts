export const INSTAGRAM_URL = 'https://www.instagram.com/gacconstruye/';
export const PUBLIC_API = '/api/v1/public/ventas';

export type LotStatus = 'available' | 'reserved' | 'sold' | 'consultar';

export interface PublicProject {
  slug: string;
  name: string;
  location: string | null;
  status: string;
  tagline: string | null;
  description: string | null;
  highlights: string[];
  unit_label: string;
  total_units: number;
  counts: Record<LotStatus, number>;
  price_note: string | null;
  whatsapp: string | null;
}

export interface PublicLot {
  number: string;
  block: string | null;
  phase: string | null;
  area_m2: number | null;
  frontage_m: number | null;
  depth_m: number | null;
  orientation: string | null;
  status: LotStatus;
  status_label: string;
  price: number | null;
}

export const STATUS_ORDER: LotStatus[] = ['available', 'reserved', 'sold', 'consultar'];
export const STATUS_LABEL: Record<LotStatus, string> = {
  available: 'Disponible',
  reserved: 'Separado',
  sold: 'Vendido',
  consultar: 'Consultar',
};

export function formatCOP(value: number | null): string | null {
  if (value == null || !Number.isFinite(value)) return null;
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(value);
}

export function formatM2(value: number | null): string | null {
  if (value == null || !Number.isFinite(value)) return null;
  return `${value.toLocaleString('es-CO', { maximumFractionDigits: 2 })} m²`;
}

export function whatsappHref(number: string, text: string): string {
  return `https://wa.me/${number}?text=${encodeURIComponent(text)}`;
}

export const VENTAS_CSS = `
body:has([data-ventas-page]) { overflow: auto !important; height: auto !important; background: #F4F7F5 !important; }
html:has([data-ventas-page]) { overflow-y: auto !important; height: auto !important; }
.gv-root { --g: #208D63; --gd: #051B12; --acc: #ECA400; --bg: #F4F7F5; --ink: #0E2219; --mut: #5B6B64;
  font-family: 'Lato', system-ui, -apple-system, 'Segoe UI', sans-serif; color: var(--ink); background: var(--bg);
  min-height: 100vh; min-height: 100dvh; display: flex; flex-direction: column; -webkit-text-size-adjust: 100%; }
.gv-root *, .gv-root *::before, .gv-root *::after { box-sizing: border-box; }
.gv-root a { color: inherit; }
.gv-wrap { width: 100%; max-width: 1120px; margin: 0 auto; padding: 0 16px; }
.gv-header { background: var(--gd); color: #fff; position: sticky; top: 0; z-index: 30; }
.gv-header-row { display: flex; align-items: center; justify-content: space-between; min-height: 56px; gap: 12px; }
.gv-brand { display: flex; align-items: baseline; gap: 10px; text-decoration: none; }
.gv-brand-mark { font-weight: 900; font-size: 22px; letter-spacing: 2px; color: #fff; }
.gv-brand-sub { font-size: 13px; color: #BFE3D3; }
.gv-ig { font-size: 13px; color: var(--acc) !important; text-decoration: none; font-weight: 700; }
.gv-main { flex: 1; padding: 20px 0 48px; }
.gv-footer { background: var(--gd); color: #DCEFE6; padding: 24px 0; font-size: 14px; }
.gv-footer a { color: var(--acc); font-weight: 700; }
.gv-footer p { margin: 4px 0; }
.gv-muted { color: var(--mut); font-size: 13px; }
.gv-footer .gv-muted { color: #9FC3B3; }
.gv-h1 { font-size: 28px; line-height: 1.15; font-weight: 900; margin: 6px 0 8px; color: var(--gd); }
.gv-h2 { font-size: 20px; font-weight: 900; margin: 0 0 12px; color: var(--gd); }
.gv-lead { font-size: 16px; line-height: 1.5; color: #24392F; margin: 0 0 16px; }
.gv-back { display: inline-flex; align-items: center; gap: 6px; font-size: 14px; font-weight: 700; color: var(--g) !important; text-decoration: none; padding: 8px 0; }
.gv-grid { display: grid; grid-template-columns: 1fr; gap: 16px; }
@media (min-width: 720px) { .gv-grid { grid-template-columns: 1fr 1fr; } .gv-h1 { font-size: 36px; } }
.gv-card { background: #fff; border-radius: 16px; overflow: hidden; box-shadow: 0 1px 3px rgba(5,27,18,.08), 0 6px 24px rgba(5,27,18,.06); text-decoration: none; display: flex; flex-direction: column; }
.gv-card-body { padding: 16px; display: flex; flex-direction: column; gap: 8px; }
.gv-card h3 { margin: 0; font-size: 20px; font-weight: 900; color: var(--gd); }
.gv-chip { display: inline-block; font-size: 12px; font-weight: 700; padding: 3px 10px; border-radius: 999px; background: #E3F3EC; color: var(--g); }
.gv-chip-acc { background: #FFF3D6; color: #8A6000; }
.gv-ph { position: relative; background: repeating-linear-gradient(135deg, #DDEBE4 0 12px, #E8F2ED 12px 24px); color: #3D5A4D;
  display: flex; align-items: center; justify-content: center; text-align: center; font-size: 13px; font-weight: 700; aspect-ratio: 16/9; padding: 12px; }
.gv-ph small { display: block; font-weight: 400; color: var(--mut); margin-top: 2px; }
.gv-ph-tag { position: absolute; top: 8px; left: 8px; background: var(--acc); color: var(--gd); font-size: 11px; font-weight: 900; padding: 2px 8px; border-radius: 6px; text-transform: uppercase; letter-spacing: .5px; }
.gv-bar { display: flex; height: 8px; border-radius: 999px; overflow: hidden; background: #E6ECE9; }
.gv-bar span { display: block; height: 100%; }
.gv-counts { display: flex; flex-wrap: wrap; gap: 6px 14px; font-size: 13px; color: #24392F; }
.gv-dot { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 5px; vertical-align: -1px; }
.gv-s-available { background: var(--g); color: #fff; border: 2px solid var(--g); }
.gv-s-reserved { background: var(--acc); color: var(--gd); border: 2px solid var(--acc); }
.gv-s-sold { background: #8C9A94; color: #fff; border: 2px solid #8C9A94; }
.gv-s-consultar { background: #fff; color: var(--gd); border: 2px dashed var(--g); }
.gv-section { background: #fff; border-radius: 16px; padding: 16px; margin-top: 16px; box-shadow: 0 1px 3px rgba(5,27,18,.06); }
.gv-map { display: grid; grid-template-columns: repeat(auto-fill, minmax(52px, 1fr)); gap: 8px; }
.gv-lot { min-height: 52px; border-radius: 10px; font-family: inherit; font-weight: 900; font-size: 15px; cursor: pointer; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 4px; line-height: 1.1; }
.gv-lot small { font-size: 9px; font-weight: 700; text-transform: uppercase; opacity: .9; }
.gv-lot:focus-visible { outline: 3px solid var(--gd); outline-offset: 2px; }
.gv-lot[aria-pressed="true"] { box-shadow: 0 0 0 3px var(--gd); }
.gv-filter { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 12px; }
.gv-filter button { font-family: inherit; font-size: 13px; font-weight: 700; padding: 6px 12px; border-radius: 999px; border: 1px solid #CFDCD5; background: #fff; color: var(--ink); cursor: pointer; }
.gv-filter button[aria-pressed="true"] { background: var(--gd); color: #fff; border-color: var(--gd); }
.gv-panel { position: fixed; left: 0; right: 0; bottom: 0; z-index: 40; background: #fff; border-radius: 18px 18px 0 0; box-shadow: 0 -8px 30px rgba(5,27,18,.25); padding: 18px 18px calc(18px + env(safe-area-inset-bottom)); max-height: 70vh; overflow-y: auto; }
@media (min-width: 900px) { .gv-panel { left: auto; right: 24px; bottom: 24px; width: 360px; border-radius: 18px; } }
.gv-panel dl { display: grid; grid-template-columns: auto 1fr; gap: 6px 12px; margin: 12px 0; font-size: 15px; }
.gv-panel dt { color: var(--mut); }
.gv-panel dd { margin: 0; font-weight: 700; }
.gv-btn { display: inline-flex; align-items: center; justify-content: center; gap: 8px; font-family: inherit; font-weight: 900; font-size: 15px; padding: 12px 18px; border-radius: 12px; border: 0; cursor: pointer; text-decoration: none; min-height: 46px; }
.gv-btn-primary { background: var(--g); color: #fff !important; }
.gv-btn-primary:disabled { opacity: .6; cursor: wait; }
.gv-btn-ghost { background: #EEF4F1; color: var(--gd) !important; }
.gv-btn-wa { background: #25D366; color: #06321A !important; }
.gv-close { position: absolute; top: 10px; right: 12px; background: transparent; border: 0; font-size: 26px; line-height: 1; cursor: pointer; color: var(--mut); padding: 6px; }
.gv-gallery { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
@media (min-width: 720px) { .gv-gallery { grid-template-columns: repeat(3, 1fr); } }
.gv-gallery .gv-ph { border-radius: 12px; aspect-ratio: 4/3; }
.gv-form { display: grid; gap: 12px; }
.gv-form label { display: grid; gap: 4px; font-size: 14px; font-weight: 700; color: #24392F; }
.gv-form input, .gv-form select, .gv-form textarea { font-family: inherit; font-size: 16px; padding: 11px 12px; border-radius: 10px; border: 1px solid #C9D7D0; background: #fff; color: var(--ink); width: 100%; }
.gv-form input:focus, .gv-form select:focus, .gv-form textarea:focus { outline: 2px solid var(--g); border-color: var(--g); }
.gv-form .gv-check { display: flex; gap: 10px; align-items: flex-start; font-weight: 400; }
.gv-form .gv-check input { width: 20px; height: 20px; margin-top: 2px; flex: none; }
.gv-hp { position: absolute !important; left: -10000px !important; width: 1px; height: 1px; overflow: hidden; }
.gv-msg { padding: 12px 14px; border-radius: 10px; font-size: 15px; font-weight: 700; }
.gv-msg-ok { background: #E3F3EC; color: #0F5A3C; }
.gv-msg-err { background: #FDECEC; color: #8A1C1C; }
.gv-wa-float { position: fixed; right: 16px; bottom: calc(16px + env(safe-area-inset-bottom)); z-index: 35; border-radius: 999px; box-shadow: 0 6px 20px rgba(0,0,0,.25); }
.gv-hl { margin: 0; padding-left: 18px; line-height: 1.6; }
.gv-hero { border-radius: 16px; overflow: hidden; }
.gv-hero .gv-ph { aspect-ratio: 16/8; }
.gv-row { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
`;
