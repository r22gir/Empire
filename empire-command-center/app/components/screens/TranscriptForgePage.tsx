'use client';
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { API } from '../../lib/api';
import {
  FileAudio, Upload, List, Eye, CheckCircle, XCircle, AlertTriangle,
  Loader2, ChevronRight, ChevronDown, Clock, User, Download,
  Copy, Check, X, Pause, Play, MessageSquare, Shield, ArrowLeft,
  RefreshCw, Zap, BookOpen, Edit3
} from 'lucide-react';
import { ProofreadingProvider } from '../../hooks/useTranscriptForgeProofreading';
import TranscriptProofreadingPanel from './TranscriptProofreadingPanel';
import TranscriptExportPanel from './TranscriptExportPanel';

// ============ TYPES ============

interface ChunkInfo {
  chunk_id: string;
  job_id: string;
  sequence: number;
  start_time: number;
  end_time: number;
  raw_transcript: string | null;
  verified_transcript: string | null;
  confidence: number | null;
  mismatch_flags: string[];
  review_status: string;
  reviewer: string | null;
  reviewer_timestamp: string | null;
  processing_status?: string;
  raw_transcript_path?: string | null;
  verified_transcript_path?: string | null;
}

interface QCSummary {
  chunks_total: number;
  chunks_complete: number;
  chunks_failed: number;
  low_confidence_segments: number;
  unreviewed_low_confidence: number;
  mismatch_count: number;
  reviewer_corrections_count: number;
  overall_confidence: number | null;
}

interface TranscriptJob {
  job_id: string;
  state: string;
  source_mode: string;
  uploader: string;
  created_at: string;
  updated_at: string;
  file_name: string;
  file_size: number;
  duration_sec: number | null;
  chunks_total: number;
  chunks_complete: number;
  chunks_failed: number;
  overall_confidence: number | null;
  raw_transcript_path: string | null;
  verified_transcript_path: string | null;
  approved_transcript_path: string | null;
  critical_field_flags: string[];
  boundary_coherence_flags?: Array<Record<string, unknown>>;
  qc_summary: QCSummary | null;
  chunks: ChunkInfo[];
  audit_trail: AuditEntry[];
  display_state?: string;
  truth_summary?: string;
}

interface AuditEntry {
  event: string;
  timestamp: string;
  actor?: string;
  chunk_id?: string;
  status?: string;
  notes?: string;
  corrections_applied?: number;
  flags?: string[];
}

interface ApprovalAction {
  action: 'approve' | 'reject' | 'correct_and_approve';
  reviewer: string;
  notes?: string;
  chunk_corrections?: Record<string, string>;
}

type SourceMode = 'deposition' | 'court_hearing' | 'conference' | 'general_intake' | 'web_chat';

const SOURCE_MODE_LABELS: Record<SourceMode, string> = {
  deposition: 'Deposition',
  court_hearing: 'Court Hearing',
  conference: 'Conference',
  general_intake: 'General Transcript Intake',
  web_chat: 'Web Chat (Future-Ready)',
};

const STATE_COLORS: Record<string, { bg: string; color: string; label: string }> = {
  uploaded: { bg: '#e0e7ff', color: '#3730a3', label: 'Uploaded' },
  chunking: { bg: '#fef3c7', color: '#92400e', label: 'Chunking' },
  first_chunk_processing: { bg: '#fef3c7', color: '#92400e', label: 'Processing Chunk 1' },
  first_chunk_ready: { bg: '#dbeafe', color: '#1e40af', label: 'Paused awaiting review of first chunk' },
  paused_awaiting_review: { bg: '#dbeafe', color: '#1e40af', label: 'Paused awaiting review of first chunk' },
  processing_remaining_chunks: { bg: '#dbeafe', color: '#1e40af', label: 'Processing' },
  verification_running: { bg: '#f3e8ff', color: '#6b21a8', label: 'Verifying' },
  needs_review: { bg: '#fef9c3', color: '#854d0e', label: 'Needs Review' },
  approved: { bg: '#dcfce7', color: '#166534', label: 'Approved' },
  corrected_and_approved: { bg: '#dcfce7', color: '#14532d', label: 'Corrected & Approved' },
  rejected: { bg: '#fee2e2', color: '#991b1b', label: 'Rejected' },
};

// ============ COMPONENT ============

export default function TranscriptForgePage() {
  const [jobs, setJobs] = useState<TranscriptJob[]>([]);
  const [selectedJob, setSelectedJob] = useState<TranscriptJob | null>(null);
  const [activeTab, setActiveTab] = useState<'jobs' | 'detail' | 'review'>('jobs');
  const [activeDetailTab, setActiveDetailTab] = useState<'chunks' | 'transcript' | 'proofread' | 'export'>('chunks');
  const [showProofreading, setShowProofreading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingJob, setLoadingJob] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [jobsError, setJobsError] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState<string | null>(null);
  const [selectedMode, setSelectedMode] = useState<SourceMode>('deposition');
  const [expandedChunks, setExpandedChunks] = useState<Set<string>>(new Set());
  const [copiedJobId, setCopiedJobId] = useState<string | null>(null);
  const [approvalNotes, setApprovalNotes] = useState('');
  const [reviewerName, setReviewerName] = useState('founder');
  const [showApproveModal, setShowApproveModal] = useState(false);
  const [transcriptText, setTranscriptText] = useState<string | null>(null);
  const [transcriptKind, setTranscriptKind] = useState<'raw' | 'verified' | 'approved'>('approved');
  const [jobIdInput, setJobIdInput] = useState('');

  // Load jobs on mount
  useEffect(() => {
    loadJobs();
  }, []);

  const loadJobs = async () => {
    setLoading(true);
    setJobsError(null);
    try {
      const res = await fetch(`${API}/transcriptforge/jobs`);
      if (!res.ok) throw new Error(`Failed to load jobs: ${res.status}`);
      const data = await res.json();
      setJobs(data.jobs || []);
    } catch (e: any) {
      setJobsError(e.message || 'Failed to load jobs');
    } finally {
      setLoading(false);
    }
  };

  const loadJob = async (jobId: string) => {
    setLoadingJob(true);
    setError(null);
    setTranscriptText(null);
    try {
      const res = await fetch(`${API}/transcriptforge/jobs/${jobId}`);
      if (!res.ok) throw new Error(`Failed to load job: ${res.status}`);
      const data = await res.json();
      setSelectedJob(data);
      setActiveTab('detail');
    } catch (e: any) {
      setError(e.message || 'Failed to load job');
    } finally {
      setLoadingJob(false);
    }
  };

  const uploadAndCreateJob = async (file: File) => {
    setError(null);
    setUploadProgress('Creating job...');

    try {
      // 1. Create job
      const createRes = await fetch(`${API}/transcriptforge/jobs?source_mode=${selectedMode}&uploader=${reviewerName}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!createRes.ok) throw new Error(`Failed to create job: ${createRes.status}`);
      const { job_id } = await createRes.json();

      setUploadProgress('Uploading audio file...');

      // 2. Upload audio
      const form = new FormData();
      form.append('file', file);
      const uploadRes = await fetch(`${API}/transcriptforge/jobs/${job_id}/upload`, {
        method: 'PUT',
        body: form,
      });
      if (!uploadRes.ok) throw new Error(`Failed to upload audio: ${uploadRes.status}`);
      const uploadData = await uploadRes.json();

      setUploadProgress(`Uploaded. ${uploadData.chunks_total} chunks discovered. Chunk 1 processing started...`);

      // 3. Poll for chunk 1 completion
      let attempts = 0;
      while (attempts < 60) {  // 60 * 2s = 120s timeout
        await new Promise(r => setTimeout(r, 2000));
        const statusRes = await fetch(`${API}/transcriptforge/jobs/${job_id}`);
        const status = await statusRes.json();

        if (status.state === 'first_chunk_ready' || status.state === 'processing_remaining_chunks' || status.chunks_complete >= 1) {
          setSelectedJob(status);
          setActiveTab('detail');
          setUploadProgress(null);
          await loadJobs();
          return;
        }
        attempts++;
        setUploadProgress(`Processing chunk 1... (${status.chunks_complete || 0}/1, state: ${status.display_state || status.state})`);
      }

      setUploadProgress('Processing started. Check job list for updates.');
      await loadJobs();
    } catch (e: any) {
      setError(e.message || 'Upload failed');
      setUploadProgress(null);
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    uploadAndCreateJob(file);
  };

  const reviewChunk = async (jobId: string, chunkId: string, status: 'good' | 'needs_review' | 'edited') => {
    try {
      const res = await fetch(`${API}/transcriptforge/jobs/${jobId}/chunks/${chunkId}/review?status=${status}&reviewer=${reviewerName}`, {
        method: 'POST',
      });
      if (res.ok) {
        // Reload job to get updated state
        await loadJob(jobId);
      }
    } catch (e) {
      console.error('Review failed:', e);
    }
  };

  const continueRemainingChunks = async (jobId: string) => {
    try {
      const res = await fetch(`${API}/transcriptforge/jobs/${jobId}/continue?reviewer=${encodeURIComponent(reviewerName)}`, {
        method: 'POST',
      });
      const data = await res.json();
      if (!res.ok) {
        alert(data.detail || 'Continue failed');
        return;
      }
      await loadJob(jobId);
      await loadJobs();
    } catch (e) {
      console.error('Continue failed:', e);
    }
  };

  const readTranscriptText = (text: string) => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      alert('Transcript readback is not available in this browser.');
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.95;
    utterance.pitch = 1;
    window.speechSynthesis.speak(utterance);
  };

  const stopTranscriptReadback = () => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
  };

  const submitApproval = async (action: 'approve' | 'reject' | 'correct_and_approve') => {
    if (!selectedJob) return;

    const corrections: Record<string, string> = {};
    if (action === 'correct_and_approve') {
      selectedJob.chunks.forEach(c => {
        if (c.review_status === 'edited' && c.verified_transcript) {
          corrections[c.chunk_id] = c.verified_transcript;
        }
      });
    }

    const payload: ApprovalAction = {
      action,
      reviewer: reviewerName,
      notes: approvalNotes || undefined,
      chunk_corrections: action === 'correct_and_approve' ? corrections : undefined,
    };

    try {
      const res = await fetch(`${API}/transcriptforge/jobs/${selectedJob.job_id}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const result = await res.json();

      if (!res.ok) {
        // Blocked by critical fields or unreviewed low-confidence segments
        if (result.flags) {
          alert(`Cannot approve — unresolved issues:\n${result.flags.join('\n')}`);
        } else {
          alert(`Approval failed: ${result.detail}`);
        }
        return;
      }

      setShowApproveModal(false);
      setApprovalNotes('');
      await loadJob(selectedJob.job_id);
      await loadJobs();
    } catch (e) {
      console.error('Approval failed:', e);
    }
  };

  const loadTranscript = async (jobId: string, kind: 'raw' | 'verified' | 'approved') => {
    try {
      const res = await fetch(`${API}/transcriptforge/jobs/${jobId}/transcript/${kind}`);
      if (res.ok) {
        const data = await res.json();
        setTranscriptText(data.text);
        setTranscriptKind(kind);
      } else {
        const err = await res.json();
        alert(`Cannot load ${kind} transcript: ${err.detail}`);
      }
    } catch (e) {
      console.error('Failed to load transcript:', e);
    }
  };

  const stopJob = async (jobId: string) => {
    try {
      const res = await fetch(`${API}/transcriptforge/jobs/${jobId}/stop`, { method: 'POST' });
      if (res.ok) {
        await loadJob(jobId);
        await loadJobs();
      }
    } catch (e) {
      console.error('Stop failed:', e);
    }
  };

  const toggleChunk = (chunkId: string) => {
    setExpandedChunks(prev => {
      const next = new Set(prev);
      if (next.has(chunkId)) next.delete(chunkId);
      else next.add(chunkId);
      return next;
    });
  };

  const copyToClipboard = async (text: string, jobId: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedJobId(jobId);
      setTimeout(() => setCopiedJobId(null), 2000);
    } catch {}
  };

  const StateBadge = ({ state }: { state: string }) => {
    const s = STATE_COLORS[state] || STATE_COLORS.uploaded;
    return (
      <span style={{ background: s.bg, color: s.color, padding: '3px 10px', borderRadius: 999, fontSize: 11, fontWeight: 600 }}>
        {s.label}
      </span>
    );
  };

  const fmtTime = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  // ===== JOBS LIST VIEW =====
  const renderJobsList = () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Upload Section */}
      <div className="empire-card" style={{ padding: 24 }}>
        <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Upload size={16} /> New Transcription Job
        </h3>

        <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 16 }}>
          <label style={{ fontSize: 13, color: '#6b7280' }}>Source Mode:</label>
          <select
            value={selectedMode}
            onChange={e => setSelectedMode(e.target.value as SourceMode)}
            style={{ padding: '6px 12px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 13 }}
          >
            {Object.entries(SOURCE_MODE_LABELS).map(([k, v]) => (
              <option key={k} value={k}>{v}{k === 'web_chat' ? ' ⚠️' : ''}</option>
            ))}
          </select>

          <label style={{ fontSize: 13, color: '#6b7280' }}>Reviewer:</label>
          <input
            type="text"
            value={reviewerName}
            onChange={e => setReviewerName(e.target.value)}
            placeholder="Your name"
            style={{ padding: '6px 12px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 13, width: 140 }}
          />
        </div>

        <label
          style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '12px 20px', background: '#2563eb', color: 'white', borderRadius: 8, cursor: 'pointer', fontSize: 14, fontWeight: 600 }}
        >
          <FileAudio size={16} />
          Select Audio File
          <input type="file" accept="audio/*,.mp3,.wav,.m4a,.ogg,.flac,.webm" onChange={handleFileUpload} style={{ display: 'none' }} />
        </label>

        {uploadProgress && (
          <div style={{ marginTop: 12, padding: '10px 14px', background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 6, fontSize: 13, color: '#1e40af', display: 'flex', alignItems: 'center', gap: 8 }}>
            <Loader2 size={14} className="animate-spin" />
            {uploadProgress}
          </div>
        )}

        {error && (
          <div style={{ marginTop: 12, padding: '10px 14px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 6, fontSize: 13, color: '#dc2626' }}>
            <AlertTriangle size={14} style={{ display: 'inline', marginRight: 6 }} />
            {error}
          </div>
        )}

        {selectedMode === 'web_chat' && (
          <div style={{ marginTop: 10, padding: '8px 12px', background: '#fef9c3', border: '1px solid #fde047', borderRadius: 6, fontSize: 12, color: '#854d0e' }}>
            ⚠️ Web Chat mode is future-ready. Full integration not yet active in this pass.
          </div>
        )}
      </div>

      {/* Jobs Table */}
      <div className="empire-card" style={{ padding: 0 }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid #f3f4f6', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ fontSize: 15, fontWeight: 700 }}>Transcript Jobs</h3>
          <button onClick={loadJobs} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px', fontSize: 12, color: '#6b7280', background: 'none', border: 'none', cursor: 'pointer' }}>
            <RefreshCw size={13} /> Refresh
          </button>
        </div>

        {loading && <div style={{ padding: 40, textAlign: 'center', color: '#6b7280' }}><Loader2 size={20} className="animate-spin" style={{ margin: '0 auto' }} /></div>}
        {jobsError && <div style={{ padding: 20, color: '#dc2626', fontSize: 13 }}>{jobsError}</div>}

        {!loading && jobs.length === 0 && !jobsError && (
          <div style={{ padding: 40, textAlign: 'center', color: '#9ca3af', fontSize: 14 }}>
            No transcription jobs yet. Upload an audio file above to start.
          </div>
        )}

        {jobs.length > 0 && (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#f9fafb' }}>
                <th style={{ padding: '10px 16px', textAlign: 'left', fontSize: 11, fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Job ID</th>
                <th style={{ padding: '10px 16px', textAlign: 'left', fontSize: 11, fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Mode</th>
                <th style={{ padding: '10px 16px', textAlign: 'left', fontSize: 11, fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em' }}>State</th>
                <th style={{ padding: '10px 16px', textAlign: 'left', fontSize: 11, fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em' }}>File</th>
                <th style={{ padding: '10px 16px', textAlign: 'left', fontSize: 11, fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Progress</th>
                <th style={{ padding: '10px 16px', textAlign: 'left', fontSize: 11, fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map(job => (
                <tr key={job.job_id} style={{ borderBottom: '1px solid #f3f4f6' }} className="hover:bg-gray-50">
                  <td style={{ padding: '12px 16px', fontSize: 12, fontFamily: 'monospace' }}>
                    <span style={{ cursor: 'pointer', color: '#2563eb' }} onClick={() => loadJob(job.job_id)}>
                      {job.job_id}
                    </span>
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: 13 }}>
                    {SOURCE_MODE_LABELS[job.source_mode as SourceMode] || job.source_mode}
                  </td>
                  <td style={{ padding: '12px 16px' }}><StateBadge state={job.display_state || job.state} /></td>
                  <td style={{ padding: '12px 16px', fontSize: 12, color: '#6b7280' }}>{job.file_name || '—'}</td>
                  <td style={{ padding: '12px 16px', fontSize: 12 }}>
                    {job.chunks_total > 0 ? (
                      <span>{job.chunks_complete}/{job.chunks_total} chunks</span>
                    ) : job.file_name ? 'Preparing / detecting chunks' : 'No file uploaded'}
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    <button
                      onClick={() => loadJob(job.job_id)}
                      style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '5px 10px', fontSize: 12, color: '#2563eb', background: '#eff6ff', border: 'none', borderRadius: 6, cursor: 'pointer' }}
                    >
                      <Eye size={12} /> View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Direct Job Lookup */}
      <div className="empire-card" style={{ padding: 20 }}>
        <h4 style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Load Job by ID</h4>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            type="text"
            value={jobIdInput}
            onChange={e => setJobIdInput(e.target.value)}
            placeholder="tf_xxxxxxxxxxxx"
            style={{ flex: 1, padding: '8px 12px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 13 }}
          />
          <button
            onClick={() => jobIdInput && loadJob(jobIdInput)}
            style={{ padding: '8px 16px', background: '#6b7280', color: 'white', border: 'none', borderRadius: 6, fontSize: 13, cursor: 'pointer' }}
          >
            Load
          </button>
        </div>
      </div>
    </div>
  );

  // ===== JOB DETAIL VIEW =====
  const renderJobDetail = () => {
    if (!selectedJob) return null;

    const state = selectedJob.state as keyof typeof STATE_COLORS;
    const displayState = selectedJob.display_state || selectedJob.state;
    const isApprovable = ['verification_running', 'needs_review'].includes(state);
    const isStoppable = ['first_chunk_processing', 'first_chunk_ready', 'processing_remaining_chunks'].includes(state);
    const firstChunkReviewed = selectedJob.chunks[0]?.raw_transcript && selectedJob.chunks[0]?.review_status !== 'pending';

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16 }}>
          <button
            onClick={() => { setSelectedJob(null); setActiveTab('jobs'); setTranscriptText(null); }}
            style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', background: '#f3f4f6', border: 'none', borderRadius: 6, fontSize: 13, cursor: 'pointer', color: '#374151' }}
          >
            <ArrowLeft size={14} /> Back to Jobs
          </button>

          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
              <h2 style={{ fontSize: 18, fontWeight: 700 }}>Transcript Job</h2>
              <span style={{ fontFamily: 'monospace', fontSize: 13, color: '#6b7280' }}>{selectedJob.job_id}</span>
              <StateBadge state={displayState} />
            </div>
            <div style={{ fontSize: 12, color: '#6b7280', display: 'flex', gap: 16 }}>
              <span>{SOURCE_MODE_LABELS[selectedJob.source_mode as SourceMode] || selectedJob.source_mode}</span>
              <span>|</span>
              <span>{selectedJob.file_name || '—'}</span>
              <span>|</span>
              <span>Uploader: {selectedJob.uploader}</span>
              <span>|</span>
              <span>Reviewer: {reviewerName}</span>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 8 }}>
            {isStoppable && (
              <button
                onClick={() => stopJob(selectedJob.job_id)}
                style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', background: '#fef3c7', border: '1px solid #fde047', borderRadius: 6, fontSize: 13, cursor: 'pointer', color: '#92400e' }}
              >
                <Pause size={14} /> Stop / Pause
              </button>
            )}
            {selectedJob.state === 'first_chunk_ready' && (
              <button
                onClick={() => continueRemainingChunks(selectedJob.job_id)}
                disabled={!firstChunkReviewed}
                title={firstChunkReviewed ? 'Queue remaining chunks' : 'Review chunk_000 before continuing'}
                style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', background: firstChunkReviewed ? '#2563eb' : '#e5e7eb', border: 'none', borderRadius: 6, fontSize: 13, cursor: firstChunkReviewed ? 'pointer' : 'not-allowed', color: firstChunkReviewed ? 'white' : '#6b7280' }}
              >
                <Play size={14} /> Continue Remaining Chunks
              </button>
            )}
          </div>
        </div>

        {/* Error Banner */}
        {error && (
          <div style={{ padding: '12px 16px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8, color: '#dc2626', fontSize: 13, display: 'flex', alignItems: 'center', gap: 8 }}>
            <AlertTriangle size={14} /> {error}
          </div>
        )}

        {/* Detail sub-tabs */}
        <div style={{ display: 'flex', gap: 4, borderBottom: '1px solid #e5e7eb', paddingBottom: 0 }}>
          {[
            { key: 'chunks', label: 'Chunks', icon: <MessageSquare size={13} /> },
            { key: 'transcript', label: 'Transcript', icon: <BookOpen size={13} /> },
            { key: 'proofread', label: 'Proofread', icon: <Edit3 size={13} /> },
            { key: 'export', label: 'Export', icon: <Download size={13} /> },
          ].map(tab => (
            <button
              key={tab.key}
              onClick={() => {
                setActiveDetailTab(tab.key as typeof activeDetailTab);
                if (tab.key !== 'proofread') setShowProofreading(false);
                if (tab.key === 'proofread') setShowProofreading(true);
              }}
              aria-selected={activeDetailTab === tab.key}
              style={{
                display: 'flex', alignItems: 'center', gap: 5,
                padding: '8px 14px',
                background: activeDetailTab === tab.key ? '#7c3aed' : 'transparent',
                color: activeDetailTab === tab.key ? '#fff' : '#6b7280',
                border: 'none',
                borderBottom: activeDetailTab === tab.key ? '2px solid #7c3aed' : '2px solid transparent',
                borderRadius: '6px 6px 0 0',
                fontSize: 13, fontWeight: 600, cursor: 'pointer',
                marginBottom: -1,
              }}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>

        {selectedJob.state === 'first_chunk_ready' && (
          <div style={{ padding: '12px 16px', background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 8, color: '#1e40af', fontSize: 13 }}>
            <strong>Paused awaiting review of first chunk.</strong> Remaining chunks are intentionally pending. Verify the original audio against the transcript, mark chunk 1 Good or Needs Review, then continue only when ready.
          </div>
        )}

        {/* QC Summary */}
        {selectedJob.qc_summary && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
            {[
              { label: 'Chunks', value: `${selectedJob.qc_summary.chunks_complete}/${selectedJob.qc_summary.chunks_total}` },
              { label: 'Failed', value: selectedJob.qc_summary.chunks_failed },
              { label: 'Low Confidence', value: selectedJob.qc_summary.low_confidence_segments },
              { label: 'Corrections', value: selectedJob.qc_summary.reviewer_corrections_count },
            ].map(({ label, value }) => (
              <div key={label} className="empire-card" style={{ padding: 16, textAlign: 'center' }}>
                <div style={{ fontSize: 22, fontWeight: 700 }}>{value}</div>
                <div style={{ fontSize: 11, color: '#6b7280', marginTop: 2 }}>{label}</div>
              </div>
            ))}
          </div>
        )}

        {/* Critical Field Flags */}
        {selectedJob.critical_field_flags && selectedJob.critical_field_flags.length > 0 && (
          <div style={{ padding: '12px 16px', background: '#fef9c3', border: '1px solid #fde047', borderRadius: 8 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#92400e', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
              <AlertTriangle size={14} /> Critical Field Flags — Require Human Resolution
            </div>
            <ul style={{ fontSize: 12, color: '#92400e', margin: 0, paddingLeft: 20 }}>
              {selectedJob.critical_field_flags.map((f, i) => <li key={i}>{f}</li>)}
            </ul>
          </div>
        )}

        {selectedJob.boundary_coherence_flags && selectedJob.boundary_coherence_flags.length > 0 && (
          <div style={{ padding: '12px 16px', background: '#fff7ed', border: '1px solid #fed7aa', borderRadius: 8 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#9a3412', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
              <AlertTriangle size={14} /> Boundary Coherence Warnings
            </div>
            <ul style={{ fontSize: 12, color: '#9a3412', margin: 0, paddingLeft: 20 }}>
              {selectedJob.boundary_coherence_flags.map((f, i) => <li key={i}>{String(f.message || f.type || 'Verify chunk boundary')}</li>)}
            </ul>
          </div>
        )}

        {/* Tab content */}
        {activeDetailTab === 'chunks' && (
          <>
        {/* Chunk Review Section */}
        {['first_chunk_ready', 'processing_remaining_chunks', 'verification_running', 'needs_review'].includes(state) && (
          <div className="empire-card" style={{ padding: 20 }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
              <MessageSquare size={16} /> Chunk Review
            </h3>

            {selectedJob.chunks.length === 0 && (
              <div style={{ color: '#9ca3af', fontSize: 13 }}>No chunks available yet.</div>
            )}

            {selectedJob.chunks.map(chunk => {
              const isExpanded = expandedChunks.has(chunk.chunk_id);
              const hasIssues = chunk.mismatch_flags.length > 0;
              const confidence = chunk.confidence;
              const hasConfidence = confidence !== null && confidence !== undefined;
              const confidenceValue = confidence ?? 0;
              const lowConfidence = hasConfidence && confidenceValue < 0.7;

              return (
                <div key={chunk.chunk_id} style={{ marginBottom: 12, border: '1px solid #e5e7eb', borderRadius: 8, overflow: 'hidden' }}>
                  {/* Chunk Header */}
                  <div
                    onClick={() => toggleChunk(chunk.chunk_id)}
                    style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px', cursor: 'pointer', background: hasIssues ? '#fef9c3' : lowConfidence ? '#fef3c7' : '#f9fafb' }}
                  >
                    {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}

                    <span style={{ fontSize: 12, fontWeight: 600, fontFamily: 'monospace', minWidth: 80 }}>
                      {chunk.chunk_id}
                    </span>

                    <span style={{ fontSize: 12, color: '#6b7280' }}>
                      {fmtTime(chunk.start_time)} — {fmtTime(chunk.end_time)}
                    </span>

                    {hasConfidence && (
                      <span style={{
                        fontSize: 11, padding: '2px 8px', borderRadius: 999,
                        background: confidenceValue >= 0.8 ? '#dcfce7' : confidenceValue >= 0.5 ? '#fef3c7' : '#fee2e2',
                        color: confidenceValue >= 0.8 ? '#166534' : confidenceValue >= 0.5 ? '#92400e' : '#991b1b',
                      }}>
                        {(confidenceValue * 100).toFixed(0)}% conf.
                      </span>
                    )}

                    {hasIssues && (
                      <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 999, background: '#fee2e2', color: '#991b1b' }}>
                        {chunk.mismatch_flags.length} flags
                      </span>
                    )}

                    <span style={{
                      fontSize: 11, padding: '2px 8px', borderRadius: 999,
                      background: chunk.review_status === 'good' ? '#dcfce7' : chunk.review_status === 'edited' ? '#f3e8ff' : '#f3f4f6',
                      color: chunk.review_status === 'good' ? '#166534' : chunk.review_status === 'edited' ? '#6b21a8' : '#6b7280',
                    }}>
                      {chunk.review_status}
                    </span>

                    <span style={{
                      fontSize: 11, padding: '2px 8px', borderRadius: 999,
                      background: chunk.processing_status === 'transcribing' ? '#fef3c7' : chunk.processing_status === 'transcribed' ? '#dcfce7' : chunk.processing_status === 'failed' ? '#fee2e2' : '#f3f4f6',
                      color: chunk.processing_status === 'transcribing' ? '#92400e' : chunk.processing_status === 'transcribed' ? '#166534' : chunk.processing_status === 'failed' ? '#991b1b' : '#6b7280',
                    }}>
                      {chunk.processing_status || 'pending'}
                    </span>

                    {!chunk.raw_transcript && chunk.processing_status === 'transcribing' && (
                      <Loader2 size={12} className="animate-spin" style={{ color: '#92400e' }} />
                    )}
                  </div>

                  {/* Chunk Content */}
                  {isExpanded && (
                    <div style={{ padding: 16, borderTop: '1px solid #e5e7eb', background: 'white' }}>
                      <div style={{ marginBottom: 12, padding: '10px 12px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 6 }}>
                        <div style={{ fontSize: 12, fontWeight: 600, color: '#334155', marginBottom: 6 }}>
                          Original chunk audio — source of truth
                        </div>
                        <audio
                          controls
                          preload="none"
                          src={`${API}/transcriptforge/jobs/${selectedJob.job_id}/chunks/${chunk.chunk_id}/audio#t=${Math.max(0, chunk.start_time)},${chunk.end_time}`}
                          style={{ width: '100%' }}
                        />
                        <div style={{ fontSize: 11, color: '#64748b', marginTop: 6 }}>
                          Verify original audio against the transcript. TTS readback, if used, is only a reviewer aid.
                        </div>
                      </div>

                      {chunk.mismatch_flags.length > 0 && (
                        <div style={{ marginBottom: 12, padding: '8px 12px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 6 }}>
                          <div style={{ fontSize: 12, fontWeight: 600, color: '#dc2626', marginBottom: 4 }}>Flags / Issues:</div>
                          <ul style={{ fontSize: 12, color: '#991b1b', margin: 0, paddingLeft: 20 }}>
                            {chunk.mismatch_flags.map((f, i) => <li key={i}>{f}</li>)}
                          </ul>
                        </div>
                      )}

                      {chunk.raw_transcript ? (
                        <>
                          <div style={{ fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 6 }}>Transcript:</div>
                          <div style={{ fontSize: 13, lineHeight: 1.6, whiteSpace: 'pre-wrap', background: '#f9fafb', padding: 12, borderRadius: 6, maxHeight: 200, overflowY: 'auto' }}>
                            {chunk.raw_transcript}
                          </div>
                        </>
                      ) : (
                        <div style={{ color: '#9ca3af', fontSize: 13, fontStyle: 'italic' }}>
                          {chunk.review_status === 'pending' ? 'Awaiting transcription...' : 'No transcript available'}
                        </div>
                      )}

                      {/* Review Actions */}
                      {chunk.raw_transcript && ['first_chunk_ready', 'needs_review', 'verification_running', 'processing_remaining_chunks'].includes(state) && (
                        <div style={{ display: 'flex', gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
                          <button
                            onClick={() => reviewChunk(selectedJob.job_id, chunk.chunk_id, 'good')}
                            style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '6px 12px', background: '#dcfce7', border: 'none', borderRadius: 6, fontSize: 12, color: '#166534', cursor: 'pointer' }}
                          >
                            <Check size={12} /> Good
                          </button>
                          <button
                            onClick={() => reviewChunk(selectedJob.job_id, chunk.chunk_id, 'needs_review')}
                            style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '6px 12px', background: '#fef3c7', border: 'none', borderRadius: 6, fontSize: 12, color: '#92400e', cursor: 'pointer' }}
                          >
                            <AlertTriangle size={12} /> Needs Review
                          </button>
                          <button
                            onClick={() => readTranscriptText(chunk.raw_transcript || '')}
                            style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '6px 12px', background: '#eff6ff', border: 'none', borderRadius: 6, fontSize: 12, color: '#1e40af', cursor: 'pointer' }}
                            title="Transcript readback uses current displayed transcript text. Reviewer aid only."
                          >
                            <Play size={12} /> Transcript Readback
                          </button>
                          <button
                            onClick={stopTranscriptReadback}
                            style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '6px 12px', background: '#f3f4f6', border: 'none', borderRadius: 6, fontSize: 12, color: '#374151', cursor: 'pointer' }}
                          >
                            <Pause size={12} /> Stop Readback
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Transcript Viewer */}
        {['approved', 'corrected_and_approved', 'rejected', 'verification_running', 'needs_review'].includes(state) && (
          <div className="empire-card" style={{ padding: 20 }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
              <BookOpen size={16} /> Full Transcript
            </h3>

            <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
              {['approved', 'corrected_and_approved'].includes(state) && (
                <button onClick={() => loadTranscript(selectedJob.job_id, 'approved')} style={{ padding: '6px 12px', background: transcriptKind === 'approved' ? '#2563eb' : '#f3f4f6', color: transcriptKind === 'approved' ? 'white' : '#374151', border: 'none', borderRadius: 6, fontSize: 12, cursor: 'pointer' }}>
                  Approved
                </button>
              )}
              {['approved', 'corrected_and_approved', 'verification_running', 'needs_review'].includes(state) && (
                <button onClick={() => loadTranscript(selectedJob.job_id, 'verified')} style={{ padding: '6px 12px', background: transcriptKind === 'verified' ? '#2563eb' : '#f3f4f6', color: transcriptKind === 'verified' ? 'white' : '#374151', border: 'none', borderRadius: 6, fontSize: 12, cursor: 'pointer' }}>
                  Verified
                </button>
              )}
              {['approved', 'corrected_and_approved', 'verification_running', 'needs_review', 'rejected'].includes(state) && (
                <button onClick={() => loadTranscript(selectedJob.job_id, 'raw')} style={{ padding: '6px 12px', background: transcriptKind === 'raw' ? '#2563eb' : '#f3f4f6', color: transcriptKind === 'raw' ? 'white' : '#374151', border: 'none', borderRadius: 6, fontSize: 12, cursor: 'pointer' }}>
                  Raw
                </button>
              )}
            </div>

            {transcriptText ? (
              <div style={{ position: 'relative' }}>
                <pre style={{ fontSize: 13, lineHeight: 1.6, whiteSpace: 'pre-wrap', background: '#f9fafb', padding: 16, borderRadius: 6, maxHeight: 400, overflowY: 'auto', border: '1px solid #e5e7eb' }}>
                  {transcriptText}
                </pre>
                <button
                  onClick={() => copyToClipboard(transcriptText, selectedJob.job_id)}
                  style={{ position: 'absolute', top: 8, right: 8, display: 'flex', alignItems: 'center', gap: 4, padding: '5px 10px', background: 'white', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 11, cursor: 'pointer' }}
                >
                  {copiedJobId === selectedJob.job_id ? <Check size={11} /> : <Copy size={11} />}
                  {copiedJobId === selectedJob.job_id ? 'Copied' : 'Copy'}
                </button>
              </div>
            ) : (
              <div style={{ color: '#9ca3af', fontSize: 13, fontStyle: 'italic' }}>
                {state === 'approved' || state === 'corrected_and_approved' || state === 'corrected_and_approved'
                  ? 'No approved transcript available yet.'
                  : 'Load a transcript version above.'}
              </div>
            )}
          </div>
        )}

        {/* Audit Trail */}
        {selectedJob.audit_trail && selectedJob.audit_trail.length > 0 && (
          <div className="empire-card" style={{ padding: 20 }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Shield size={16} /> Audit Trail
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {selectedJob.audit_trail.map((entry, i) => (
                <div key={i} style={{ display: 'flex', gap: 12, fontSize: 12, padding: '8px 12px', background: '#f9fafb', borderRadius: 6 }}>
                  <span style={{ color: '#9ca3af', minWidth: 150 }}>{entry.timestamp}</span>
                  <span style={{ fontWeight: 600 }}>{entry.event}</span>
                  {entry.actor && <span style={{ color: '#6b7280' }}>by {entry.actor}</span>}
                  {entry.status && <span style={{ color: '#2563eb' }}>[{entry.status}]</span>}
                  {entry.notes && <span style={{ color: '#6b7280' }}>— {entry.notes}</span>}
                </div>
              ))}
            </div>
          </div>
        )}
          </>
        )}

        {/* Transcript tab (read-only view) */}
        {activeDetailTab === 'transcript' && (
          <>
        {/* Transcript Viewer */}
        {['approved', 'corrected_and_approved', 'rejected', 'verification_running', 'needs_review'].includes(state) && (
          <div className="empire-card" style={{ padding: 20 }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
              <BookOpen size={16} /> Full Transcript
            </h3>

            <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
              {['approved', 'corrected_and_approved'].includes(state) && (
                <button onClick={() => loadTranscript(selectedJob.job_id, 'approved')} style={{ padding: '6px 12px', background: transcriptKind === 'approved' ? '#2563eb' : '#f3f4f6', color: transcriptKind === 'approved' ? 'white' : '#374151', border: 'none', borderRadius: 6, fontSize: 12, cursor: 'pointer' }}>
                  Approved
                </button>
              )}
              {['approved', 'corrected_and_approved', 'verification_running', 'needs_review'].includes(state) && (
                <button onClick={() => loadTranscript(selectedJob.job_id, 'verified')} style={{ padding: '6px 12px', background: transcriptKind === 'verified' ? '#2563eb' : '#f3f4f6', color: transcriptKind === 'verified' ? 'white' : '#374151', border: 'none', borderRadius: 6, fontSize: 12, cursor: 'pointer' }}>
                  Verified
                </button>
              )}
              {['approved', 'corrected_and_approved', 'verification_running', 'needs_review', 'rejected'].includes(state) && (
                <button onClick={() => loadTranscript(selectedJob.job_id, 'raw')} style={{ padding: '6px 12px', background: transcriptKind === 'raw' ? '#2563eb' : '#f3f4f6', color: transcriptKind === 'raw' ? 'white' : '#374151', border: 'none', borderRadius: 6, fontSize: 12, cursor: 'pointer' }}>
                  Raw
                </button>
              )}
            </div>

            {transcriptText ? (
              <div style={{ position: 'relative' }}>
                <pre style={{ fontSize: 13, lineHeight: 1.6, whiteSpace: 'pre-wrap', background: '#f9fafb', padding: 16, borderRadius: 6, maxHeight: 400, overflowY: 'auto', border: '1px solid #e5e7eb' }}>
                  {transcriptText}
                </pre>
                <button
                  onClick={() => copyToClipboard(transcriptText, selectedJob.job_id)}
                  style={{ position: 'absolute', top: 8, right: 8, display: 'flex', alignItems: 'center', gap: 4, padding: '5px 10px', background: 'white', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 11, cursor: 'pointer' }}
                >
                  {copiedJobId === selectedJob.job_id ? <Check size={11} /> : <Copy size={11} />}
                  {copiedJobId === selectedJob.job_id ? 'Copied' : 'Copy'}
                </button>
              </div>
            ) : (
              <div style={{ color: '#9ca3af', fontSize: 13, fontStyle: 'italic' }}>
                {state === 'approved' || state === 'corrected_and_approved' || state === 'corrected_and_approved'
                  ? 'No approved transcript available yet.'
                  : 'Load a transcript version above.'}
              </div>
            )}
          </div>
        )}
          </>
        )}

        {/* Proofread tab */}
        {activeDetailTab === 'proofread' && (
          <div className="empire-card" style={{ padding: 20 }}>
            <TranscriptProofreadingPanel
              job={selectedJob}
              apiBase={API}
            />
          </div>
        )}

        {/* Export tab */}
        {activeDetailTab === 'export' && (
          <div className="empire-card" style={{ padding: 20 }}>
            <TranscriptExportPanel
              jobId={selectedJob.job_id}
              segments={[]}
              speakerLabelMode="manual"
            />
          </div>
        )}

        {/* Approval Actions */}
        {isApprovable && (
          <div className="empire-card" style={{ padding: 20 }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
              <CheckCircle size={16} /> Approval Gate
            </h3>
            <p style={{ fontSize: 13, color: '#6b7280', marginBottom: 16 }}>
              No transcript is final just because text exists. All conditions must be satisfied before approval.
              Auto-approval is never permitted.
            </p>

            <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
              <input
                type="text"
                value={reviewerName}
                onChange={e => setReviewerName(e.target.value)}
                placeholder="Reviewer name"
                style={{ padding: '8px 12px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 13, width: 160 }}
              />

              {['verification_running', 'needs_review'].includes(state) ? (
                <button
                  onClick={() => setShowApproveModal(true)}
                  style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px', background: '#16a34a', color: 'white', border: 'none', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: 'pointer' }}
                >
                  <CheckCircle size={14} /> Approve / Correct & Approve
                </button>
              ) : (
                <span style={{ fontSize: 12, color: '#9ca3af', fontStyle: 'italic' }}>
                  Cannot approve in current state: {state}
                </span>
              )}

              {['verification_running', 'needs_review'].includes(state) && (
                <button
                  onClick={() => submitApproval('reject')}
                  style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px', background: '#dc2626', color: 'white', border: 'none', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: 'pointer' }}
                >
                  <XCircle size={14} /> Reject
                </button>
              )}
            </div>

            {/* Notes */}
            <textarea
              value={approvalNotes}
              onChange={e => setApprovalNotes(e.target.value)}
              placeholder="Approval notes (optional but recommended for audit trail)..."
              style={{ marginTop: 12, width: '100%', padding: '10px 12px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 13, minHeight: 80, resize: 'vertical' }}
            />
          </div>
        )}

        {/* Final State Display */}
        {['approved', 'corrected_and_approved', 'rejected'].includes(state) && (
          <div style={{
            padding: 20, borderRadius: 8, textAlign: 'center',
            background: state === 'approved' || state === 'corrected_and_approved' ? '#dcfce7' : state === 'rejected' ? '#fee2e2' : '#f3e8ff',
            border: `2px solid ${state === 'approved' || state === 'corrected_and_approved' ? '#16a34a' : state === 'rejected' ? '#dc2626' : '#7c3aed'}`
          }}>
            <div style={{ fontSize: 18, fontWeight: 700, color: state === 'approved' || state === 'corrected_and_approved' ? '#166534' : state === 'rejected' ? '#991b1b' : '#6b21a8', marginBottom: 4 }}>
              {state === 'approved' ? 'APPROVED — Human Reviewed' : state === 'corrected_and_approved' ? 'CORRECTED & APPROVED' : 'REJECTED'}
            </div>
            <div style={{ fontSize: 13, color: '#6b7280' }}>
              {state === 'approved' ? 'Transcript has been human-reviewed and approved without edits.' :
               state === 'corrected_and_approved' ? 'Transcript was edited during review, then approved.' :
               'Transcript has been explicitly rejected as unusable.'}
            </div>
          </div>
        )}
      </div>
    );
  };

  // ===== APPROVE MODAL =====
  const ApproveModal = () => {
    const [action, setAction] = useState<'approve' | 'correct_and_approve'>('approve');

    return (
      <div style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex',
        alignItems: 'center', justifyContent: 'center', zIndex: 1000
      }}>
        <div style={{ background: 'white', borderRadius: 12, padding: 24, width: 480, maxWidth: '90vw' }}>
          <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 16 }}>Submit Approval Decision</h3>

          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 13, color: '#374151', marginBottom: 8, display: 'block' }}>
              Approval Type:
            </label>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={() => setAction('approve')}
                style={{ padding: '10px 16px', background: action === 'approve' ? '#16a34a' : '#f3f4f6', color: action === 'approve' ? 'white' : '#374151', border: 'none', borderRadius: 6, fontSize: 13, cursor: 'pointer' }}
              >
                <CheckCircle size={14} style={{ marginRight: 6 }} />
                Approve (No Edits)
              </button>
              <button
                onClick={() => setAction('correct_and_approve')}
                style={{ padding: '10px 16px', background: action === 'correct_and_approve' ? '#7c3aed' : '#f3f4f6', color: action === 'correct_and_approve' ? 'white' : '#374151', border: 'none', borderRadius: 6, fontSize: 13, cursor: 'pointer' }}
              >
                <Zap size={14} style={{ marginRight: 6 }} />
                Correct & Approve
              </button>
            </div>
            <div style={{ marginTop: 8, fontSize: 12, color: '#6b7280' }}>
              {action === 'correct_and_approve' ? 'Applied corrections from edited chunks will be included.' : 'All chunk edits must be marked before selecting this option.'}
            </div>
          </div>

          <div style={{ marginBottom: 20 }}>
            <label style={{ fontSize: 13, color: '#374151', marginBottom: 8, display: 'block' }}>Notes (recommended):</label>
            <textarea
              value={approvalNotes}
              onChange={e => setApprovalNotes(e.target.value)}
              placeholder="e.g., 'Approved after reviewing flagged segments. Names and dates verified.'"
              style={{ width: '100%', padding: '10px 12px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 13, minHeight: 80, resize: 'vertical' }}
            />
          </div>

          <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
            <button
              onClick={() => setShowApproveModal(false)}
              style={{ padding: '8px 16px', background: '#f3f4f6', border: 'none', borderRadius: 6, fontSize: 13, cursor: 'pointer' }}
            >
              Cancel
            </button>
            <button
              onClick={() => submitApproval(action)}
              style={{ padding: '8px 16px', background: action === 'approve' ? '#16a34a' : '#7c3aed', color: 'white', border: 'none', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: 'pointer' }}
            >
              Confirm {action === 'approve' ? 'Approval' : 'Correct & Approve'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <ProofreadingProvider>
    <div style={{ height: '100%', overflowY: 'auto', padding: '24px 28px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
        <div style={{ width: 40, height: 40, borderRadius: 10, background: '#7c3aed', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <FileAudio size={20} style={{ color: 'white' }} />
        </div>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700 }}>TranscriptForge</h1>
          <p style={{ fontSize: 12, color: '#6b7280' }}>
            Legal/High-Risk Transcription Pipeline — Chunked, Reviewable, Approval-Gated
          </p>
        </div>
        <div style={{ marginLeft: 'auto', fontSize: 11, color: '#9ca3af' }}>
          {activeTab === 'detail' ? `${selectedJob?.job_id || ''}` : `${jobs.length} job${jobs.length !== 1 ? 's' : ''}`}
        </div>
      </div>

      {showApproveModal && <ApproveModal />}

      {activeTab === 'jobs' && renderJobsList()}
      {activeTab === 'detail' && renderJobDetail()}
    </div>
    </ProofreadingProvider>
  );
}
