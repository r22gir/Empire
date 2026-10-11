/**
 * Spanish text layer for the family editions (Maxine, Max-e).
 *
 * Exact-match dictionary for English UI text that still lives in shared
 * Empire modules. Keys match case-insensitively after trimming, so labels
 * shown in CSS uppercase are covered by their sentence-case key. Brand and
 * module names (ShipForge, SocialForge, …) are left as they are.
 */
export const FAMILY_ES: Record<string, string> = {
  // ── generic UI ──
  'Back': 'Volver', 'Next': 'Siguiente', 'Start': 'Empezar', 'Retry': 'Reintentar', 'Refresh': 'Actualizar',
  'Load': 'Cargar', 'Save': 'Guardar', 'Cancel': 'Cancelar', 'Delete': 'Eliminar', 'Edit': 'Editar', 'Remove': 'Quitar',
  'Close': 'Cerrar', 'Search': 'Buscar', 'Filter': 'Filtrar', 'Export': 'Exportar', 'Import': 'Importar', 'Upload': 'Subir',
  'All': 'Todos', 'New': 'Nuevo', 'Add': 'Agregar', 'View All': 'Ver todo', 'View': 'Ver', 'Actions': 'Acciones',
  'Status': 'Estado', 'Type': 'Tipo', 'Name': 'Nombre', 'Name *': 'Nombre *', 'Email': 'Correo', 'Phone': 'Teléfono',
  'Address': 'Dirección', 'Street Address': 'Dirección', 'City': 'Ciudad', 'State': 'Estado', 'ZIP Code': 'Código postal',
  'Company': 'Empresa', 'Website': 'Sitio web', 'Notes': 'Notas', 'Tags': 'Etiquetas', 'Photo': 'Foto', 'Photos': 'Fotos',
  'Settings': 'Configuración', 'Preferences': 'Preferencias', 'Overview': 'Resumen', 'Dashboard': 'Panel',
  'Analytics': 'Analítica', 'Reports': 'Reportes', 'Statistics': 'Estadísticas', 'Stats': 'Estadísticas',
  'History': 'Historial', 'Log': 'Registro', 'Audit': 'Auditoría', 'Templates': 'Plantillas', 'Docs': 'Guía',
  'Payments': 'Pagos', 'Pricing': 'Precios', 'Plans': 'Planes', 'Subscriptions': 'Suscripciones', 'Invoices': 'Facturas',
  'Orders': 'Pedidos', 'Products': 'Productos', 'Customers': 'Clientes', 'Services': 'Servicios', 'Inventory': 'Inventario',
  'Suppliers': 'Proveedores', 'Employees': 'Empleados', 'Projects': 'Proyectos', 'Schedule': 'Programar', 'Calendar': 'Calendario',
  'Today': 'Hoy', 'This Month': 'Este mes', 'This Week': 'Esta semana', 'Last 30 days': 'Últimos 30 días', 'Daily': 'Diario',
  'Weekly': 'Semanal', 'Monthly': 'Mensual', 'Full Week': 'Semana completa', 'Current': 'Actual', 'Complete': 'Completo',
  'Completed': 'Completado', 'In Progress': 'En curso', 'In progress': 'En curso', 'Open': 'Abiertos', 'Pending': 'Pendiente',
  'Locked': 'Bloqueado', 'Unlocked': 'Desbloqueado', 'Unknown': 'Desconocido', 'N/A': 'N/D', 'Free': 'Gratis', 'Soon': 'Pronto',
  'Synced': 'Sincronizado', 'Sync': 'Sincronizar', 'Sync All': 'Sincronizar todo', 'Connect': 'Conectar', 'Connected': 'Conectado',
  'Disconnect': 'Desconectar', 'Disconnected': 'Desconectado', 'All connected': 'Todo conectado', 'Quick Action': 'Acción rápida',
  'Quick Access': 'Acceso rápido', 'Quick Stats': 'Datos rápidos', 'Revenue': 'Ingresos', 'Revenue MTD': 'Ingresos del mes',
  'Total Revenue': 'Ingresos totales', 'Monthly Revenue': 'Ingresos del mes', 'Total Profit': 'Ganancia total',
  'Transactions': 'Transacciones', 'Breakdown': 'Desglose', 'Pipeline': 'Embudo', 'Rates': 'Tarifas', 'Tracking': 'Seguimiento',
  'Saving...': 'Guardando…', 'Loading...': 'Cargando…', 'Importing...': 'Importando…', 'Verifying...': 'Verificando…',
  'Select type...': 'Selecciona un tipo…', 'currently in progress': 'en curso ahora', 'scheduled this week': 'programados esta semana',
  'from paid invoices': 'de facturas pagadas', 'Total records': 'Registros totales', 'Print / Export PDF': 'Imprimir / exportar PDF',
  'Owner Name': 'Nombre del dueño', 'Contact Info': 'Datos de contacto', 'Location & Service Area': 'Ubicación y zona de servicio',
  'Service Area': 'Zona de servicio', 'Upgrade required': 'Requiere mejorar el plan', 'Current Tier': 'Plan actual',
  'Starter': 'Inicial', 'Pro': 'Pro', 'Approvals': 'Aprobaciones', 'Pending Approvals': 'Aprobaciones pendientes',
  'Approval workflow': 'Flujo de aprobación', 'Blocked by policy': 'Bloqueado por política', 'Manual Override': 'Ajuste manual',
  'Override requires reason': 'El ajuste requiere un motivo', 'Reviewer:': 'Revisor:', 'Source Mode:': 'Modo de origen:',

  // ── Business Profile ──
  'Business Profile': 'Perfil del negocio', 'Used by SocialForge, LuxeForge, quotes, invoices, and AI agents':
    'Lo usan SocialForge, las cotizaciones, las facturas y tu asistente', 'Profile Completion': 'Perfil completo',
  'Business Basics': 'Datos básicos', 'Business Name': 'Nombre del negocio', 'Business Email': 'Correo del negocio',
  'Support Email': 'Correo de soporte', 'Founded Year': 'Año de fundación', 'Tagline': 'Lema', 'Short Bio': 'Descripción corta',
  'Full Bio': 'Descripción completa', 'Branding & Description': 'Marca y descripción', 'Brand Colors': 'Colores de marca',
  'Logo URL': 'URL del logo', 'Target Audience': 'Público objetivo', 'Style Keywords': 'Palabras de estilo', 'Save Profile': 'Guardar perfil',
  'Service Business': 'Negocio de servicios',

  // ── Pricing Studio / nav ──
  "Owner's Desk": 'Centro de mando', 'Owner’s Desk': 'Centro de mando',
  'Pricing Studio': 'Estudio de precios', 'Tokens & Costs': 'Tokens y costos',

  // ── SocialForge ──
  'AI-Powered Social Media Manager': 'Gestor de redes sociales con IA', 'Compose': 'Redactar', 'Accounts': 'Cuentas',
  'Setup Wizard': 'Asistente de configuración', 'New Post': 'Nueva publicación', 'Total Followers': 'Seguidores totales',
  'Engagement Rate': 'Tasa de interacción', 'Connected Accounts': 'Cuentas conectadas', 'Weekly Reach': 'Alcance semanal',
  'Upcoming Scheduled Posts': 'Próximas publicaciones programadas', 'Recent Post Performance': 'Rendimiento reciente',
  'No scheduled posts. Create one to get started!': 'No hay publicaciones programadas. ¡Crea una para empezar!',
  'No posted content yet. Compose and publish posts to see performance data.':
    'Todavía no hay publicaciones. Redacta y publica para ver resultados.',
  'No accounts connected yet. Go to Accounts tab to connect your social profiles.':
    'Todavía no hay cuentas conectadas. Ve a Cuentas para conectar tus redes.',
  'All Scheduled & Draft Posts': 'Publicaciones programadas y borradores', 'Best Time': 'Mejor hora',
  'Best posting time:': 'Mejor hora para publicar:', 'Click to add image or video': 'Haz clic para agregar imagen o video',
  'Compose Post': 'Redactar publicación', 'Connect Account': 'Conectar cuenta', 'Connected successfully!': '¡Conectado!',
  'Content Calendar': 'Calendario de contenido', 'Engagement': 'Interacción', 'Follower Growth (Last 30 Days)':
    'Crecimiento de seguidores (últimos 30 días)', 'Followers': 'Seguidores', 'Generating setup guide...': 'Generando la guía…',
  'Handle': 'Usuario', 'API Token / Handle': 'Token o usuario', 'Hashtags': 'Hashtags', 'Impressions': 'Impresiones',
  'JPG, PNG, MP4 up to 50MB': 'JPG, PNG o MP4 de hasta 50 MB', 'Last Sync': 'Última sincronización',
  'Leave empty to save as draft': 'Déjalo vacío para guardar como borrador', 'Loading SocialForge data...': 'Cargando SocialForge…',
  'Mark Posted': 'Marcar publicada', 'Media': 'Imagen o video', 'No posts in the queue.': 'No hay publicaciones en cola.',
  'Platform': 'Plataforma', 'Platform Breakdown': 'Por plataforma', 'Platforms': 'Plataformas', 'Post Content': 'Contenido',
  'Post Queue': 'Cola de publicaciones', 'Posts': 'Publicaciones', 'Preview': 'Vista previa', 'Reach': 'Alcance',
  'Save as Draft': 'Guardar borrador', 'Schedule (optional)': 'Programar (opcional)', 'Schedule Post': 'Programar publicación',
  'Select one or more platforms to post to': 'Elige una o más redes', 'Setup Guide': 'Guía de configuración',
  'Top Hashtags': 'Hashtags principales', 'Top Performing Posts': 'Mejores publicaciones', 'Total Reach': 'Alcance total',
  'Using your business profile for personalized instructions': 'Uso el perfil del negocio para darte instrucciones a tu medida',
  'Verification failed — check your token and try again.': 'No se pudo verificar. Revisa el token e intenta de nuevo.',
  'Verify & Connect': 'Verificar y conectar', 'Weekly Engagement': 'Interacción semanal',
  'Write your post content here. Be engaging, authentic, and include a call to action...':
    'Escribe aquí tu publicación. Sé cercano, auténtico e incluye una invitación a actuar…',
  'Social Scheduler': 'Programador social', 'Instagram Business': 'Instagram para empresas', 'Facebook Business Page': 'Página de Facebook',
  'LinkedIn Company Page': 'Página de LinkedIn', 'TikTok Business': 'TikTok para empresas', 'Pinterest Business': 'Pinterest para empresas',
  'Google Business Profile': 'Perfil de Google Business', 'Yelp Business': 'Yelp para empresas', 'Nextdoor Business': 'Nextdoor para empresas',
  'Email Marketing': 'Email marketing', 'Domain Email Setup': 'Correo con dominio propio', 'Canva Pro': 'Canva Pro',

  // ── StoreFront / MarketForge / RelistApp ──
  'Store Dashboard': 'Panel de la tienda', 'Retail Store Management': 'Gestión de la tienda', 'Overview of your retail operations':
    'Resumen de la tienda', 'Add Product': 'Agregar producto', 'Import Product URL': 'Importar producto por URL', 'Scan Barcode': 'Escanear código',
  'POS Terminal': 'Punto de venta', 'Gift Cards': 'Tarjetas de regalo', 'Purchase Orders': 'Órdenes de compra', 'Active Orders': 'Pedidos activos',
  'Pending Orders': 'Pedidos pendientes', 'Recent Orders': 'Pedidos recientes', 'No recent orders': 'No hay pedidos recientes',
  'No orders yet': 'Todavía no hay pedidos', 'Orders will appear here once customers start buying': 'Los pedidos aparecerán cuando los clientes compren',
  'New Order': 'Nuevo pedido', 'View Orders': 'Ver pedidos', 'View Reports': 'Ver reportes', 'View Analytics': 'Ver analítica',
  'Process Orders': 'Procesar pedidos', 'Track Order': 'Rastrear pedido', 'MarketForge Dashboard': 'Panel de MarketForge',
  'Multi-marketplace listing management': 'Publicaciones en varios marketplaces', 'Multi-Marketplace': 'Varios marketplaces',
  'Active Listings': 'Publicaciones activas', 'My Listings': 'Mis publicaciones', 'Listings': 'Publicaciones', 'Manage Listings': 'Gestionar publicaciones',
  'View, edit, and manage all product listings': 'Ve, edita y gestiona tus publicaciones', 'Marketplace Status': 'Estado de marketplaces',
  'Marketplaces': 'Marketplaces', 'Sales breakdown by marketplace and product': 'Ventas por marketplace y producto', 'Cross-List': 'Publicar en varios',
  'sold this month': 'vendidos este mes', 'RelistApp Dashboard': 'Panel de RelistApp', 'Drop-ship arbitrage overview': 'Resumen de reventa',
  'Source Products': 'Buscar productos', 'Product Scout': 'Buscador de productos', 'Price Monitor': 'Monitor de precios',
  'Profit Calculator': 'Calculadora de ganancia', 'Smart Lister': 'Publicador inteligente', 'AI Deal Finder': 'Buscador de ofertas con IA',
  'Check All Prices': 'Revisar todos los precios', 'Name A-Z': 'Nombre A-Z', 'Est. Savings': 'Ahorro estimado',
  'Failed to fetch listings: 404': 'No se pudieron cargar las publicaciones.', 'Failed to fetch orders: 404': 'No se pudieron cargar los pedidos.',

  // ── ContractorForge ──
  'ContractorForge Dashboard': 'Panel de ContractorForge', 'Manage projects, contractors, and invoices': 'Proyectos, contratistas y facturas',
  'New Project': 'Nuevo proyecto', 'Active Projects': 'Proyectos activos', 'Recent Projects': 'Proyectos recientes', 'No projects yet': 'Todavía no hay proyectos',
  'Contractors': 'Contratistas', 'Contractor': 'Contratista', 'No contractors yet': 'Todavía no hay contratistas', 'Contractor Availability': 'Disponibilidad de contratistas',
  'Total Invoiced': 'Total facturado', 'New Sale': 'Nueva venta', 'No documents yet': 'Todavía no hay documentos',
  'Active Subscriptions': 'Suscripciones activas', 'Recent Invoices': 'Facturas recientes', 'No invoices yet': 'Todavía no hay facturas',
  "Today's Schedule": 'Agenda de hoy', 'No jobs scheduled today': 'No hay trabajos programados hoy', 'Upcoming Jobs': 'Próximos trabajos',
  'Completed This Month': 'Completados este mes', 'Financials': 'Finanzas', 'Install Plan': 'Plan de instalación',

  // ── ShipForge ──
  'Shipping Dashboard': 'Panel de envíos', 'Shipping Management': 'Gestión de envíos', 'Overview of your shipping operations': 'Resumen de tus envíos',
  'Shipments': 'Envíos', 'shipments': 'envíos', 'Create Shipment': 'Crear envío', 'Ship Now': 'Enviar ahora', 'Ship a new package': 'Enviar un paquete',
  'Track Package': 'Rastrear paquete', 'Compare Rates': 'Comparar tarifas', 'Find the best rate': 'Encuentra la mejor tarifa',
  'Recent Shipments': 'Envíos recientes', 'No shipments yet — create your first label': 'Todavía no hay envíos. Crea tu primera guía.',
  'Awaiting shipment': 'Por enviar', 'Shipped Today': 'Enviados hoy', 'Carrier Breakdown': 'Por transportadora', 'Packages': 'Paquetes',
  'Couriers': 'Transportadoras', 'Fulfill pending orders and track shipments': 'Despacha pedidos y rastrea envíos',
  'Failed to load shipments': 'No se pudieron cargar los envíos',

  // ── SupportForge ──
  'Customer Support Management': 'Atención al cliente', 'Tickets': 'Casos', 'Knowledge Base': 'Base de conocimiento',
  'Failed to load data: 500': 'No se pudieron cargar los datos.',
  'Open Tickets': 'Casos abiertos', 'Recent Tickets': 'Casos recientes', 'Total Tickets': 'Casos totales',
  'Tickets by Priority': 'Casos por prioridad', 'No tickets yet.': 'Todavía no hay casos.', 'total tickets': 'casos en total',
  'Calculated from ticket data': 'Calculado con los casos', 'Quick Actions': 'Acciones rápidas', 'Failed to load data': 'No se pudieron cargar los datos',

  // ── ForgeCRM ──
  'Customer Management': 'Gestión de clientes', 'All Customers': 'Todos los clientes', 'Add Customer': 'Agregar cliente',
  'Create Customer': 'Crear cliente', 'No customers yet': 'Todavía no hay clientes', 'customers': 'clientes',
  'Add a customer or import from your quotes.': 'Agrega un cliente o impórtalo desde tus cotizaciones.',
  'Import from Quotes': 'Importar de cotizaciones', 'Designer': 'Aliado', 'Designers': 'Aliados', 'Residential': 'Residencial',
  'Commercial': 'Comercial', 'VIP': 'VIP', 'Assign to customer': 'Asignar a cliente',

  // ── ArchiveForge / TranscriptForge ──
  'ArchiveForge LIFE Intake': 'Ingreso de ArchiveForge', 'LIFE Listing Engine — V1': 'Motor de publicaciones — V1',
  'Choose input method': 'Elige cómo empezar',
  'Capture the front cover first, then run AI identification and confirm the reference match.':
    'Primero toma la foto de la portada, luego corre la identificación con IA y confirma la coincidencia.', 'Start with Photo': 'Empezar con foto', 'Take Photo': 'Tomar foto', 'Upload Photo': 'Subir foto',
  'Manual Entry': 'Ingreso manual', 'Search Issue': 'Buscar edición', 'Search Known Issue': 'Buscar edición conocida',
  'Use date, person, event, or cover subject when the issue is already known.': 'Usa fecha, persona, evento o tema de portada si ya conoces la edición.',
  'Load Job by ID': 'Cargar trabajo por ID', '7. Listing': '7. Publicación', '8. Export/Review': '8. Exportar / revisar',
  'Transcript Jobs': 'Transcripciones', 'New Transcription Job': 'Nueva transcripción', 'General Transcript Intake': 'Ingreso de transcripción',
  'Select Audio File': 'Elegir archivo de audio', 'Total Jobs': 'Trabajos totales', 'Top Document Types': 'Tipos de documento',
  'No transcription jobs yet. Upload an audio file above to start.': 'Todavía no hay transcripciones. Sube un audio arriba para empezar.',
  'Court Hearing': 'Audiencia', 'Deposition': 'Declaración', 'Conference': 'Conferencia',

  // ── LLCFactory / ApostApp ──
  'LLC Factory': 'Fábrica de empresas', 'Start a new filing': 'Iniciar un trámite', 'Name Check': 'Revisar nombre',
  'Check name availability': 'Revisar disponibilidad del nombre', 'Generate OA': 'Generar acuerdo', 'Operating agreement': 'Acuerdo operativo',
  'State Guide': 'Guías por estado', 'State Guides': 'Guías por estado', 'DC, MD, VA guides': 'Requisitos por estado', 'Formations': 'Constituciones',
  'Forms Library': 'Biblioteca de formularios', 'AI Form Assist': 'Asistente de formularios', 'Business Services': 'Servicios empresariales',
  'At State': 'En trámite', 'Document Apostille Services': 'Servicio de apostilla de documentos', 'Apostille Center': 'Centro de apostillas',
  'Remote Notary': 'Notaría remota', 'E-Signatures': 'Firmas electrónicas', 'Top Services': 'Servicios principales',
  'Assisted signup tracking': 'Seguimiento de registros asistidos', 'LLC Integration': 'Integración de empresas',

  // ── VendorOps ──
  'Standalone Add-On': 'Complemento', 'Founder-managed vendor account setup and renewal tracking.':
    'Cuentas de proveedores, configuración y renovaciones.', 'Renewal alerts': 'Alertas de renovación', 'Renewals 30d': 'Renovaciones 30 d',
  'No active renewal alerts in the next 30 days.': 'No hay renovaciones en los próximos 30 días.', 'Total Accounts': 'Cuentas totales',
  'Useful trial for tracking one vendor workflow.': 'Prueba útil para seguir un proveedor.', 'Record upgrade intent': 'Registrar interés en mejorar',
  'Start checkout': 'Ir al pago', 'Deliver queued alerts': 'Enviar alertas en cola', 'Query VendorOps from MAX': 'Consultar VendorOps desde el asistente',
  'Advanced querying and automation policy': 'Consultas avanzadas y automatización', 'Activation and locked states': 'Activación y bloqueos',
  'Stronger querying, monitoring, and approval-bound automation.': 'Más consultas, monitoreo y automatización con aprobación.',
  'Provider Billing Cycles': 'Ciclos de cobro de proveedores', 'Provider Reported': 'Reportado por el proveedor',

  // ── AI Vision (tailored for family editions) ──
  'AI Vision': 'Visión IA', 'Vision': 'Visión', 'AI Photo Analysis': 'Análisis de fotos con IA', 'Photo Analysis Tool': 'Análisis de fotos',
  'Photo Analyzer': 'Analizador de fotos', 'Analysis Jobs': 'Análisis', 'Measure': 'Medir', 'Window measurement analysis': 'Medidas a partir de fotos',
  'Upholstery': 'Acabados', 'Furniture reupholstery estimate': 'Estimación de acabados y materiales', 'Design Mockup': 'Propuesta de diseño',
  '3-tier design proposals with AI images': 'Tres propuestas de diseño con imágenes IA',
  'Window type identification': 'Identificación de espacios', 'Window width & height (inches)': 'Ancho y alto (pulgadas)', 'Treatment suggestions': 'Sugerencias de diseño',
  'Measurement notes': 'Notas de medidas', 'Photo reference points': 'Puntos de referencia', 'Reference object detection': 'Detección de objetos de referencia',
  'Scale method used': 'Método de escala', 'Confidence score': 'Nivel de confianza', 'Use device camera': 'Usar la cámara',
  'Upload a photo or 3D model first': 'Primero sube una foto o un modelo 3D', 'JPG, PNG up to 20 MB': 'JPG o PNG de hasta 20 MB',
  'What measure generates:': 'Qué genera la medición:', 'Analysis Modes Used': 'Modos de análisis usados', 'Client Intake': 'Datos del cliente',
  'Client preferences (optional)': 'Preferencias del cliente (opcional)',

  // ── EmpirePay ──
  'EmpirePay Dashboard': 'Panel de EmpirePay', 'Crypto payments, wallets, and EMPIRE token management': 'Pagos cripto, billeteras y token',
  'Crypto Payments': 'Pagos cripto', 'Wallets': 'Billeteras', 'Payment Links': 'Enlaces de pago', 'Supported Chains': 'Redes soportadas',
  'Token not yet live': 'El token aún no está activo', 'EMPIRE Token': 'Token', 'Empire price': 'Precio del token',

  // ── EmpireAssist / pets ──
  'Coachees': 'Coachees',
};

/** Regex rules for text that carries numbers or short variable parts. */
export const FAMILY_ES_RULES: Array<[RegExp, string]> = [
  [/^(\d+) customers$/i, '$1 clientes'],
  [/^(\d+) shipments$/i, '$1 envíos'],
  [/^(\d+) In Progress$/i, '$1 en curso'],
  [/^(\d+) Open$/i, '$1 abiertos'],
  [/^(\d+) active · (\d+) orders$/i, '$1 activos · $2 pedidos'],
  [/^(\d+) sold this month$/i, '$1 vendidos este mes'],
  [/^Failed to (?:load|fetch) [a-z ]+: \d{3}$/i, 'No se pudieron cargar los datos.'],
  [/^Avg (\$[\d.,]+) per shipment$/i, 'Promedio $1 por envío'],
  [/^Route: \/api\/v1\/[a-z_/-]+$/i, 'Complemento'],
  [/^DB prefix: [a-z_]+$/i, 'Datos propios'],
  [/^MAX query-only$/i, 'Solo consulta'],
  [/^MAX write actions$/i, 'Acciones del asistente'],
  [/^(\d+) active ·$/i, '$1 activos ·'],
  [/^active ·$/i, 'activos ·'],
  [/^(\$[\d.,]+) total$/i, '$1 en total'],
  [/^(\d+) total tickets$/i, '$1 casos en total'],
  [/^Billing: [a-z_]+ · Checkout: [a-z_]+$/i, 'Plan gratuito'],
  [/^Credential policy: [a-z_]+$/i, 'Las credenciales no se guardan en texto plano'],
];

const LOOKUP: Map<string, string> = new Map(
  Object.entries(FAMILY_ES).map(([k, v]) => [k.trim().toLowerCase(), v]),
);

export function translateFamily(text: string): string | null {
  const trimmed = text.trim();
  if (!trimmed || trimmed.length > 160) return null;
  const hit = LOOKUP.get(trimmed.toLowerCase());
  let out: string | null = hit ?? null;
  if (out === null) {
    for (const [re, rep] of FAMILY_ES_RULES) {
      if (re.test(trimmed)) { out = trimmed.replace(re, rep); break; }
    }
  }
  if (out === null || out === trimmed) return null;
  const lead = text.slice(0, text.indexOf(trimmed));
  const tail = text.slice(text.indexOf(trimmed) + trimmed.length);
  return `${lead}${out}${tail}`;
}
