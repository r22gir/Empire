'use client';
/**
 * ArtifactActions — approval workflow panel for artifacts.
 * Buttons reflect allowed_actions and local state (no backend persistence).
 */

import React from 'react';
import { Check, X, MessageSquare, Copy, ExternalLink } from 'lucide-react';
import { MaxArtifact, ArtifactMode } from '../../../lib/types';

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
  const isApproved = displayMode === 'approved';
  const isRejected = displayMode === 'rejected';
  const isChanges = displayMode === 'changes_requested';
  const isPending = displayMode === 'approval_required';

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

      {/* Note: local review state only */}
      {(isApproved || isRejected || isChanges) && (
        <div style={{ fontSize: 10, color: '#64748b', fontStyle: 'italic' }}>
          Local review state — not persisted to backend. Refresh to reset.
        </div>
      )}

      {/* Action buttons */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {isPending && artifact.allowed_actions.includes('approve') && (
          <button
            onClick={() => onApprove(artifact.id)}
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
            onClick={() => onReject(artifact.id)}
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
            onClick={() => onRequestChanges(artifact.id)}
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
      </div>

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