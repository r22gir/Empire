export interface Coach {
  id: string;
  name: string;
  role: string;
  tagline: string;
  bio: string;
  specialties: string[];
  photoPlaceholder: string; // clearly marked royalty-free stock placeholder
  photoLocal: string;
  color: string;
  programsCount: number;
  meditationsCount: number;
}

export const COACHES: Coach[] = [
  {
    id: "juan-diego",
    name: "Juan Diego Giraldo",
    role: "Fundador & Coach de Vida y Negocios",
    tagline: "Soy un ser valiente, líder, abundante, saludable y organizado.",
    bio: "Ingeniero de Sistemas y especialista en proyectos de tecnología y ciberseguridad. Integra el desarrollo personal profundo, la actitud mental positiva y el liderazgo consciente para acompañar a personas y profesionales a desbloquear su potencial y vivir con propósito.",
    specialties: ["Confianza interior", "Liderazgo consciente", "Desbloqueos de mentalidad", "Emprendimiento con propósito"],
    photoPlaceholder: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=800&q=80",
    photoLocal: "/coaches/juan-diego.jpg",
    color: "#E0A526",
    programsCount: 3,
    meditationsCount: 18,
  },
  {
    id: "andrea-silva",
    name: "Andrea Silva",
    role: "Mentora de Padres y Familias Conscientes",
    tagline: "Estoy aquí con el propósito de servir y recordar que todos somos una fuente de amor inagotable.",
    bio: "Profesional en Marketing y Negocios Internacionales. Certificada en coaching ontológico, PNL internacional, familias conscientes (Mindvalley) y facilitación de transformación con la John Maxwell Foundation. Acompaña a padres a construir vínculos profundos y amorosos con sus hijos.",
    specialties: ["Crianza consciente", "Límites saludables", "Comunicación no violenta", "Autoestima infantil"],
    photoPlaceholder: "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&w=800&q=80",
    photoLocal: "/coaches/andrea-silva.jpg",
    color: "#F28C6B",
    programsCount: 2,
    meditationsCount: 14,
  },
  {
    id: "dericielo-jimenez",
    name: "Dericielo Jiménez",
    role: "Mentora de Sanación y Empoderamiento Femenino",
    tagline: "Yo soy chispa divina del universo conectada con la tierra y el amor propio.",
    bio: "Especialista en acompañamiento compasivo para mujeres que han atravesado dolor, abandono o relaciones complejas. Su enfoque integra reprogramación de creencias, trabajo de niña interior y reconexión con la fuerza vital propia.",
    specialties: ["Sanación de heridas", "Superación de patrones tóxicos", "Reconstrucción del amor propio", "Paz interior"],
    photoPlaceholder: "https://images.unsplash.com/photo-1580489944761-15a19d654956?auto=format&fit=crop&w=800&q=80",
    photoLocal: "/coaches/dericielo-jimenez.jpg",
    color: "#7E9F84",
    programsCount: 2,
    meditationsCount: 16,
  },
  {
    id: "lina-valencia",
    name: "Lina Valencia Triviño",
    role: "Life Coach — Duelo y Transiciones de Vida",
    tagline: "Soy una persona que fluye con la vida en amor, perdón y tranquilidad.",
    bio: "Ingeniera Industrial, Magíster en Ciencias Económicas y Sociales e International Master Coach (ICF). Certificada en coaching espiritual, PNL y sanación holística. Guía procesos de duelo, cierre de ciclos y reconciliación personal.",
    specialties: ["Gestión del duelo", "Cierre de ciclos de pareja", "Perdón y reconciliación", "Mindfulness compasivo"],
    photoPlaceholder: "https://images.unsplash.com/photo-1567532939604-b6b5b0db2604?auto=format&fit=crop&w=800&q=80",
    photoLocal: "/coaches/lina-valencia.jpg",
    color: "#9B8EC4",
    programsCount: 2,
    meditationsCount: 12,
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
  audioUrl: string; // real local playable audio file
  imageCover: string;
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
    description: "Una pausa guiada de 5 minutos utilizando la técnica de respiración 4-7-8 para calmar el sistema nervioso en momentos de agobio.",
    transcript: "Inhala profundamente por la nariz contando mentalmente 1, 2, 3, 4. Retén suavemente el aire: 1, 2, 3, 4, 5, 6, 7. Y ahora exhala despacio por la boca dejando ir toda tensión: 1, 2, 3, 4, 5, 6, 7, 8. Siente tus hombros descender. En este momento estás a salvo, en paz y en control de tu presente.",
    audioUrl: "/audio/respiracion-ansiedad.wav",
    imageCover: "/themes/ansiedad.jpg",
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
    description: "Cultiva una vibración de agradecimiento desde la primera hora del día y predispone tu mente a la abundancia y la paz.",
    transcript: "Cierra tus ojos y lleva una mano hacia tu pecho. Agradece hoy por tres cosas sencillas pero sagradas: el aire que llena tus pulmones, la oportunidad de este nuevo amanecer y la capacidad de amar y ser amado. Todo lo que necesitas ya habita dentro de ti.",
    audioUrl: "/audio/gratitud-matutina.wav",
    imageCover: "/themes/gratitud.jpg",
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
    description: "Conecta con tu fuerza y convicción para tomar decisiones sabias con integridad, calma y empatía.",
    transcript: "Imagina un camino dorado frente a ti. Cada paso que das está firme en tus valores. No lideras para impresionar, lideras para servir e inspirar a quienes te rodean.",
    audioUrl: "/audio/lider-interior.wav",
    imageCover: "/themes/liderazgo.jpg",
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
    description: "Un abrazo amoroso a tu corazón en momentos de pérdida, cambio o transición dolorosa de vida.",
    transcript: "Honra lo que dolió. Acepta que sentir tristeza no es debilidad, es el eco del amor que existió. Respira profundo y permite que la emoción fluya como agua clara.",
    audioUrl: "/audio/sanar-duelo.wav",
    imageCover: "/themes/duelo.jpg",
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
    description: "Afirmaciones diarias para elevar tu sentido de merecimiento y soltar el síndrome del impostor definitivamente.",
    transcript: "Repite en silencio o en voz alta: Soy valiosa. Merezco amor genuino, abundancia sin culpa y una vida llena de alegría y bendiciones.",
    audioUrl: "/audio/merezco-prosperidad.wav",
    imageCover: "/themes/autoestima.jpg",
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
    description: "Viaje sonoro para aquietar la mente, relajar cada músculo del cuerpo y dormir en un templo de descanso reparador.",
    transcript: "Suelta los pensamientos del día. Lo que se hizo está bien; lo que quedó pendiente esperará a mañana. Ahora es tiempo de descansar y recargar tu ser.",
    audioUrl: "/audio/sueno-profundo.wav",
    imageCover: "/themes/sueno.jpg",
  },
];

export interface Program {
  id: string;
  title: string;
  tagline: string;
  coach: string;
  coachId: string;
  durationWeeks: number;
  lessonsCount: number;
  level: "Iniciación" | "Intermedio" | "Avanzado";
  coverImage: string;
  pillar: "mentalidad" | "bienestar" | "liderazgo";
}

export const PROGRAMS: Program[] = [
  {
    id: "prog-1",
    title: "Mentalidad Invencible & Hábitos de Alegría",
    tagline: "21 días para reprogramar pensamientos limitantes y manifestar una actitud positiva.",
    coach: "Juan Diego Giraldo",
    coachId: "juan-diego",
    durationWeeks: 3,
    lessonsCount: 21,
    level: "Iniciación",
    coverImage: "/programs/mentalidad-invencible.jpg",
    pillar: "mentalidad",
  },
  {
    id: "prog-2",
    title: "Crianza con Amor & Presencia Plena",
    tagline: "Aprende a conectar con tus hijos desde la empatía sin perder la paciencia ni los límites.",
    coach: "Andrea Silva",
    coachId: "andrea-silva",
    durationWeeks: 4,
    lessonsCount: 16,
    level: "Intermedio",
    coverImage: "/programs/crianza-amorosa.jpg",
    pillar: "bienestar",
  },
  {
    id: "prog-3",
    title: "Sanación del Niño Interior & Amor Propio",
    tagline: "Libera cargas del pasado y aprende a amarte incondicionalmente en cada faceta.",
    coach: "Dericielo Jiménez",
    coachId: "dericielo-jimenez",
    durationWeeks: 3,
    lessonsCount: 15,
    level: "Intermedio",
    coverImage: "/programs/sanacion-emocional.jpg",
    pillar: "mentalidad",
  },
  {
    id: "prog-4",
    title: "Trascendiendo el Duelo con Serenidad",
    tagline: "Herramientas compasivas para superar separaciones, pérdidas o transiciones difíciles.",
    coach: "Lina Valencia Triviño",
    coachId: "lina-valencia",
    durationWeeks: 4,
    lessonsCount: 18,
    level: "Avanzado",
    coverImage: "/programs/resiliencia-duelo.jpg",
    pillar: "liderazgo",
  },
];

export interface ThemeCategory {
  key: string;
  title: string;
  description: string;
  image: string;
  trackCount: number;
  gradient: string;
}

export const THEME_CATEGORIES: ThemeCategory[] = [
  {
    key: "ansiedad",
    title: "Ansiedad & Calma",
    description: "Técnicas de respiración y presencia para sosegar la mente inquieta.",
    image: "/themes/ansiedad.jpg",
    trackCount: 14,
    gradient: "from-[#F28C6B]/80 to-[#E0A526]/80",
  },
  {
    key: "sueño",
    title: "Sueño Profundo",
    description: "Paisajes sonoros y pausas nocturnas para descansar como un niño.",
    image: "/themes/sueno.jpg",
    trackCount: 18,
    gradient: "from-[#14122B]/90 to-[#3A2E6B]/80",
  },
  {
    key: "gratitud",
    title: "Gratitud & Dicha",
    description: "Cultiva agradecimiento y abre las puertas a la abundancia genuina.",
    image: "/themes/gratitud.jpg",
    trackCount: 12,
    gradient: "from-[#E0A526]/80 to-[#F2C14E]/70",
  },
  {
    key: "autoestima",
    title: "Amor Propio & Merecimiento",
    description: "Afirmaciones y prácticas para reconciliarte con tu valor intrínseco.",
    image: "/themes/autoestima.jpg",
    trackCount: 16,
    gradient: "from-[#7E9F84]/80 to-[#9DBFA2]/80",
  },
  {
    key: "duelo",
    title: "Duelo & Sanación",
    description: "Abraza el cambio y transita el dolor con compasión y perdón.",
    image: "/themes/duelo.jpg",
    trackCount: 10,
    gradient: "from-[#6B625A]/80 to-[#9B8EC4]/80",
  },
  {
    key: "liderazgo",
    title: "Liderazgo & Enfoque",
    description: "Claridad mental, disciplina diaria y dirección con propósito ético.",
    image: "/themes/liderazgo.jpg",
    trackCount: 15,
    gradient: "from-[#C68C14]/80 to-[#F28C6B]/80",
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
    authorRole: "Coach de Vida & Negocios",
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
    category: "Familia",
    author: "Andrea Silva",
    authorRole: "Mentora de Crianza Consciente",
    date: "25 de Septiembre, 2026",
    readTime: "7 min",
    relatedTheme: "gratitud",
    content: [
      "Nuestros hijos no aprenden de lo que les decimos repetidamente; aprenden de cómo reaccionamos cuando las cosas se salen de control.",
      "Cuando un niño experimenta una rabieta, no está buscando manipularnos; su corteza prefrontal aún inmadura se encuentra desbordada. Nuestro deber como padres es ser su termostato emocional, no el fuego.",
      "Aplica la técnica de la pausa de 3 segundos antes de responder. Conéctate visualmente a su altura, valida su emoción con amor y establece el límite con firmeza pero sin gritos."
    ]
  },
  {
    slug: "sanar-heridas-del-pasado-amor-propio",
    title: "Sanar el pasado: el camino para reconstruir tu merecimiento",
    excerpt: "Nadie puede dar lo que no tiene. Aprender a habitar tu propia ternura es el primer paso para relaciones sanas y duraderas.",
    category: "Bienestar",
    author: "Dericielo Jiménez",
    authorRole: "Mentora de Sanación Femenina",
    date: "20 de Septiembre, 2026",
    readTime: "6 min",
    relatedTheme: "autoestima",
    content: [
      "Muchas veces confundimos el amor propio con indulgencias superficiales. El verdadero amor propio es la valentía de poner límites a situaciones que desgastan tu paz.",
      "Identifica las creencias heredadas: ¿quién te dijo que para ser amada tenías que complacer a todos sacrificando tus propios anhelos?",
      "Al abrazar a tu niña interior y decirle 'aquí estoy yo para protegerte y cuidarte hoy', se disuelve la necesidad de buscar aprobación externa."
    ]
  },
  {
    slug: "transitar-el-duelo-con-compasion",
    title: "Transitar el duelo: por qué permitir la tristeza es el inicio de la paz",
    excerpt: "El dolor no es un enemigo que deba adormecerse, sino una señal de que algo valioso transformó para siempre tu biografía.",
    category: "Liderazgo Personal",
    author: "Lina Valencia Triviño",
    authorRole: "Master Coach en Transiciones",
    date: "14 de Septiembre, 2026",
    readTime: "8 min",
    relatedTheme: "duelo",
    content: [
      "En nuestra sociedad solemos presionar a quien sufre con frases como 'tienes que ser fuerte' o 'la vida sigue'. Pero el duelo exige su propio tiempo y respeto.",
      "Permitirte llorar no es retroceder; es drenar el vaso emocional para que pueda haber espacio para un nuevo amanecer.",
      "Honra lo vivido celebrando la memoria con gratitud, sin apresurar tus pasos hacia una falsa alegría. La verdadera resiliencia nace de la autenticidad."
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
      "Programas estructurados de transformación mental",
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
      "Conferencias inspiradoras para convenciones anuales"
    ],
    ctaLabel: "Solicitar Propuesta para mi Empresa"
  }
];
