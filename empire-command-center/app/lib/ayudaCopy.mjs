/** Shared Spanish help copy. Plain JS so Node 20 can import it. */

export const AYUDA_OPENER = '¡Quiubo manito!';

export const KEYS_HANDOFF =
  'Las llaves no van en el chat ni en esta página. Cuando las tengas, avísale a Rafael y él te dice cómo entregárselas de forma segura.';

export function ayudaOpenerHtml(extraStyle = '') {
  return `<p class="ayuda-opener" data-ayuda-opener="1" style="font-family:'Playfair Display',Georgia,serif;font-size:28px;line-height:1.2;margin:8px 0 12px;color:#2D2A26;${extraStyle}">${AYUDA_OPENER}</p>`;
}
