'use client';
/**
 * ArtifactCard — inline card rendered below a chat message bubble.
 * Shows artifact type, title, mode badge, safety badge, and action buttons.
 */

import React from 'react';
import { FileText, Code, Layout, Component, Eye, Copy, Download, Check, X, MessageSquare } from 'lucide-react';
import { MaxArtifact, ArtifactMode } from '../../../lib/types';

interface ArtifactCardProps {
  artifact: MaxArtifact;
  displayMode?: ArtifactMode;
  onOpenViewer: (artifact: MaxArtifact) => void;
  onApprove?: (id: string) => void;
  onReject?: (id: string) => void;
  onRequestChanges?: (id: string) => void;
}

const TYPE_CONFIG = {
  plain_text: { color: '#6b7280', label: 'Text', Icon: FileText },
  markdown_report: { color: '#3b82f6', label: 'Report', Icon: FileText },
  html_artifact: { color: '#a855f7', label: 'HTML', Icon: Layout },
  react_component_proposal: { color: '#10b981', label: 'Component', Icon: Component },
} as const;

const MODE_COLORS: Record<ArtifactMode, string> = {
  review_only: '#6b7280',
  approval_required: '#f59e0b',
  approved: '#10b981',
  rejected: '#ef4444',
  changes_requested: '#3b82f6',
};

const MODE_LABELS: Record<ArtifactMode, string> = {
  review_only: 'Review',
  approval_required: 'Approval Required',
  approved: 'Approved',
  rejected: 'Rejected',
  changes_requested: 'Changes Requested',
};

export function ArtifactCard({ artifact, displayMode, onOpenViewer, onApprove, onReject, onRequestChanges }: ArtifactCardProps) {
  const config = TYPE_CONFIG[artifact.artifact_type] || TYPE_CONFIG.plain_text;
  const Icon = config.Icon;
  const effectiveMode = displayMode || artifact.mode;
  const isApproval = artifact.requires_approval || effectiveMode === 'approval_required';

  return (
    <div style={{
      marginTop: '8px',
      borderLeft: `3px solid ${config.color}`,
      background: 'rgba(15,23,42,0.8)',
      backdropFilter: 'blur(12px)',
      border: '1px solid rgba(255,255,255,0.08)',
      borderRadius: '8px',
      padding: '12px 14px',
      display: 'flex',
      flexDirection: 'column',
      gap: 10,
    }}>
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Icon size={14} color={config.color} />
        <span style={{ fontSize: 10, fontWeight: 700, color: config.color, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          {config.label}
        </span>
        <span style={{
          fontSize: 9, fontWeight: 700, padding: '1px 6px', borderRadius: 3,
          background: `${MODE_COLORS[effectiveMode]}22`, color: MODE_COLORS[effectiveMode],
        }}>
          {MODE_LABELS[effectiveMode]}
        </span>
        {artifact.safety.sandboxed && (
          <span style={{
            fontSize: 9, fontWeight: 600, padding: '1px 6px', borderRadius: 3,
            background: 'rgba(16,185,129,0.15)', color: '#10b981',
          }}>
            sandboxed
          </span>
        )}
        {artifact.safety.scripts_allowed === false && (
          <span style={{
            fontSize: 9, fontWeight: 600, padding: '1px 6px', borderRadius: 3,
            background: 'rgba(239,68,68,0.15)', color: '#ef4444',
          }}>
            no scripts
          </span>
        )}
        <span style={{ marginLeft: 'auto', fontSize: 11, color: '#94a3b8' }}>
          {artifact.source}
        </span>
      </div>

      {/* Title */}
      <div style={{ fontSize: 13, fontWeight: 700, color: '#f1f5f9', lineHeight: 1.3 }}>
        {artifact.title}
      </div>

      {/* Description */}
      {artifact.description && (
        <div style={{ fontSize: 11, color: '#94a3b8', lineHeight: 1.5 }}>
          {artifact.description}
        </div>
      )}

      {/* Content preview */}
      <div style={{
        fontSize: 11, color: '#64748b', lineHeight: 1.6,
        overflow: 'hidden', maxHeight: 60,
        textOverflow: 'ellipsis', whiteSpace: 'pre-wrap',
        fontFamily: 'var(--font-mono, monospace)',
      }}>
        {artifact.content.slice(0, 200)}
        {artifact.content.length > 200 && '…'}
      </div>

      {/* Actions row */}
      <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
        <button
          onClick={() => onOpenViewer(artifact)}
          style={{
            display: 'flex', alignItems: 'center', gap: 4,
            padding: '4px 10px', borderRadius: 6,
            border: '1px solid rgba(255,255,255,0.12)',
            background: 'rgba(99,102,241,0.15)', color: '#818cf8',
            cursor: 'pointer', fontSize: 11, fontWeight: 600,
          }}
        >
          <Eye size={11} /> Preview
        </button>

        {artifact.allowed_actions.includes('export_html') && (
          <button
            onClick={() => {
              const { cleaned } = (window as any).__artifact_sanitize
                ? (window as any).__artifact_sanitize(artifact.content)
                : { cleaned: artifact.content };
              const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>${artifact.title}</title></head><body>${cleaned}</body></html>`;
              const blob = new Blob([html], { type: 'text/html' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url; a.download = `artifact-${artifact.id}.html`; a.click();
              URL.revokeObjectURL(url);
            }}
            style={{
              display: 'flex', alignItems: 'center', gap: 4,
              padding: '4px 10px', borderRadius: 6,
              border: '1px solid rgba(255,255,255,0.08)',
              background: 'rgba(255,255,255,0.04)', color: '#94a3b8',
              cursor: 'pointer', fontSize: 11, fontWeight: 500,
            }}
          >
            <Download size={11} /> Export
          </button>
        )}

        {artifact.allowed_actions.includes('copy_source') && (
          <button
            onClick={() => navigator.clipboard.writeText(artifact.content)}
            style={{
              display: 'flex', alignItems: 'center', gap: 4,
              padding: '4px 10px', borderRadius: 6,
              border: '1px solid rgba(255,255,255,0.08)',
              background: 'rgba(255,255,255,0.04)', color: '#94a3b8',
              cursor: 'pointer', fontSize: 11, fontWeight: 500,
            }}
          >
            <Copy size={11} /> Copy
          </button>
        )}

        {/* Approval actions */}
        {isApproval && (
          <>
            {effectiveMode === 'approval_required' && onApprove && (
              <button
                onClick={() => onApprove(artifact.id)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 4,
                  padding: '4px 10px', borderRadius: 6,
                  border: 'none',
                  background: '#10b981', color: '#fff',
                  cursor: 'pointer', fontSize: 11, fontWeight: 700,
                }}
              >
                <Check size={11} /> Approve
              </button>
            )}
            {effectiveMode === 'approval_required' && onReject && (
              <button
                onClick={() => onReject(artifact.id)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 4,
                  padding: '4px 10px', borderRadius: 6,
                  border: '1px solid rgba(239,68,68,0.4)',
                  background: 'rgba(239,68,68,0.1)', color: '#ef4444',
                  cursor: 'pointer', fontSize: 11, fontWeight: 600,
                }}
              >
                <X size={11} /> Reject
              </button>
            )}
            {effectiveMode === 'approval_required' && onRequestChanges && (
              <button
                onClick={() => onRequestChanges(artifact.id)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 4,
                  padding: '4px 10px', borderRadius: 6,
                  border: '1px solid rgba(59,130,246,0.4)',
                  background: 'rgba(59,130,246,0.1)', color: '#3b82f6',
                  cursor: 'pointer', fontSize: 11, fontWeight: 600,
                }}
              >
                <MessageSquare size={11} /> Changes
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}