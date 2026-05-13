'use client';
/**
 * ArtifactSourcePanel — escaped source code view of artifact content.
 * Shows raw content with proper escaping and format detection.
 */

import React from 'react';
import { Copy, Check } from 'lucide-react';
import { MaxArtifact } from '../../../lib/types';

interface ArtifactSourcePanelProps {
  artifact: MaxArtifact;
}

function formatSource(content: string, format: string): string {
  if (format === 'json') {
    try {
      return JSON.stringify(JSON.parse(content), null, 2);
    } catch {
      return content;
    }
  }
  return content;
}

export function ArtifactSourcePanel({ artifact }: ArtifactSourcePanelProps) {
  const [copied, setCopied] = React.useState(false);
  const formatted = formatSource(artifact.content, artifact.content_format);

  const handleCopy = () => {
    navigator.clipboard.writeText(formatted);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '10px 14px',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        background: 'rgba(15,23,42,0.6)',
      }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          Source — {artifact.content_format}
        </span>
        <button
          onClick={handleCopy}
          style={{
            display: 'flex', alignItems: 'center', gap: 5,
            padding: '4px 10px', borderRadius: 5,
            border: '1px solid rgba(255,255,255,0.1)',
            background: 'rgba(255,255,255,0.05)', color: '#94a3b8',
            cursor: 'pointer', fontSize: 11, fontWeight: 500,
          }}
        >
          {copied ? <Check size={11} color="#10b981" /> : <Copy size={11} />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>

      {/* Code content */}
      <pre style={{
        flex: 1,
        overflow: 'auto',
        padding: '14px',
        margin: 0,
        background: '#0a0f1a',
        color: '#94a3b8',
        fontSize: 11.5,
        fontFamily: 'var(--font-mono, Consolas, "Courier New", monospace)',
        lineHeight: 1.7,
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
      }}>
        <code>{formatted}</code>
      </pre>
    </div>
  );
}