'use client';

import React from 'react';
import {
  BookOpen, RefreshCw, Send, Sparkles, Trash2, Wand2, ExternalLink,
} from 'lucide-react';
import ChatMarkdown from '../chat/ChatMarkdown';
import '../chat/chat.css';
import type { FamilyDraft, HelpGuide } from '../../lib/familyHelpModel';
import { EDITION_WHO } from '../../lib/familyHelpModel';

const ACCENT = '#b8960c';
const ACCENT_BG = 'rgba(184,150,12,0.12)';
const ACCENT_BORDER = 'rgba(184,150,12,0.28)';

export function FamilyGenerateBar({
  busy,
  onReply,
  onManual,
}: {
  busy: boolean;
  onReply: () => void;
  onManual: () => void;
}) {
  return (
    <div
      data-testid="family-generate-bar"
      style={{
        display: 'flex', gap: 10, flexWrap: 'wrap',
        padding: 14, borderRadius: 12,
        background: 'linear-gradient(180deg, rgba(184,150,12,0.10), rgba(184,150,12,0.03))',
        border: `1px solid ${ACCENT_BORDER}`,
      }}
    >
      <div style={{ flex: '1 1 220px', minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: ACCENT, marginBottom: 4 }}>Max, on demand</div>
        <div style={{ fontSize: 12, color: 'var(--muted, #8b8b80)', lineHeight: 1.45 }}>
          Nothing is drafted, sent, or saved until you tap. Replies greet with “manito”. Manuals
          link the live screen map for their edition.
        </div>
      </div>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        <button
          type="button"
          data-testid="generate-reply-btn"
          disabled={busy}
          onClick={onReply}
          style={btn(ACCENT)}
        >
          <Wand2 size={14} /> Generar respuesta
        </button>
        <button
          type="button"
          data-testid="generate-manual-btn"
          disabled={busy}
          onClick={onManual}
          style={btn('#2563eb')}
        >
          <BookOpen size={14} /> Generar manual
        </button>
      </div>
    </div>
  );
}

export function FamilyDraftPane({
  draft,
  busy,
  onChange,
  onSend,
  onRegenerate,
  onDiscard,
  onSave,
}: {
  draft: FamilyDraft;
  busy: boolean;
  onChange: (body: string) => void;
  onSend: () => void;
  onRegenerate: () => void;
  onDiscard: () => void;
  onSave?: () => void;
}) {
  const isManual = draft.kind === 'manual';
  return (
    <div
      data-testid="family-draft-pane"
      style={{
        background: 'rgba(184,150,12,0.05)',
        border: `1px solid ${ACCENT}`,
        borderRadius: 14,
        padding: 16,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10, flexWrap: 'wrap' }}>
        <Sparkles size={14} color={ACCENT} />
        <span style={{ fontSize: 13, fontWeight: 800, letterSpacing: 0.3 }}>
          Borrador · {isManual ? 'Manual' : 'Respuesta'}
        </span>
        <span style={{
          fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 999,
          background: ACCENT_BG, color: ACCENT,
        }}>
          No enviado
        </span>
        {draft.included_model && (
          <span style={{ fontSize: 11, color: 'var(--muted, #8b8b80)' }}>Max included model</span>
        )}
      </div>
      <div style={{ fontSize: 12, color: 'var(--muted, #8b8b80)', marginBottom: 10, lineHeight: 1.45 }}>
        Editable. Send / Regenerate / Discard — and Save to help library for manuals — wait for your tap.
      </div>
      <textarea
        data-testid="family-draft-body"
        value={draft.body}
        onChange={(e) => onChange(e.target.value)}
        rows={isManual ? 10 : 6}
        style={{
          width: '100%', boxSizing: 'border-box', padding: '10px 12px', borderRadius: 10,
          fontSize: 14, lineHeight: 1.5, resize: 'vertical', fontFamily: 'inherit',
          background: '#0b0f14', color: 'inherit', border: `1px solid ${ACCENT_BORDER}`,
        }}
      />
      {isManual && (
        <div
          data-testid="family-draft-preview"
          style={{
            marginTop: 12, padding: 12, borderRadius: 10,
            background: 'rgba(0,0,0,0.25)', border: `1px solid ${ACCENT_BORDER}`,
            fontSize: 14, lineHeight: 1.55,
          }}
        >
          <div style={{ fontSize: 11, fontWeight: 700, color: ACCENT, marginBottom: 8, letterSpacing: 0.4 }}>
            PREVIEW · TAPPABLE LINKS
          </div>
          <ChatMarkdown text={draft.body} />
          {(draft.screens || []).length > 0 && (
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 10 }}>
              {draft.screens!.map((s) => (
                <a
                  key={s.id}
                  href={s.href}
                  style={{
                    display: 'inline-flex', alignItems: 'center', gap: 4,
                    padding: '4px 9px', borderRadius: 999, fontSize: 12, fontWeight: 600,
                    background: ACCENT_BG, color: ACCENT, textDecoration: 'none',
                    border: `1px solid ${ACCENT_BORDER}`,
                  }}
                >
                  <ExternalLink size={11} /> {s.label || s.name}
                </a>
              ))}
            </div>
          )}
        </div>
      )}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 12 }}>
        <button type="button" data-testid="draft-send" disabled={busy || !draft.body.trim()} onClick={onSend} style={btn(ACCENT)}>
          <Send size={14} /> Send
        </button>
        <button type="button" data-testid="draft-regenerate" disabled={busy} onClick={onRegenerate} style={btn('#2563eb')}>
          <RefreshCw size={14} /> Regenerate
        </button>
        {isManual && onSave && (
          <button type="button" data-testid="draft-save-library" disabled={busy || !draft.body.trim()} onClick={onSave} style={btn('#15803d')}>
            <BookOpen size={14} /> Save to help library
          </button>
        )}
        <button type="button" data-testid="draft-discard" disabled={busy} onClick={onDiscard} style={ghostBtn}>
          <Trash2 size={14} /> Discard
        </button>
      </div>
    </div>
  );
}

export function FamilyHelpLibrary({
  edition,
  guides,
  onOpen,
}: {
  edition: string;
  guides: HelpGuide[];
  onOpen: (guide: HelpGuide) => void;
}) {
  const who = EDITION_WHO[edition] || edition;
  return (
    <div data-testid="help-library" style={{
      background: 'rgba(255,255,255,0.025)',
      border: `1px solid ${ACCENT_BORDER}`,
      borderRadius: 12,
      padding: 16,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, fontWeight: 700, marginBottom: 10 }}>
        <BookOpen size={14} color={ACCENT} /> Help library · {who}
      </div>
      {guides.length === 0 && (
        <div style={{ fontSize: 13, color: 'var(--muted, #8b8b80)', lineHeight: 1.5 }}>
          No guides saved for this edition yet. Generate a manual, then tap Save to help library.
        </div>
      )}
      {guides.map((g) => (
        <button
          key={g.id}
          type="button"
          data-guide-id={g.id}
          onClick={() => onOpen(g)}
          style={{
            display: 'block', width: '100%', textAlign: 'left', marginBottom: 8, padding: 10,
            borderRadius: 10, cursor: 'pointer', color: 'inherit',
            border: '1px solid rgba(255,255,255,0.06)', background: 'rgba(255,255,255,0.02)',
          }}
        >
          <div style={{ fontSize: 13, fontWeight: 600 }}>{g.title}</div>
          <div style={{ fontSize: 11, color: 'var(--muted, #8b8b80)', marginTop: 3 }}>
            {g.created_at?.slice(0, 16).replace('T', ' ')}
          </div>
        </button>
      ))}
    </div>
  );
}

function btn(bg: string): React.CSSProperties {
  return {
    display: 'inline-flex', alignItems: 'center', gap: 6, padding: '9px 13px', borderRadius: 8,
    border: 'none', background: bg, color: '#fff', fontSize: 13, fontWeight: 600, cursor: 'pointer',
  };
}
const ghostBtn: React.CSSProperties = {
  ...btn('transparent'),
  color: 'inherit',
  border: `1px solid ${ACCENT_BORDER}`,
};
