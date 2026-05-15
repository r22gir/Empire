'use client';
/**
 * ArtifactActions — approval workflow panel for artifacts.
 * Buttons reflect allowed_actions and local state (no backend persistence).
 */

import React from 'react';
import { Check, X, MessageSquare, Copy, ExternalLink, Save } from 'lucide-react';
import { MaxArtifact, ArtifactMode } from '../../../lib/types';
import { API } from '../../../lib/api';

const HERMES_ARTIFACT_STATE_KEY = 'v10_hermes_artifact_state_v1';

interface ArtifactActionsProps {
  artifact: MaxArtifact;
  displayMode: ArtifactMode;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  onRequestChanges: (id: string) => void;
  onCopySource: () => void;
  onOpenFullscreen?: () => void;
}

export function ArtifactActions({
  artifact,
  displayMode,
  onApprove,
  onReject,
  onRequestChanges,
  onCopySource,
  onOpenFullscreen,
}: ArtifactActionsProps) {
  const [persistState, setPersistState] = React.useState<
    { status: 'idle' } |
    { status: 'saving' } |
    { status: 'saved'; artifactId: string } |
    { status: 'error'; error: string }
  >({ status: 'idle' });
  const [persistedBackendStatus, setPersistedBackendStatus] = React.useState<{
    artifactId: string;
    approvalStatus: string;
    updatedAt?: string;
    approvalTimestamp?: string;
    isCurrent?: boolean;
    supersededBy?: string | null;
    approvalActorLabel?: string;
    approvalActorType?: string;
    approvalConfidence?: string;
  } | null>(null);

  const isApproved = displayMode === 'approved';
  const isRejected = displayMode === 'rejected';
  const isChanges = displayMode === 'changes_requested';
  const isPending = displayMode === 'approval_required';
  const inferredModule = React.useMemo(() => {
    const meta = (artifact.metadata || {}) as Record<string, unknown>;
    const module = meta.module;
    if (typeof module === 'string' && module.trim()) {
      return module;
    }
    return 'system';
  }, [artifact.metadata]);

  const persistedFromMetadata = React.useMemo(() => {
    const meta = (artifact.metadata || {}) as Record<string, unknown>;
    const id = meta.hermes_artifact_id;
    return typeof id === 'string' && id.trim() ? id.trim() : '';
  }, [artifact.metadata]);

  const readPersistedMap = React.useCallback((): Record<string, { artifactId: string; approvalStatus?: string; updatedAt?: string; approvalTimestamp?: string; isCurrent?: boolean; supersededBy?: string | null; approvalActorLabel?: string; approvalActorType?: string; approvalConfidence?: string }> => {
    if (typeof window === 'undefined') return {};
    try {
      const raw = window.localStorage.getItem(HERMES_ARTIFACT_STATE_KEY);
      if (!raw) return {};
      const parsed = JSON.parse(raw);
      return parsed && typeof parsed === 'object' ? parsed as Record<string, { artifactId: string; approvalStatus?: string; updatedAt?: string; approvalTimestamp?: string; isCurrent?: boolean; supersededBy?: string | null; approvalActorLabel?: string; approvalActorType?: string; approvalConfidence?: string }> : {};
    } catch {
      return {};
    }
  }, []);

  const writePersistedMap = React.useCallback((nextMap: Record<string, { artifactId: string; approvalStatus?: string; updatedAt?: string; approvalTimestamp?: string; isCurrent?: boolean; supersededBy?: string | null; approvalActorLabel?: string; approvalActorType?: string; approvalConfidence?: string }>) => {
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.setItem(HERMES_ARTIFACT_STATE_KEY, JSON.stringify(nextMap));
    } catch {
      // Non-fatal; UI still works without local cache.
    }
  }, []);

  const rememberPersistedState = React.useCallback((
    artifactId: string,
    approvalStatus?: string,
    updatedAt?: string,
    extra?: {
      approvalTimestamp?: string;
      isCurrent?: boolean;
      supersededBy?: string | null;
      approvalActorLabel?: string;
      approvalActorType?: string;
      approvalConfidence?: string;
    },
  ) => {
    const map = readPersistedMap();
    map[artifact.id] = {
      artifactId,
      approvalStatus,
      updatedAt,
      approvalTimestamp: extra?.approvalTimestamp,
      isCurrent: extra?.isCurrent,
      supersededBy: extra?.supersededBy,
      approvalActorLabel: extra?.approvalActorLabel,
      approvalActorType: extra?.approvalActorType,
      approvalConfidence: extra?.approvalConfidence,
    };
    writePersistedMap(map);
    setPersistedBackendStatus({
      artifactId,
      approvalStatus: approvalStatus || 'draft',
      updatedAt,
      approvalTimestamp: extra?.approvalTimestamp,
      isCurrent: extra?.isCurrent,
      supersededBy: extra?.supersededBy,
      approvalActorLabel: extra?.approvalActorLabel,
      approvalActorType: extra?.approvalActorType,
      approvalConfidence: extra?.approvalConfidence,
    });
  }, [artifact.id, readPersistedMap, writePersistedMap]);

  React.useEffect(() => {
    if (persistedFromMetadata) {
      setPersistedBackendStatus({
        artifactId: persistedFromMetadata,
        approvalStatus: 'draft',
      });
      return;
    }
    const map = readPersistedMap();
    const saved = map[artifact.id];
    if (saved?.artifactId) {
      setPersistedBackendStatus({
        artifactId: saved.artifactId,
        approvalStatus: saved.approvalStatus || 'draft',
        updatedAt: saved.updatedAt,
        approvalTimestamp: saved.approvalTimestamp,
        isCurrent: saved.isCurrent,
        supersededBy: saved.supersededBy ?? null,
        approvalActorLabel: saved.approvalActorLabel,
        approvalActorType: saved.approvalActorType,
        approvalConfidence: saved.approvalConfidence,
      });
    }
  }, [artifact.id, persistedFromMetadata, readPersistedMap]);

  React.useEffect(() => {
    async function fetchPersistedDetails(artifactId: string) {
      try {
        const response = await fetch(`${API}/hermes/artifacts/${encodeURIComponent(artifactId)}`);
        if (!response.ok) return;
        const data = await response.json();
        const metadata = data?.metadata || {};
        const history = Array.isArray(metadata.approval_history) ? metadata.approval_history : [];
        const last = history.length > 0 ? history[history.length - 1] : {};
        rememberPersistedState(
          artifactId,
          String(metadata.approval_status || persistedBackendStatus?.approvalStatus || 'draft'),
          String(metadata.updated_at || ''),
          {
            approvalTimestamp: String(metadata.approval_timestamp || last?.approval_timestamp || ''),
            isCurrent: Boolean(data?.is_current),
            supersededBy: metadata.superseded_by ? String(metadata.superseded_by) : null,
            approvalActorLabel: String(metadata.approval_actor_label || last?.approval_actor_label || ''),
            approvalActorType: String(metadata.approval_actor_type || last?.approval_actor_type || ''),
            approvalConfidence: String(metadata.approval_confidence || last?.approval_confidence || ''),
          },
        );
      } catch {
        // Keep existing local/persisted state even if detail fetch fails.
      }
    }

    if (persistedBackendStatus?.artifactId) {
      fetchPersistedDetails(persistedBackendStatus.artifactId);
    }
  }, [persistedBackendStatus?.artifactId, rememberPersistedState]);

  async function syncBackendStatus(nextStatus: 'approved' | 'rejected' | 'changes_requested') {
    if (!persistedBackendStatus?.artifactId) return;
    try {
      const response = await fetch(`${API}/hermes/artifacts/${encodeURIComponent(persistedBackendStatus.artifactId)}/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          approval_status: nextStatus,
          actor_type: 'founder',
          actor_label: 'Founder/Web MAX',
          actor_source: 'local_ui',
          approval_method: 'ui',
          approval_confidence: 'local_ui',
          actor_note: 'artifact_viewer_review_action',
        }),
      });
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `HTTP ${response.status}`);
      }
      const data = await response.json();
      rememberPersistedState(
        persistedBackendStatus.artifactId,
        String(data.approval_status || nextStatus),
        String(data.updated_at || ''),
        {
          approvalTimestamp: String(data.approval_timestamp || ''),
          isCurrent: Boolean(data.approval_status === 'approved' && !data.superseded_by),
          supersededBy: data.superseded_by ? String(data.superseded_by) : null,
          approvalActorLabel: String(data.approval_actor_label || ''),
          approvalActorType: String(data.approval_actor_type || ''),
          approvalConfidence: String(data.approval_confidence || ''),
        },
      );
    } catch (err) {
      setPersistState({
        status: 'error',
        error: `Backend status sync failed: ${err instanceof Error ? err.message : String(err)}`,
      });
    }
  }

  async function handleApprove() {
    onApprove(artifact.id);
    await syncBackendStatus('approved');
  }

  async function handleReject() {
    onReject(artifact.id);
    await syncBackendStatus('rejected');
  }

  async function handleRequestChanges() {
    onRequestChanges(artifact.id);
    await syncBackendStatus('changes_requested');
  }

  async function saveToHermesMemory() {
    if (persistState.status === 'saving') return;
    setPersistState({ status: 'saving' });
    try {
      const meta = (artifact.metadata || {}) as Record<string, unknown>;
      const provenance = (meta.provenance && typeof meta.provenance === 'object')
        ? meta.provenance as Record<string, unknown>
        : {};
      const response = await fetch(`${API}/hermes/artifacts/write`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: artifact.title,
          artifact_type: artifact.artifact_type,
          content: artifact.content,
          content_format: artifact.content_format,
          module: inferredModule,
          source_agent: artifact.source,
          approval_status: displayMode === 'approved' ? 'approved' : 'draft',
          tags: [artifact.artifact_type, inferredModule, artifact.source],
          retrieval_keywords: [artifact.title, inferredModule],
          provenance: {
            ...provenance,
            source_agent: artifact.source,
            artifact_view: 'v10_artifact_viewer',
          },
        }),
      });
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `HTTP ${response.status}`);
      }
      const data = await response.json();
      const savedId = String(data.artifact_id || '');
      setPersistState({ status: 'saved', artifactId: savedId });
      rememberPersistedState(savedId, String(data?.metadata?.approval_status || 'draft'), String(data?.metadata?.updated_at || ''));
    } catch (err) {
      setPersistState({ status: 'error', error: err instanceof Error ? err.message : String(err) });
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: '14px' }}>
      {/* Status banner */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '10px 14px',
        borderRadius: 8,
        background: isApproved ? 'rgba(16,185,129,0.15)'
          : isRejected ? 'rgba(239,68,68,0.15)'
          : isChanges ? 'rgba(59,130,246,0.15)'
          : 'rgba(245,158,11,0.15)',
        border: `1px solid ${
          isApproved ? 'rgba(16,185,129,0.3)'
          : isRejected ? 'rgba(239,68,68,0.3)'
          : isChanges ? 'rgba(59,130,246,0.3)'
          : 'rgba(245,158,11,0.3)'
        }`,
        fontSize: 12, fontWeight: 700,
        color: isApproved ? '#10b981' : isRejected ? '#ef4444' : isChanges ? '#3b82f6' : '#f59e0b',
      }}>
        {isApproved && <><Check size={14} /> Approved — artifact accepted</>}
        {isRejected && <><X size={14} /> Rejected — artifact not accepted</>}
        {isChanges && <><MessageSquare size={14} /> Changes Requested — awaiting revision</>}
        {isPending && <><Check size={14} /> Pending Approval — review and approve or reject</>}
      </div>

      {/* Local vs persisted status */}
      {persistedBackendStatus ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 10, color: '#22c55e' }}>
              Persisted Hermes state
            </span>
            <span style={{ fontSize: 10, color: '#94a3b8' }}>
              id={persistedBackendStatus.artifactId}
            </span>
            <span style={{ fontSize: 10, color: '#f8fafc' }}>
              approval_status={persistedBackendStatus.approvalStatus}
            </span>
            <span style={{ fontSize: 10, color: persistedBackendStatus.isCurrent ? '#10b981' : '#f59e0b' }}>
              {persistedBackendStatus.isCurrent ? 'current' : 'not-current'}
            </span>
            {persistedBackendStatus.supersededBy && (
              <span style={{ fontSize: 10, color: '#f59e0b' }}>
                superseded_by={persistedBackendStatus.supersededBy}
              </span>
            )}
          </div>
          <div style={{ fontSize: 10, color: '#64748b' }}>
            {persistedBackendStatus.approvalActorLabel
              ? `approval_actor=${persistedBackendStatus.approvalActorLabel}`
              : persistedBackendStatus.approvalActorType
                ? `approval_actor_type=${persistedBackendStatus.approvalActorType}`
                : 'approval_actor=unknown'}
            {persistedBackendStatus.approvalConfidence ? `, confidence=${persistedBackendStatus.approvalConfidence}` : ''}
            {persistedBackendStatus.approvalTimestamp
              ? `, approval_timestamp=${persistedBackendStatus.approvalTimestamp}`
              : persistedBackendStatus.updatedAt
                ? `, updated_at=${persistedBackendStatus.updatedAt}`
                : ''}
          </div>
        </div>
      ) : (
        <div style={{ fontSize: 10, color: '#64748b', fontStyle: 'italic' }}>
          Local-only review state — persist to Hermes before backend approval state can be synced.
        </div>
      )}

      {/* Action buttons */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {isPending && artifact.allowed_actions.includes('approve') && (
          <button
            onClick={handleApprove}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '8px 16px', borderRadius: 8,
              border: 'none',
              background: '#10b981', color: '#fff',
              cursor: 'pointer', fontSize: 12, fontWeight: 700,
            }}
          >
            <Check size={13} /> Approve
          </button>
        )}

        {isPending && artifact.allowed_actions.includes('reject') && (
          <button
            onClick={handleReject}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '8px 16px', borderRadius: 8,
              border: '1px solid rgba(239,68,68,0.5)',
              background: 'rgba(239,68,68,0.1)', color: '#ef4444',
              cursor: 'pointer', fontSize: 12, fontWeight: 600,
            }}
          >
            <X size={13} /> Reject
          </button>
        )}

        {isPending && artifact.allowed_actions.includes('request_changes') && (
          <button
            onClick={handleRequestChanges}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '8px 16px', borderRadius: 8,
              border: '1px solid rgba(59,130,246,0.5)',
              background: 'rgba(59,130,246,0.1)', color: '#3b82f6',
              cursor: 'pointer', fontSize: 12, fontWeight: 600,
            }}
          >
            <MessageSquare size={13} /> Request Changes
          </button>
        )}
      </div>

      {/* Secondary actions */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {artifact.allowed_actions.includes('copy_source') && (
          <button
            onClick={onCopySource}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '6px 12px', borderRadius: 6,
              border: '1px solid rgba(255,255,255,0.1)',
              background: 'rgba(255,255,255,0.05)', color: '#94a3b8',
              cursor: 'pointer', fontSize: 11, fontWeight: 500,
            }}
          >
            <Copy size={12} /> Copy Source
          </button>
        )}

        {artifact.allowed_actions.includes('open_fullscreen') && onOpenFullscreen && (
          <button
            onClick={onOpenFullscreen}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '6px 12px', borderRadius: 6,
              border: '1px solid rgba(255,255,255,0.1)',
              background: 'rgba(255,255,255,0.05)', color: '#94a3b8',
              cursor: 'pointer', fontSize: 11, fontWeight: 500,
            }}
          >
            <ExternalLink size={12} /> Fullscreen
          </button>
        )}

        <button
          onClick={saveToHermesMemory}
          disabled={persistState.status === 'saving'}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '6px 12px', borderRadius: 6,
            border: '1px solid rgba(99,102,241,0.35)',
            background: 'rgba(99,102,241,0.12)', color: '#818cf8',
            cursor: persistState.status === 'saving' ? 'not-allowed' : 'pointer',
            fontSize: 11, fontWeight: 600, opacity: persistState.status === 'saving' ? 0.7 : 1,
          }}
        >
          <Save size={12} />
          {persistState.status === 'saving' ? 'Saving...' : 'Save to Hermes Memory'}
        </button>
      </div>

      {persistState.status === 'saved' && (
        <div style={{ fontSize: 10, color: '#22c55e' }}>
          Persisted to Hermes artifact layer: {persistState.artifactId || '(saved)'}
        </div>
      )}
      {persistState.status === 'error' && (
        <div style={{ fontSize: 10, color: '#ef4444' }}>
          Persist failed: {persistState.error}
        </div>
      )}

      {/* Safety info */}
      <div style={{
        marginTop: 4,
        padding: '8px 12px',
        background: 'rgba(15,23,42,0.6)',
        borderRadius: 6,
        fontSize: 10, color: '#64748b', lineHeight: 1.6,
      }}>
        <strong style={{ color: '#94a3b8' }}>Safety:</strong> scripts_allowed={artifact.safety.scripts_allowed ? 'true' : 'false'}, external_network={artifact.safety.external_network_allowed ? 'true' : 'false'}, sandboxed={artifact.safety.sandboxed}
      </div>
    </div>
  );
}
