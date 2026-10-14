/** Spanish WhatsApp setup guide. Plain JS so Node 20 can import it.
 *
 * Secrets are never rendered. Owner numbers live only in the Dell env file.
 * Maxine reuses this via edition config (construction copy, no legal details).
 */

import { AYUDA_OPENER, ayudaOpenerHtml } from './ayudaCopy.mjs';

export { AYUDA_OPENER };

export const WHATSAPP_SETUP = {
  amp: {
    id: 'amp',
    assistant: 'Max-e',
    ownerFirst: 'Juan Diego',
    siteHost: 'amp.empirebox.store',
    siteUrl: 'https://amp.empirebox.store',
    webhookUrl: 'https://amp.empirebox.store/api/v1/whatsapp/webhook',
    envFile: '/home/rg/empire-amp.env',
    backendPort: 8011,
    trade: 'coaching y tus propias empresas',
    otherAssistant: 'Maxine',
    voiceExample: 'una nota de voz sobre el programa de coaching o una propuesta de Cibernettic',
    photoExample: 'la foto de un taller, un tablero de curso o un contrato en borrador',
    draftExample: 'el borrador de una cotización, un plan de membresía o una orden de trabajo',
    reuseWarning: 'No uses la cuenta, las llaves ni el número de Rafael. Esta instancia es solo tuya.',
    firstTest: 'Manda un texto o una nota de voz al número de prueba, por ejemplo: “arma el borrador del curso de liderazgo”.',
  },
  maxine: {
    id: 'maxine',
    assistant: 'Maxine',
    ownerFirst: 'Camilo',
    siteHost: 'maxine.empirebox.store',
    siteUrl: 'https://maxine.empirebox.store',
    webhookUrl: 'https://maxine.empirebox.store/api/v1/whatsapp/webhook',
    envFile: '/home/rg/empire-maxine.env',
    backendPort: 8012,
    trade: 'inmuebles, construcción y desarrollo',
    otherAssistant: 'Max-e',
    voiceExample: 'una nota de voz sobre el lote 12, etapa cimentación',
    photoExample: 'la foto de la obra, del lote o del avance de estructura',
    draftExample: 'el borrador del plan de pagos, de la reserva o de la disponibilidad del lote',
    reuseWarning: 'No reutilices las llaves ni el número de Juan ni de Rafael. Esta instancia tiene su propia cuenta de Meta y su propio número.',
    firstTest: 'Manda un texto o una nota de voz al número de prueba, por ejemplo: “reserva el lote 12, cuota inicial 30%, saldo en 24 meses”.',
  },
};

export function familyEdition(edition) {
  const key = String(edition || '').trim().toLowerCase().replace(/-/g, '_');
  if (key === 'amp' || key === 'max_e' || key === 'maxe') return 'amp';
  if (key === 'maxine') return 'maxine';
  return null;
}

export function setupConfig(edition) {
  const family = familyEdition(edition);
  return family ? WHATSAPP_SETUP[family] : null;
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
<p>Abre esta guía dentro de tu propio centro de mando (Max-e o Maxine).</p>
</main>`;
  }
  const name = escapeHtml(cfg.assistant);
  const webhook = escapeHtml(cfg.webhookUrl);
  const envFile = escapeHtml(cfg.envFile);
  const site = escapeHtml(cfg.siteUrl);
  const host = escapeHtml(cfg.siteHost);
  const trade = escapeHtml(cfg.trade);
  const voice = escapeHtml(cfg.voiceExample);
  const photo = escapeHtml(cfg.photoExample);
  const draft = escapeHtml(cfg.draftExample);
  const reuse = escapeHtml(cfg.reuseWarning);
  const firstTest = escapeHtml(cfg.firstTest);
  const last4 = Array.isArray(extras.ownerLast4)
    ? extras.ownerLast4.map((n) => String(n).replace(/\D/g, '').slice(-4)).filter(Boolean)
    : [];
  const last4Note = last4.length
    ? `El archivo de esta instancia ya tiene un número que termina en ···${escapeHtml(last4[0])}. Confirma que es el tuyo.`
    : 'Rafael pone tu número solo en el archivo de secretos del Dell. Esta página no lo muestra completo.';

  const phoneMock = figure(
    `${name} recibe voz, fotos y texto. Arma borradores. <strong>Nunca escribe a tus clientes.</strong>`,
    `<div class="wa-phone"><div class="wa-phone-bar"></div>
<div class="wa-bubble wa-in">🎙 ${voice}</div>
<div class="wa-bubble wa-in">📷 ${photo}</div>
<div class="wa-bubble wa-out">Borrador listo. Nada se envía a clientes.</div></div>`,
    `Celular de prueba con voz, foto y borrador de ${cfg.assistant}`,
  );

  const metaMock = figure(
    'Entras a Meta for Developers con <strong>tu</strong> Facebook. El panel debe mostrar tus apps, no las de otra persona.',
    browserChrome(
      'developers.facebook.com',
      `<div style="font-size:13px;font-weight:800;margin-bottom:6px">Meta for Developers</div>
<div class="wa-meta-row"><span>Mis apps</span><span class="wa-btn">Crear app</span></div>
<div class="wa-meta-row"><span>${name} WhatsApp</span><span>Negocios</span></div>`,
    ),
    'Panel de Meta for Developers',
  );

  const businessMock = figure(
    'La app es tipo <strong>Negocios / Business</strong> y le agregas el producto WhatsApp. El nombre es tuyo.',
    browserChrome(
      'developers.facebook.com/apps',
      `<div style="font-size:13px;font-weight:800">Nueva app</div>
<div class="wa-field">Tipo: Negocios / Business</div>
<div class="wa-field">Nombre: ${name} WhatsApp</div>
<div class="wa-meta-row"><span>Producto WhatsApp</span><span class="wa-btn">Agregar</span></div>`,
    ),
    'Alta de app de negocios y producto WhatsApp',
  );

  const testNumberMock = figure(
    'Usa el <strong>número de prueba de Meta</strong> y añade <strong>tu celular</strong> como destinatario. No pidas el SIM de nadie más.',
    browserChrome(
      'WhatsApp · API Setup',
      `<div class="wa-meta-row"><span>From</span><span>Número de prueba de Meta</span></div>
<div class="wa-meta-row"><span>To</span><span>Tu celular (destinatario)</span></div>
<div class="wa-field">Código de 6 dígitos → verifícalo en tu teléfono</div>`,
    ),
    'Número de prueba y destinatario propio',
  );

  const keysMock = figure(
    'Las llaves se entregan por el <strong>formulario seguro de esta app</strong>, no por el chat. Esta ilustración no guarda nada.',
    browserChrome(
      `${cfg.siteHost} · formulario seguro`,
      `<div style="font-size:13px;font-weight:800">Solicitud segura de secretos</div>
<div class="wa-field">Token permanente · ID del número · App secret · Verify token</div>
<div class="wa-field">Los valores no se pegan en el chat ni en esta guía</div>
<div class="wa-meta-row"><span>Destino</span><span>${envFile}</span></div>`,
    ),
    'Formulario seguro de llaves, solo ilustración',
  );

  const webhookMock = figure(
    `Callback URL de esta instancia: <code>${webhook}</code>. Suscríbete a <strong>messages</strong> y pulsa Verificar.`,
    browserChrome(
      'WhatsApp · Webhooks',
      `<div class="wa-field">${webhook}</div>
<div class="wa-meta-row"><span>Verify token</span><span>el mismo del formulario seguro</span></div>
<div class="wa-meta-row"><span>Campo</span><span>messages</span></div>
<div class="wa-btn">Verificar y guardar</div>`,
    ),
    'Pantalla de webhook en Meta',
  );

  const chatsMock = figure(
    'Después del primer mensaje, ábrelo en <strong>Chats (solo lectura)</strong>. Esa pantalla no envía nada.',
    browserChrome(
      `${cfg.siteHost}/amp/whatsapp/chats`,
      `<div style="font-size:13px;font-weight:800">Chats · solo lectura</div>
<div class="wa-meta-row"><span>··· tu número</span><span>hola, arma el borrador</span></div>
<div class="wa-field">Esta pantalla no envía mensajes a clientes</div>`,
    ),
    'Pantalla de chats de solo lectura',
  );

  const problemsMock = figure(
    'Si no contesta: revisa token permanente (no el de 24 h), la ventana de 24 h, las plantillas y que el webhook sea el de <strong>esta</strong> instancia.',
    browserChrome(
      'Problemas comunes',
      `<div class="wa-meta-row"><span>Token de 24 h</span><span>caduca · usa permanente</span></div>
<div class="wa-meta-row"><span>Ventana 24 h</span><span>tú escribes primero</span></div>
<div class="wa-meta-row"><span>Plantillas</span><span>solo las aprobadas</span></div>`,
    ),
    'Lista de problemas comunes de WhatsApp',
  );

  const realNumberMock = figure(
    'Más adelante puedes pasar a un número real tuyo. Sigue siendo otra cuenta, otro token y otro webhook de <strong>esta</strong> instancia.',
    browserChrome(
      'WhatsApp · número real',
      `<div class="wa-field">Fase 1: número de prueba de Meta</div>
<div class="wa-field">Después: tu número real, verificado en tu Business</div>
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
<p>Sirve para ${trade}. ${name} oye voz, guarda fotos y arma borradores. <strong>Nunca escribe a clientes.</strong> Tope de uso: <strong>20%</strong>. Las llaves no van en esta página ni en el chat: van por la <strong>solicitud segura</strong> (formulario seguro dentro de la app) hacia <code>${envFile}</code>.</p>
<p class="wa-warn"><strong>Importante.</strong> ${reuse}</p>

<nav class="wa-toc" aria-label="Secciones de la guía">
<a href="#wa-0"><span>0</span> Qué hace ${name}</a>
<a href="#wa-1"><span>1</span> Lo que necesitas</a>
<a href="#wa-2"><span>2</span> Meta for Developers</a>
<a href="#wa-3"><span>3</span> App de negocios</a>
<a href="#wa-4"><span>4</span> Número de prueba</a>
<a href="#wa-5"><span>5</span> Formulario seguro</a>
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
<li>El formulario seguro de esta app para entregar las llaves. No las pegues en el chat.</li>
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
<h2>3. App de tipo Negocios + producto WhatsApp</h2>
<ol>
<li>Crea una app tipo <strong>Negocios / Business</strong>.</li>
<li>Ponle un nombre tuyo (por ejemplo “${name} WhatsApp”).</li>
<li>Agrega el producto <strong>WhatsApp</strong>.</li>
</ol>
${businessMock}
<p><strong>Punto de control:</strong> la app aparece en tu cuenta, no en el Workroom.</p>
</div>

<div class="wa-card" id="wa-4">
<h2>4. Número de prueba + tu celular como destinatario</h2>
<ol>
<li>En WhatsApp → API Setup usa el <strong>número de prueba de Meta</strong>. No pidas el SIM del Workroom.</li>
<li>Añade como destinatario de prueba <strong>tu celular</strong> (el que Rafael guarda en <code>WHATSAPP_OWNER_NUMBERS</code> de esta instancia).</li>
<li>Meta te manda un código de 6 dígitos. Verifícalo en tu teléfono.</li>
</ol>
${testNumberMock}
<p>${last4Note}</p>
<p><strong>Punto de control:</strong> el sandbox acepta solo tu número. No el de Rafael.</p>
</div>

<div class="wa-card" id="wa-5">
<h2>5. Las llaves van por el formulario seguro (no por el chat)</h2>
<ol>
<li>Copia el <em>Phone Number ID</em> (solo el ID, no el token).</li>
<li>Genera un <strong>token permanente</strong> de usuario del sistema (no el token temporal de 24 horas).</li>
<li>Copia el <em>App Secret</em> y elige un <em>Verify Token</em> largo y aleatorio.</li>
<li>Entrégalos por el <strong>formulario seguro de esta app</strong> — la solicitud segura de secretos. <strong>No los escribas en el chat ni en esta página.</strong></li>
</ol>
<p class="wa-note">Rafael (o el operador) los pone solo en <code>${envFile}</code>:</p>
<ul>
<li><code>WHATSAPP_ACCESS_TOKEN</code></li>
<li><code>WHATSAPP_PHONE_NUMBER_ID</code></li>
<li><code>WHATSAPP_VERIFY_TOKEN</code></li>
<li><code>WHATSAPP_APP_SECRET</code></li>
<li><code>WHATSAPP_OWNER_NUMBERS</code> (solo tu número)</li>
</ul>
${keysMock}
<p><strong>Punto de control:</strong> el archivo del Dell tiene los valores. Esta página sigue vacía. El chat no tiene tokens.</p>
</div>

<div class="wa-card" id="wa-6">
<h2>6. Webhook</h2>
<ol>
<li>En Meta, Callback URL de <strong>esta</strong> instancia:</li>
</ol>
<p class="wa-code">${webhook}</p>
<ol start="2">
<li>Verify token: el mismo que fue al formulario seguro y a <code>${envFile}</code>.</li>
<li>Suscríbete al campo <strong>messages</strong>.</li>
<li>Pulsa Verificar y guardar. Meta hace GET a esta instancia.</li>
</ol>
${webhookMock}
<p><strong>Punto de control:</strong> Meta muestra el webhook verificado. Si falla, Rafael confirma que ${host} apunta al puerto ${cfg.backendPort}.</p>
</div>

<div class="wa-card" id="wa-7">
<h2>7. Primera prueba + pantalla de chats</h2>
<ol>
<li>Desde tu celular, ${firstTest}</li>
<li>${name} responde en español. No crea carpetas del Workroom.</li>
<li>Revisa <a class="wa-link" href="/amp/whatsapp/chats">Chats (solo lectura)</a>.</li>
</ol>
${chatsMock}
<p><strong>Punto de control:</strong> un mensaje tuyo aparece. Nada se envía a clientes. El PDF solo sale si tú dices “envía el borrador” a ti mismo.</p>
</div>

<div class="wa-card" id="wa-8">
<h2>8. Problemas comunes</h2>
<ul>
<li><strong>Token temporal de 24 horas vs permanente.</strong> El token que Meta muestra al empezar caduca. Si ${name} deja de contestar al día siguiente, genera un token permanente de usuario del sistema y vuélvelo a entregar por el formulario seguro. No lo pegues en el chat.</li>
<li><strong>Ventana de respuesta de 24 horas.</strong> ${name} solo puede contestarte en las 24 horas siguientes a tu último mensaje. Si se pasó el tiempo, escríbele tú otra vez.</li>
<li><strong>Plantillas.</strong> Fuera de esa ventana, Meta solo deja salir una plantilla ya aprobada. En esta fase no las necesitas: tú escribes primero.</li>
<li><strong>No responde.</strong> Revisa que el webhook sea exactamente <code>${webhook}</code>, que el destinatario sea tu celular, que las llaves estén en <code>${envFile}</code> y que no hayas mezclado el token de otra persona.</li>
</ul>
${problemsMock}
</div>

<div class="wa-card" id="wa-9">
<h2>9. Pasar a un número real después</h2>
<ol>
<li>Cuando el número de prueba ya funcione, puedes verificar un número real tuyo en tu propio Business.</li>
<li>Sigue siendo <strong>otra</strong> cuenta, otro token y el mismo webhook de esta instancia.</li>
<li>Entrega las llaves nuevas por el formulario seguro. No copies las de Rafael ni las de nadie más.</li>
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
<p class="wa-foot"><a class="wa-link" href="/amp/dashboard">Volver al panel</a> · <a class="wa-link" href="/ayuda">Ayuda</a> · <a class="wa-link" href="/ayuda/empresa">Tu empresa</a></p>
</main>`;

  for (const banned of FORBIDDEN_SECRET_WORDS) {
    if (html.includes(banned)) {
      throw new Error('whatsapp setup page leaked a secret marker');
    }
  }
  if (cfg.otherAssistant && html.includes(cfg.otherAssistant)) {
    throw new Error('whatsapp setup page leaked the other edition');
  }
  if (!html.includes(AYUDA_OPENER)) {
    throw new Error('whatsapp setup page missing manito opener');
  }
  return html;
}
