/** Family-edition chrome. Plain JS so Node 20 can import it. */

export function isFamilyEdition(edition) {
  const key = String(edition || '').trim().toLowerCase();
  return key === 'amp' || key === 'maxine';
}

export function assistantFallback(edition) {
  const key = String(edition || '').trim().toLowerCase();
  if (key === 'maxine') return 'Maxine';
  if (key === 'amp') return 'Max-e';
  return 'MAX';
}

export function navGroupLabel(edition, key, english) {
  if (!isFamilyEdition(edition)) return english;
  if (key === 'command') return 'Comando';
  if (key === 'business') return 'Negocio';
  return english;
}

export function dailySummaryLabel(edition) {
  return isFamilyEdition(edition) ? 'Resumen del día' : 'Daily Summary';
}

export function searchPlaceholder(edition) {
  return isFamilyEdition(edition) ? 'Buscar cualquier cosa...' : 'Search anything...';
}

export function presentationChrome(edition, assistantName) {
  const family = isFamilyEdition(edition);
  const name = (assistantName || '').trim() || assistantFallback(edition);
  if (!family) {
    return {
      header: 'MAX — Empire AI',
      presentation: 'Presentation',
      compact: 'Compact',
      text: 'Text',
      presentationMode: 'Presentation Mode',
      compactMode: 'Compact Mode',
      textMode: 'Text Mode',
      ask: 'Ask MAX anything.',
      voice: 'Voice + avatar active.',
      textOnly: 'Text responses only.',
      cycle: 'Ctrl+Shift+P to cycle modes',
      thinking: 'MAX is thinking...',
      listening: 'Listening...',
      stop: 'Stop recording',
      start: 'Start voice input',
      placeholder: 'Type or ask MAX...',
      send: 'Send message',
      connected: 'Connected',
      disconnected: 'Disconnected',
      desks: '18 desks',
      quality: 'Quality engine active',
      withVoice: 'with voice',
      loading: 'Loading avatar...',
      expand: 'Expand to Presentation mode',
      simliOff: 'Simli off — TalkingHead',
      simliFace: 'Simli face only',
      session: 'session',
    };
  }
  return {
    header: name,
    presentation: 'Presentación',
    compact: 'Compacto',
    text: 'Texto',
    presentationMode: 'Modo presentación',
    compactMode: 'Modo compacto',
    textMode: 'Modo texto',
    ask: `Pregúntale a ${name}.`,
    voice: 'Voz y avatar activos.',
    textOnly: 'Solo texto.',
    cycle: 'Ctrl+Shift+P cambia el modo',
    thinking: `${name} está pensando...`,
    listening: 'Escuchando...',
    stop: 'Detener',
    start: 'Hablar',
    placeholder: `Escribe o pregunta a ${name}...`,
    send: 'Enviar',
    connected: 'Conectado',
    disconnected: 'Sin conexión',
    desks: '18 escritorios',
    quality: 'Motor de calidad activo',
    withVoice: 'con voz',
    loading: 'Cargando el avatar...',
    expand: 'Abrir presentación',
    simliOff: 'Simli apagado — TalkingHead',
    simliFace: 'Solo el rostro de Simli',
    session: 'sesión',
  };
}

/** Chat greeting. Family editions use the assistant name in Spanish. */
export function chatWelcome(edition, assistantName) {
  const name = (assistantName || '').trim() || assistantFallback(edition);
  if (!isFamilyEdition(edition)) {
    return "Hello! I'm **MAX**, your Empire AI Assistant.\n\n_Tip: Ctrl+V to paste images · Shift+Enter for newlines_";
  }
  return `¡Hola! Soy **${name}**, tu asistente de EmpireBox.\n\n_Consejo: Ctrl+V para pegar imágenes · Shift+Enter para una línea nueva_`;
}

const FAMILY_HOSTS = new Set(['amp.empirebox.store', 'maxine.empirebox.store']);

export function isFamilyHost(host) {
  const h = String(host || '').split(':')[0].toLowerCase();
  return FAMILY_HOSTS.has(h);
}

export function isFamilySurface(edition, host) {
  return isFamilyEdition(edition) || isFamilyHost(host);
}

export function normalizeFamilyPath(pathname) {
  let path = String(pathname || '/').split('?')[0].split('#')[0] || '/';
  if (!path.startsWith('/')) path = `/${path}`;
  while (path.includes('//')) path = path.split('//').join('/');
  if (path.length > 1 && path.endsWith('/')) path = path.slice(0, -1);
  return path || '/';
}

export function isFamilyPublicPath(pathname) {
  const path = normalizeFamilyPath(pathname);
  if (
    path === '/login'
    || path === '/amp/login'
    || path === '/amp/signup'
    || path === '/amp'
    || path === '/favicon.ico'
    || path === '/robots.txt'
  ) return true;
  if (path.startsWith('/_next/')) return true;
  if (path.startsWith('/api/')) return true;
  return false;
}

/** Logged-out family home and operator pages go to /login. Workroom stays on the shell.
 *  Edition is NEXT_PUBLIC_EMPIRE_EDITION (baked at build). Host covers amp.empirebox.store
 *  even when that env was missing from an old build. */
export function familyHomeRedirect(edition, pathname, hasSession, host) {
  if (!isFamilySurface(edition, host)) return null;
  if (hasSession) return null;
  const path = normalizeFamilyPath(pathname);
  if (isFamilyPublicPath(path)) return null;
  if (path === '/' || path.startsWith('/amp/')) return '/login';
  return null;
}
