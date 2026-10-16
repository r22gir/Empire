'use client';
import { useMemo, useState } from 'react';
import { Camera, Keyboard, Link2, Mic, Sun, X } from 'lucide-react';
import { Orb } from '../v3/ui';
import { useLiveVoice } from '../components/LiveVoiceCall';
import { EDITION } from '../v3/edition';
import { EXAMPLE_MARK, EXAMPLE_TRANSCRIPT, useExampleMode } from './exampleData';
import { STUDIO_INTENTS } from './studioIntents';

export default function VoiceHome({
  onKeyboard,
  onIntent,
  onClose,
}: {
  onKeyboard: () => void;
  onIntent: (id: 'today' | 'photo' | 'link') => void;
  onClose?: () => void;
}) {
  const voice = useLiveVoice();
  const example = useExampleMode();
  const [typed, setTyped] = useState('');
  const active = voice.state === 'connecting' || voice.state === 'live' || voice.state === 'ending';
  const lastUser = [...voice.lines].reverse().find((l) => l.role === 'user');
  const transcript = example
    ? EXAMPLE_TRANSCRIPT
    : (lastUser?.text || (active ? 'Listening…' : `Talk to ${EDITION.assistantName}.`));

  const status = useMemo(() => {
    if (active) return voice.speaking ? 'SPEAKING' : 'LISTENING';
    if (voice.state === 'error') return 'NO SIGNAL';
    return 'READY';
  }, [active, voice.speaking, voice.state]);

  return (
    <section className="studio-voice" data-testid="studio-voice-home" aria-label={`${EDITION.assistantName} voice`}>
      <div className="studio-orb-wrap">
        <i className="studio-orb-ring s2" />
        <i className="studio-orb-ring" />
        <Orb size={168} />
      </div>
      <div className="studio-listen">
        {EDITION.assistantName.toUpperCase()} · {status}
      </div>
      <p className="studio-transcript">“{transcript}”</p>
      <div>
        <span className="studio-ex">Live transcript {example ? `· ${EXAMPLE_MARK}` : ''}</span>
      </div>
      {voice.error && !example ? <p className="studio-ex" style={{ color: '#f08a7a', marginTop: 8 }}>{voice.error}</p> : null}

      <div className="studio-intents" role="group" aria-label="One-tap intents">
        {STUDIO_INTENTS.map((it) => (
          <button key={it.id} type="button" className="studio-intent" onClick={() => onIntent(it.id)} data-testid={`studio-intent-${it.id}`}>
            <span className="ic">
              {it.id === 'today' ? <Sun size={16} /> : it.id === 'photo' ? <Camera size={16} /> : <Link2 size={16} />}
            </span>
            {it.label}
          </button>
        ))}
      </div>

      <div className="studio-dock">
        {onClose ? (
          <button type="button" className="side" onClick={onClose} aria-label="Close voice"><X size={16} /></button>
        ) : (
          <span className="side" style={{ visibility: 'hidden' }} />
        )}
        <button
          type="button"
          className={`talk${active ? ' live' : ''}`}
          data-testid="studio-talk"
          aria-label={active ? 'End live call with Max' : 'Talk to Max'}
          onClick={() => (active ? voice.stop() : voice.start())}
        >
          <Mic size={22} />
        </button>
        <button type="button" className="side" onClick={onKeyboard} aria-label="Open typed chat" data-testid="studio-keyboard">
          <Keyboard size={16} />
        </button>
      </div>

      <form
        className="studio-ask"
        style={{ maxWidth: 420, width: '100%' }}
        onSubmit={(e) => {
          e.preventDefault();
          const q = typed.trim();
          if (q) onIntent('today');
        }}
        hidden
      >
        <input value={typed} onChange={(e) => setTyped(e.target.value)} />
      </form>
    </section>
  );
}
