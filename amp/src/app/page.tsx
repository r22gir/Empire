'use client';
import { useState } from 'react';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import { getTodayAffirmation, getTodayMeditation, PILLAR_CONFIG, COURSES } from '../lib/data';
import { Sun, Play, ArrowRight, Star, Users, BookOpen, Check, Sparkles } from 'lucide-react';

export default function LandingPage() {
  const [email, setEmail] = useState('');
  const [subscribed, setSubscribed] = useState(false);
  const affirmation = getTodayAffirmation();
  const meditation = getTodayMeditation();

  const handleSubscribe = (e: React.FormEvent) => {
    e.preventDefault();
    if (email.includes('@')) {
      setSubscribed(true);
      setEmail('');
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      {/* ── Hero ── */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-gold-light/30 via-warmwhite to-sage-light/20" />
        <div className="absolute top-20 right-10 w-72 h-72 bg-sunrise/10 rounded-full blur-3xl" />
        <div className="absolute bottom-10 left-10 w-60 h-60 bg-lavender/10 rounded-full blur-3xl" />

        <div className="relative max-w-5xl mx-auto px-4 py-16 md:py-24 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gold/10 border border-gold/20 text-sm font-semibold text-gold-dark mb-6">
            <Sparkles size={16} />
            El Portal de la Alegría
          </div>

          <h1 className="font-serif text-4xl md:text-6xl font-bold leading-tight mb-6 text-[#2D2A26]">
            Transforma tu mente,<br />
            <span className="gradient-text">transforma tu vida</span>
          </h1>

          <p className="text-lg md:text-xl text-[#5C5650] max-w-2xl mx-auto mb-8 leading-relaxed">
            Una plataforma para ayudarte a generar un cambio mental positivo, manifestar bienestar
            y compartir herramientas maravillosas de aprendizaje y sanación.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mb-12">
            <a href="/daily"
              className="inline-flex items-center gap-2 px-8 py-4 rounded-2xl bg-gradient-to-r from-gold to-sunrise text-white font-bold text-lg shadow-lg shadow-gold/25 hover:shadow-xl hover:shadow-gold/30 transition-all hover:scale-[1.02] no-underline">
              Comienza Hoy <ArrowRight size={20} />
            </a>
            <a href="/retos"
              className="inline-flex items-center gap-2 px-8 py-4 rounded-2xl border-2 border-gold/30 text-gold-dark font-bold text-lg hover:bg-gold/5 transition-all no-underline">
              Ver Retos <BookOpen size={20} />
            </a>
          </div>

          {/* Daily preview card */}
          <div className="max-w-lg mx-auto bg-white rounded-3xl shadow-lg shadow-gold/10 border border-gold-light/40 p-6 text-left">
            <p className="text-xs font-bold text-gold tracking-wider mb-2">AFIRMACIÓN DEL DÍA</p>
            <p className="font-serif text-lg italic text-[#2D2A26] leading-relaxed mb-4">&ldquo;{affirmation}&rdquo;</p>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm text-sage-dark font-semibold">
                <Play size={14} className="text-sage" /> {meditation.title} · {meditation.duration}
              </div>
              <a href="/daily" className="text-xs font-bold text-gold hover:text-gold-dark no-underline">Ir al Diario →</a>
            </div>
          </div>
        </div>
      </section>

      {/* ── Mission ── */}
      <section className="py-12 bg-gradient-to-b from-cream to-warmwhite">
        <div className="max-w-3xl mx-auto px-4 text-center">
          <h2 className="font-serif text-2xl md:text-3xl font-bold text-[#2D2A26] mb-4">Nuestra Misión</h2>
          <p className="text-[#5C5650] leading-relaxed text-lg">
            Motivar e inspirar a cada persona del mundo para que alcance su máximo potencial
            a través de contenido de crecimiento personal de alta calidad, guiándolas en los momentos difíciles,
            facilitándoles procesos de automotivación para que avancen hacia un siguiente nivel de plenitud
            y prosperidad en las diferentes áreas de sus vidas.
          </p>
          <div className="flex flex-wrap justify-center gap-3 mt-6">
            {['Confianza', 'Empatía', 'Gratitud', 'Autenticidad', 'Amor Propio', 'Optimismo', 'Crecimiento'].map(v => (
              <span key={v} className="px-3 py-1.5 rounded-full text-xs font-semibold bg-gold/10 text-gold-dark border border-gold/20">{v}</span>
            ))}
          </div>
        </div>
      </section>

      {/* ── 3 Pillars ── */}
      <section className="py-16 md:py-20">
        <div className="max-w-5xl mx-auto px-4">
          <h2 className="font-serif text-3xl md:text-4xl font-bold text-center mb-3 text-[#2D2A26]">Los 3 Pilares</h2>
          <p className="text-center text-[#9B9590] mb-10 text-lg">La base de tu transformación personal</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {(Object.entries(PILLAR_CONFIG) as [string, typeof PILLAR_CONFIG.mentalidad][]).map(([key, p]) => (
              <div key={key} className={`rounded-3xl p-8 bg-gradient-to-br ${p.gradient} border border-white/60 hover:shadow-lg transition-all hover:scale-[1.02]`}>
                <span className="text-4xl mb-4 block">{p.icon}</span>
                <h3 className="font-serif text-2xl font-bold mb-2" style={{ color: p.color }}>{p.label}</h3>
                <p className="text-[#5C5650] leading-relaxed">{p.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Featured Courses ── */}
      <section className="py-16 bg-gradient-to-b from-warmwhite to-cream">
        <div className="max-w-5xl mx-auto px-4">
          <h2 className="font-serif text-3xl md:text-4xl font-bold text-center mb-3 text-[#2D2A26]">Retos AMP</h2>
          <p className="text-center text-[#9B9590] mb-10 text-lg">Desafíos de 21 días que transforman tu vida</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {COURSES.slice(0, 3).map(c => {
              const pillar = PILLAR_CONFIG[c.pillar as keyof typeof PILLAR_CONFIG];
              return (
                <a href={`/retos?id=${c.id}`} key={c.id}
                  className="bg-white rounded-3xl p-6 border border-gold-light/30 hover:shadow-lg hover:border-gold/30 transition-all group no-underline">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-xl">{pillar.icon}</span>
                    <span className="text-xs font-bold px-2 py-1 rounded-full" style={{ color: pillar.color, background: pillar.color + '15' }}>{pillar.label}</span>
                    {c.premium && <span className="text-xs font-bold text-sunrise bg-sunrise/10 px-2 py-1 rounded-full ml-auto">Premium</span>}
                  </div>
                  <h3 className="font-serif text-xl font-bold text-[#2D2A26] mb-2 group-hover:text-gold-dark transition-colors">{c.title}</h3>
                  <p className="text-sm text-[#9B9590] mb-4 leading-relaxed">{c.description}</p>
                  <div className="flex items-center gap-4 text-xs text-[#9B9590]">
                    <span className="flex items-center gap-1"><BookOpen size={12} /> {c.days} días</span>
                    <span className="flex items-center gap-1"><Users size={12} /> {c.enrolled.toLocaleString()}</span>
                    <span className="flex items-center gap-1"><Star size={12} className="text-gold" /> {c.rating}</span>
                  </div>
                </a>
              );
            })}
          </div>
          <div className="text-center mt-8">
            <a href="/retos" className="inline-flex items-center gap-2 text-gold-dark font-bold hover:text-gold transition-colors no-underline">
              Ver todos los retos <ArrowRight size={16} />
            </a>
          </div>
        </div>
      </section>

      {/* ── Nuestro Equipo ── */}
      <section className="py-16">
        <div className="max-w-5xl mx-auto px-4">
          <h2 className="font-serif text-3xl md:text-4xl font-bold text-center mb-3 text-[#2D2A26]">Nuestro Equipo</h2>
          <p className="text-center text-[#9B9590] mb-10 text-lg">Coaches certificados comprometidos con tu transformación</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {[
              { name: "Andrea Silva", role: "Mentora de Padres (0-12 años)", color: "#D4A030", icon: "🌻",
                bio: "Profesional en Marketing y Negocios Internacionales. Certificada en Coaching Espiritual, Coaching Ontológico, PNL, Familias Conscientes (Mindvalley) y Liderazgo John C. Maxwell.",
                focus: "Crianza consciente y desarrollo familiar" },
              { name: "Dericielo Jimenez", role: "Coach de Vida para Mujeres", color: "#7CB98B", icon: "🌿",
                bio: "Especialista en recuperación de trauma, sanación del abuso y reconstrucción de autoestima. Herramientas: PNL, meditación interior, danza y coaching espiritual.",
                focus: "Sanación del abandono, abuso emocional y físico" },
              { name: "Lina Valencia Trivino", role: "Coach de Vida (Duelo y Relaciones)", color: "#9B8EC4", icon: "💫",
                bio: "ICF International Master Coach, Ingeniera Industrial, Máster en Ciencias Económicas y Sociales. Certificada en Coaching Espiritual, Coaching de Personalidad y PNL.",
                focus: "Duelo, pérdida, conflictos de relación y transiciones de vida" },
              { name: "Juan Diego Giraldo", role: "Coach de Negocios y Vida", color: "#D4A030", icon: "⚡",
                bio: "Ingeniero de Sistemas, especializado en Gestión de Proyectos TI y Ciberseguridad. Certificado en Coaching de Personalidad, PNL y Propósito de Vida.",
                focus: "Profesionales, emprendedores y bloqueo creativo" },
            ].map((t, i) => (
              <div key={i} className="bg-white rounded-3xl p-6 border border-gold-light/30 shadow-sm hover:shadow-md transition-all">
                <div className="flex items-start gap-4 mb-3">
                  <div className="w-14 h-14 rounded-2xl flex items-center justify-center text-3xl shrink-0"
                    style={{ background: t.color + '15' }}>
                    {t.icon}
                  </div>
                  <div>
                    <div className="font-serif font-bold text-lg text-[#2D2A26]">{t.name}</div>
                    <div className="text-sm font-semibold" style={{ color: t.color }}>{t.role}</div>
                  </div>
                </div>
                <p className="text-sm text-[#5C5650] leading-relaxed mb-2">{t.bio}</p>
                <p className="text-xs text-[#9B9590]"><span className="font-bold">Enfoque:</span> {t.focus}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Testimonios ── */}
      <section className="py-16 bg-gradient-to-b from-warmwhite to-cream">
        <div className="max-w-5xl mx-auto px-4">
          <h2 className="font-serif text-3xl font-bold text-center mb-10 text-[#2D2A26]">Historias de Transformación</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              { name: "María Elena", loc: "Bogotá, Colombia", text: "AMP me ayudó a salir de un momento muy difícil. Las meditaciones diarias se convirtieron en mi refugio de paz.", avatar: "🌸" },
              { name: "Carlos R.", loc: "Ciudad de México", text: "El reto de 21 días de gratitud cambió mi perspectiva completamente. Ahora veo oportunidades donde antes veía problemas.", avatar: "🌟" },
              { name: "Ana Lucía", loc: "Buenos Aires, Argentina", text: "Como líder de equipo, el contenido de liderazgo me dio herramientas que uso todos los días. Genuino y profundo.", avatar: "💫" },
            ].map((t, i) => (
              <div key={i} className="bg-white rounded-3xl p-6 border border-gold-light/30 shadow-sm">
                <div className="flex items-center gap-3 mb-4">
                  <span className="text-2xl w-10 h-10 rounded-full bg-gold/10 flex items-center justify-center">{t.avatar}</span>
                  <div>
                    <div className="font-bold text-sm text-[#2D2A26]">{t.name}</div>
                    <div className="text-xs text-[#9B9590]">{t.loc}</div>
                  </div>
                </div>
                <p className="text-sm text-[#5C5650] italic leading-relaxed">&ldquo;{t.text}&rdquo;</p>
                <div className="flex gap-0.5 mt-3">
                  {[...Array(5)].map((_, j) => <Star key={j} size={14} className="text-gold fill-gold" />)}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Pricing ── */}
      <section className="py-16 bg-gradient-to-b from-warmwhite to-cream">
        <div className="max-w-4xl mx-auto px-4">
          <h2 className="font-serif text-3xl md:text-4xl font-bold text-center mb-3 text-[#2D2A26]">Tu Camino Comienza Aquí</h2>
          <p className="text-center text-[#9B9590] mb-10 text-lg">Contenido gratuito para empezar. Premium para profundizar.</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-3xl mx-auto">
            {/* Free */}
            <div className="bg-white rounded-3xl p-8 border border-gold-light/30 shadow-sm">
              <h3 className="font-serif text-2xl font-bold text-[#2D2A26] mb-1">Gratis</h3>
              <p className="text-[#9B9590] text-sm mb-6">Para siempre</p>
              <div className="text-4xl font-bold text-[#2D2A26] mb-6">$0<span className="text-lg text-[#9B9590] font-normal">/mes</span></div>
              <ul className="space-y-3 mb-8">
                {["Afirmación diaria", "1 meditación por día", "Seguimiento de ánimo", "Acceso a la comunidad", "Reto de 21 Días de Gratitud"].map(f => (
                  <li key={f} className="flex items-start gap-2 text-sm text-[#5C5650]">
                    <Check size={16} className="text-sage mt-0.5 shrink-0" /> {f}
                  </li>
                ))}
              </ul>
              <a href="/daily" className="block text-center py-3 rounded-2xl border-2 border-gold/30 text-gold-dark font-bold hover:bg-gold/5 transition-all no-underline">
                Comenzar Gratis
              </a>
            </div>

            {/* Premium */}
            <div className="bg-white rounded-3xl p-8 border-2 border-gold shadow-lg shadow-gold/15 relative">
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-gradient-to-r from-gold to-sunrise text-white text-xs font-bold px-4 py-1 rounded-full">
                Más Popular
              </div>
              <h3 className="font-serif text-2xl font-bold text-[#2D2A26] mb-1">Premium</h3>
              <p className="text-[#9B9590] text-sm mb-6">Acceso completo</p>
              <div className="text-4xl font-bold text-[#2D2A26] mb-1">$9.99<span className="text-lg text-[#9B9590] font-normal">/mes</span></div>
              <p className="text-xs text-sage-dark font-semibold mb-6">o $79.99/año (ahorra 33%)</p>
              <ul className="space-y-3 mb-8">
                {["Todo lo gratuito", "Biblioteca completa de meditaciones", "Todos los retos de 21 días", "Micro-lecciones diarias", "Sesiones en vivo mensuales", "Diario de reflexión", "Estadísticas de progreso", "Sin anuncios"].map(f => (
                  <li key={f} className="flex items-start gap-2 text-sm text-[#5C5650]">
                    <Check size={16} className="text-gold mt-0.5 shrink-0" /> {f}
                  </li>
                ))}
              </ul>
              <button className="w-full py-3 rounded-2xl bg-gradient-to-r from-gold to-sunrise text-white font-bold shadow-md shadow-gold/20 hover:shadow-lg transition-all hover:scale-[1.02]">
                Comenzar Premium
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* ── Email Capture ── */}
      <section className="py-16">
        <div className="max-w-2xl mx-auto px-4 text-center">
          <Sun size={40} className="text-gold mx-auto mb-4" />
          <h2 className="font-serif text-3xl font-bold mb-3 text-[#2D2A26]">Únete al Portal de la Alegría</h2>
          <p className="text-[#9B9590] mb-8">Recibe la afirmación del día y contenido exclusivo en tu correo. Sin spam, solo alegría.</p>
          {subscribed ? (
            <div className="bg-sage-light rounded-2xl p-6 border border-sage/30">
              <p className="text-sage-dark font-bold text-lg">🎉 ¡Bienvenido/a al Portal!</p>
              <p className="text-sage-dark/70 text-sm mt-1">Revisa tu correo para confirmar tu suscripción.</p>
            </div>
          ) : (
            <form onSubmit={handleSubscribe} className="flex flex-col sm:flex-row gap-3 max-w-md mx-auto">
              <input type="email" value={email} onChange={e => setEmail(e.target.value)}
                placeholder="tu@correo.com" required
                className="flex-1 px-5 py-3.5 rounded-2xl border border-gold-light bg-white text-[#2D2A26] placeholder:text-[#ccc] focus:outline-none focus:border-gold focus:ring-2 focus:ring-gold/20 text-sm" />
              <button type="submit"
                className="px-6 py-3.5 rounded-2xl bg-gradient-to-r from-gold to-sunrise text-white font-bold shadow-md shadow-gold/20 hover:shadow-lg transition-all hover:scale-[1.02] whitespace-nowrap">
                Suscribirme
              </button>
            </form>
          )}
        </div>
      </section>

      <Footer />
    </div>
  );
}
