// Edition profile for the v3 shell and Max home. The main studio is Rafael's Empire.
// Family editions (Max-e / AMP, Maxine) are picked at build time from
// NEXT_PUBLIC_EMPIRE_EDITION and only ever read their own backend, so nothing here
// leaks across editions. Family editions speak Spanish (T() below).
export type RailKey =
  | 'max' | 'workroom' | 'craft' | 'construction' | 'amp' | 'lead' | 'social' | 'market' | 'finance' | 'comms' | 'docs' | 'system'
  | 'cibernettic' | 'empresas' | 'crm' | 'lots' | 'works' | 'sales' | 'payments' | 'help';

export interface RailItem { key: RailKey; label: string; product?: string; screen?: string; section?: string; href: string; hint: string }

export interface EditionProfile {
  id: 'empire' | 'amp' | 'maxine';
  family: boolean;
  lang: 'en' | 'es';
  ownerName: string;
  ownerFullName: string;
  ownerInitials: string;
  assistantName: string;
  wordmark: string;
  homeUser: string; // key for /home-center lists
  rail: RailItem[];
  /** bottom rail entry: System on the main studio, Help on family editions (no host stats there) */
  footItem: RailItem;
  /** neutral starter topics the user can add with one tap (nothing is pre-filled) */
  interestSuggestions: { name: string; icon: string }[];
  goalSuggestions: string[];
  learningPlaceholder: string;
  askChips: string[];
  /** Improvements launch Cursor builds on the Empire repo: main studio only. */
  showImprovements: boolean;
}

const item = (key: RailKey, label: string, target: { product?: string; screen?: string; section?: string; href?: string }, hint: string): RailItem => ({
  key, label, ...target,
  href: target.href || (target.product
    ? `/?product=${target.product}${target.section ? `&section=${target.section}` : ''}`
    : target.screen ? `/?screen=${target.screen}` : '/'),
  hint,
});

const EMPIRE: EditionProfile = {
  id: 'empire',
  family: false,
  lang: 'en',
  ownerName: 'Rafael',
  ownerFullName: 'Rafael Giraldo',
  ownerInitials: 'RG',
  assistantName: 'Max',
  wordmark: 'EMPIRE',
  homeUser: 'owner',
  rail: [
    item('workroom', 'Workroom', { product: 'workroom' }, 'Drapery & upholstery: jobs, quotes, invoices'),
    item('craft', 'WoodCraft', { product: 'craft' }, 'CNC and woodwork jobs'),
    item('construction', 'Construct.', { product: 'construction' }, 'ConstructionForge projects and lots'),
    item('amp', 'Max-e', { product: 'amp' }, 'AMP coaching edition'),
    item('lead', 'LeadForge', { product: 'lead' }, 'Prospects, pipeline, approvals'),
    item('social', 'Social', { product: 'social' }, 'SocialForge posts and DMs'),
    item('market', 'Market', { product: 'market' }, 'MarketForge listings'),
    item('finance', 'Finance', { screen: 'invoices' }, 'Invoices, payments, overdue'),
    item('comms', 'Comms', { screen: 'inbox' }, 'Inbox and messages'),
    item('docs', 'Docs', { screen: 'final-docs' }, 'Final estimates, invoices, drawings'),
  ],
  footItem: item('system', 'System', { product: 'system' }, 'Services, health, improvements'),
  interestSuggestions: [
    { name: 'AI & Tech', icon: 'cpu' }, { name: 'Markets', icon: 'trend' }, { name: 'Making & CNC', icon: 'tool' },
    { name: 'Real Estate', icon: 'home' }, { name: 'Health', icon: 'heart' }, { name: 'Design', icon: 'layers' },
  ],
  goalSuggestions: ['Read 12 books', 'Finish a certification', 'Ship a personal project'],
  learningPlaceholder: 'Course or book, e.g. CNC toolpaths',
  askChips: ['Brief me on today', 'What needs my approval?', 'Research a topic for me'],
  showImprovements: true,
};

/** Max-e: Juan Diego Giraldo. AMP coaching plus Cibernettic IT. */
const AMP: EditionProfile = {
  id: 'amp',
  family: true,
  lang: 'es',
  ownerName: 'Juan Diego',
  ownerFullName: 'Juan Diego Giraldo',
  ownerInitials: 'JG',
  assistantName: 'Max-e',
  wordmark: 'MAX-E',
  homeUser: 'owner',
  rail: [
    item('amp', 'AMP', { product: 'amp' }, 'AMP: coaching, cursos y coachees'),
    item('cibernettic', 'Cibernettic', { href: '/amp/empresas/cibernettic' }, 'Cibernettic: servicios de TI'),
    item('empresas', 'Empresas', { href: '/amp/empresas' }, 'Tus empresas y proyectos'),
    item('crm', 'Coachees', { product: 'crm' }, 'Coachees y clientes'),
    item('lead', 'Ingreso', { product: 'lead' }, 'Prospectos y seguimientos'),
    item('social', 'Social', { product: 'social' }, 'SocialForge: publicaciones'),
    item('finance', 'Finanzas', { screen: 'invoices' }, 'Facturas y pagos'),
    item('comms', 'Mensajes', { screen: 'inbox' }, 'Bandeja y mensajes'),
    item('docs', 'Docs', { screen: 'final-docs' }, 'Documentos finales'),
  ],
  footItem: item('help', 'Ayuda', { href: '/ayuda' }, 'Ayuda y dispositivos'),
  interestSuggestions: [
    { name: 'Coaching', icon: 'heart' }, { name: 'Ciberseguridad', icon: 'cpu' }, { name: 'IA y tecnología', icon: 'cpu' },
    { name: 'Liderazgo', icon: 'trend' }, { name: 'Bienestar', icon: 'heart' }, { name: 'Redes y nube', icon: 'layers' },
  ],
  goalSuggestions: ['Lanzar un curso AMP', 'Sacar una certificación de TI', 'Leer 12 libros'],
  learningPlaceholder: 'Curso o libro, p. ej. Azure o coaching',
  askChips: ['Resúmeme el día', '¿Qué necesita mi aprobación?', 'Investiga un tema por mí'],
  showImprovements: false,
};

/** Maxine: Camilo Giraldo. Real estate, lots and construction on ConstructionForge. */
const MAXINE: EditionProfile = {
  id: 'maxine',
  family: true,
  lang: 'es',
  ownerName: 'Camilo',
  ownerFullName: 'Camilo Giraldo',
  ownerInitials: 'CG',
  assistantName: 'Maxine',
  wordmark: 'MAXINE',
  homeUser: 'owner',
  rail: [
    item('construction', 'Portafolio', { product: 'construction' }, 'Proyectos de ConstructionForge'),
    item('lots', 'Lotes', { product: 'construction', section: 'lotmap' }, 'Mapa de lotes y disponibilidad'),
    item('works', 'Obra', { product: 'construction', section: 'construction' }, 'Avance de obra'),
    item('crm', 'Compradores', { product: 'construction', section: 'buyers' }, 'Compradores y ventas'),
    item('payments', 'Pagos', { product: 'construction', section: 'payments' }, 'Pagos y planes de pago'),
    item('lead', 'Prospectos', { product: 'lead' }, 'Prospectos y seguimientos'),
    item('social', 'Contenido', { product: 'social' }, 'Publicaciones y contenido'),
    item('comms', 'Mensajes', { screen: 'inbox' }, 'Bandeja y mensajes'),
    item('docs', 'Docs', { screen: 'final-docs' }, 'Documentos finales'),
  ],
  footItem: item('help', 'Ayuda', { href: '/ayuda' }, 'Ayuda y dispositivos'),
  interestSuggestions: [
    { name: 'Finca raíz', icon: 'home' }, { name: 'Construcción', icon: 'tool' }, { name: 'Mercado de lotes', icon: 'trend' },
    { name: 'Urbanismo', icon: 'layers' }, { name: 'Financiación', icon: 'trend' }, { name: 'Diseño', icon: 'layers' },
  ],
  goalSuggestions: ['Vender 10 lotes', 'Terminar la etapa 1', 'Leer 12 libros'],
  learningPlaceholder: 'Curso o libro, p. ej. presupuestos de obra',
  askChips: ['Resúmeme el día', '¿Qué necesita mi aprobación?', 'Investiga un tema por mí'],
  showImprovements: false,
};

function pickEdition(): EditionProfile {
  const e = (process.env.NEXT_PUBLIC_EMPIRE_EDITION || '').trim().toLowerCase();
  if (e === 'amp') return AMP;
  if (e === 'maxine') return MAXINE;
  return EMPIRE;
}

export const EDITION: EditionProfile = pickEdition();

/** Bottom rail entry (kept for older imports). */
export const SYSTEM_ITEM: RailItem = EDITION.footItem;

const ES: Record<string, string> = {
  // shell
  'All': 'Todo', 'All modules': 'Todos los módulos', 'FORGES': 'NEGOCIOS', 'Businesses': 'Negocios', 'Close': 'Cerrar',
  'Notifications': 'Notificaciones', 'Sections': 'Secciones', 'Home sections': 'Secciones', 'soon': 'pronto', 'dev': 'en desarrollo',
  'All businesses and modules': 'Todos los negocios y módulos', 'Modules': 'Módulos',
  // nav groups / items
  'Command': 'Comando', 'Business': 'Negocio', 'Tools': 'Herramientas', 'Growth / Channels': 'Crecimiento / Canales', 'System': 'Sistema', 'More': 'Más',
  "Owner's Desk": 'Centro de mando', 'Final Docs': 'Documentos finales', 'Business Profile': 'Perfil del negocio', 'Pricing Studio': 'Precios',
  'AI Vision': 'Visión IA', 'Improvements': 'Mejoras', 'Tokens & Costs': 'Tokens y costos', 'Developer Panel': 'Panel de desarrollo',
  // home
  'Research': 'Investigación', 'Growth': 'Crecimiento', 'Today': 'Hoy', 'Tomorrow': 'Mañana', 'Your interests': 'Tus intereses',
  'Edit': 'Editar', 'Done': 'Listo', 'Loading…': 'Cargando…', 'Goals': 'Metas', 'Learning': 'Aprendizaje', 'Projects': 'Proyectos',
  'Personal project': 'Proyecto personal', 'Add': 'Agregar', 'Add one': 'Agrega uno', 'None yet.': 'Nada todavía.', 'steps': 'pasos',
  'Analyzing…': 'Analizando…', 'Nothing needs attention.': 'Nada necesita tu atención.', 'Open': 'Abrir', 'Review': 'Revisar',
  'Schedule': 'Agenda', 'Approvals': 'Aprobaciones', 'Reminders': 'Recordatorios', 'Tasks': 'Tareas', 'No data': 'Sin datos',
  'Nothing waiting for approval.': 'Nada espera tu aprobación.', 'No open tasks.': 'No hay tareas abiertas.',
  'No calendar connected': 'Sin calendario conectado', 'Nothing scheduled on jobs in the next 7 days.': 'Nada agendado en los próximos 7 días.',
  'From job dates · no calendar connected': 'De las fechas de trabajos · sin calendario conectado',
  'Checking…': 'Revisando…', 'Nothing in progress': 'Nada en curso', 'Gathering your day…': 'Preparando tu día…',
  'All quiet. Nothing needs you right now.': 'Todo en calma. Nada te necesita ahora.', 'All businesses': 'Todos los negocios',
  'PULSE': 'PULSO', 'Business pulse': 'Pulso del negocio', 'ONLINE': 'EN LÍNEA', 'DEGRADED': 'DEGRADADO', 'CHECKING': 'REVISANDO', 'NO SIGNAL': 'SIN SEÑAL',
  'Good morning': 'Buenos días', 'Good afternoon': 'Buenas tardes', 'Good evening': 'Buenas noches', 'Send': 'Enviar',
  'Ask': 'Pregúntale a', 'Add a topic': 'Agrega un tema', 'Suggestions': 'Sugerencias', 'more': 'más',
  'Finance': 'Finanzas', 'Invoice recovery': 'Cobro de facturas', 'Quote follow-up': 'Seguimiento de cotizaciones', 'Lead follow-up': 'Seguimiento de prospectos',
  'Quotes ready to send': 'Cotizaciones listas para enviar', 'Payment reminders': 'Recordatorios de pago',
  'Slide': 'Diapositiva', 'of': 'de',
  // job hub
  'Jobs': 'Trabajos', 'Job': 'Trabajo', 'Back': 'Volver', 'Documents': 'Documentos', 'Photos': 'Fotos', 'Timeline': 'Historial',
  'Client': 'Cliente', 'Status': 'Estado', 'Balance': 'Saldo', 'Total': 'Total', 'Paid': 'Pagado', 'Notes': 'Notas',
};

/** UI string in the edition language. English is the key; unknown strings stay English. */
export function T(en: string): string {
  return EDITION.lang === 'es' ? (ES[en] ?? en) : en;
}

/** Date/number locale for the edition. */
export const LOCALE = EDITION.lang === 'es' ? 'es-CO' : 'en-US';
