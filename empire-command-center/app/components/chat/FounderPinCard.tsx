'use client';

import { useState } from 'react';
import { ShieldCheck } from 'lucide-react';
import { PinPrompt } from '../../lib/types';

interface Props {
  prompt: PinPrompt;
  disabled?: boolean;
  onSubmit: (resumeId: string, pin: string) => Promise<void> | void;
  onCancel?: (resumeId: string) => void;
}

export default function FounderPinCard({ prompt, disabled, onSubmit, onCancel }: Props) {
  const [value, setValue] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);
  const busy = prompt.status === 'submitting' || disabled;

  if (prompt.status === 'cancelled') return null;

  if (prompt.status === 'done') {
    return (
      <div style={{
        marginTop: 10,
        padding: '14px 16px',
        borderRadius: 14,
        border: '1.5px solid #bbf7d0',
        background: '#f0fdf4',
        maxWidth: 480,
      }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: '#166534', marginBottom: 6 }}>
          Approved. {prompt.tool} finished.
        </div>
        {prompt.detail && (
          <pre style={{
            margin: 0,
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            fontSize: 12,
            lineHeight: 1.45,
            color: '#14532d',
            fontFamily: 'ui-monospace, monospace',
          }}>{prompt.detail}</pre>
        )}
      </div>
    );
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        const pin = value;
        if (!pin.trim() || busy) return;
        setLocalError(null);
        setValue('');
        Promise.resolve(onSubmit(prompt.resumeId, pin)).catch(() => {
          setLocalError('Could not send the PIN. Try again.');
        });
      }}
      style={{
        marginTop: 10,
        padding: '14px 16px',
        borderRadius: 14,
        border: '1.5px solid #f0e6c0',
        background: '#fffdf7',
        maxWidth: 480,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <ShieldCheck size={18} color="#96750a" />
        <div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>
          Founder PIN
        </div>
      </div>
      <p style={{ margin: '0 0 12px', fontSize: 13, lineHeight: 1.45, color: '#555' }}>
        {prompt.tool} is restricted. Enter the founder PIN to run it. The PIN stays in this field and is not added to the chat.
      </p>
      <input
        type="password"
        inputMode="numeric"
        autoComplete="off"
        autoCapitalize="off"
        autoCorrect="off"
        spellCheck={false}
        enterKeyHint="done"
        name="founder-approval"
        aria-label="Founder PIN"
        placeholder="Founder PIN"
        value={value}
        disabled={busy}
        onChange={(e) => setValue(e.target.value)}
        style={{
          width: '100%',
          boxSizing: 'border-box',
          minHeight: 48,
          padding: '12px 14px',
          fontSize: 16,
          letterSpacing: '0.2em',
          border: '1.5px solid #ece8e0',
          borderRadius: 10,
          background: busy ? '#f8f8f6' : '#fff',
        }}
      />
      {(localError || prompt.detail) && prompt.status !== 'submitting' && (
        <div style={{
          marginTop: 8,
          background: '#fef2f2',
          border: '1px solid #fecaca',
          color: '#991b1b',
          borderRadius: 8,
          padding: '8px 10px',
          fontSize: 13,
        }}>
          {localError || prompt.detail}
        </div>
      )}
      <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
        <button
          type="button"
          disabled={busy}
          onClick={() => {
            setValue('');
            onCancel?.(prompt.resumeId);
          }}
          style={{
            flex: 1,
            minHeight: 48,
            borderRadius: 10,
            border: '1.5px solid #ece8e0',
            background: '#fff',
            color: '#1a1a1a',
            fontSize: 16,
            fontWeight: 700,
            cursor: busy ? 'default' : 'pointer',
          }}
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={busy || !value.trim()}
          style={{
            flex: 1,
            minHeight: 48,
            border: 'none',
            borderRadius: 10,
            background: busy || !value.trim() ? '#d6d3cd' : '#1a1a1a',
            color: '#fff',
            fontSize: 16,
            fontWeight: 700,
            cursor: busy || !value.trim() ? 'default' : 'pointer',
          }}
        >
          {busy ? 'Checking…' : 'Submit'}
        </button>
      </div>
    </form>
  );
}
