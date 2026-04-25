'use client';

import { useEffect, useState } from 'react';
import type { CSSProperties } from 'react';
import { API } from '../lib/api';

type ReviewerUser = {
  email: string;
  display_name: string;
  role: 'viewer' | 'reviewer' | 'admin';
};

type ReviewJobSummary = {
  job_id: string;
  state: string;
  display_state?: string;
  file_name?: string;
  chunks_total: number;
  chunks_complete: number;
  updated_at?: string;
};

type ReviewChunk = {
  chunk_id: string;
  sequence: number;
  start_time: number;
  end_time: number;
  raw_transcript?: string | null;
  review_status: string;
  processing_status?: string;
  confidence?: number | null;
};

type ReviewJob = ReviewJobSummary & {
  chunks: ReviewChunk[];
  audit_trail?: Array<Record<string, unknown>>;
  truth_summary?: string;
};

const TOKEN_KEY = 'tf_review_token';

export default function TranscriptForgeReviewPortal() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<ReviewerUser | null>(null);
  const [jobs, setJobs] = useState<ReviewJobSummary[]>([]);
  const [job, setJob] = useState<ReviewJob | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);

  const authHeaders = (currentToken = token) => ({
    'Content-Type': 'application/json',
    ...(currentToken ? { Authorization: `Bearer ${currentToken}` } : {}),
  });

  const apiFetch = async <T,>(path: string, options: RequestInit = {}): Promise<T> => {
    const res = await fetch(`${API}${path}`, {
      ...options,
      headers: { ...authHeaders(), ...(options.headers || {}) },
      credentials: 'include',
      cache: 'no-store',
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || `API ${res.status}`);
    return data as T;
  };

  const loadJobs = async () => {
    const data = await apiFetch<{ jobs: ReviewJobSummary[]; user: ReviewerUser }>('/transcriptforge/reviewer/jobs');
    setJobs(data.jobs || []);
    setUser(data.user);
  };

  const loadJob = async (jobId: string) => {
    const data = await apiFetch<ReviewJob>(`/transcriptforge/reviewer/jobs/${jobId}`);
    setJob(data);
  };

  useEffect(() => {
    fetch(`${API}/transcriptforge/reviewer/status`, { cache: 'no-store' })
      .then(r => r.json())
      .then(setStatus)
      .catch(() => setStatus(null));

    const saved = typeof window !== 'undefined' ? localStorage.getItem(TOKEN_KEY) : null;
    if (!saved) return;
    setToken(saved);
    fetch(`${API}/transcriptforge/reviewer/me`, {
      headers: { Authorization: `Bearer ${saved}` },
      credentials: 'include',
      cache: 'no-store',
    })
      .then(r => {
        if (!r.ok) throw new Error('session expired');
        return r.json();
      })
      .then(data => {
        setUser(data.user);
        return fetch(`${API}/transcriptforge/reviewer/jobs`, {
          headers: { Authorization: `Bearer ${saved}` },
          credentials: 'include',
          cache: 'no-store',
        });
      })
      .then(r => r.json())
      .then(data => setJobs(data.jobs || []))
      .catch(() => {
        localStorage.removeItem(TOKEN_KEY);
        setToken(null);
      });
  }, []);

  const login = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API}/transcriptforge/reviewer/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Login failed');
      localStorage.setItem(TOKEN_KEY, data.token);
      setToken(data.token);
      setUser(data.user);
      const jobsRes = await fetch(`${API}/transcriptforge/reviewer/jobs`, {
        headers: { Authorization: `Bearer ${data.token}` },
        credentials: 'include',
        cache: 'no-store',
      });
      const jobsData = await jobsRes.json();
      setJobs(jobsData.jobs || []);
    } catch (err: any) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    await fetch(`${API}/transcriptforge/reviewer/logout`, {
      method: 'POST',
      headers: authHeaders(),
      credentials: 'include',
    }).catch(() => {});
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
    setJobs([]);
    setJob(null);
  };

  const reviewChunk = async (chunkId: string, reviewStatus: 'good' | 'needs_review') => {
    if (!job) return;
    await apiFetch(`/transcriptforge/reviewer/jobs/${job.job_id}/chunks/${chunkId}/review`, {
      method: 'POST',
      body: JSON.stringify({ status: reviewStatus }),
    });
    await loadJob(job.job_id);
    await loadJobs();
  };

  const readBack = (text: string) => {
    if (!('speechSynthesis' in window)) {
      setError('Transcript readback is not available in this browser.');
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.95;
    window.speechSynthesis.speak(utterance);
  };

  return (
    <main style={styles.page}>
      <section style={styles.shell}>
        <aside style={styles.aside}>
          <div style={styles.kicker}>TranscriptForge external review</div>
          <h1 style={styles.title}>Secure chunk review without Command Center access.</h1>
          <p style={styles.copy}>
            Login is required. Reviewers only see assigned transcript jobs. Original audio is the source of truth; transcript readback is a reviewer aid only.
          </p>
          <div style={styles.statusBox}>
            <strong>Portal status</strong>
            <span>Login required: {String(status?.login_required ?? true)}</span>
            <span>Accounts configured: {String(status?.accounts_configured ?? false)}</span>
            <span>Anonymous transcript access: false</span>
          </div>
        </aside>

        <section style={styles.panel}>
          {!token || !user ? (
            <div style={styles.card}>
              <h2 style={styles.cardTitle}>Reviewer login</h2>
              <input style={styles.input} value={email} onChange={e => setEmail(e.target.value)} placeholder="email" />
              <input style={styles.input} value={password} onChange={e => setPassword(e.target.value)} placeholder="password" type="password" />
              <button style={styles.primaryButton} onClick={login} disabled={loading}>
                {loading ? 'Signing in...' : 'Sign in'}
              </button>
              {error && <div style={styles.error}>{error}</div>}
            </div>
          ) : (
            <div style={styles.grid}>
              <div style={styles.card}>
                <div style={styles.rowBetween}>
                  <div>
                    <div style={styles.kicker}>Signed in</div>
                    <h2 style={styles.cardTitle}>{user.display_name}</h2>
                    <p style={styles.muted}>{user.role}</p>
                  </div>
                  <button style={styles.secondaryButton} onClick={logout}>Logout</button>
                </div>
                <button style={styles.secondaryButton} onClick={loadJobs}>Refresh assigned jobs</button>
                <div style={styles.jobList}>
                  {jobs.length === 0 && <p style={styles.muted}>No jobs assigned.</p>}
                  {jobs.map(item => (
                    <button key={item.job_id} style={styles.jobButton} onClick={() => loadJob(item.job_id)}>
                      <span style={styles.mono}>{item.job_id}</span>
                      <span>{item.file_name || 'Unnamed audio'}</span>
                      <span style={styles.muted}>{item.display_state || item.state} - {item.chunks_complete}/{item.chunks_total}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div style={styles.card}>
                {!job ? (
                  <p style={styles.muted}>Select an assigned job to review chunks.</p>
                ) : (
                  <>
                    <div style={styles.rowBetween}>
                      <div>
                        <div style={styles.kicker}>Active job</div>
                        <h2 style={styles.cardTitle}>{job.job_id}</h2>
                        <p style={styles.muted}>{job.file_name} - {job.display_state || job.state}</p>
                      </div>
                      <button style={styles.secondaryButton} onClick={() => loadJob(job.job_id)}>Refresh</button>
                    </div>
                    {job.truth_summary && <div style={styles.notice}>{job.truth_summary}</div>}
                    <div style={styles.chunkList}>
                      {job.chunks.map(chunk => (
                        <div key={chunk.chunk_id} style={styles.chunkCard}>
                          <div style={styles.rowBetween}>
                            <strong>{chunk.chunk_id}</strong>
                            <span style={styles.muted}>{chunk.processing_status || 'pending'} - {chunk.review_status}</span>
                          </div>
                          <audio
                            controls
                            preload="none"
                            src={`${API}/transcriptforge/reviewer/jobs/${job.job_id}/chunks/${chunk.chunk_id}/audio#t=${chunk.start_time},${chunk.end_time}`}
                            style={{ width: '100%', marginTop: 10 }}
                          />
                          <p style={styles.sourceNote}>Original audio vs transcript is primary verification. TTS readback is a reviewer aid only.</p>
                          <pre style={styles.transcript}>{chunk.raw_transcript || 'Awaiting transcription...'}</pre>
                          {chunk.raw_transcript && (
                            <div style={styles.actions}>
                              <button style={styles.goodButton} onClick={() => reviewChunk(chunk.chunk_id, 'good')}>Good</button>
                              <button style={styles.warnButton} onClick={() => reviewChunk(chunk.chunk_id, 'needs_review')}>Needs Review</button>
                              <button style={styles.secondaryButton} onClick={() => readBack(chunk.raw_transcript || '')}>Transcript Readback</button>
                              <button style={styles.secondaryButton} onClick={() => window.speechSynthesis?.cancel()}>Stop Readback</button>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>
            </div>
          )}
        </section>
      </section>
    </main>
  );
}

const styles: Record<string, CSSProperties> = {
  page: { minHeight: '100vh', background: '#f2efe5', color: '#161616', fontFamily: 'Georgia, Cambria, serif' },
  shell: { minHeight: '100vh', display: 'grid', gridTemplateColumns: '340px minmax(0, 1fr)' },
  aside: { background: '#18221c', color: '#f7f3e8', padding: 30, display: 'flex', flexDirection: 'column', gap: 20 },
  kicker: { fontSize: 11, textTransform: 'uppercase', letterSpacing: 1.4, color: '#b6d7a8', fontWeight: 800 },
  title: { fontSize: 34, lineHeight: 1.05, margin: 0 },
  copy: { fontSize: 15, lineHeight: 1.6, color: '#d9e2d4' },
  statusBox: { marginTop: 'auto', border: '1px solid #425440', borderRadius: 10, padding: 14, display: 'grid', gap: 8, fontSize: 13 },
  panel: { padding: 28 },
  grid: { display: 'grid', gridTemplateColumns: 'minmax(260px, 360px) minmax(0, 1fr)', gap: 18 },
  card: { background: '#fffdf7', border: '1px solid #ddd3bc', borderRadius: 14, padding: 20, boxShadow: '0 18px 45px rgba(45, 38, 20, 0.08)' },
  cardTitle: { margin: '4px 0 10px', fontSize: 22 },
  input: { display: 'block', width: '100%', padding: '12px 13px', marginBottom: 10, border: '1px solid #c9bea7', borderRadius: 8, background: '#fff', fontSize: 15 },
  primaryButton: { padding: '11px 16px', border: 0, borderRadius: 8, background: '#1f5f3b', color: '#fff', fontWeight: 800, cursor: 'pointer' },
  secondaryButton: { padding: '9px 12px', border: '1px solid #c9bea7', borderRadius: 8, background: '#fff8e8', color: '#1f2b20', fontWeight: 700, cursor: 'pointer' },
  goodButton: { padding: '9px 12px', border: 0, borderRadius: 8, background: '#dff3df', color: '#14532d', fontWeight: 800, cursor: 'pointer' },
  warnButton: { padding: '9px 12px', border: 0, borderRadius: 8, background: '#fdecc8', color: '#8a4b0f', fontWeight: 800, cursor: 'pointer' },
  error: { marginTop: 12, color: '#991b1b', background: '#fee2e2', padding: 10, borderRadius: 8 },
  muted: { color: '#6c6659', fontSize: 13, margin: 0 },
  mono: { fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', fontSize: 12 },
  rowBetween: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 },
  jobList: { display: 'grid', gap: 10, marginTop: 16 },
  jobButton: { display: 'grid', gap: 4, textAlign: 'left', border: '1px solid #e2d8c0', borderRadius: 10, background: '#fffaf0', padding: 12, cursor: 'pointer' },
  notice: { margin: '12px 0', padding: 12, borderRadius: 10, background: '#e8f1ff', color: '#1e3a8a', fontSize: 13 },
  chunkList: { display: 'grid', gap: 14, marginTop: 16 },
  chunkCard: { border: '1px solid #e2d8c0', borderRadius: 12, padding: 14, background: '#fffaf0' },
  transcript: { whiteSpace: 'pre-wrap', maxHeight: 220, overflow: 'auto', background: '#f6f1e5', borderRadius: 8, padding: 12, fontSize: 13, lineHeight: 1.55 },
  sourceNote: { fontSize: 12, color: '#766e5f', margin: '8px 0' },
  actions: { display: 'flex', gap: 8, flexWrap: 'wrap' },
};
