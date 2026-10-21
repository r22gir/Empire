/** Spanish WhatsApp setup guide. Plain JS so Node 20 can import it.
 *
 * Secrets are never rendered. This tree ships one edition file only.
 */

import { AYUDA_OPENER, KEYS_HANDOFF, ayudaOpenerHtml } from './ayudaCopy.mjs';
import { FAMILY_EDITION, familyEdition } from './familyEdition.mjs';

export { AYUDA_OPENER, KEYS_HANDOFF, FAMILY_EDITION, familyEdition };

export const WHATSAPP_SETUP = { [FAMILY_EDITION.id]: FAMILY_EDITION };

export function setupConfig(edition) {
  const family = familyEdition(edition);
  return family && family === FAMILY_EDITION.id ? FAMILY_EDITION : null;
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

const FORBIDDEN_SECRET_WORDS = [
  'WHATSAPP_ACCESS_TOKEN=',
  'WHATSAPP_APP_SECRET=',
  'EAA',
  'BEGIN PRIVATE',
];

const HIDDEN_INFRA = [
  '/home/rg/',
  'empire-amp.env',
  'empire-maxine.env',
  '8011',
  '8012',
];

const GUIDE_CSS = `
.wa-guide{max-width:760px;margin:0 auto;padding:20px 16px 80px;font-family:Nunito,Inter,sans-serif;color:#2D2A26;background:#FFF9F0;min-height:100vh;box-sizing:border-box}
.wa-kicker{letter-spacing:1.4px;color:#D4A030;font-weight:800;font-size:11px;margin:12px 0 4px}
.wa-guide h1{font-family:'Playfair Display',Georgia,serif;font-size:34px;line-height:1.15;margin:0 0 8px}
.wa-lead,.wa-guide p,.wa-guide li{font-size:15.5px;line-height:1.6}
.wa-toc{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:18px 0 8px}
.wa-toc a{display:block;background:#fff;border:1px solid #F0E6D8;border-radius:12px;padding:10px 12px;color:#2D2A26;text-decoration:none;font-size:13px;font-weight:700}
.wa-toc a span{display:block;color:#D4A030;font-size:11px;letter-spacing:.08em}
.wa-card{background:#fff;border:1px solid #F0E6D8;border-radius:18px;padding:18px 18px 16px;margin-top:18px;box-shadow:0 10px 28px rgba(45,42,38,.04)}
.wa-card h2{font-family:'Playfair Display',Georgia,serif;font-size:22px;margin:0 0 10px}
.wa-card ol,.wa-card ul{margin:8px 0 0;padding-left:20px}
.wa-card li{margin:0 0 8px}
.wa-note{background:#FFF4D6;border-radius:12px;padding:12px 14px;margin:12px 0 0}
.wa-warn{background:#FDECE6;border-radius:12px;padding:12px 14px;margin:12px 0 0}
.wa-code{font-family:ui-monospace,'IBM Plex Mono',monospace;background:#2D2A26;color:#FFF9F0;padding:12px 14px;border-radius:12px;word-break:break-all;font-size:13px}
.wa-figure{margin:16px 0 4px}
.wa-figure figcaption{font-size:13px;color:#6F685F;margin-top:8px;line-height:1.45}
.wa-frame{background:linear-gradient(180deg,#f7f1e6,#fff);border:1px solid #E8DCC8;border-radius:16px;padding:12px;box-shadow:inset 0 1px 0 #fff}
.wa-chrome{display:flex;align-items:center;gap:6px;margin-bottom:10px}
.wa-dot{width:8px;height:8px;border-radius:50%;background:#E0D2BE}
.wa-url{flex:1;background:#fff;border:1px solid #F0E6D8;border-radius:999px;padding:4px 10px;font-size:11px;color:#7A736C;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
.wa-phone{max-width:280px;margin:0 auto;background:#1f1c19;border-radius:28px;padding:12px 10px 16px;color:#fff}
.wa-phone-bar{height:18px;border-radius:12px 12px 0 0;background:#111;margin:-4px 40px 10px;opacity:.5}
.wa-bubble{border-radius:14px;padding:8px 10px;margin:8px 8px 0;font-size:12px;line-height:1.4;max-width:86%}
.wa-in{background:#2d4a3a;margin-right:auto}
.wa-out{background:#D4A030;color:#2D2A26;margin-left:auto;font-weight:700}
.wa-meta-row{display:flex;justify-content:space-between;gap:8px;background:#fff;border:1px solid #F0E6D8;border-radius:10px;padding:8px 10px;margin-top:8px;font-size:12px}
.wa-btn{display:inline-block;background:#1877F2;color:#fff;border-radius:8px;padding:6px 10px;font-size:12px;font-weight:800}
.wa-field{background:#FFF9F0;border:1px dashed #D4A030;border-radius:10px;padding:8px 10px;margin-top:8px;font-size:12px;color:#7A736C}
.wa-link{color:#D4A030;font-weight:700}
.wa-foot{margin-top:28px}
@media (max-width:640px){.wa-toc{grid-template-columns:1fr}}
`;

function figure(caption, inner, label) {
  return `<figure class="wa-figure">
<div class="wa-frame" role="img" aria-label="${escapeHtml(label)}">${inner}</div>
<figcaption><strong>Ilustración.</strong> ${caption}</figcaption>
</figure>`;
}

function browserChrome(url, body) {
  return `<div class="wa-chrome"><span class="wa-dot"></span><span class="wa-dot"></span><span class="wa-dot"></span><span class="wa-url">${escapeHtml(url)}</span></div>${body}`;
}

export function renderWhatsAppSetupPage(edition, extras = {}) {
  const cfg = setupConfig(edition);
  if (!cfg) {
    return `<main class="wa-guide">
<p>Abre esta guía dentro de tu propio centro de mando.</p>
</main>`;
  }
  const name = escapeHtml(cfg.assistant);
  const webhook = escapeHtml(cfg.webhookUrl);
  const site = escapeHtml(cfg.siteUrl);
  const host = escapeHtml(cfg.siteHost);
  const trade = escapeHtml(cfg.trade);
  const voice = escapeHtml(cfg.voiceExample);
  const photo = escapeHtml(cfg.photoExample);
  const draft = escapeHtml(cfg.draftExample);
  const reuse = escapeHtml(cfg.reuseWarning);
  const firstTest = escapeHtml(cfg.firstTest);
  const chatsPath = escapeHtml(cfg.chatsPath);
  const homePath = escapeHtml(cfg.homePath);
  const empresaLabel = escapeHtml(cfg.empresaLabel);
  const keysHandoff = escapeHtml(KEYS_HANDOFF);
  const last4 = Array.isArray(extras.ownerLast4)
    ? extras.ownerLast4.map((n) => String(n).replace(/\D/g, '').slice(-4)).filter(Boolean)
    : [];
  const last4Note = last4.length
    ? `Esta instancia ya tiene un número que termina en ···${escapeHtml(last4[0])}. Confirma que es el tuyo.`
    : 'Rafael guarda tu número fuera de esta página. Aquí no se muestra completo.';

  const phoneMock = figure(
    `${name} recibe voz, fotos y texto. Arma borradores. <strong>Nunca escribe a tus clientes.</strong>`,
    `<div class="wa-phone"><div class="wa-phone-bar"></div>
<div class="wa-bubble wa-in">🎙 ${voice}</div>
<div class="wa-bubble wa-in">📷 ${photo}</div>
<div class="wa-bubble wa-out">Borrador listo. Nada se envía a clientes.</div></div>`,
    `Celular de prueba con voz, foto y borrador de ${cfg.assistant}`,
  );

  const metaMock = figure(
    'Entras a <strong>Meta for Developers</strong> con <strong>tu</strong> Facebook. El panel debe mostrar tus apps, no las de otra persona.',
    browserChrome(
      'developers.facebook.com',
      `<div style="font-size:13px;font-weight:800;margin-bottom:6px">Meta for Developers</div>
<div class="wa-meta-row"><span>My Apps</span><span class="wa-btn">Create app</span></div>
<div class="wa-meta-row"><span>${name} WhatsApp</span><span>Business</span></div>`,
    ),
    'Panel de Meta for Developers',
  );

  const businessMock = figure(
    'App tipo <strong>Business</strong>. En el use-case flow actual elige <strong>Conectar con clientes por WhatsApp</strong> y agrega el producto <strong>WhatsApp</strong>.',
    browserChrome(
      'developers.facebook.com/apps',
      `<div style="font-size:13px;font-weight:800">Create app</div>
<div class="wa-field">Type: Business</div>
<div class="wa-field">Use case: Conectar con clientes por WhatsApp</div>
<div class="wa-field">Name: ${name} WhatsApp</div>
<div class="wa-meta-row"><span>WhatsApp</span><span class="wa-btn">Add product</span></div>`,
    ),
    'Business app, use case and WhatsApp product',
  );

  const testNumberMock = figure(
    'En <strong>WhatsApp → API Setup</strong> usa el <strong>número de prueba de Meta</strong> y añade <strong>tu celular</strong> como destinatario.',
    browserChrome(
      'WhatsApp · API Setup',
      `<div class="wa-meta-row"><span>From</span><span>Meta test number</span></div>
<div class="wa-meta-row"><span>To</span><span>Your phone (recipient)</span></div>
<div class="wa-field">6-digit code → verify on your phone</div>`,
    ),
    'Número de prueba y destinatario propio',
  );

  const keysMock = figure(
    keysHandoff,
    browserChrome(
      'Entrega de las llaves',
      `<div style="font-size:13px;font-weight:800">Qué copias en Meta</div>
<div class="wa-field">Phone Number ID · permanent token · App Secret · Verify Token</div>
<div class="wa-field">Business Settings → System users</div>
<div class="wa-field">App settings → Basic</div>
<div class="wa-meta-row"><span>Chat / esta página</span><span>no</span></div>`,
    ),
    'Entrega de las llaves en la pantalla segura, nunca en el chat',
  );

  const webhookMock = figure(
    `Callback URL de esta instancia: <code>${webhook}</code>. Suscríbete a <strong>messages</strong> y pulsa Verify and save.`,
    browserChrome(
      'WhatsApp · Configuration · Webhook',
      `<div class="wa-field">${webhook}</div>
<div class="wa-meta-row"><span>Verify token</span><span>the one you invented</span></div>
<div class="wa-meta-row"><span>Webhook fields</span><span>messages</span></div>
<div class="wa-btn">Verify and save</div>`,
    ),
    'Pantalla de webhook en Meta',
  );

  const chatsMock = figure(
    'Después del primer mensaje, ábrelo en <strong>Chats (solo lectura)</strong>. Esa pantalla no envía nada.',
    browserChrome(
      `${cfg.siteHost}${cfg.chatsPath}`,
      `<div style="font-size:13px;font-weight:800">Chats · solo lectura</div>
<div class="wa-meta-row"><span>··· tu número</span><span>hola, arma el borrador</span></div>
<div class="wa-field">Esta pantalla no envía mensajes a clientes</div>`,
    ),
    'Pantalla de chats de solo lectura',
  );

  const problemsMock = figure(
    'Si no contesta: revisa el token permanente (no el de 24 h), la ventana de 24 h, las plantillas y que el webhook sea el de <strong>esta</strong> instancia.',
    browserChrome(
      'Common problems',
      `<div class="wa-meta-row"><span>24h token</span><span>expires · use System users</span></div>
<div class="wa-meta-row"><span>24h window</span><span>you write first</span></div>
<div class="wa-meta-row"><span>Templates</span><span>approved names only</span></div>`,
    ),
    'Lista de problemas comunes de WhatsApp',
  );

  const realNumberMock = figure(
    'Más adelante puedes pasar a un número real tuyo. Sigue siendo otra cuenta, otro token y el mismo webhook de <strong>esta</strong> instancia.',
    browserChrome(
      'WhatsApp · phone number',
      `<div class="wa-field">Phase 1: Meta test number</div>
<div class="wa-field">Later: your real number, verified in your Business</div>
<div class="wa-meta-row"><span>Webhook</span><span>${host}</span></div>`,
    ),
    'Paso de número de prueba a número real',
  );

  const html = `<main class="wa-guide" data-ayuda="whatsapp" data-edition="${escapeHtml(cfg.id)}">
<style>${GUIDE_CSS}</style>
<p class="wa-kicker">${name.toUpperCase()} · CENTRO DE MANDO</p>
<h1>WhatsApp de ${name}</h1>
${ayudaOpenerHtml()}
<p class="wa-lead">Esta guía es solo para <strong>tu</strong> ${name} en ${site}. Vas a crear <strong>tu propia cuenta nueva de Meta / WhatsApp</strong> — no la de Rafael y no el número del Workroom.</p>
<p>Sirve para ${trade}. ${name} oye voz, guarda fotos y arma borradores. <strong>Nunca escribe a clientes.</strong> Tope de uso: <strong>20%</strong>. ${keysHandoff}</p>
<p class="wa-warn"><strong>Importante.</strong> ${reuse}</p>

<nav class="wa-toc" aria-label="Secciones de la guía">
<a href="#wa-0"><span>0</span> Qué hace ${name}</a>
<a href="#wa-1"><span>1</span> Lo que necesitas</a>
<a href="#wa-2"><span>2</span> Meta for Developers</a>
<a href="#wa-3"><span>3</span> Business app</a>
<a href="#wa-4"><span>4</span> Número de prueba</a>
<a href="#wa-5"><span>5</span> Entrega de las llaves</a>
<a href="#wa-6"><span>6</span> Webhook</a>
<a href="#wa-7"><span>7</span> Primera prueba</a>
<a href="#wa-8"><span>8</span> Problemas comunes</a>
<a href="#wa-9"><span>9</span> Número real después</a>
</nav>

<div class="wa-card" id="wa-0">
<h2>0. Qué hace ${name} por WhatsApp</h2>
<ul>
<li><strong>Voz:</strong> ${voice}. Se transcribe y entra al mismo borrador.</li>
<li><strong>Fotos:</strong> ${photo}. Quedan en la línea de tiempo del proyecto.</li>
<li><strong>Borradores:</strong> ${draft}. Siguen marcados DRAFT hasta que tú los apruebas.</li>
<li><strong>Nunca escribe a clientes.</strong> Solo te responde a ti. El PDF no sale hacia afuera.</li>
</ul>
${phoneMock}
<p><strong>Punto de control:</strong> entiendes que este canal es para ti y ${name}, no para tus clientes.</p>
</div>

<div class="wa-card" id="wa-1">
<h2>1. Lo que necesitas</h2>
<ol>
<li>Tu celular con WhatsApp.</li>
<li>Tu Facebook personal (cuenta nueva o la tuya — <strong>no la de Rafael</strong>).</li>
<li>Un navegador abierto en este sitio (${host}).</li>
<li>${keysHandoff}</li>
</ol>
<p><strong>Punto de control:</strong> confirmas que la cuenta de Meta es tuya, no del Workroom.</p>
</div>

<div class="wa-card" id="wa-2">
<h2>2. Meta for Developers</h2>
<ol>
<li>Abre <a class="wa-link" href="https://developers.facebook.com">developers.facebook.com</a>.</li>
<li>Entra con <strong>tu</strong> Facebook.</li>
<li>Acepta las condiciones de desarrollador.</li>
</ol>
${metaMock}
<p><strong>Punto de control:</strong> ves el panel de tus apps, no las de Rafael.</p>
</div>

<div class="wa-card" id="wa-3">
<h2>3. Business app + producto WhatsApp</h2>
<ol>
<li>Crea una app tipo <strong>Business</strong>.</li>
<li>En el use-case flow actual, elige <strong>Conectar con clientes por WhatsApp</strong>.</li>
<li>Agrega el producto <strong>WhatsApp</strong>.</li>
</ol>
${businessMock}
<p><strong>Punto de control:</strong> la app aparece en tu cuenta, no en el Workroom.</p>
</div>

<div class="wa-card" id="wa-4">
<h2>4. Número de prueba + tu celular como destinatario</h2>
<ol>
<li>En <strong>WhatsApp → API Setup</strong> usa el <strong>número de prueba de Meta</strong>. No pidas el SIM del Workroom.</li>
<li>Añade como destinatario de prueba <strong>tu celular</strong>.</li>
<li>Meta te manda un código de 6 dígitos. Verifícalo en tu teléfono.</li>
</ol>
${testNumberMock}
<p>${last4Note}</p>
<p><strong>Punto de control:</strong> el sandbox acepta solo tu número. No el de Rafael.</p>
</div>

<div class="wa-card" id="wa-5">
<h2>5. Entrega de las llaves</h2>
<ol>
<li>Copia el <em>Phone Number ID</em> (solo el ID, no el token).</li>
<li>El token permanente se crea en <strong>Business Settings → System users</strong>. Dale al system user los permisos <code>whatsapp_business_messaging</code> y <code>whatsapp_business_management</code>. No uses el token temporal de 24 horas.</li>
<li>El <em>App Secret</em> está en <strong>App settings → Basic</strong>. Inventa un <em>Verify Token</em> largo y aleatorio.</li>
<li>${keysHandoff}</li>
</ol>
${keysMock}
<p><strong>Punto de control:</strong> las llaves no están en el chat ni en esta página. Rafael te dice cómo entregárselas.</p>
</div>

<div class="wa-card" id="wa-6">
<h2>6. Webhook</h2>
<ol>
<li>En Meta, <strong>WhatsApp → Configuration</strong>, Callback URL de <strong>esta</strong> instancia:</li>
</ol>
<p class="wa-code">${webhook}</p>
<ol start="2">
<li>Verify token: el mismo que inventaste al pedir las llaves.</li>
<li>Suscríbete al campo <strong>messages</strong>.</li>
<li>Pulsa <strong>Verify and save</strong>. Meta hace GET a esta instancia.</li>
</ol>
${webhookMock}
<p><strong>Punto de control:</strong> Meta muestra el webhook verificado. Si falla, revisa el verify token en la pantalla segura.</p>
</div>

<div class="wa-card" id="wa-7">
<h2>7. Primera prueba + pantalla de chats</h2>
<ol>
<li>Desde tu celular, ${firstTest}</li>
<li>${name} responde en español. No crea carpetas del Workroom.</li>
<li>Revisa <a class="wa-link" href="${chatsPath}">Chats (solo lectura)</a>.</li>
</ol>
${chatsMock}
<p><strong>Punto de control:</strong> un mensaje tuyo aparece. Nada se envía a clientes. El PDF solo sale si tú dices “envía el borrador” a ti mismo.</p>
</div>

<div class="wa-card" id="wa-8">
<h2>8. Problemas comunes</h2>
<ul>
<li><strong>Token temporal de 24 horas vs permanente.</strong> El token que Meta muestra al empezar caduca. Si ${name} deja de contestar al día siguiente, crea un token permanente en <strong>Business Settings → System users</strong> (permisos <code>whatsapp_business_messaging</code> y <code>whatsapp_business_management</code>). ${keysHandoff}</li>
<li><strong>Ventana de respuesta de 24 horas.</strong> ${name} solo puede contestarte en las 24 horas siguientes a tu último mensaje. Si se pasó el tiempo, escríbele tú otra vez.</li>
<li><strong>Plantillas.</strong> Fuera de esa ventana, Meta solo deja salir una plantilla ya aprobada. En esta fase no las necesitas: tú escribes primero.</li>
<li><strong>No responde.</strong> Revisa que el webhook sea exactamente <code>${webhook}</code>, que el destinatario sea tu celular y que no hayas mezclado el token de otra persona. Si sigue igual, vuelve a pegar las llaves en la pantalla segura.</li>
</ul>
${problemsMock}
</div>

<div class="wa-card" id="wa-9">
<h2>9. Pasar a un número real después</h2>
<ol>
<li>Cuando el número de prueba ya funcione, puedes verificar un número real tuyo en tu propio Business.</li>
<li>Sigue siendo <strong>otra</strong> cuenta, otro token y el mismo webhook de esta instancia.</li>
<li>${keysHandoff}</li>
<li>El canal sigue en borrador: ${name} no escribe a clientes.</li>
</ol>
${realNumberMock}
</div>

<div class="wa-card">
<h2>Límites de esta fase</h2>
<ul>
<li>Borrador solamente. No hay envíos a clientes.</li>
<li>Tope de uso 20%. Modelo incluido: MiniMax.</li>
<li>No se publica nada. No se mezcla con el Workroom.</li>
</ul>
</div>
<p class="wa-foot"><a class="wa-link" href="${homePath}">Volver al panel</a> · <a class="wa-link" href="/ayuda">Ayuda</a> · <a class="wa-link" href="/ayuda/empresa">${empresaLabel}</a></p>
</main>`;

  for (const banned of FORBIDDEN_SECRET_WORDS) {
    if (html.includes(banned)) {
      throw new Error('whatsapp setup page leaked a secret marker');
    }
  }
  for (const banned of HIDDEN_INFRA) {
    if (html.includes(banned)) {
      throw new Error(`whatsapp setup page leaked infra (${banned})`);
    }
  }
  if (!html.includes(AYUDA_OPENER)) {
    throw new Error('whatsapp setup page missing manito opener');
  }
  if (!html.includes(KEYS_HANDOFF)) {
    throw new Error('whatsapp setup page missing keys handoff');
  }
  if (html.includes('formulario seguro') || html.includes('solicitud segura')) {
    throw new Error('whatsapp setup page still mentions a missing form');
  }
  return html;
}
