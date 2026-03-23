'use client';
import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { getAmpToken, ampFetch } from '../../../lib/amp-auth';
import AmpNav from '../../../components/amp/AmpNav';
import {
  BookOpen, Clock, ChevronLeft, CheckCircle, Circle, Play,
  Flame, ChevronDown, ChevronUp, Star,
} from 'lucide-react';

const PILLAR_COLORS: Record<string, string> = {
  mentalidad: '#D4A030',
  bienestar: '#7CB98B',
  liderazgo: '#9B8EC4',
};

export default function CoursePlayerPage() {
  const router = useRouter();
  const params = useParams();
  const courseId = params.id as string;

  const [user, setUser] = useState<any>(null);
  const [course, setCourse] = useState<any>(null);
  const [progress, setProgress] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeLesson, setActiveLesson] = useState<any>(null);
  const [marking, setMarking] = useState(false);

  useEffect(() => {
    if (!getAmpToken()) { router.push('/amp/login'); return; }
    Promise.all([
      ampFetch('/me'),
      ampFetch(`/courses/${courseId}`),
      ampFetch('/progress'),
    ]).then(([u, c, p]) => {
      setUser(u);
      setCourse(c);
      setProgress(p);
      setLoading(false);
      // Auto-open first incomplete lesson
      const completedIds = new Set(p.filter((pr: any) => pr.course_id === courseId).map((pr: any) => pr.lesson_id));
      const firstIncomplete = c.lessons?.find((l: any) => !completedIds.has(l.id));
      if (firstIncomplete) setActiveLesson(firstIncomplete);
      else if (c.lessons?.length) setActiveLesson(c.lessons[0]);
    }).catch(() => router.push('/amp/login'));
  }, [router, courseId]);

  const completedIds = new Set(progress.filter(p => p.course_id === courseId).map(p => p.lesson_id));
  const pct = course?.lessons?.length
    ? Math.round((completedIds.size / course.lessons.length) * 100)
    : 0;
  const color = PILLAR_COLORS[course?.pillar] || '#D4A030';

  const markComplete = async (lessonId: string) => {
    setMarking(true);
    try {
      await ampFetch('/progress', {
        method: 'POST',
        body: JSON.stringify({ course_id: courseId, lesson_id: lessonId }),
      });
      setProgress(prev => [...prev, { course_id: courseId, lesson_id: lessonId }]);
      // Auto-advance to next lesson
      if (course?.lessons) {
        const idx = course.lessons.findIndex((l: any) => l.id === lessonId);
        const next = course.lessons[idx + 1];
        if (next) setTimeout(() => setActiveLesson(next), 500);
      }
    } catch (e) {
      console.error('Failed to mark complete:', e);
    }
    setMarking(false);
  };

  if (loading) return (
    <div style={{ minHeight: '100vh', background: '#FFF9F0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <Flame size={32} color="#D4A030" style={{ animation: 'pulse 1.5s infinite' }} />
    </div>
  );

  if (!course) return (
    <div style={{ minHeight: '100vh', background: '#FFF9F0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <p style={{ color: '#9B9590' }}>Curso no encontrado</p>
    </div>
  );

  return (
    <div style={{ minHeight: '100vh', background: '#FFF9F0' }}>
      <AmpNav user={user} />
      <div style={{ maxWidth: 640, margin: '0 auto', padding: '20px 16px 60px' }}>
        {/* Back + Header */}
        <button onClick={() => router.push('/amp/cursos')}
          style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontSize: 13, color: '#9B9590', marginBottom: 16, padding: 0 }}>
          <ChevronLeft size={16} /> Todos los cursos
        </button>

        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14, marginBottom: 16 }}>
          <div style={{
            width: 56, height: 56, borderRadius: 16, background: color + '20',
            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
          }}>
            <BookOpen size={26} color={color} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
              <span style={{ fontSize: 9, fontWeight: 700, padding: '2px 8px', borderRadius: 4, background: color + '20', color }}>
                {course.pillar?.charAt(0).toUpperCase() + course.pillar?.slice(1)}
              </span>
              {course.premium ? (
                <span style={{ fontSize: 9, fontWeight: 700, padding: '2px 6px', borderRadius: 4, background: '#FEF3C7', color: '#D97706' }}>
                  <Star size={8} style={{ verticalAlign: 'middle', marginRight: 2 }} />Premium
                </span>
              ) : null}
            </div>
            <h1 style={{ fontSize: 20, fontWeight: 700, color: '#2D2A26', margin: '0 0 4px' }}>{course.title}</h1>
            <p style={{ fontSize: 12, color: '#9B9590', margin: 0 }}>{course.description}</p>
          </div>
        </div>

        {/* Progress bar */}
        <div style={{ background: '#fff', borderRadius: 14, padding: 16, border: '1px solid #F5EDE0', marginBottom: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, fontWeight: 600, marginBottom: 6 }}>
            <span style={{ color: '#2D2A26' }}>Progreso del curso</span>
            <span style={{ color }}>{completedIds.size}/{course.lessons?.length || 0} lecciones ({pct}%)</span>
          </div>
          <div style={{ height: 8, borderRadius: 4, background: '#F5EDE0' }}>
            <div style={{ height: 8, borderRadius: 4, background: color, width: `${pct}%`, transition: 'width 0.3s' }} />
          </div>
          {pct === 100 && (
            <div style={{ textAlign: 'center', marginTop: 10, fontSize: 13, fontWeight: 700, color }}>
              Curso completado!
            </div>
          )}
        </div>

        {/* Lesson list + active lesson content */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {course.lessons?.map((lesson: any) => {
            const done = completedIds.has(lesson.id);
            const isActive = activeLesson?.id === lesson.id;
            return (
              <div key={lesson.id}>
                <div
                  onClick={() => setActiveLesson(isActive ? null : lesson)}
                  style={{
                    background: isActive ? color + '10' : '#fff',
                    borderRadius: isActive ? '14px 14px 0 0' : 14,
                    padding: '14px 16px',
                    border: `1px solid ${isActive ? color + '40' : '#F5EDE0'}`,
                    borderBottom: isActive ? 'none' : undefined,
                    cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 12,
                    transition: 'all 0.2s',
                  }}
                >
                  {done ? (
                    <CheckCircle size={20} color={color} />
                  ) : (
                    <Circle size={20} color="#D5D0C8" />
                  )}
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 10, color: '#9B9590', fontWeight: 600 }}>Dia {lesson.day_number}</div>
                    <div style={{ fontSize: 14, fontWeight: 600, color: '#2D2A26' }}>{lesson.title}</div>
                  </div>
                  {lesson.duration_seconds && (
                    <span style={{ fontSize: 10, color: '#9B9590' }}>
                      <Clock size={10} style={{ verticalAlign: 'middle', marginRight: 2 }} />
                      {Math.ceil(lesson.duration_seconds / 60)} min
                    </span>
                  )}
                  {isActive ? <ChevronUp size={16} color="#9B9590" /> : <ChevronDown size={16} color="#9B9590" />}
                </div>

                {/* Expanded lesson content */}
                {isActive && (
                  <div style={{
                    background: '#fff', borderRadius: '0 0 14px 14px',
                    padding: '20px 16px', border: `1px solid ${color + '40'}`, borderTop: 'none',
                  }}>
                    {lesson.description && (
                      <p style={{ fontSize: 12, color: '#9B9590', margin: '0 0 12px', fontStyle: 'italic' }}>{lesson.description}</p>
                    )}
                    <div style={{ fontSize: 14, color: '#2D2A26', lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
                      {lesson.content_text || 'Contenido de la leccion en desarrollo...'}
                    </div>

                    {lesson.audio_url && (
                      <div style={{ marginTop: 16, background: color + '10', borderRadius: 12, padding: 14, display: 'flex', alignItems: 'center', gap: 10 }}>
                        <Play size={18} color={color} />
                        <span style={{ fontSize: 12, fontWeight: 600, color }}>Escuchar audio de la leccion</span>
                      </div>
                    )}

                    {!done && (
                      <button
                        onClick={(e) => { e.stopPropagation(); markComplete(lesson.id); }}
                        disabled={marking}
                        style={{
                          marginTop: 16, width: '100%', background: color, color: '#fff', border: 'none',
                          borderRadius: 10, padding: '12px 20px', fontSize: 14, fontWeight: 700,
                          cursor: marking ? 'wait' : 'pointer', opacity: marking ? 0.6 : 1,
                        }}
                      >
                        <CheckCircle size={16} style={{ verticalAlign: 'middle', marginRight: 6 }} />
                        {marking ? 'Guardando...' : 'Marcar como completada'}
                      </button>
                    )}
                    {done && (
                      <div style={{ marginTop: 16, textAlign: 'center', fontSize: 13, fontWeight: 600, color }}>
                        <CheckCircle size={16} style={{ verticalAlign: 'middle', marginRight: 4 }} />
                        Leccion completada
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
