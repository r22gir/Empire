/** Max-e only. Do not add the other family edition or her host here. */

export const FAMILY_EDITION = {
  id: 'amp',
  assistant: 'Max-e',
  siteHost: 'amp.empirebox.store',
  siteUrl: 'https://amp.empirebox.store',
  webhookUrl: 'https://amp.empirebox.store/api/v1/whatsapp/webhook',
  trade: 'coaching y tus propias empresas',
  voiceExample: 'una nota de voz sobre el programa de coaching o una propuesta de Cibernettic',
  photoExample: 'la foto de un taller, un tablero de curso o un contrato en borrador',
  draftExample: 'el borrador de una cotización, un plan de membresía o una orden de trabajo',
  reuseWarning: 'No uses la cuenta, las llaves ni el número de Rafael. Esta instancia es solo tuya.',
  firstTest: 'Manda un texto o una nota de voz al número de prueba, por ejemplo: “arma el borrador del curso de liderazgo”.',
  chatsPath: '/amp/whatsapp/chats',
  setupPath: '/ayuda/whatsapp',
  homePath: '/amp/dashboard',
  empresaHeadline: 'Tu empresa en Max-e',
  empresaLead: 'Aquí viven AMP (coaching) y Cibernettic (TI), más las empresas que tú armes. Nada se publica solo. Los documentos salen en borrador hasta que los apruebas.',
  empresaLabel: 'Tu empresa',
  screens: [
    { href: '/', title: 'Centro de mando', note: 'Chat, voz y el pulso del día.' },
    { href: '/amp/dashboard', title: 'Panel AMP', note: 'Cursos, afirmaciones y el tablero de AMP.' },
    { href: '/amp/cursos', title: 'Cursos', note: 'Programas, membresías y material de coaching.' },
    { href: '/amp/empresas', title: 'Empresas', note: 'AMP, Cibernettic y las que agregues.' },
    { href: '/amp/empresas/entrevista', title: 'Entrevista de empresa', note: 'Una pregunta por pantalla para armar una empresa.' },
    { href: '/amp/empresas/cibernettic', title: 'Cibernettic', note: 'Propuestas, SLA, órdenes de trabajo y facturas.' },
    { href: '/ayuda/whatsapp', title: 'WhatsApp', note: 'Voz, fotos y borradores. Nunca escribe a clientes.' },
    { href: '/amp/whatsapp/chats', title: 'Chats', note: 'Solo lectura. Revisa el primer mensaje de prueba.' },
    { href: '/ayuda/voz', title: 'Cómo usar la voz', note: 'Dicta y arma el borrador.' },
    { href: '/ayuda/dispositivos', title: 'Dispositivos', note: 'Celular, tableta o computador.' },
  ],
};

export function familyEdition(edition) {
  const key = String(edition || '').trim().toLowerCase().replace(/-/g, '_');
  if (key === 'amp' || key === 'max_e' || key === 'maxe') return 'amp';
  return null;
}
