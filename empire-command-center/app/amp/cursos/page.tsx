'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { getAmpToken, ampFetch } from '../../lib/amp-auth';
import AmpNav from '../../components/amp/AmpNav';
import {
  BookOpen, Clock, Star, ChevronRight, Lock, Flame, Search,
} from 'lucide-react';

const PILLAR_COLORS: Record<string, string> = {
  mentalidad: '#D4A030',
  bienestar: '#7CB98B',
  liderazgo: '#9B8EC4',
};

export default function CursosPage() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [courses, setCourses] = useState<any[]>([]);
  const [progress, setProgress] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    if (!getAmpToken()) { router.push('/amp/login'); return; }
    Promise.all([
      ampFetch('/me'),
      ampFetch('/courses'),
      ampFetch('/progress'),
    ]).then(([u, c, p]) => {
      setUser(u);
      setCourses(c);
      setProgress(p);
      setLoading(false);
    }).catch(() => router.push('/amp/login'));
  }, [router]);

  const getCoursePct = (courseId: string, lessonCount: number) => {
    const done = progress.filter((p: any) => p.course_id === courseId).length;
    return lessonCount > 0 ? Math.round((done / lessonCount) * 100) : 0;
  };

  const filtered = courses.filter(c =>
    !search || c.title?.toLowerCase().includes(search.toLowerCase()) ||
    c.pillar?.toLowerCase().includes(search.toLowerCase())
  );

  if (loading) return (
    <div style={{ minHeight: '100vh', background: '#FFF9F0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <Flame size={32} color="#D4A030" style={{ animation: 'pulse 1.5s infinite' }} />
    </div>
  );

  return (
    <div style={{ minHeight: '100vh', background: '#FFF9F0' }}>
      <AmpNav user={user} />
      <div style={{ maxWidth: 640, margin: '0 auto', padding: '20px 16px 60px' }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#2D2A26', marginBottom: 4 }}>Cursos</h1>
        <p style={{ fontSize: 13, color: '#9B9590', marginBottom: 16 }}>Programas paso a paso para tu crecimiento personal</p>

        {/* Search */}
        <div style={{ position: 'relative', marginBottom: 20 }}>
          <Search size={16} style={{ position: 'absolute', left: 14, top: 12, color: '#9B9590' }} />
          <input
            value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Buscar cursos..."
            style={{ width: '100%', padding: '10px 14px 10px 38px', borderRadius: 12, border: '1px solid #F5EDE0', background: '#fff', fontSize: 13, outline: 'none', boxSizing: 'border-box' }}
          />
        </div>

        {/* Course Cards */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {filtered.map(course => {
            const pct = getCoursePct(course.id, course.lesson_count || 0);
            const color = PILLAR_COLORS[course.pillar] || '#D4A030';
            return (
              <div
                key={course.id}
                onClick={() => router.push(`/amp/cursos/${course.id}`)}
                style={{
                  background: '#fff', borderRadius: 16, padding: 20, border: '1px solid #F5EDE0',
                  cursor: 'pointer', transition: 'border-color 0.2s',
                }}
                onMouseEnter={e => (e.currentTarget.style.borderColor = color)}
                onMouseLeave={e => (e.currentTarget.style.borderColor = '#F5EDE0')}
              >
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
                  <div style={{
                    width: 52, height: 52, borderRadius: 14, background: color + '20',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                  }}>
                    <BookOpen size={24} color={color} />
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                      <span style={{
                        fontSize: 9, fontWeight: 700, padding: '2px 8px', borderRadius: 4,
                        background: color + '20', color,
                      }}>
                        {course.pillar?.charAt(0).toUpperCase() + course.pillar?.slice(1)}
                      </span>
                      {course.premium ? (
                        <span style={{ fontSize: 9, fontWeight: 700, padding: '2px 6px', borderRadius: 4, background: '#FEF3C7', color: '#D97706' }}>
                          <Star size={8} style={{ verticalAlign: 'middle', marginRight: 2 }} />Premium
                        </span>
                      ) : null}
                    </div>
                    <div style={{ fontSize: 15, fontWeight: 700, color: '#2D2A26', marginBottom: 4 }}>{course.title}</div>
                    <p style={{ fontSize: 12, color: '#9B9590', margin: 0, lineHeight: 1.5 }}>{course.description}</p>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 10, fontSize: 11, color: '#9B9590' }}>
                      <span><Clock size={11} style={{ verticalAlign: 'middle', marginRight: 3 }} />{course.duration_days} dias</span>
                      <span><BookOpen size={11} style={{ verticalAlign: 'middle', marginRight: 3 }} />{course.lesson_count} lecciones</span>
                    </div>
                  </div>
                  <ChevronRight size={18} color="#9B9590" style={{ marginTop: 16, flexShrink: 0 }} />
                </div>

                {/* Progress bar */}
                {pct > 0 && (
                  <div style={{ marginTop: 14 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, fontWeight: 600, marginBottom: 4 }}>
                      <span style={{ color }}>Progreso</span>
                      <span style={{ color: '#9B9590' }}>{pct}%</span>
                    </div>
                    <div style={{ height: 6, borderRadius: 3, background: '#F5EDE0' }}>
                      <div style={{ height: 6, borderRadius: 3, background: color, width: `${pct}%`, transition: 'width 0.3s' }} />
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {filtered.length === 0 && (
          <div style={{ textAlign: 'center', padding: 40, color: '#9B9590' }}>
            <BookOpen size={32} style={{ marginBottom: 8, opacity: 0.4 }} />
            <p style={{ fontSize: 14 }}>No se encontraron cursos</p>
          </div>
        )}
      </div>
    </div>
  );
}
