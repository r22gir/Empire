'use client';
/**
 * SafeHtmlPreview — sandboxed iframe renderer for html_artifact content.
 *
 * Rules enforced:
 * - sandbox="" (NO allow-scripts, NO allow-same-origin, NO allow-forms)
 * - Strip <script>, event handlers, javascript: URLs, external resources
 * - Show "Content sanitized" warning if any dangerous content was stripped
 */

import React, { useState } from 'react';
import { AlertTriangle } from 'lucide-react';
import { MaxArtifact } from '../../../lib/types';
import { stripDangerousHtml, buildArtifactHtmlDoc } from '../../../lib/artifacts';

interface SafeHtmlPreviewProps {
  artifact: MaxArtifact;
  height?: number | string;
}

export function SafeHtmlPreview({ artifact, height = 600 }: SafeHtmlPreviewProps) {
  const { cleaned, hadDangerous } = stripDangerousHtml(artifact.content);
  const htmlDoc = buildArtifactHtmlDoc({ ...artifact, content: cleaned });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
      {hadDangerous && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6,
          padding: '8px 12px',
          background: 'rgba(245,158,11,0.12)',
          borderBottom: '1px solid rgba(245,158,11,0.25)',
          fontSize: 11, color: '#f59e0b', fontWeight: 600,
        }}>
          <AlertTriangle size={12} />
          Content was sanitized — dangerous elements (scripts, event handlers, external resources) were removed before preview.
        </div>
      )}
      <div style={{
        position: 'relative',
        width: '100%',
        height: typeof height === 'number' ? `${height}px` : height,
        background: '#0f172a',
        borderRadius: '0 0 8px 8px',
        overflow: 'hidden',
      }}>
        <iframe
          srcDoc={htmlDoc}
          sandbox=""  // NO allow-scripts, NO allow-same-origin, NO allow-forms, NO allow-popups
          title={artifact.title}
          style={{
            width: '100%',
            height: '100%',
            border: 'none',
            background: '#0f172a',
          }}
        />
      </div>
      <div style={{
        padding: '6px 12px',
        background: 'rgba(15,23,42,0.6)',
        borderTop: '1px solid rgba(255,255,255,0.06)',
        fontSize: 10, color: '#64748b', fontWeight: 500,
        display: 'flex', justifyContent: 'space-between',
      }}>
        <span>sandboxed preview — scripts blocked</span>
        <span>{artifact.content_format}</span>
      </div>
    </div>
  );
}