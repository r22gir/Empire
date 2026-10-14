/** Maxine only. Do not add the other family edition, her brother, or Dell paths. */

export const FAMILY_EDITION = {
  id: 'maxine',
  assistant: 'Maxine',
  siteHost: 'maxine.empirebox.store',
  siteUrl: 'https://maxine.empirebox.store',
  webhookUrl: 'https://maxine.empirebox.store/api/v1/whatsapp/webhook',
  trade: 'inmuebles, construcción y desarrollo',
  voiceExample: 'una nota de voz sobre el lote 12, etapa cimentación',
  photoExample: 'la foto de la obra, del lote o del avance de estructura',
  draftExample: 'el borrador del plan de pagos, de la reserva o de la disponibilidad del lote',
  reuseWarning: 'No reutilices llaves ni números de otra instancia.',
  firstTest: 'Manda un texto o una nota de voz al número de prueba, por ejemplo: “reserva el lote 12, cuota inicial 30%, saldo en 24 meses”.',
  chatsPath: '/whatsapp/chats',
  setupPath: '/ayuda/whatsapp',
  homePath: '/',
  empresaHeadline: 'Tu proyecto de inmuebles y construcción',
  empresaLead: 'Aquí viven el portafolio, los lotes, la obra, los compradores y los planes de pago. El lote no cambia de estado y el precio no se inventa: lo dices tú. WhatsApp arma borradores; nunca escribe a clientes.',
  empresaLabel: 'Tu proyecto',
  screens: [
    { href: '/', title: 'Centro de mando', note: 'Chat, voz y el pulso del día.' },
    { href: '/?product=construction', title: 'Portafolio', note: 'Proyectos de construcción e inmuebles.' },
    { href: '/?product=construction&section=lotmap', title: 'Lotes', note: 'Mapa de lotes y disponibilidad.' },
    { href: '/?product=construction&section=construction', title: 'Obra', note: 'Avance de obra y etapas (cimentación, estructura).' },
    { href: '/?product=construction&section=buyers', title: 'Compradores', note: 'Reservas y ventas. El estado del lote solo cambia cuando tú confirmas.' },
    { href: '/?product=construction&section=payments', title: 'Planes de pago', note: 'Cuota inicial y saldo. El precio lo dices tú.' },
    { href: '/ayuda/whatsapp', title: 'WhatsApp', note: 'Notas de voz, fotos de obra y borradores. Nunca escribe a clientes.' },
    { href: '/whatsapp/chats', title: 'Chats', note: 'Solo lectura. Revisa el primer mensaje de prueba.' },
    { href: '/ayuda/voz', title: 'Cómo usar la voz', note: 'Dicta lote, etapa y plan de pagos.' },
    { href: '/ayuda/dispositivos', title: 'Dispositivos', note: 'Celular, tableta o computador.' },
  ],
};

export function familyEdition(edition) {
  const key = String(edition || '').trim().toLowerCase().replace(/-/g, '_');
  if (key === 'maxine') return 'maxine';
  return null;
}
