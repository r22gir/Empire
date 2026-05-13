'use client';
/**
 * ArtifactViewer — full modal/drawer with Preview/Source/Actions tabs.
 * Renders artifact content safely based on content_format.
 */

import React, { useState } from 'react';
import { X, Eye, Code, CheckSquare, AlertTriangle } from 'lucide-react';
import { MaxArtifact, ArtifactMode } from '../../../lib/types';
import { SafeHtmlPreview } from './SafeHtmlPreview';
import { ArtifactSourcePanel } from './ArtifactSourcePanel';
import { ArtifactActions } from './ArtifactActions';

interface ArtifactViewerProps {
  artifact: MaxArtifact;
  displayMode?: ArtifactMode;
  onClose: () => void;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  onRequestChanges: (id: string) => void;
}

type Tab = 'preview' | 'source' | 'actions';

export function ArtifactViewer({
  artifact,
  displayMode,
  onClose,
  onApprove,
  onReject,
  onRequestChanges,
}: ArtifactViewerProps) {
  const [activeTab, setActiveTab] = useState<Tab>('preview');
  const effectiveMode = displayMode || artifact.mode;

  const tabs: { id: Tab; label: string; Icon: React.ElementType }[] = [
    { id: 'preview', label: 'Preview', Icon: Eye },
    { id: 'source', label: 'Source', Icon: Code },
    { id: 'actions', label: 'Actions', Icon: CheckSquare },
  ];

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 500,
      background: 'rgba(0,0,0,0.85)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '16px',
    }}>
      <div style={{
        background: 'rgba(15,23,42,0.98)',
        backdropFilter: 'blur(24px)',
        border: '1px solid rgba(255,255,255,0.12)',
        borderRadius: 16,
        width: '100%',
        maxWidth: 960,
        maxHeight: '90vh',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}>
        {/* Header */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 12,
          padding: '16px 20px',
          borderBottom: '1px solid rgba(255,255,255,0.08)',
        }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 15, fontWeight: 800, color: '#f1f5f9', marginBottom: 2 }}>
              {artifact.title}
            </div>
            {artifact.description && (
              <div style={{ fontSize: 12, color: '#64748b' }}>
                {artifact.description}
              </div>
            )}
          </div>

          {/* Badges */}
          <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
            <span style={{
              fontSize: 9, fontWeight: 700, padding: '2px 8px', borderRadius: 4,
              background: 'rgba(168,85,247,0.2)', color: '#a855f7', textTransform: 'uppercase',
            }}>
              {artifact.artifact_type}
            </span>
            <span style={{
              fontSize: 9, fontWeight: 700, padding: '2px 8px', borderRadius: 4,
              background: `${effectiveMode === 'approved' ? 'rgba(16,185,129,0.2)' : effectiveMode === 'approval_required' ? 'rgba(245,158,11,0.2)' : 'rgba(255,255,255,0.08)'}`,
              color: effectiveMode === 'approved' ? '#10b981' : effectiveMode === 'approval_required' ? '#f59e0b' : '#94a3b8',
            }}>
              {effectiveMode.replace('_', ' ')}
            </span>
          </div>

          <button
            onClick={onClose}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              width: 32, height: 32, borderRadius: 8,
              border: '1px solid rgba(255,255,255,0.12)',
              background: 'rgba(255,255,255,0.05)', color: '#94a3b8',
              cursor: 'pointer', flexShrink: 0,
            }}
          >
            <X size={14} />
          </button>
        </div>

        {/* Tab bar */}
        <div style={{
          display: 'flex', gap: 0,
          borderBottom: '1px solid rgba(255,255,255,0.08)',
        }}>
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '10px 20px',
                border: 'none',
                borderBottom: activeTab === tab.id ? '2px solid #6366f1' : '2px solid transparent',
                background: 'transparent',
                color: activeTab === tab.id ? '#818cf8' : '#64748b',
                cursor: 'pointer', fontSize: 12, fontWeight: 600,
                transition: 'all 0.15s',
              }}
            >
              <tab.Icon size={13} />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div style={{ flex: 1, overflow: 'auto', minHeight: 0 }}>
          {activeTab === 'preview' && (
            <div style={{ padding: '16px' }}>
              {artifact.content_format === 'html' ? (
                <SafeHtmlPreview artifact={artifact} height={500} />
              ) : artifact.content_format === 'markdown' ? (
                <div style={{
                  padding: '16px',
                  background: 'rgba(15,23,42,0.6)',
                  borderRadius: 8,
                  fontSize: 13, lineHeight: 1.7, color: '#e2e8f0',
                  whiteSpace: 'pre-wrap',
                }}>
                  {artifact.content}
                </div>
              ) : (
                <div style={{
                  padding: '16px',
                  background: 'rgba(15,23,42,0.6)',
                  borderRadius: 8,
                  fontSize: 12, fontFamily: 'var(--font-mono, monospace)',
                  color: '#94a3b8',
                  overflow: 'auto',
                  whiteSpace: 'pre-wrap',
                }}>
                  {artifact.content}
                </div>
              )}
            </div>
          )}

          {activeTab === 'source' && (
            <ArtifactSourcePanel artifact={artifact} />
          )}

          {activeTab === 'actions' && (
            <ArtifactActions
              artifact={artifact}
              displayMode={effectiveMode}
              onApprove={onApprove}
              onReject={onReject}
              onRequestChanges={onRequestChanges}
              onCopySource={() => navigator.clipboard.writeText(artifact.content)}
            />
          )}
        </div>

        {/* Footer */}
        <div style={{
          padding: '10px 20px',
          borderTop: '1px solid rgba(255,255,255,0.06)',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <span style={{ fontSize: 10, color: '#475569' }}>
            v10 Artifact Viewer — local review only
          </span>
          <span style={{ fontSize: 10, color: '#475569' }}>
            {artifact.source} · {artifact.content_format}
          </span>
        </div>
      </div>
    </div>
  );
}