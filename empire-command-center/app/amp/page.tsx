'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Flame, Heart, Brain, Shield, Users, Star, BookOpen, Calendar,
  Sparkles, ArrowRight, Play, Video, MessageCircle, Instagram,
  Facebook, Linkedin, Mail, MapPin, ChevronDown, Sun, Leaf, Crown,
  Target, Lightbulb, Compass, Gift, Eye, Smile, HandHeart,
  ChevronLeft, ChevronRight, Tag, Clock,
} from 'lucide-react';

const AMP_LOGO = 'https://actitudmentalpositivacom-43908122.hubspotpagebuilder.com/hubfs/main-logo-transparent-1.png';
const HUBSPOT_BASE = 'https://actitudmentalpositivacom-43908122.hubspotpagebuilder.com/hubfs/';

const GALLERY_IMAGES = [
  { src: `${HUBSPOT_BASE}IMG_9038.jpg`, alt: 'Taller AMP - Sesion grupal' },
  { src: `${HUBSPOT_BASE}IMG_9042.jpg`, alt: 'Taller AMP - Participantes' },
  { src: `${HUBSPOT_BASE}IMG_9140-2.jpg`, alt: 'Evento AMP - Comunidad' },
  { src: `${HUBSPOT_BASE}IMG_9109.jpg`, alt: 'Mentoria AMP - Coaching' },
  { src: `${HUBSPOT_BASE}IMG_8977.jpg`, alt: 'AMP - Crecimiento personal' },
];

const TALLERES = [
  { title: 'Autoconocimiento y Amor Propio', date: 'Proximo taller', duration: '3 horas', desc: 'Descubre quien eres realmente, identifica tus fortalezas y aprende a amarte sin condiciones.', color: '#D4A030' },
  { title: 'Manejo del Estres y Ansiedad', date: 'Cada mes', duration: '2 horas', desc: 'Tecnicas practicas de respiracion, mindfulness y reprogramacion mental para una vida en calma.', color: '#7CB98B' },
  { title: 'Comunicacion Consciente en Familia', date: 'Trimestral', duration: '4 horas', desc: 'Fortalece los vinculos familiares a traves de la escucha activa y la comunicacion no violenta.', color: '#9B8EC4' },
  { title: 'Liderazgo con Proposito', date: 'Bimensual', duration: '3 horas', desc: 'Lidera desde tu esencia. Desarrolla habilidades de liderazgo consciente para tu vida y negocio.', color: '#D4A030' },
  { title: 'Reto de Transformacion 21 Dias', date: 'Inicio cada mes', duration: '21 dias', desc: 'Programa intensivo de habitos positivos con tareas diarias, afirmaciones y reflexiones guiadas.', color: '#E07A5F' },
  { title: 'Meditacion y Sanacion Interior', date: 'Semanal', duration: '1 hora', desc: 'Sesiones guiadas de meditacion profunda para liberar emociones y conectar con tu paz interior.', color: '#7CB98B' },
];

const BLOG_POSTS = [
  { title: 'El poder de las afirmaciones positivas en tu vida diaria', tag: 'AmorPropio', date: '5 Mar 2026', excerpt: 'Las afirmaciones positivas son herramientas poderosas que reprograman tu mente subconsciente. Descubre como integrarlas en tu rutina matutina para transformar tu dia desde el primer momento.', color: '#D4A030' },
  { title: 'Como la actitud mental positiva transforma tus relaciones', tag: 'Transformacion', date: '28 Feb 2026', excerpt: 'Cuando cambias la forma en que ves el mundo, el mundo que ves cambia. Aprende como una mentalidad positiva mejora cada relacion en tu vida, desde la pareja hasta los companeros de trabajo.', color: '#9B8EC4' },
  { title: 'Crianza consciente: 5 claves para educar hijos emocionalmente inteligentes', tag: 'Educacion Hijos', date: '20 Feb 2026', excerpt: 'La educacion emocional comienza en casa. Te compartimos cinco practicas fundamentales para criar hijos resilientes, empaticos y seguros de si mismos.', color: '#7CB98B' },
  { title: 'De la frustacion a la motivacion: cambia tu perspectiva hoy', tag: 'Actitud', date: '15 Feb 2026', excerpt: 'La frustracion no es tu enemiga, es una senal de que algo necesita cambiar. Descubre como convertir cada obstaculo en un escalon hacia tu mejor version.', color: '#E07A5F' },
  { title: 'Mindfulness para principiantes: tu guia de 7 dias', tag: 'AmorPropio', date: '10 Feb 2026', excerpt: 'No necesitas experiencia para comenzar a meditar. Esta guia paso a paso te llevara de la curiosidad a la practica constante en solo una semana.', color: '#D4A030' },
  { title: 'El impacto del lenguaje positivo en la autoestima', tag: 'Transformacion', date: '5 Feb 2026', excerpt: 'Las palabras que usas contigo mismo crean tu realidad. Aprende a identificar y reemplazar el dialogo interno negativo por afirmaciones que te empoderen.', color: '#9B8EC4' },
];

const TEAM = [
  {
    name: 'Andrea Silva',
    role: 'Mentora de Padres (0-12 anos)',
    image: 'https://actitudmentalpositivacom-43908122.hubspotpagebuilder.com/hubfs/IMG_8929.jpg',
    quote: 'Yo estoy aqui con el proposito de servir y ayudar, para recordar que todos somos una fuente de amor inagotable',
    bio: 'Profesional en Marketing y Negocios Internacionales. Certificada en coaching espiritual, coaching ontologico, PNL internacional, familias conscientes (Mindvalley), lider de transformacion (John C. Maxwell Foundation).',
    specialties: ['Comunicacion', 'Vinculos familiares', 'Autoestima', 'Limites saludables'],
    color: '#D4A030',
  },
  {
    name: 'Dericielo Jimenez',
    role: 'Mentora de Vida Personal para Mujeres',
    image: 'https://actitudmentalpositivacom-43908122.hubspotpagebuilder.com/hubfs/WhatsApp%20Image%202024-09-23%20at%2010.54.14%20AM.jpeg',
    quote: 'Yo soy chispa divina del universo conectada con la tierra',
    bio: 'Guia a mujeres a traves del abandono, abuso (fisico, emocional, verbal, sexual) y efectos del trauma en las relaciones.',
    specialties: ['Superacion del abuso', 'Recuperacion de trauma', 'Reconstruccion de autoestima'],
    color: '#7CB98B',
  },
  {
    name: 'Lina Valencia Trivino',
    role: 'Life Coach — Duelo y Relaciones',
    image: 'https://actitudmentalpositivacom-43908122.hubspotpagebuilder.com/hubfs/LinaMerced2.jpg',
    quote: 'Soy una persona que fluye con la vida en amor y tranquilidad',
    bio: 'Ingeniera Industrial, Master en Ciencias Economicas y Sociales. International Master Coach (ICF). Certificada en coaching espiritual, PNL, coaching de personalidad, Sanadores de Luz.',
    specialties: ['Duelo', 'Perdida de relaciones', 'Conflictos familiares', 'Mindfulness'],
    color: '#9B8EC4',
  },
  {
    name: 'Juan Diego Giraldo',
    role: 'Coach de Negocios y Vida',
    image: 'https://actitudmentalpositivacom-43908122.hubspotpagebuilder.com/hubfs/Copia%20de%20IMG_9033.jpg',
    quote: 'Soy un ser valiente, lider, abundante, saludable y organizado',
    bio: 'Ingeniero de Sistemas, especialista en Gestion de Proyectos IT y Ciberseguridad. Integra el desarrollo personal en el liderazgo empresarial.',
    specialties: ['Confianza', 'Bloqueos creativos', 'Vida consciente', 'Emprendimiento'],
    color: '#D4A030',
  },
];

const SERVICES = [
  { icon: <Users size={24} />, title: 'Sesiones de Coaching Individual', desc: 'Mentoria personalizada enfocada en creencias limitantes, miedos, gestion emocional y establecimiento de metas.' },
  { icon: <BookOpen size={24} />, title: 'Talleres y Seminarios en Vivo', desc: 'Online y presenciales sobre autoconocimiento, manejo del estres, resiliencia, motivacion y autoempoderamiento.' },
  { icon: <Sparkles size={24} />, title: 'Programas de Transformacion Personal', desc: 'Experiencias de inmersion multi-dia que convierten pensamientos negativos en positivos, mejorando la autoestima.' },
  { icon: <Play size={24} />, title: 'Meditaciones Guiadas y Mindfulness', desc: 'Biblioteca de audio/video para bienestar emocional, reduccion de ansiedad y conexion con el presente.' },
  { icon: <Target size={24} />, title: 'Cursos Online de Actitud Mental Positiva', desc: 'Modulos interactivos con ejercicios practicos y materiales descargables.' },
  { icon: <MessageCircle size={24} />, title: 'Club AMP — Comunidad de Apoyo', desc: 'Espacio virtual para apoyo entre pares y experiencias compartidas de crecimiento.' },
  { icon: <Video size={24} />, title: 'Mentorias Grupales en Video', desc: 'Sesiones en grupos pequenos con mentores especializados. Conecta en vivo desde cualquier lugar.' },
  { icon: <Gift size={24} />, title: 'Biblioteca de Recursos', desc: 'Articulos, libros, podcasts y videos sobre desarrollo personal y crecimiento.' },
  { icon: <Calendar size={24} />, title: 'Retos de 9, 18 y 21 Dias', desc: 'Programas estructurados con tareas diarias, afirmaciones y reflexiones profundas.' },
];

const VALUES = [
  { name: 'Confianza', icon: <Shield size={18} />, desc: 'Seguridad en uno mismo y en los demas' },
  { name: 'Empatia', icon: <Heart size={18} />, desc: 'Comprender las emociones de otros' },
  { name: 'Respeto', icon: <Eye size={18} />, desc: 'Reconocimiento del valor humano inherente' },
  { name: 'Compasion', icon: <HandHeart size={18} />, desc: 'Deseo sincero de aliviar el sufrimiento' },
  { name: 'Empoderamiento', icon: <Crown size={18} />, desc: 'Descubrir el poder interior' },
  { name: 'Optimismo', icon: <Sun size={18} />, desc: 'Vivir el presente con vision positiva' },
  { name: 'Crecimiento', icon: <Leaf size={18} />, desc: 'Aprendizaje y desarrollo constante' },
  { name: 'Autenticidad', icon: <Compass size={18} />, desc: 'Honestidad, integridad, ser uno mismo' },
  { name: 'Gratitud', icon: <Sparkles size={18} />, desc: 'Apreciacion y mentalidad de abundancia' },
  { name: 'Amor Propio', icon: <Smile size={18} />, desc: 'Autocuidado como base de transformacion' },
];

const TAG_COLORS: Record<string, string> = {
  AmorPropio: '#D4A030',
  Transformacion: '#9B8EC4',
  'Educacion Hijos': '#7CB98B',
  Actitud: '#E07A5F',
};

export default function AmpLanding() {
  const router = useRouter();
  const [expandedTeam, setExpandedTeam] = useState<number | null>(null);
  const [galleryIndex, setGalleryIndex] = useState(0);

  const nextSlide = () => setGalleryIndex((galleryIndex + 1) % GALLERY_IMAGES.length);
  const prevSlide = () => setGalleryIndex((galleryIndex - 1 + GALLERY_IMAGES.length) % GALLERY_IMAGES.length);

  return (
    <div style={{ fontFamily: "'Nunito', sans-serif", background: '#FFF9F0', color: '#2D2A26', minHeight: '100vh' }}>
      {/* Nav */}
      <nav style={{ background: '#2D2A26', position: 'sticky', top: 0, zIndex: 50 }}>
        <div style={{ maxWidth: 1100, margin: '0 auto', padding: '0 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 56 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <img src={AMP_LOGO} alt="AMP Logo" style={{ height: 36, width: 'auto', objectFit: 'contain' }} />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
            {['Inicio', 'Galeria', 'Equipo', 'Talleres', 'Servicios', 'Blog', 'Valores'].map(item => (
              <a key={item} href={`#${item.toLowerCase()}`} style={{ color: '#9B9590', fontSize: 12, fontWeight: 600, textDecoration: 'none', letterSpacing: 0.5 }}>{item}</a>
            ))}
            <button onClick={() => router.push('/amp/login')}
              style={{ background: '#D4A030', color: '#fff', border: 'none', borderRadius: 8, padding: '8px 20px', fontSize: 12, fontWeight: 700, cursor: 'pointer' }}>
              Ingresar
            </button>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section id="inicio" style={{
        position: 'relative', minHeight: 520, display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'linear-gradient(135deg, #2D2A26 0%, #3d3530 50%, #2D2A26 100%)',
        overflow: 'hidden',
      }}>
        <div style={{ position: 'absolute', inset: 0, opacity: 0.15 }}>
          <img src="https://actitudmentalpositivacom-43908122.hubspotpagebuilder.com/hubfs/IMG_8786.jpg"
            alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
        </div>
        <div style={{ position: 'relative', textAlign: 'center', maxWidth: 700, padding: '60px 20px' }}>
          <img src={AMP_LOGO} alt="Actitud Mental Positiva" style={{ height: 80, width: 'auto', objectFit: 'contain', marginBottom: 24 }} />
          <h1 style={{ fontFamily: "'Playfair Display', serif", fontSize: 48, fontWeight: 700, color: '#FFF9F0', lineHeight: 1.2, margin: '0 0 20px' }}>
            Transforma tu mente,<br /><span style={{ color: '#D4A030' }}>transforma tu vida</span>
          </h1>
          <p style={{ fontSize: 17, color: '#c0b8a8', lineHeight: 1.7, margin: '0 0 32px' }}>
            Una Actitud Mental Positiva nos permite disfrutar cada nuevo dia y vivir en el aqui y en el ahora.
            Descubre tu maximo potencial a traves de contenido de crecimiento personal de alta calidad.
          </p>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
            <button onClick={() => router.push('/amp/signup')}
              style={{ background: '#D4A030', color: '#fff', border: 'none', borderRadius: 12, padding: '14px 32px', fontSize: 14, fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8, boxShadow: '0 4px 20px rgba(212,160,48,0.3)' }}>
              Comienza Gratis <ArrowRight size={16} />
            </button>
            <button onClick={() => window.open('https://actitudmentalpositiva.com/', '_blank')}
              style={{ background: 'transparent', color: '#FFF9F0', border: '2px solid #5C5650', borderRadius: 12, padding: '14px 32px', fontSize: 14, fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
              <Video size={16} /> Agendar Llamada
            </button>
          </div>
          <p style={{ fontSize: 12, color: '#9B9590', marginTop: 16 }}>
            Mentoria inicial de 15 minutos GRATIS
          </p>
        </div>
      </section>

      {/* Mission */}
      <section style={{ background: '#FEF7EC', padding: '48px 20px', textAlign: 'center' }}>
        <div style={{ maxWidth: 700, margin: '0 auto' }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#D4A030', letterSpacing: 2, marginBottom: 12 }}>NUESTRA MISION</div>
          <p style={{ fontFamily: "'Playfair Display', serif", fontSize: 22, fontWeight: 600, color: '#2D2A26', lineHeight: 1.6, margin: 0 }}>
            &ldquo;Motivar e inspirar a cada persona del mundo para que alcance su maximo potencial a traves de contenido de crecimiento personal de alta calidad&rdquo;
          </p>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#9B9590', letterSpacing: 2, marginTop: 24 }}>VISION</div>
          <p style={{ fontSize: 14, color: '#5C5650', marginTop: 6 }}>
            Ser la plataforma de transformacion personal con mas impacto global en los proximos 10 anos
          </p>
        </div>
      </section>

      {/* Gallery / Carousel */}
      <section id="galeria" style={{ padding: '56px 20px', background: '#2D2A26' }}>
        <div style={{ maxWidth: 1000, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 32 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: '#D4A030', letterSpacing: 2, marginBottom: 8 }}>NUESTRA COMUNIDAD</div>
            <h2 style={{ fontFamily: "'Playfair Display', serif", fontSize: 28, color: '#FFF9F0', margin: 0 }}>Galeria AMP</h2>
          </div>
          <div style={{ position: 'relative', borderRadius: 20, overflow: 'hidden', maxHeight: 480 }}>
            <img
              src={GALLERY_IMAGES[galleryIndex].src}
              alt={GALLERY_IMAGES[galleryIndex].alt}
              style={{ width: '100%', height: 480, objectFit: 'cover', display: 'block', transition: 'opacity 0.3s' }}
            />
            <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, background: 'linear-gradient(transparent, rgba(0,0,0,0.7))', padding: '40px 24px 20px' }}>
              <p style={{ color: '#FFF9F0', fontSize: 14, fontWeight: 600, margin: 0 }}>{GALLERY_IMAGES[galleryIndex].alt}</p>
            </div>
            <button onClick={prevSlide} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', background: 'rgba(0,0,0,0.5)', border: 'none', borderRadius: 12, width: 40, height: 40, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', color: '#fff' }}>
              <ChevronLeft size={20} />
            </button>
            <button onClick={nextSlide} style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', background: 'rgba(0,0,0,0.5)', border: 'none', borderRadius: 12, width: 40, height: 40, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', color: '#fff' }}>
              <ChevronRight size={20} />
            </button>
          </div>
          {/* Dots */}
          <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginTop: 16 }}>
            {GALLERY_IMAGES.map((_, i) => (
              <button key={i} onClick={() => setGalleryIndex(i)} style={{
                width: galleryIndex === i ? 24 : 8, height: 8, borderRadius: 4,
                background: galleryIndex === i ? '#D4A030' : '#5C5650',
                border: 'none', cursor: 'pointer', transition: 'all 0.3s',
              }} />
            ))}
          </div>
          {/* Thumbnails */}
          <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginTop: 16 }}>
            {GALLERY_IMAGES.map((img, i) => (
              <button key={i} onClick={() => setGalleryIndex(i)} style={{
                width: 72, height: 52, borderRadius: 10, overflow: 'hidden', border: galleryIndex === i ? '2px solid #D4A030' : '2px solid transparent',
                cursor: 'pointer', opacity: galleryIndex === i ? 1 : 0.5, transition: 'all 0.2s', padding: 0, background: 'none',
              }}>
                <img src={img.src} alt={img.alt} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* 3 Pillars */}
      <section style={{ padding: '48px 20px', maxWidth: 1000, margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: 36 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#D4A030', letterSpacing: 2, marginBottom: 8 }}>TRES PILARES</div>
          <h2 style={{ fontFamily: "'Playfair Display', serif", fontSize: 28, color: '#2D2A26', margin: 0 }}>Fundamentos de Transformacion</h2>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
          {[
            { icon: <Brain size={28} />, name: 'Mentalidad', desc: 'Reprograma tus pensamientos, supera creencias limitantes y desarrolla una mentalidad de crecimiento y abundancia.', color: '#D4A030', bg: '#FEF7EC' },
            { icon: <Heart size={28} />, name: 'Bienestar', desc: 'Cultiva paz interior, gestiona el estres y construye habitos que nutren tu cuerpo, mente y espiritu.', color: '#7CB98B', bg: '#E8F5EC' },
            { icon: <Crown size={28} />, name: 'Liderazgo', desc: 'Lidera tu propia vida con proposito, inspira a otros y toma decisiones conscientes hacia tus metas.', color: '#9B8EC4', bg: '#EDE8F5' },
          ].map(p => (
            <div key={p.name} style={{ background: p.bg, borderRadius: 16, padding: 28, textAlign: 'center', border: `1px solid ${p.color}25` }}>
              <div style={{ width: 56, height: 56, borderRadius: 16, background: '#fff', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', color: p.color, marginBottom: 14, boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
                {p.icon}
              </div>
              <h3 style={{ fontSize: 18, fontWeight: 700, color: '#2D2A26', margin: '0 0 8px' }}>{p.name}</h3>
              <p style={{ fontSize: 13, color: '#5C5650', lineHeight: 1.6, margin: 0 }}>{p.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Team */}
      <section id="equipo" style={{ background: '#2D2A26', padding: '56px 20px' }}>
        <div style={{ maxWidth: 1000, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 40 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: '#D4A030', letterSpacing: 2, marginBottom: 8 }}>NUESTRO EQUIPO</div>
            <h2 style={{ fontFamily: "'Playfair Display', serif", fontSize: 28, color: '#FFF9F0', margin: 0 }}>Mentores Certificados</h2>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 16 }}>
            {TEAM.map((m, i) => (
              <div key={m.name} style={{ background: '#3d3a36', borderRadius: 16, overflow: 'hidden', border: '1px solid #4d4a46' }}>
                <div style={{ display: 'flex', gap: 16, padding: 20 }}>
                  <img src={m.image} alt={m.name}
                    style={{ width: 90, height: 90, borderRadius: 14, objectFit: 'cover', flexShrink: 0 }} />
                  <div>
                    <h3 style={{ fontSize: 16, fontWeight: 700, color: '#FFF9F0', margin: '0 0 4px' }}>{m.name}</h3>
                    <div style={{ fontSize: 11, fontWeight: 600, color: m.color, marginBottom: 8 }}>{m.role}</div>
                    <p style={{ fontSize: 12, color: '#c0b8a8', lineHeight: 1.5, margin: 0, fontStyle: 'italic' }}>
                      &ldquo;{m.quote}&rdquo;
                    </p>
                  </div>
                </div>
                <button onClick={() => setExpandedTeam(expandedTeam === i ? null : i)}
                  style={{ width: '100%', background: '#4d4a46', border: 'none', padding: '8px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer', color: '#9B9590', fontSize: 11, fontWeight: 600 }}>
                  Ver mas <ChevronDown size={14} style={{ transform: expandedTeam === i ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />
                </button>
                {expandedTeam === i && (
                  <div style={{ padding: '16px 20px', borderTop: '1px solid #4d4a46' }}>
                    <p style={{ fontSize: 12, color: '#c0b8a8', lineHeight: 1.6, margin: '0 0 12px' }}>{m.bio}</p>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {m.specialties.map(s => (
                        <span key={s} style={{ fontSize: 10, fontWeight: 600, padding: '3px 10px', borderRadius: 6, background: m.color + '20', color: m.color }}>{s}</span>
                      ))}
                    </div>
                    <button onClick={() => window.open('https://actitudmentalpositiva.com/', '_blank')}
                      style={{ marginTop: 12, background: m.color, color: '#fff', border: 'none', borderRadius: 8, padding: '8px 16px', fontSize: 11, fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
                      <Video size={13} /> Agendar Mentoria
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Talleres (Workshops) */}
      <section id="talleres" style={{ padding: '56px 20px', background: '#FFF9F0' }}>
        <div style={{ maxWidth: 1000, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 36 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: '#D4A030', letterSpacing: 2, marginBottom: 8 }}>TALLERES Y PROGRAMAS</div>
            <h2 style={{ fontFamily: "'Playfair Display', serif", fontSize: 28, color: '#2D2A26', margin: 0 }}>Transforma Tu Vida con Nuestros Talleres</h2>
            <p style={{ fontSize: 14, color: '#5C5650', marginTop: 10, maxWidth: 600, marginLeft: 'auto', marginRight: 'auto' }}>
              Experiencias presenciales y virtuales disenadas para activar tu potencial y crear cambios duraderos.
            </p>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
            {TALLERES.map((t, i) => (
              <div key={i} style={{
                background: '#fff', borderRadius: 16, padding: 24, border: '1px solid #F5EDE0',
                borderTop: `3px solid ${t.color}`, transition: 'box-shadow 0.2s, transform 0.2s',
              }}
                onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.boxShadow = '0 8px 24px rgba(0,0,0,0.08)'; (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-2px)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.boxShadow = 'none'; (e.currentTarget as HTMLDivElement).style.transform = 'none'; }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                  <div style={{ width: 36, height: 36, borderRadius: 10, background: t.color + '15', display: 'flex', alignItems: 'center', justifyContent: 'center', color: t.color }}>
                    <BookOpen size={18} />
                  </div>
                  <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                    <Clock size={11} color="#9B9590" />
                    <span style={{ fontSize: 10, color: '#9B9590', fontWeight: 600 }}>{t.duration}</span>
                  </div>
                </div>
                <h3 style={{ fontSize: 15, fontWeight: 700, color: '#2D2A26', margin: '0 0 6px' }}>{t.title}</h3>
                <div style={{ fontSize: 11, fontWeight: 600, color: t.color, marginBottom: 8 }}>{t.date}</div>
                <p style={{ fontSize: 12, color: '#5C5650', lineHeight: 1.6, margin: '0 0 14px' }}>{t.desc}</p>
                <button onClick={() => window.open('https://actitudmentalpositiva.com/', '_blank')}
                  style={{ background: t.color, color: '#fff', border: 'none', borderRadius: 8, padding: '8px 16px', fontSize: 11, fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, width: '100%', justifyContent: 'center' }}>
                  Inscribirme <ArrowRight size={13} />
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Services */}
      <section id="servicios" style={{ padding: '56px 20px', maxWidth: 1000, margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: 36 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#D4A030', letterSpacing: 2, marginBottom: 8 }}>SERVICIOS POSITIVOS</div>
          <h2 style={{ fontFamily: "'Playfair Display', serif", fontSize: 28, color: '#2D2A26', margin: 0 }}>Lo Que Ofrecemos</h2>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14 }}>
          {SERVICES.map((s, i) => (
            <div key={i} style={{
              background: '#fff', borderRadius: 14, padding: 22, border: '1px solid #F5EDE0',
              transition: 'box-shadow 0.2s, transform 0.2s',
            }}
              onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.boxShadow = '0 8px 24px rgba(0,0,0,0.08)'; (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-2px)'; }}
              onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.boxShadow = 'none'; (e.currentTarget as HTMLDivElement).style.transform = 'none'; }}
            >
              <div style={{ width: 44, height: 44, borderRadius: 12, background: '#FEF7EC', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#D4A030', marginBottom: 12 }}>
                {s.icon}
              </div>
              <h3 style={{ fontSize: 14, fontWeight: 700, color: '#2D2A26', margin: '0 0 6px' }}>{s.title}</h3>
              <p style={{ fontSize: 12, color: '#5C5650', lineHeight: 1.5, margin: 0 }}>{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Blog Preview */}
      <section id="blog" style={{ padding: '56px 20px', background: '#FEF7EC' }}>
        <div style={{ maxWidth: 1000, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 36 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: '#D4A030', letterSpacing: 2, marginBottom: 8 }}>BLOG AMP</div>
            <h2 style={{ fontFamily: "'Playfair Display', serif", fontSize: 28, color: '#2D2A26', margin: 0 }}>Articulos de Crecimiento Personal</h2>
            <p style={{ fontSize: 14, color: '#5C5650', marginTop: 10 }}>
              Reflexiones, consejos y herramientas para tu transformacion diaria.
            </p>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
            {BLOG_POSTS.map((post, i) => (
              <div key={i} style={{
                background: '#fff', borderRadius: 16, overflow: 'hidden', border: '1px solid #F5EDE0',
                transition: 'box-shadow 0.2s, transform 0.2s',
              }}
                onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.boxShadow = '0 8px 24px rgba(0,0,0,0.08)'; (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-2px)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.boxShadow = 'none'; (e.currentTarget as HTMLDivElement).style.transform = 'none'; }}
              >
                <div style={{ height: 4, background: post.color }} />
                <div style={{ padding: 22 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                    <span style={{ fontSize: 10, fontWeight: 700, padding: '3px 10px', borderRadius: 6, background: (TAG_COLORS[post.tag] || '#D4A030') + '20', color: TAG_COLORS[post.tag] || '#D4A030' }}>
                      <Tag size={9} style={{ marginRight: 3, verticalAlign: 'middle' }} />{post.tag}
                    </span>
                    <span style={{ fontSize: 10, color: '#9B9590' }}>{post.date}</span>
                  </div>
                  <h3 style={{ fontSize: 15, fontWeight: 700, color: '#2D2A26', margin: '0 0 8px', lineHeight: 1.4 }}>{post.title}</h3>
                  <p style={{ fontSize: 12, color: '#5C5650', lineHeight: 1.6, margin: '0 0 14px' }}>{post.excerpt}</p>
                  <button onClick={() => window.open('https://actitudmentalpositiva.com/', '_blank')}
                    style={{ background: 'transparent', color: post.color, border: 'none', padding: 0, fontSize: 12, fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
                    Leer mas <ArrowRight size={12} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Values */}
      <section id="valores" style={{ background: '#FFF9F0', padding: '48px 20px' }}>
        <div style={{ maxWidth: 1000, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 36 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: '#D4A030', letterSpacing: 2, marginBottom: 8 }}>NUESTROS VALORES</div>
            <h2 style={{ fontFamily: "'Playfair Display', serif", fontSize: 28, color: '#2D2A26', margin: 0 }}>Lo Que Nos Define</h2>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, justifyContent: 'center' }}>
            {VALUES.map(v => (
              <div key={v.name} style={{
                background: '#fff', borderRadius: 12, padding: '12px 18px', display: 'flex', alignItems: 'center', gap: 10,
                border: '1px solid #F5EDE0', minWidth: 200,
              }}>
                <div style={{ color: '#D4A030' }}>{v.icon}</div>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: '#2D2A26' }}>{v.name}</div>
                  <div style={{ fontSize: 10, color: '#9B9590' }}>{v.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section style={{
        background: 'linear-gradient(135deg, #D4A030 0%, #c49028 50%, #b48020 100%)',
        padding: '56px 20px', textAlign: 'center',
      }}>
        <div style={{ maxWidth: 600, margin: '0 auto' }}>
          <img src={AMP_LOGO} alt="AMP" style={{ height: 48, width: 'auto', marginBottom: 16, filter: 'brightness(10)' }} />
          <h2 style={{ fontFamily: "'Playfair Display', serif", fontSize: 30, color: '#fff', margin: '0 0 12px' }}>
            Tu Transformacion Comienza Hoy
          </h2>
          <p style={{ fontSize: 15, color: '#fff', opacity: 0.9, lineHeight: 1.6, margin: '0 0 28px' }}>
            Unete a nuestra comunidad. Accede a afirmaciones diarias, meditaciones, seguimiento de animo,
            diario de gratitud y retos de crecimiento personal.
          </p>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
            <button onClick={() => router.push('/amp/signup')}
              style={{ background: '#fff', color: '#D4A030', border: 'none', borderRadius: 12, padding: '14px 36px', fontSize: 15, fontWeight: 800, cursor: 'pointer' }}>
              Crear Cuenta Gratis
            </button>
            <button onClick={() => router.push('/amp/login')}
              style={{ background: 'transparent', color: '#fff', border: '2px solid rgba(255,255,255,0.5)', borderRadius: 12, padding: '14px 36px', fontSize: 15, fontWeight: 700, cursor: 'pointer' }}>
              Ya Tengo Cuenta
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer style={{ background: '#2D2A26', padding: '36px 20px', textAlign: 'center' }}>
        <div style={{ maxWidth: 600, margin: '0 auto' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, marginBottom: 16 }}>
            <img src={AMP_LOGO} alt="AMP" style={{ height: 32, width: 'auto', objectFit: 'contain' }} />
          </div>
          <p style={{ fontSize: 12, color: '#9B9590', margin: '0 0 12px' }}>Actitud Mental Positiva — Productos Positivos para su Bienestar</p>
          <div style={{ display: 'flex', gap: 16, justifyContent: 'center', marginBottom: 16 }}>
            {[
              { icon: <Instagram size={16} />, url: 'https://www.instagram.com/actitudmentalpositiva_amp/' },
              { icon: <Facebook size={16} />, url: 'https://www.facebook.com/people/Actitud-Mental-Positiva/61563915498792/' },
              { icon: <Linkedin size={16} />, url: 'https://www.linkedin.com/company/actitud-mental-positiva-amp/' },
              { icon: <Mail size={16} />, url: 'mailto:info@actitudmentalpositiva.com' },
            ].map((s, i) => (
              <a key={i} href={s.url} target="_blank" rel="noopener noreferrer"
                style={{ color: '#9B9590', display: 'flex', padding: 8 }}>
                {s.icon}
              </a>
            ))}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, fontSize: 11, color: '#5C5650', marginBottom: 8 }}>
            <MapPin size={11} /> Cra 24D #4-64 OE, Cali, VA — Colombia
          </div>
          <p style={{ fontSize: 10, color: '#5C5650', margin: 0 }}>&copy; 2026 AMP — Actitud Mental Positiva. Powered by Empire.</p>
        </div>
      </footer>
    </div>
  );
}
