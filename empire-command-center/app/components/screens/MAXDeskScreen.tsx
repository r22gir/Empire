'use client';
import React, { useState, useCallback } from 'react';
import { EmpireShell } from '../ui/EmpireShell';
import { DeskSelector } from './DeskSelector';
import { ChatInterface } from './ChatInterface';
import { ContinuityPanel } from './ContinuityPanel';
import { Message } from '../../lib/types';

const API = 'http://localhost:8000/api/v1';
const STORAGE_KEY = 'empire_max_messages';

function loadStoredMessages(): Message[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const msgs = JSON.parse(raw);
      if (Array.isArray(msgs) && msgs.length > 0) return msgs;
    }
  } catch { /* ignore */ }
  return [];
}

function saveMessages(msgs: Message[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(msgs.slice(-50)));
  } catch { /* ignore */ }
}

const WELCOME: Message = {
  id: 'welcome',
  role: 'assistant',
  content: "Hello! I'm **MAX**, your Empire AI Assistant.\n\n_Select a desk from the left panel to begin._",
  timestamp: '',
};

export function MAXDeskScreen() {
  const [activeDesk, setActiveDesk] = useState('codedesk');
  const [messages, setMessages] = useState<Message[]>(() => {
    const stored = loadStoredMessages();
    const initial = stored.length > 0 ? stored : [WELCOME];
    return initial;
  });
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [codeMode, setCodeMode] = useState(false);
  const [voiceMode, setVoiceMode] = useState(false);
  const abortRef = React.useRef<AbortController | null>(null);
  const streamingRef = React.useRef(false);

  const updateMessages = useCallback((msgs: Message[] | ((prev: Message[]) => Message[])) => {
    setMessages(prev => {
      const next = typeof msgs === 'function' ? msgs(prev) : msgs;
      saveMessages(next);
      return next;
    });
  }, []);

  const handleSendMessage = useCallback(async (input: string, imageFile?: File) => {
    if (!input.trim() || streamingRef.current) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    const current = messages;
    const newMsgs = [...current, userMsg];
    updateMessages(newMsgs);
    setIsStreaming(true);
    streamingRef.current = true;
    setStreamingContent('');

    const ctrl = new AbortController();
    abortRef.current = ctrl;
    let accumulated = '';
    let modelUsed = '';

    try {
      const historySlice = newMsgs.slice(-20).map(m => ({ role: m.role, content: m.content }));

      const body: Record<string, unknown> = {
        message: input,
        model: 'auto',
        history: historySlice,
        channel: 'dashboard',
      };
      if (activeDesk) body.desk = activeDesk;
      if (codeMode) body.code_mode = true;
      if (imageFile) body.image_filename = imageFile.name;

      const response = await fetch(`${API}/max/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: ctrl.signal,
      });

      if (!response.body) throw new Error('No response body');
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buf = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split('\n');
        buf = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const ev = JSON.parse(line.slice(6));
            if (ev.type === 'text' && ev.content) {
              accumulated += ev.content;
              setStreamingContent(accumulated);
            } else if (ev.type === 'done') {
              modelUsed = ev.model_used || '';
              if (ev.conversation_id) { /* track if needed */ }
            } else if (ev.type === 'error') {
              accumulated += '\n\n*Error: ' + (ev.content || 'Unknown error') + '*';
              setStreamingContent(accumulated);
            }
          } catch { /* skip */ }
        }
      }

      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: accumulated || 'No response.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        model: modelUsed,
      };
      updateMessages([...newMsgs, assistantMsg]);
      setStreamingContent('');
    } catch (e: any) {
      if (e.name === 'AbortError') {
        if (accumulated) {
          updateMessages(prev => [...prev, {
            id: (Date.now() + 1).toString(),
            role: 'assistant', content: accumulated + '\n\n*[Stopped]*',
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          }]);
        }
      } else {
        updateMessages(prev => [...prev, {
          id: (Date.now() + 1).toString(),
          role: 'assistant', content: '**Connection error.** Backend may be offline.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        }]);
      }
      setStreamingContent('');
    } finally {
      setIsStreaming(false);
      streamingRef.current = false;
      abortRef.current = null;
    }
  }, [messages, activeDesk, codeMode, updateMessages]);

  const handleStopStreaming = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const handleClearChat = useCallback(() => {
    updateMessages([WELCOME]);
  }, [updateMessages]);

  return (
    <EmpireShell commitHash="f535d53">
      <div className="animated-gradient" style={{
        display: 'grid',
        gridTemplateColumns: '280px 1fr 300px',
        gap: 'var(--space-4)',
        height: 'calc(100vh - var(--topbar-height) - var(--space-12))',
        minHeight: 600,
      }}>
        {/* Left: Desk Selector */}
        <div style={{
          background: 'rgba(30,41,59,0.6)',
          backdropFilter: 'blur(18px)',
          border: '1px solid rgba(255,255,255,0.1)',
          borderRadius: 'var(--radius-lg)',
          overflow: 'hidden',
        }}>
          <DeskSelector
            activeDesk={activeDesk}
            onDeskChange={setActiveDesk}
          />
        </div>

        {/* Center: Chat */}
        <div style={{
          background: 'rgba(30,41,59,0.6)',
          backdropFilter: 'blur(18px)',
          border: '1px solid rgba(255,255,255,0.1)',
          borderRadius: 'var(--radius-lg)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}>
          <ChatInterface
            messages={messages}
            isStreaming={isStreaming}
            streamingContent={streamingContent}
            onSendMessage={handleSendMessage}
            onStopStreaming={handleStopStreaming}
            onClearChat={handleClearChat}
            codeMode={codeMode}
            onToggleCodeMode={() => setCodeMode(v => !v)}
            voiceMode={voiceMode}
            onToggleVoiceMode={() => setVoiceMode(v => !v)}
            activeDesk={activeDesk}
          />
        </div>

        {/* Right: Continuity Panel */}
        <div style={{
          background: 'rgba(30,41,59,0.6)',
          backdropFilter: 'blur(18px)',
          border: '1px solid rgba(255,255,255,0.1)',
          borderRadius: 'var(--radius-lg)',
          overflow: 'hidden',
          padding: 'var(--space-4)',
        }}>
          <ContinuityPanel activeDesk={activeDesk} />
        </div>
      </div>
    </EmpireShell>
  );
}
