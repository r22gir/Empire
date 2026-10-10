/** Spanish WhatsApp setup guide. Plain JS so Node 20 can import it.
 *
 * Secrets are never rendered. Owner numbers live only in the Dell env file.
 * Maxine reuses this via edition config (construction copy, no legal details).
 */

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

export function renderWhatsAppSetupPage(edition, extras = {}) {
  const cfg = setupConfig(edition);
  if (!cfg) {
    return `<main style="max-width:720px;margin:0 auto;padding:32px 20px;font-family:Nunito,sans-serif;color:#2D2A26">
<p>Abre esta guía dentro de tu propio centro de mando (Max-e o Maxine).</p>
</main>`;
  }
  const name = escapeHtml(cfg.assistant);
  const owner = escapeHtml(cfg.ownerFirst);
  const webhook = escapeHtml(cfg.webhookUrl);
  const envFile = escapeHtml(cfg.envFile);
  const site = escapeHtml(cfg.siteUrl);
  const trade = escapeHtml(cfg.trade);
  const last4 = Array.isArray(extras.ownerLast4) ? extras.ownerLast4.map((n) => String(n).replace(/\D/g, '').slice(-4)).filter(Boolean) : [];
  const last4Note = last4.length
    ? `El archivo de esta instancia ya tiene un número que termina en ···${escapeHtml(last4[0])}. Confirma que es el tuyo.`
    : 'Rafael pone tu número solo en el archivo de secretos del Dell. Esta página no lo muestra completo.';

  const html = `<main style="max-width:720px;margin:0 auto;padding:20px 16px 72px;font-family:Nunito,sans-serif;color:#2D2A26;background:#FFF9F0;min-height:100vh;box-sizing:border-box">
<p style="letter-spacing:1px;color:#D4A030;font-weight:800;font-size:12px;margin:16px 0 4px">${name.toUpperCase()} · CENTRO DE MANDO</p>
<h1 style="font-family:'Playfair Display',serif;font-size:32px;margin:0 0 8px">WhatsApp de ${name}</h1>
<p style="font-size:16px;line-height:1.55">Hola ${owner}. Esta guía es solo para <strong>tu</strong> ${name} en ${site}. Vas a crear <strong>tu propia cuenta nueva de Meta / WhatsApp</strong> — no la de Rafael y no el número del Workroom.</p>
<p style="font-size:15px;line-height:1.55">Sirve para ${trade}. Nada se envía a clientes. Tope de uso: <strong>20%</strong>. Los secretos no se escriben aquí ni en el chat: van por la solicitud segura de secretos a <code>${envFile}</code>.</p>

<div style="background:#fff;border:1px solid #F0E6D8;border-radius:16px;padding:16px;margin-top:16px">
<h2 style="margin:0 0 8px;font-size:20px">Antes de empezar</h2>
<ol>
<li>Tu celular con WhatsApp.</li>
<li>Tu Facebook personal (cuenta nueva o la tuya — <strong>no la de Rafael</strong>).</li>
<li>Un navegador en este sitio.</li>
</ol>
<p><strong>Punto de control:</strong> confirmas que la cuenta de Meta es tuya, no del Workroom.</p>
</div>

<div style="background:#fff;border:1px solid #F0E6D8;border-radius:16px;padding:16px;margin-top:16px">
<h2 style="margin:0 0 8px;font-size:20px">1. Meta for Developers</h2>
<ol>
<li>Abre <a href="https://developers.facebook.com" style="color:#D4A030;font-weight:700">developers.facebook.com</a>.</li>
<li>Entra con <strong>tu</strong> Facebook.</li>
<li>Acepta las condiciones de desarrollador.</li>
</ol>
<p><strong>Punto de control:</strong> ves el panel de tus apps, no las de Rafael.</p>
</div>

<div style="background:#fff;border:1px solid #F0E6D8;border-radius:16px;padding:16px;margin-top:16px">
<h2 style="margin:0 0 8px;font-size:20px">2. App de tipo Negocios + producto WhatsApp</h2>
<ol>
<li>Crea una app tipo <strong>Negocios / Business</strong>.</li>
<li>Ponle un nombre tuyo (por ejemplo “${name} WhatsApp”).</li>
<li>Agrega el producto <strong>WhatsApp</strong>.</li>
</ol>
<p><strong>Punto de control:</strong> la app aparece en tu cuenta, no en el Workroom.</p>
</div>

<div style="background:#fff;border:1px solid #F0E6D8;border-radius:16px;padding:16px;margin-top:16px">
<h2 style="margin:0 0 8px;font-size:20px">3. Número de prueba de Meta (sandbox)</h2>
<ol>
<li>En WhatsApp → API Setup usa el <strong>número de prueba de Meta</strong>. No pidas el SIM del Workroom.</li>
<li>Añade como destinatario de prueba <strong>tu celular</strong> (el que Rafael guarda en <code>WHATSAPP_OWNER_NUMBERS</code> de esta instancia).</li>
<li>Meta te manda un código de 6 dígitos. Verifícalo en tu teléfono.</li>
</ol>
<p>${last4Note}</p>
<p><strong>Punto de control:</strong> el sandbox acepta solo tu número. No el de Rafael.</p>
</div>

<div style="background:#fff;border:1px solid #F0E6D8;border-radius:16px;padding:16px;margin-top:16px">
<h2 style="margin:0 0 8px;font-size:20px">4. Token permanente, IDs y secretos</h2>
<ol>
<li>Copia el <em>Phone Number ID</em> (solo el ID, no el token).</li>
<li>Genera un <strong>token permanente</strong> de usuario del sistema (no el token de 24 horas).</li>
<li>Copia el <em>App Secret</em> y elige un <em>Verify Token</em> largo y aleatorio.</li>
</ol>
<p style="background:#FFF4D6;border-radius:12px;padding:12px"><strong>No los escribas en esta página ni en el chat con Max.</strong> Pídelos por la solicitud segura de secretos. Rafael (o el operador) los pone solo en <code>${envFile}</code>:</p>
<ul>
<li><code>WHATSAPP_ACCESS_TOKEN</code></li>
<li><code>WHATSAPP_PHONE_NUMBER_ID</code></li>
<li><code>WHATSAPP_VERIFY_TOKEN</code></li>
<li><code>WHATSAPP_APP_SECRET</code></li>
<li><code>WHATSAPP_OWNER_NUMBERS</code> (solo tu número)</li>
</ul>
<p><strong>Punto de control:</strong> el archivo del Dell tiene los valores. Esta página sigue vacía.</p>
</div>

<div style="background:#fff;border:1px solid #F0E6D8;border-radius:16px;padding:16px;margin-top:16px">
<h2 style="margin:0 0 8px;font-size:20px">5. Webhook</h2>
<ol>
<li>En Meta, Callback URL:</li>
</ol>
<p style="font-family:ui-monospace,monospace;background:#2D2A26;color:#FFF9F0;padding:12px;border-radius:10px;word-break:break-all">${webhook}</p>
<ol start="2">
<li>Verify token: el mismo que fue a <code>${envFile}</code>.</li>
<li>Suscríbete al campo <strong>messages</strong>.</li>
<li>Pulsa Verificar y guardar. Meta hace GET a esta instancia.</li>
</ol>
<p><strong>Punto de control:</strong> Meta muestra el webhook verificado. Si falla, Rafael confirma que ${escapeHtml(cfg.siteHost)} apunta al puerto ${cfg.backendPort}.</p>
</div>

<div style="background:#fff;border:1px solid #F0E6D8;border-radius:16px;padding:16px;margin-top:16px">
<h2 style="margin:0 0 8px;font-size:20px">6. Prueba (solo tú)</h2>
<ol>
<li>Desde tu celular, manda un texto al número de prueba de Meta.</li>
<li>${name} responde en español. No crea carpetas del Workroom.</li>
<li>Revisa <a href="/amp/whatsapp/chats" style="color:#D4A030;font-weight:700">Chats (solo lectura)</a>.</li>
</ol>
<p><strong>Punto de control:</strong> un mensaje tuyo aparece. Nada se envía a clientes. El PDF solo sale si tú dices “envía el borrador” a ti mismo.</p>
</div>

<div style="background:#fff;border:1px solid #F0E6D8;border-radius:16px;padding:16px;margin-top:16px">
<h2 style="margin:0 0 8px;font-size:20px">Límites de esta fase</h2>
<ul>
<li>Borrador solamente. No hay envíos a clientes.</li>
<li>Tope de uso 20%. Modelo incluido: MiniMax.</li>
<li>No se publica nada. No se mezcla con el Workroom.</li>
</ul>
</div>
<p style="margin-top:24px"><a href="/amp/dashboard" style="color:#D4A030;font-weight:700">Volver al panel</a> · <a href="/ayuda" style="color:#D4A030;font-weight:700">Ayuda</a></p>
</main>`;

  for (const banned of FORBIDDEN_SECRET_WORDS) {
    if (html.includes(banned)) {
      throw new Error('whatsapp setup page leaked a secret marker');
    }
  }
  if (cfg.otherAssistant && html.includes(cfg.otherAssistant)) {
    throw new Error('whatsapp setup page leaked the other edition');
  }
  return html;
}
