// ── AMP Content Data ──

export const AFFIRMATIONS = [
  "Hoy elijo la alegría. Mi mente es fuerte y mi corazón está abierto.",
  "Soy capaz de superar cualquier desafío que la vida me presente.",
  "Mi bienestar es mi prioridad. Merezco paz, amor y abundancia.",
  "Cada día es una nueva oportunidad para crecer y brillar.",
  "La gratitud transforma mi perspectiva y abre puertas increíbles.",
  "Confío en mi proceso de aprendizaje y sanación.",
  "Mi actitud positiva es mi superpoder más grande.",
  "Hoy planto semillas de alegría que florecerán mañana.",
  "Soy el líder de mi propia vida y elijo caminar con propósito.",
  "La paz interior es mi derecho. Hoy la reclamo con amor.",
  "Mi mente positiva crea mi realidad positiva.",
  "Abrazo cada momento con gratitud y esperanza.",
  "Tengo el poder de transformar mis pensamientos y mi vida.",
  "Hoy me comprometo con mi crecimiento personal.",
  "La alegría no es un destino, es el camino que elijo cada día.",
];

export const MEDITATIONS = [
  { id: "m1", title: "Respiración de la Mañana", duration: "5 min", pillar: "bienestar", description: "Comienza tu día con una respiración consciente que llena tu cuerpo de energía y paz." },
  { id: "m2", title: "Meditación de Gratitud", duration: "10 min", pillar: "mentalidad", description: "Cultiva un corazón agradecido y transforma tu perspectiva del mundo." },
  { id: "m3", title: "Visualización del Líder Interior", duration: "12 min", pillar: "liderazgo", description: "Conecta con tu poder interior y visualiza la versión más fuerte de ti mismo." },
  { id: "m4", title: "Calma para la Ansiedad", duration: "8 min", pillar: "bienestar", description: "Técnicas probadas para calmar la mente cuando la ansiedad toca tu puerta." },
  { id: "m5", title: "Afirmaciones de Abundancia", duration: "7 min", pillar: "mentalidad", description: "Reprograma tu mente con afirmaciones poderosas de prosperidad y abundancia." },
  { id: "m6", title: "Relajación para Dormir", duration: "15 min", pillar: "bienestar", description: "Un viaje guiado hacia un sueño profundo y reparador." },
];

export const MICRO_LESSONS = [
  { title: "Los 3 Pilares de una Mente Positiva", read: "3 min", pillar: "mentalidad", content: "La actitud mental positiva no es ignorar los problemas — es enfrentarlos con la certeza de que puedes superarlos. Los tres pilares son: consciencia de tus pensamientos, gratitud diaria, y acción con propósito." },
  { title: "El Arte de Liderar desde Dentro", read: "2 min", pillar: "liderazgo", content: "John Maxwell nos enseña que el liderazgo no empieza con un título. Empieza con liderarte a ti mismo. Hoy, practica tomar una decisión difícil con integridad." },
  { title: "Bienestar no es un Lujo", read: "3 min", pillar: "bienestar", content: "Tu bienestar físico y mental son la base de todo lo demás. No es egoísta priorizarte — es necesario. Hoy, dedica 10 minutos solo para ti." },
];

export const COURSES = [
  {
    id: "c1", title: "21 Días de Gratitud", pillar: "mentalidad", instructor: "AMP Team",
    description: "Transforma tu perspectiva con 21 días de prácticas de gratitud que cambiarán cómo ves el mundo.",
    days: 21, enrolled: 1247, rating: 4.9, premium: false,
    lessons: Array.from({ length: 21 }, (_, i) => ({
      day: i + 1, title: `Día ${i + 1}: ${["Descubriendo la Gratitud", "Gratitud por lo Simple", "Tu Cuerpo Agradecido", "Personas que Amas", "Gratitud en la Adversidad", "Carta de Agradecimiento", "Naturaleza y Gratitud", "Gratitud Financiera", "Tu Historia de Superación", "Medio Camino: Reflexión", "Gratitud por Ti Mismo", "Tus Talentos", "Momentos de Alegría", "Gratitud por los Retos", "El Poder del Perdón", "Gratitud en el Trabajo", "Tu Legado", "Abundancia Interior", "Conexiones que Sanan", "Gratitud por el Presente", "Gratitud como Estilo de Vida"][i]}`,
      duration: `${12 + (i % 5) * 2} min`, completed: false
    }))
  },
  {
    id: "c2", title: "Meditación para Principiantes", pillar: "bienestar", instructor: "AMP Team",
    description: "Aprende a meditar desde cero. Sin experiencia necesaria. Solo tú, tu respiración y la calma.",
    days: 14, enrolled: 2103, rating: 4.8, premium: false,
    lessons: Array.from({ length: 14 }, (_, i) => ({
      day: i + 1, title: `Día ${i + 1}: ${["¿Qué es Meditar?", "Tu Primera Respiración", "Observar sin Juzgar", "El Cuerpo Habla", "Pensamientos como Nubes", "5 Minutos de Silencio", "Meditación Caminando", "Mantra Personal", "Meditación y Emociones", "Mindfulness en lo Cotidiano", "Meditación con Música", "Gratitud Meditada", "Tu Espacio Sagrado", "Meditación como Hábito"][i]}`,
      duration: `${8 + (i % 4) * 3} min`, completed: false
    }))
  },
  {
    id: "c3", title: "Liderazgo Personal", pillar: "liderazgo", instructor: "AMP Team",
    description: "Inspirado en los principios de John Maxwell. Descubre el líder que llevas dentro y lidera tu propia vida con propósito.",
    days: 21, enrolled: 856, rating: 4.7, premium: true,
    lessons: Array.from({ length: 21 }, (_, i) => ({
      day: i + 1, title: `Día ${i + 1}: ${["El Liderazgo Empieza Contigo", "Visión Personal", "Los 5 Niveles", "Influencia Positiva", "Decisiones con Integridad", "Comunicación Efectiva", "Empatía como Fortaleza", "Servir para Liderar", "Tu Equipo Interior", "Resiliencia del Líder", "Mentalidad de Crecimiento", "Liderazgo y Humildad", "Construir Confianza", "El Poder del Ejemplo", "Liderar en Crisis", "Creatividad y Liderazgo", "Delegar con Confianza", "Motivar desde el Corazón", "Legado de un Líder", "Tu Plan de Liderazgo", "Comienza Hoy"][i]}`,
      duration: `${15 + (i % 3) * 3} min`, completed: false
    }))
  },
  {
    id: "c4", title: "Manejo del Estrés y la Ansiedad", pillar: "bienestar", instructor: "AMP Team",
    description: "Herramientas prácticas para cuando la vida se pone difícil. Aprende a navegar el estrés con calma y claridad.",
    days: 14, enrolled: 1891, rating: 4.9, premium: true,
    lessons: Array.from({ length: 14 }, (_, i) => ({
      day: i + 1, title: `Día ${i + 1}: ${["Entendiendo tu Estrés", "Respiración 4-7-8", "El Cuerpo bajo Estrés", "Pensamientos Automáticos", "Técnica de Grounding", "Límites Saludables", "Movimiento y Calma", "Diario de Emociones", "Soltar el Control", "Autocompasión", "Rutinas que Sanan", "Pedir Ayuda", "Estrés como Maestro", "Tu Kit Anti-Estrés"][i]}`,
      duration: `${10 + (i % 4) * 3} min`, completed: false
    }))
  },
  {
    id: "c5", title: "Mentalidad de Abundancia", pillar: "mentalidad", instructor: "AMP Team",
    description: "Cambia tu relación con la abundancia. No solo dinero — abundancia en amor, salud, tiempo y propósito.",
    days: 21, enrolled: 678, rating: 4.8, premium: true,
    lessons: Array.from({ length: 21 }, (_, i) => ({
      day: i + 1, title: `Día ${i + 1}: ${["Escasez vs Abundancia", "Tus Creencias sobre el Dinero", "Abundancia en Relaciones", "Gratitud como Imán", "Reprogramar Creencias", "Visualización Creativa", "Abundancia de Tiempo", "Generosidad Estratégica", "Tu Relación con el Éxito", "Abundancia y Salud", "Mentalidad de Crecimiento", "Atraer Oportunidades", "Abundancia en el Trabajo", "Soltar la Comparación", "Abundancia Espiritual", "El Poder de la Intención", "Acciones de Abundancia", "Comunidad y Abundancia", "Abundancia Creativa", "Tu Mapa de Abundancia", "Vivir en Abundancia"][i]}`,
      duration: `${12 + (i % 5) * 2} min`, completed: false
    }))
  },
];

export const MOODS = [
  { emoji: "😊", label: "Feliz", color: "#FFD700" },
  { emoji: "😌", label: "En paz", color: "#7CB98B" },
  { emoji: "😐", label: "Neutral", color: "#9B9590" },
  { emoji: "😔", label: "Triste", color: "#6B8EC4" },
  { emoji: "😤", label: "Frustrado", color: "#E07A5F" },
  { emoji: "😰", label: "Ansioso", color: "#C49B8E" },
  { emoji: "🤗", label: "Agradecido", color: "#D4A030" },
  { emoji: "💪", label: "Motivado", color: "#FF8C42" },
];

export const PILLAR_CONFIG = {
  mentalidad: { label: "Mentalidad", icon: "🧠", color: "#D4A030", gradient: "from-amber-100 to-orange-50", desc: "Transforma tus pensamientos, transforma tu realidad" },
  bienestar: { label: "Bienestar", icon: "🌿", color: "#7CB98B", gradient: "from-green-50 to-emerald-50", desc: "Cuida tu mente y tu cuerpo con amor y consciencia" },
  liderazgo: { label: "Liderazgo", icon: "⭐", color: "#9B8EC4", gradient: "from-purple-50 to-indigo-50", desc: "Lidera tu vida con propósito, integridad y corazón" },
} as const;

export type Pillar = keyof typeof PILLAR_CONFIG;

export function getTodayAffirmation(): string {
  const dayOfYear = Math.floor((Date.now() - new Date(new Date().getFullYear(), 0, 0).getTime()) / 86400000);
  return AFFIRMATIONS[dayOfYear % AFFIRMATIONS.length];
}

export function getTodayMeditation() {
  const dayOfYear = Math.floor((Date.now() - new Date(new Date().getFullYear(), 0, 0).getTime()) / 86400000);
  return MEDITATIONS[dayOfYear % MEDITATIONS.length];
}

export function getTodayLesson() {
  const dayOfYear = Math.floor((Date.now() - new Date(new Date().getFullYear(), 0, 0).getTime()) / 86400000);
  return MICRO_LESSONS[dayOfYear % MICRO_LESSONS.length];
}
