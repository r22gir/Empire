'use client';
import React, { useState, useCallback, useEffect } from 'react';
import { Maximize2, Minimize2, PanelLeftClose, PanelRightClose, PanelLeftOpen, PanelRightOpen, Layout, ChevronDown, X, MessageSquare } from 'lucide-react';
import { EmpireShell } from '../ui/EmpireShell';
import { DeskSelector } from './DeskSelector';
import { ChatInterface } from './ChatInterface';
import { ContinuityPanel } from './ContinuityPanel';
import { Message } from '../../lib/types';

const API = 'http://localhost:8000/api/v1';
const STORAGE_KEY = 'empire_max_messages';
const LAYOUT_KEY = 'empire_max_layout';

interface LayoutState {
  sidebarVisible: boolean;
  rightPanelVisible: boolean;
  focusMode: boolean;
}

function loadLayout(): LayoutState {
  try {
    const raw = localStorage.getItem(LAYOUT_KEY);
    if (raw) return JSON.parse(raw);
  } catch { /* ignore */ }
  // CHAT-FIRST: default to collapsed panels — chat takes full space on first load
  return { sidebarVisible: false, rightPanelVisible: false, focusMode: false };
}

function saveLayout(state: LayoutState) {
  try { localStorage.setItem(LAYOUT_KEY, JSON.stringify(state)); } catch { /* ignore */ }
}

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
  // Panel visibility — initialized from localStorage with safe defaults
  // CHAT-FIRST: default to collapsed side panels so chat is maximized on load
  const [sidebarVisible, setSidebarVisible] = useState<boolean>(() => loadLayout().sidebarVisible);
  const [rightPanelVisible, setRightPanelVisible] = useState<boolean>(() => loadLayout().rightPanelVisible);
  // Focus mode: hide both side panels, maximize chat
  const [focusMode, setFocusMode] = useState<boolean>(() => loadLayout().focusMode);
  // Code mode confirmation dialog
  const [showCodeModeConfirm, setShowCodeModeConfirm] = useState(false);
  const [pendingCodeMode, setPendingCodeMode] = useState(false); // true = enabling, false = disabling

  // Persist layout to localStorage when it changes
  useEffect(() => {
    saveLayout({ sidebarVisible, rightPanelVisible, focusMode });
    // On narrow screens, auto-collapse side panels for readability
    if (typeof window !== 'undefined' && window.innerWidth < 1024) {
      if (sidebarVisible && !focusMode) setSidebarVisible(false);
      if (rightPanelVisible && !focusMode) setRightPanelVisible(false);
    }
  }, [sidebarVisible, rightPanelVisible, focusMode]);

  const resetLayout = useCallback(() => {
    try { localStorage.removeItem(LAYOUT_KEY); } catch {}
    // Always reset to chat-first collapsed state
    setSidebarVisible(false);
    setRightPanelVisible(false);
    setFocusMode(false);
  }, []);

  const toggleFocus = useCallback(() => {
    setFocusMode(v => {
      if (!v) {
        // entering focus: hide both panels
        setSidebarVisible(false);
        setRightPanelVisible(false);
      }
      return !v;
    });
  }, []);

  const toggleSidebar = useCallback(() => {
    setSidebarVisible(v => {
      if (v) setFocusMode(false);
      return !v;
    });
  }, []);

  const toggleRightPanel = useCallback(() => {
    setRightPanelVisible(v => {
      if (v) setFocusMode(false);
      return !v;
    });
  }, []);

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

  const handleToggleCodeMode = useCallback((enable: boolean) => {
    if (enable) {
      setPendingCodeMode(true);
      setShowCodeModeConfirm(true);
    } else {
      setCodeMode(false);
    }
  }, []);

  const confirmCodeMode = useCallback(() => {
    setCodeMode(true);
    setShowCodeModeConfirm(false);
    setPendingCodeMode(false);
  }, []);

  const cancelCodeMode = useCallback(() => {
    setShowCodeModeConfirm(false);
    setPendingCodeMode(false);
  }, []);

  return (
    <EmpireShell commitHash="ce1695d">
      {/* Layout Controls Bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--space-2)',
        marginBottom: 'var(--space-3)',
        padding: '0 0 var(--space-2) 0',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
      }}>
        <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1px', flex: 1 }}>
          MAX AI
        </span>
        {/* Always-visible branch badge */}
        <span style={{
          fontSize: 9, fontWeight: 700, padding: '2px 8px', borderRadius: 4,
          background: 'rgba(99,102,241,0.3)', color: 'var(--accent-primary)',
        }}>
          v10 test lane
        </span>
        <button
          onClick={toggleSidebar}
          title={sidebarVisible ? 'Collapse desk panel' : 'Expand desk panel'}
          style={{
            display: 'flex', alignItems: 'center', gap: 4,
            padding: '4px 8px', borderRadius: 'var(--radius-md)',
            border: '1px solid rgba(255,255,255,0.1)',
            background: sidebarVisible ? 'rgba(99,102,241,0.2)' : 'rgba(255,255,255,0.06)',
            color: sidebarVisible ? 'var(--accent-primary)' : 'var(--text-muted)',
            cursor: 'pointer', fontSize: 'var(--text-xs)', fontWeight: 600,
          }}
        >
          {sidebarVisible ? <PanelLeftClose size={12} /> : <PanelLeftOpen size={12} />}
          {sidebarVisible ? 'Hide Desks' : 'Show Desks'}
        </button>
        <button
          onClick={toggleRightPanel}
          title={rightPanelVisible ? 'Collapse context panel' : 'Expand context panel'}
          style={{
            display: 'flex', alignItems: 'center', gap: 4,
            padding: '4px 8px', borderRadius: 'var(--radius-md)',
            border: '1px solid rgba(255,255,255,0.1)',
            background: rightPanelVisible ? 'rgba(99,102,241,0.2)' : 'rgba(255,255,255,0.06)',
            color: rightPanelVisible ? 'var(--accent-primary)' : 'var(--text-muted)',
            cursor: 'pointer', fontSize: 'var(--text-xs)', fontWeight: 600,
          }}
        >
          {rightPanelVisible ? <PanelRightClose size={12} /> : <PanelRightOpen size={12} />}
          {rightPanelVisible ? 'Hide Context' : 'Show Context'}
        </button>
        <button
          onClick={toggleFocus}
          title={focusMode ? 'Exit focus mode' : 'Enter focus mode — maximize chat'}
          style={{
            display: 'flex', alignItems: 'center', gap: 4,
            padding: '4px 8px', borderRadius: 'var(--radius-md)',
            border: focusMode ? '1px solid var(--accent-primary)' : '1px solid rgba(255,255,255,0.1)',
            background: focusMode ? 'var(--accent-primary)' : 'rgba(255,255,255,0.06)',
            color: focusMode ? '#fff' : 'var(--text-muted)',
            cursor: 'pointer', fontSize: 'var(--text-xs)', fontWeight: 600,
          }}
        >
          {focusMode ? <Minimize2 size={12} /> : <Maximize2 size={12} />}
          {focusMode ? 'Exit Focus' : 'Focus Chat'}
        </button>
        {/* Reset Layout — always visible */}
        <button
          onClick={resetLayout}
          title="Reset layout to defaults — clears saved preferences"
          style={{
            display: 'flex', alignItems: 'center', gap: 4,
            padding: '4px 8px', borderRadius: 'var(--radius-md)',
            border: '1px solid rgba(255,255,255,0.08)',
            background: 'rgba(255,255,255,0.04)',
            color: 'var(--text-muted)',
            cursor: 'pointer', fontSize: 'var(--text-xs)', fontWeight: 500,
          }}
        >
          <Layout size={12} /> Reset Layout
        </button>
        {/* Chat Only — explicit collapse of all panels */}
        <button
          onClick={() => { setSidebarVisible(false); setRightPanelVisible(false); setFocusMode(false); }}
          title="Chat Only — collapse all panels for maximum chat space"
          style={{
            display: 'flex', alignItems: 'center', gap: 4,
            padding: '4px 8px', borderRadius: 'var(--radius-md)',
            border: '1px solid var(--accent-primary)',
            background: 'var(--accent-primary)',
            color: '#fff',
            cursor: 'pointer', fontSize: 'var(--text-xs)', fontWeight: 700,
          }}
        >
          <MessageSquare size={12} /> Chat Only
        </button>
        {focusMode && (
          <span style={{
            fontSize: 9, fontWeight: 700, padding: '2px 8px', borderRadius: 4,
            background: 'rgba(99,102,241,0.3)', color: 'var(--accent-primary)',
          }}>
            Focus Mode
          </span>
        )}
      </div>

      <div className="animated-gradient" style={{
        display: 'grid',
        gridTemplateColumns: sidebarVisible && !focusMode ? '280px 1fr 300px' : '1fr',
        gridTemplateRows: '1fr',
        gap: 'var(--space-4)',
        height: focusMode
          ? 'calc(100vh - var(--topbar-height) - var(--space-12) - 60px)'
          : 'calc(100vh - var(--topbar-height) - var(--space-12))',
        minHeight: 500,
        transition: 'all 0.3s ease',
      }}>
        {/* Left: Desk Selector — only visible when sidebarVisible and not focusMode */}
        {sidebarVisible && !focusMode && (
          <div style={{
            background: 'rgba(30,41,59,0.6)',
            backdropFilter: 'blur(18px)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 'var(--radius-lg)',
            overflow: 'hidden',
            minWidth: 0,
            height: '100%',
          }}>
            <DeskSelector
              activeDesk={activeDesk}
              onDeskChange={setActiveDesk}
            />
          </div>
        )}

        {/* Center: Chat */}
        <div style={{
          background: 'rgba(30,41,59,0.6)',
          backdropFilter: 'blur(18px)',
          border: '1px solid rgba(255,255,255,0.1)',
          borderRadius: 'var(--radius-lg)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          flex: 1,
          minWidth: 0,
          minHeight: 0,
        }}>
          <ChatInterface
            messages={messages}
            isStreaming={isStreaming}
            streamingContent={streamingContent}
            onSendMessage={handleSendMessage}
            onStopStreaming={handleStopStreaming}
            onClearChat={handleClearChat}
            codeMode={codeMode}
            onToggleCodeMode={handleToggleCodeMode}
            voiceMode={voiceMode}
            onToggleVoiceMode={() => setVoiceMode(v => !v)}
            activeDesk={activeDesk}
          />
        </div>

        {/* Right: Continuity Panel — only visible when rightPanelVisible and not focusMode */}
        {rightPanelVisible && !focusMode && (
          <div style={{
            background: 'rgba(30,41,59,0.6)',
            backdropFilter: 'blur(18px)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 'var(--radius-lg)',
            overflow: 'hidden',
            padding: 'var(--space-4)',
            minWidth: 0,
          }}>
            <ContinuityPanel activeDesk={activeDesk} />
          </div>
        )}
      </div>

      {/* Code Mode Confirmation Dialog */}
      {showCodeModeConfirm && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 200,
          background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <div style={{
            background: 'rgba(30,41,59,0.95)', backdropFilter: 'blur(20px)',
            border: '1px solid rgba(255,255,255,0.15)',
            borderRadius: 16, padding: 24, maxWidth: 400, width: '90%',
          }}>
            <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 12 }}>
              Enable Code Mode?
            </div>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 20 }}>
              <strong>Target branch:</strong> feature/v10.0-test-lane<br/>
              <strong>Runtime:</strong> v10 test lane (port 3010)<br/>
              Stable/main are protected — no direct merge or deploy will occur without explicit approval.<br/><br/>
              <span style={{ color: 'var(--warning)', fontWeight: 600 }}>Warning:</span> Backend branch targeting is not yet enforced. Any file-changing task will run against whatever branch is currently active in OpenClaw.
            </div>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button
                onClick={cancelCodeMode}
                style={{
                  padding: '8px 16px', borderRadius: 8,
                  border: '1px solid rgba(255,255,255,0.1)',
                  background: 'rgba(255,255,255,0.06)', color: 'var(--text-muted)',
                  cursor: 'pointer', fontSize: 12, fontWeight: 600,
                }}
              >
                Cancel
              </button>
              <button
                onClick={confirmCodeMode}
                style={{
                  padding: '8px 16px', borderRadius: 8,
                  border: 'none',
                  background: 'var(--accent-primary)', color: '#fff',
                  cursor: 'pointer', fontSize: 12, fontWeight: 700,
                }}
              >
                Enable Code Mode
              </button>
            </div>
          </div>
        </div>
      )}
    </EmpireShell>
  );
}
