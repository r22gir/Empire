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

/** Logged-out family home goes to /login. Workroom stays on the shell. */
export function familyHomeRedirect(edition, pathname, hasSession) {
  if (!isFamilyEdition(edition)) return null;
  if (pathname !== '/') return null;
  if (hasSession) return null;
  return '/login';
}
