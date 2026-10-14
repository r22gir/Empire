/** Spanish company / project intro. Plain JS so Node 20 can import it. */

import { AYUDA_OPENER, ayudaOpenerHtml } from './ayudaCopy.mjs';
import { FAMILY_EDITION, familyEdition } from './familyEdition.mjs';

export { AYUDA_OPENER, familyEdition };

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

const CSS = `
.em-guide{max-width:760px;margin:0 auto;padding:20px 16px 80px;font-family:Nunito,Inter,sans-serif;color:#2D2A26;background:#FFF9F0;min-height:100vh;box-sizing:border-box}
.em-kicker{letter-spacing:1.4px;color:#D4A030;font-weight:800;font-size:11px;margin:12px 0 4px}
.em-guide h1{font-family:'Playfair Display',Georgia,serif;font-size:34px;line-height:1.15;margin:0 0 8px}
.em-guide p,.em-guide li{font-size:15.5px;line-height:1.6}
.em-card{background:#fff;border:1px solid #F0E6D8;border-radius:18px;padding:4px 6px;margin-top:18px;box-shadow:0 10px 28px rgba(45,42,38,.04)}
.em-card a{display:block;padding:14px 14px;border-bottom:1px solid #F5EDE0;color:#2D2A26;text-decoration:none}
.em-card a:last-child{border-bottom:0}
.em-card strong{display:block;font-size:17px}
.em-card span{display:block;color:#6F685F;font-size:14px;margin-top:4px}
.em-link{color:#D4A030;font-weight:700}
.em-figure{margin:16px 0 4px}
.em-figure figcaption{font-size:13px;color:#6F685F;margin-top:8px;line-height:1.45}
.em-frame{background:linear-gradient(180deg,#f7f1e6,#fff);border:1px solid #E8DCC8;border-radius:16px;padding:14px}
.em-tile{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.em-tile div{background:#FFF9F0;border:1px solid #F0E6D8;border-radius:12px;padding:10px;font-size:12px;font-weight:700}
@media (max-width:640px){.em-tile{grid-template-columns:1fr}}
`;

export function renderEmpresaGuidePage(edition) {
  const family = familyEdition(edition);
  const cfg = family && family === FAMILY_EDITION.id ? FAMILY_EDITION : null;
  if (!cfg) {
    return `<main class="em-guide"><p>Abre esta guía dentro de tu propio centro de mando.</p></main>`;
  }
  const name = escapeHtml(cfg.assistant);
  const tiles = cfg.screens.slice(0, 4).map((screen) => `<div>${escapeHtml(screen.title)}</div>`).join('');
  const links = cfg.screens.map((screen) => (
    `<a href="${escapeHtml(screen.href)}"><strong>${escapeHtml(screen.title)}</strong><span>${escapeHtml(screen.note)}</span></a>`
  )).join('');

  const html = `<main class="em-guide" data-ayuda="empresa" data-edition="${escapeHtml(cfg.id)}">
<style>${CSS}</style>
<nav aria-label="Navegación de ayuda" style="display:flex;flex-wrap:wrap;gap:16px;margin-bottom:8px;font-size:14px">
<a class="em-link" href="/ayuda">← Volver a Ayuda</a>
<a href="/" style="color:#6F685F;font-weight:600">Centro de mando</a>
</nav>
<p class="em-kicker">${name.toUpperCase()} · CENTRO DE MANDO</p>
<h1>${escapeHtml(cfg.empresaHeadline)}</h1>
${ayudaOpenerHtml()}
<p>${escapeHtml(cfg.empresaLead)}</p>
<figure class="em-figure">
<div class="em-frame" role="img" aria-label="Pantallas de esta instancia">
<div class="em-tile">${tiles}</div>
</div>
<figcaption><strong>Ilustración.</strong> Estas pantallas son de <strong>${name}</strong> en ${escapeHtml(cfg.siteUrl)}. No abras un centro de mando que no sea el tuyo.</figcaption>
</figure>
<div class="em-card">${links}</div>
<p style="margin-top:22px"><a class="em-link" href="/ayuda">Volver a Ayuda</a> · <a class="em-link" href="/ayuda/whatsapp">WhatsApp</a></p>
</main>`;

  if (!html.includes(AYUDA_OPENER)) {
    throw new Error('empresa guide missing manito opener');
  }
  if (html.includes('/home/rg/') || html.includes('8011') || html.includes('8012')) {
    throw new Error('empresa guide leaked infra');
  }
  return html;
}
