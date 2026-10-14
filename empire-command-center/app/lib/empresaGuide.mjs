/** Spanish company / project intro for family editions. Plain JS so Node 20 can import it. */

import { AYUDA_OPENER, ayudaOpenerHtml } from './ayudaCopy.mjs';

export { AYUDA_OPENER };

const GUIDES = {
  amp: {
    id: 'amp',
    assistant: 'Max-e',
    siteUrl: 'https://amp.empirebox.store',
    otherName: 'Maxine',
    otherHost: 'maxine.empirebox.store',
    headline: 'Tu empresa en Max-e',
    lead: 'Aquí viven AMP (coaching) y Cibernettic (TI), más las empresas que tú armes. Nada se publica solo. Los documentos salen en borrador hasta que los apruebas.',
    screens: [
      { href: '/', title: 'Centro de mando', note: 'Chat, voz y el pulso del día.' },
      { href: '/amp/dashboard', title: 'Panel AMP', note: 'Cursos, afirmaciones y el tablero de AMP.' },
      { href: '/amp/cursos', title: 'Cursos', note: 'Programas, membresías y material de coaching.' },
      { href: '/amp/empresas', title: 'Empresas', note: 'AMP, Cibernettic y las que agregues.' },
      { href: '/amp/empresas/entrevista', title: 'Entrevista de empresa', note: 'Una pregunta por pantalla para armar una empresa.' },
      { href: '/amp/empresas/cibernettic', title: 'Cibernettic', note: 'Propuestas, SLA, órdenes de trabajo y facturas.' },
      { href: '/amp/whatsapp', title: 'WhatsApp', note: 'Voz, fotos y borradores. Nunca escribe a clientes.' },
      { href: '/amp/whatsapp/chats', title: 'Chats', note: 'Solo lectura. Revisa el primer mensaje de prueba.' },
      { href: '/ayuda/whatsapp', title: 'Guía de WhatsApp', note: 'Meta, número de prueba y webhook.' },
      { href: '/ayuda/voz', title: 'Cómo usar la voz', note: 'Dicta y arma el borrador.' },
      { href: '/ayuda/dispositivos', title: 'Dispositivos', note: 'Celular, tableta o computador.' },
    ],
  },
  maxine: {
    id: 'maxine',
    assistant: 'Maxine',
    siteUrl: 'https://maxine.empirebox.store',
    otherName: 'Max-e',
    otherHost: 'amp.empirebox.store',
    headline: 'Tu proyecto de inmuebles y construcción',
    lead: 'Aquí viven el portafolio, los lotes, la obra, los compradores y los planes de pago. El lote no cambia de estado y el precio no se inventa: lo dices tú. WhatsApp arma borradores; nunca escribe a clientes.',
    screens: [
      { href: '/', title: 'Centro de mando', note: 'Chat, voz y el pulso del día.' },
      { href: '/?product=construction', title: 'Portafolio', note: 'Proyectos de construcción e inmuebles.' },
      { href: '/?product=construction&section=lotmap', title: 'Lotes', note: 'Mapa de lotes y disponibilidad.' },
      { href: '/?product=construction&section=construction', title: 'Obra', note: 'Avance de obra y etapas (cimentación, estructura).' },
      { href: '/?product=construction&section=buyers', title: 'Compradores', note: 'Reservas y ventas. El estado del lote solo cambia cuando tú confirmas.' },
      { href: '/?product=construction&section=payments', title: 'Planes de pago', note: 'Cuota inicial y saldo. El precio lo dices tú.' },
      { href: '/amp/empresas', title: 'Nuevo proyecto', note: 'Entrevista guiada para armar un proyecto.' },
      { href: '/amp/whatsapp', title: 'WhatsApp', note: 'Notas de voz, fotos de obra y borradores. Nunca escribe a clientes.' },
      { href: '/amp/whatsapp/chats', title: 'Chats', note: 'Solo lectura. Revisa el primer mensaje de prueba.' },
      { href: '/ayuda/whatsapp', title: 'Guía de WhatsApp', note: 'Meta, número de prueba y webhook. No reutilices las llaves de Juan ni de Rafael.' },
      { href: '/ayuda/voz', title: 'Cómo usar la voz', note: 'Dicta lote, etapa y plan de pagos.' },
      { href: '/ayuda/dispositivos', title: 'Dispositivos', note: 'Celular, tableta o computador.' },
    ],
  },
};

export function familyEdition(edition) {
  const key = String(edition || '').trim().toLowerCase().replace(/-/g, '_');
  if (key === 'amp' || key === 'max_e' || key === 'maxe') return 'amp';
  if (key === 'maxine') return 'maxine';
  return null;
}

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
  const cfg = family ? GUIDES[family] : null;
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
<h1>${escapeHtml(cfg.headline)}</h1>
${ayudaOpenerHtml()}
<p>${escapeHtml(cfg.lead)}</p>
<figure class="em-figure">
<div class="em-frame" role="img" aria-label="Pantallas de esta instancia">
<div class="em-tile">${tiles}</div>
</div>
<figcaption><strong>Ilustración.</strong> Estas pantallas son de <strong>${name}</strong> en ${escapeHtml(cfg.siteUrl)}. No abras un centro de mando que no sea el tuyo.</figcaption>
</figure>
<div class="em-card">${links}</div>
<p style="margin-top:22px"><a class="em-link" href="/ayuda">Volver a Ayuda</a> · <a class="em-link" href="/ayuda/whatsapp">WhatsApp</a></p>
</main>`;

  if (html.includes(cfg.otherName) || html.includes(cfg.otherHost)) {
    throw new Error('empresa guide leaked the other edition');
  }
  if (!html.includes(AYUDA_OPENER)) {
    throw new Error('empresa guide missing manito opener');
  }
  return html;
}
