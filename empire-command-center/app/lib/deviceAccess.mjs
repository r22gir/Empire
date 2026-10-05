/** Spanish device-access guide. Plain JS so Node 20 can import it. */

const SITES = {
  amp: { name: 'Max-e', url: 'https://amp.empirebox.store' },
  maxine: { name: 'Maxine', url: 'https://maxine.empirebox.store' },
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

export function renderDeviceAccessPage(edition) {
  const family = familyEdition(edition);
  const site = family ? SITES[family] : null;
  const other = family === 'amp' ? SITES.maxine : family === 'maxine' ? SITES.amp : null;
  const name = site ? escapeHtml(site.name) : 'tu Max';
  const url = site ? escapeHtml(site.url) : '';
  const intro = site
    ? `Hola. Esta página es solo de ${name}. Úsala en el celular, la tableta o el computador.`
    : 'Abre esta guía dentro de tu propio centro de mando.';
  const website = site
    ? `<p>Abre <a href="${url}">${url}</a> en cualquier celular, tableta o computador. Entra con el correo que tienes autorizado. La página es HTTPS, así que el micrófono y Live Voice funcionan.</p>`
    : '<p>Abre la dirección de tu edición en cualquier celular, tableta o computador. Entra con el correo que tienes autorizado. La página es HTTPS, así que el micrófono y Live Voice funcionan.</p>';
  const tailscale = site
    ? `<p>Si prefieres una red privada, Rafael puede compartirte solo el Dell por Tailscale. Ese acceso queda limitado a tu propio ${name}. Instala Tailscale, acepta la invitación y usa el enlace privado que te envíe.</p>`
    : '<p>Si prefieres una red privada, Rafael puede compartirte solo el Dell por Tailscale, limitado a tu propio Max. Instala Tailscale, acepta la invitación y usa el enlace privado que te envíe.</p>';

  const html = `<main style="max-width:720px;margin:0 auto;padding:32px 20px;font-family:Inter,sans-serif;color:#1a1a1a">
<nav aria-label="Navegación de ayuda" style="display:flex;flex-wrap:wrap;gap:16px;margin-bottom:24px;font-size:14px"><a href="/ayuda" style="color:#b8960c;font-weight:700">← Volver a Ayuda</a><a href="/" style="color:#444;font-weight:600">Centro de mando</a></nav>
<p style="font-size:12px;letter-spacing:0.4px;color:#b8960c;font-weight:700;margin:0">CENTRO DE MANDO</p>
<h1 style="font-size:32px;margin:8px 0">Cómo conectarte desde tus dispositivos</h1>
<p style="font-size:16px;line-height:1.5">${intro}</p>
<h2>1. Sitio web (recomendado)</h2>
${website}
<h3>iPhone</h3>
<ol>
<li>Abre la página en Safari.</li>
<li>Toca el botón Compartir.</li>
<li>Elige Agregar a pantalla de inicio.</li>
<li>Toca Agregar.</li>
</ol>
<h3>Android</h3>
<ol>
<li>Abre la página en Chrome.</li>
<li>Toca los tres puntos.</li>
<li>Elige Agregar a pantalla principal, o Instalar aplicación.</li>
<li>Confirma.</li>
</ol>
<h2>2. Tailscale, si prefieres una red privada</h2>
${tailscale}
<h2>3. WhatsApp, pronto</h2>
<p>Más adelante podrás mandar notas de voz y texto a ${name} desde tu número autorizado. Todavía no está listo.</p>
<p><a href="/ayuda" style="color:#b8960c;font-weight:700">Volver a Ayuda</a></p>
</main>`;

  if (other && (html.includes(other.url) || html.includes(other.name))) {
    throw new Error('device access page leaked the other edition');
  }
  return html;
}
