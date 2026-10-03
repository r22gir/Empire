export interface Coach {
  id: string;
  name: string;
  role: string;
  tagline: string;
  bio: string;
  specialties: string[];
  photoPlaceholder: string; // clearly marked placeholder
  color: string;
}

export const COACHES: Coach[] = [
  {
    id: "juan-diego",
    name: "Juan Diego Giraldo",
    role: "Fundador & Coach de Vida y Negocios",
    tagline: "Soy un ser valiente, líder, abundante, saludable y organizado.",
    bio: "Ingeniero de Sistemas y especialista en proyectos de tecnología y ciberseguridad. Integra el desarrollo personal profundo, la actitud mental positiva y el liderazgo consciente para acompañar a personas y profesionales a desbloquear su potencial y vivir con propósito.",
    specialties: ["Confianza interior", "Liderazgo consciente", "Desbloqueos de mentalidad", "Emprendimiento con propósito"],
    photoPlaceholder: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=600&auto=format&fit=crop&q=80",
    color: "#E0A526",
  },
  {
    id: "andrea-silva",
    name: "Andrea Silva",
    role: "Mentora de Padres y Familias Conscientes",
    tagline: "Estoy aquí con el propósito de servir y recordar que todos somos una fuente de amor inagotable.",
    bio: "Profesional en Marketing y Negocios Internacionales. Certificada en coaching ontológico, PNL internacional, familias conscientes (Mindvalley) y facilitación de transformación con la John Maxwell Foundation. Acompaña a padres a construir vínculos profundos y amorosos con sus hijos.",
    specialties: ["Crianza consciente", "Límites saludables", "Comunicación no violenta", "Autoestima infantil"],
    photoPlaceholder: "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=600&auto=format&fit=crop&q=80",
    color: "#F28C6B",
  },
  {
    id: "dericielo-jimenez",
    name: "Dericielo Jiménez",
    role: "Mentora de Sanación y Empoderamiento Femenino",
    tagline: "Yo soy chispa divina del universo conectada con la tierra y el amor propio.",
    bio: "Especialista en acompañamiento compasivo para mujeres que han atravesado dolor, abandono o relaciones complejas. Su enfoque integra reprogramación de creencias, trabajo de niña interior y reconexión con la fuerza vital propia.",
    specialties: ["Sanación de heridas", "Superación de patrones tóxicos", "Reconstrucción del amor propio", "Paz interior"],
    photoPlaceholder: "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=600&auto=format&fit=crop&q=80",
    color: "#7E9F84",
  },
  {
    id: "lina-valencia",
    name: "Lina Valencia Triviño",
    role: "Life Coach — Duelo y Transiciones de Vida",
    tagline: "Soy una persona que fluye con la vida en amor, perdón y tranquilidad.",
    bio: "Ingeniera Industrial, Magíster en Ciencias Económicas y Sociales e International Master Coach (ICF). Certificada en coaching espiritual, PNL y sanación holística. Guía procesos de duelo, cierre de ciclos y reconciliación personal.",
    specialties: ["Gestión del duelo", "Cierre de ciclos de pareja", "Perdón y reconciliación", "Mindfulness compasivo"],
    photoPlaceholder: "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=600&auto=format&fit=crop&q=80",
    color: "#9B8EC4",
  },
];

export interface TrackItem {
  id: string;
  title: string;
  coach: string;
  coachId: string;
  theme: "ansiedad" | "sueño" | "gratitud" | "autoestima" | "duelo" | "abundancia" | "enfoque" | "liderazgo";
  pillar: "mentalidad" | "bienestar" | "liderazgo";
  durationSeconds: number;
  durationLabel: string;
  premium: boolean;
  description: string;
  transcript: string;
  audioUrl?: string; // sample track
}

export const SAMPLE_TRACKS: TrackItem[] = [
  {
    id: "track-1",
    title: "Respiración Consciente para Liberar la Ansiedad",
    coach: "Juan Diego Giraldo",
    coachId: "juan-diego",
    theme: "ansiedad",
    pillar: "bienestar",
    durationSeconds: 300,
    durationLabel: "5 min",
    premium: false,
    description: "Una pausa guiada de 5 minutos utilizando la técnica de respiración 4-7-8 para calmar el sistema nervioso.",
    transcript: "Inhala profundamente por la nariz contando mentalmente 1, 2, 3, 4. Retén suavemente el aire: 1, 2, 3, 4, 5, 6, 7. Y ahora exhala despacio por la boca dejando ir toda tensión: 1, 2, 3, 4, 5, 6, 7, 8. Siente tus hombros descender. En este momento estás a salvo, en paz y en control de tu presente.",
    audioUrl: "https://actions.google.com/sounds/v1/water/rain_heavy.ogg",
  },
  {
    id: "track-2",
    title: "Meditación de Gratitud Matutina",
    coach: "Andrea Silva",
    coachId: "andrea-silva",
    theme: "gratitud",
    pillar: "mentalidad",
    durationSeconds: 600,
    durationLabel: "10 min",
    premium: false,
    description: "Cultiva una vibración de agradecimiento desde la primera hora del día y predispone tu mente a la abundancia.",
    transcript: "Cierra tus ojos y lleva una mano hacia tu pecho. Agradece hoy por tres cosas sencillas pero sagradas: el aire que llena tus pulmones, la oportunidad de este nuevo amanecer y la capacidad de amar y ser amado. Todo lo que necesitas ya habita dentro de ti.",
    audioUrl: "https://actions.google.com/sounds/v1/ambiences/morning_birds.ogg",
  },
  {
    id: "track-3",
    title: "Visualización del Líder Interior con Propósito",
    coach: "Juan Diego Giraldo",
    coachId: "juan-diego",
    theme: "liderazgo",
    pillar: "liderazgo",
    durationSeconds: 720,
    durationLabel: "12 min",
    premium: true,
    description: "Conecta con tu fuerza y convicción para tomar decisiones sabias con integridad y empatía.",
    transcript: "Imagina un camino dorado frente a ti. Cada paso que das está firme en tus valores. No lideras para impresionar, lideras para servir e inspirar a quienes te rodean.",
    audioUrl: "https://actions.google.com/sounds/v1/ambiences/forest_day.ogg",
  },
  {
    id: "track-4",
    title: "Soltar el Control y Sanar el Duelo",
    coach: "Lina Valencia Triviño",
    coachId: "lina-valencia",
    theme: "duelo",
    pillar: "bienestar",
    durationSeconds: 900,
    durationLabel: "15 min",
    premium: true,
    description: "Un abrazo amoroso a tu corazón en momentos de pérdida, cambio o transición dolorosa.",
    transcript: "Honra lo que dolió. Acepta que sentir tristeza no es debilidad, es el eco del amor que existió. Respira profundo y permite que la emoción fluya como agua clara.",
    audioUrl: "https://actions.google.com/sounds/v1/water/ocean_waves.ogg",
  },
  {
    id: "track-5",
    title: "Reprogramación: Merezco Prosperidad y Amor",
    coach: "Dericielo Jiménez",
    coachId: "dericielo-jimenez",
    theme: "autoestima",
    pillar: "mentalidad",
    durationSeconds: 420,
    durationLabel: "7 min",
    premium: false,
    description: "Afirmaciones diarias para elevar tu sentido de merecimiento y soltar el síndrome del impostor.",
    transcript: "Repite en silencio o en voz alta: Soy valiosa. Merezco amor genuino, abundancia sin culpa y una vida llena de alegría y bendiciones.",
    audioUrl: "https://actions.google.com/sounds/v1/ambiences/wind_in_trees.ogg",
  },
  {
    id: "track-6",
    title: "Sueño Profundo y Relajación Corporal",
    coach: "Lina Valencia Triviño",
    coachId: "lina-valencia",
    theme: "sueño",
    pillar: "bienestar",
    durationSeconds: 1200,
    durationLabel: "20 min",
    premium: true,
    description: "Viaje sonoro para aquietar la mente, relajar cada músculo y dormir como en un templo de paz.",
    transcript: "Suelta los pensamientos del día. Lo que se hizo está bien; lo que quedó pendiente esperará a mañana. Ahora es tiempo de descansar y recargar tu ser.",
    audioUrl: "https://actions.google.com/sounds/v1/water/gentle_stream.ogg",
  },
];

export interface BlogPost {
  slug: string;
  title: string;
  excerpt: string;
  category: string;
  author: string;
  authorRole: string;
  date: string;
  readTime: string;
  relatedTheme: string;
  content: string[];
}

export const BLOG_POSTS: BlogPost[] = [
  {
    slug: "el-poder-de-las-afirmaciones-positivas",
    title: "El poder de las afirmaciones positivas en tu rutina matutina",
    excerpt: "Las palabras que pronuncias al despertar configuran las redes neuronales de tu día. Aprende cómo integrarlas con intención real.",
    category: "Mentalidad",
    author: "Juan Diego Giraldo",
    authorRole: "Coach de Vida",
    date: "28 de Septiembre, 2026",
    readTime: "5 min",
    relatedTheme: "autoestima",
    content: [
      "La actitud mental positiva no es una máscara para ignorar los retos de la vida cotidiana; es la certeza serena de que posees los recursos interiores para superarlos.",
      "Cuando nos despertamos, nuestro cerebro opera en frecuencias alfa, un estado de receptividad óptimo donde las creencias y los pensamientos tienen un impacto multiplicador.",
      "Comienza cada día con 3 afirmaciones pronunciadas desde el corazón: 'Hoy elijo la alegría', 'Confío en mi capacidad de solucionar cualquier desafío', y 'Agradezco cada instante de aprendizaje'. Verás cómo tu perspectiva se transforma."
    ]
  },
  {
    slug: "crianza-consciente-educar-con-empatia",
    title: "Crianza consciente: 5 claves para educar hijos emocionalmente inteligentes",
    excerpt: "La educación emocional no empieza en los libros de texto, sino en la calma y presencia con la que respondes a los desafíos familiares.",
    category: "Familias",
    author: "Andrea Silva",
    authorRole: "Mentora de Padres",
    date: "24 de Septiembre, 2026",
    readTime: "6 min",
    relatedTheme: "gratitud",
    content: [
      "Nuestros hijos no aprenden de lo que les decimos, sino de la forma en que nosotros gestionamos nuestras propias emociones bajo presión.",
      "Validar el llanto o la frustración de un niño sin apresurarnos a reprimirlo construye una autoestima indestructible para toda su vida adulta.",
      "Dedica 10 minutos al día de conexión sin pantallas ni distracciones. Esa presencia plena es el mejor regalo que una familia puede sembrar."
    ]
  },
  {
    slug: "sanar-heridas-del-pasado-amor-propio",
    title: "De la herida a la fortaleza: cómo reconstruir tu autoestima tras una crisis",
    excerpt: "El dolor no tiene por qué ser tu destino final. Descubre el camino para honrar tu proceso y florecer con dignidad.",
    category: "Sanación",
    author: "Dericielo Jiménez",
    authorRole: "Mentora de Sanación",
    date: "18 de Septiembre, 2026",
    readTime: "7 min",
    relatedTheme: "autoestima",
    content: [
      "Muchas veces nos quedamos atrapados en el '¿por qué a mí?'. El giro transformador ocurre cuando preguntamos con compasión: '¿para qué me está preparando esta experiencia?'.",
      "Reconstruir el amor propio exige poner límites saludables, aprender a decir no sin culpa y reconocer que tu valor humano es sagrado e intocable.",
      "Cada paso hacia adelante, por pequeño que parezca, es una victoria sobre el pasado."
    ]
  },
  {
    slug: "transitar-el-duelo-con-compasion",
    title: "Transitar el duelo: por qué soltar el control es el primer paso hacia la paz",
    excerpt: "Nadie nos enseña a perder lo que amamos. Reflexiones compasivas para navegar los días grises con esperanza.",
    category: "Bienestar",
    author: "Lina Valencia Triviño",
    authorRole: "Life Coach",
    date: "12 de Septiembre, 2026",
    readTime: "5 min",
    relatedTheme: "duelo",
    content: [
      "El duelo no es un proceso lineal con tiempos fijos. Habrá días de calma y días de tormenta inesperada. Ambos son válidos.",
      "El perdón y la reconciliación con lo ocurrido no justifican lo que pasó, pero te liberan de cargar un peso que ya no te corresponde llevar.",
      "Permítete descansar, respirar y buscar apoyo en tu comunidad. La alegría volverá a tocar a tu puerta cuando tu corazón esté listo."
    ]
  }
];

export interface ServiceItem {
  id: string;
  title: string;
  subtitle: string;
  description: string;
  priceNote: string;
  bullets: string[];
  ctaLabel: string;
  coachName?: string;
}

export const SERVICES: ServiceItem[] = [
  {
    id: "coaching-1-1",
    title: "Sesiones de Coaching Individual 1:1",
    subtitle: "Acompañamiento personalizado y profundo",
    description: "Espacio confidencial con tu coach de elección (Juan Diego, Andrea, Dericielo o Lina) para trabajar metas concretas, superar bloqueos emocionales o transiciones de vida.",
    priceNote: "Desde $45 USD / sesión (o paquetes de 4 sesiones)",
    bullets: [
      "Diagnóstico inicial de metas y mapa de bienestar",
      "Sesión virtual de 60 minutos por videollamada",
      "Plan de acción y micro-prácticas entre sesiones",
      "Soporte y seguimiento vía mensaje"
    ],
    ctaLabel: "Agendar con un Coach"
  },
  {
    id: "talleres-grupales",
    title: "Talleres y Retiros Vivenciales",
    subtitle: "Transformación en comunidad",
    description: "Encuentros virtuales y presenciales enfocados en amor propio, manejo del estrés, respiración consciente y liderazgo personal.",
    priceNote: "Cupos limitados por taller",
    bullets: [
      "Sesiones interactivas de 2 a 4 horas",
      "Cuaderno de trabajo descargable",
      "Acceso a la grabación por 30 días",
      "Círculo de preguntas y respuestas en vivo"
    ],
    ctaLabel: "Ver Próximos Talleres"
  },
  {
    id: "membresia-portal",
    title: "Membresía El Portal de la Alegría",
    subtitle: "Tu práctica diaria ilimitada",
    description: "Acceso total a la biblioteca de meditaciones guiadas, retos de transformación de 21 días, masterclasses mensuales en vivo y seguimiento de ánimo.",
    priceNote: "$9.99 USD / mes (con 7 días de prueba gratis)",
    bullets: [
      "+100 meditaciones y audios guiados sin límites",
      "Retos estructurados de transformación mental",
      "Check-in diario con recomendaciones inteligentes",
      "Encuentro mensual exclusivo con los coaches"
    ],
    ctaLabel: "Comenzar Prueba Gratuita"
  },
  {
    id: "bienestar-empresas",
    title: "AMP para Empresas & Equipos",
    subtitle: "Salud mental y liderazgo positivo para organizaciones",
    description: "Programas corporativos diseñados para mitigar el burnout, fortalecer la resiliencia y potenciar el clima laboral.",
    priceNote: "Cotización personalizada",
    bullets: [
      "Talleres in-company presenciales o remotos",
      "Licencias colectivas para la plataforma digital",
      "Métricas agregadas de bienestar y satisfacción",
      "Conferencias magistrales con Juan Diego Giraldo"
    ],
    ctaLabel: "Solicitar Propuesta"
  }
];
