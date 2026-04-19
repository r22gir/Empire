'use client';
import { useState, useRef, useEffect, useCallback } from 'react';
import { Paperclip, Mic, MicOff, ArrowUp, Volume2, VolumeX, Mail, CheckSquare, Search, FileText, Calendar, ClipboardList, Loader2, Terminal, Headphones, Clock, MoreHorizontal, X } from 'lucide-react';
import ChatHistoryPanel from '../ChatHistoryPanel';
import { Message } from '../../lib/types';
import { API } from '../../lib/api';
import QuoteCard from '../business/quotes/QuoteCard';
import InlineDrawing from '../InlineDrawing';
import ContinuityPanel from '../ContinuityPanel';

// Parse tool call blocks from message content: ```tool\n{...}\n``` or ```\n{"tool":...}\n```
function parseToolBlocks(content: string): { cleanContent: string; toolCalls: any[] } {
  const toolCalls: any[] = [];
  // Match ```tool ... ``` or ``` {"tool": ...} ```
  const cleaned = content.replace(/```(?:tool)?\s*\n?\s*(\{[\s\S]*?\})\s*\n?```/g, (_, json) => {
    try {
      const parsed = JSON.parse(json);
      if (parsed.tool) {
        toolCalls.push(parsed);
        return ''; // Remove from display
      }
    } catch { /* not valid JSON, leave as-is */ }
    return _;
  });
  return { cleanContent: cleaned.trim(), toolCalls };
}

// Check if content has a tool block being streamed (incomplete)
function hasStreamingToolBlock(content: string): boolean {
  // Detect an open ```tool block that hasn't closed yet
  const lastToolStart = content.lastIndexOf('```tool');
  const lastCodeStart = Math.max(content.lastIndexOf('```\n{"tool"'), content.lastIndexOf('```{"tool"'));
  const start = Math.max(lastToolStart, lastCodeStart);
  if (start === -1) return false;
  const afterStart = content.slice(start + 3);
  // Count closing ``` after the opening
  const closingMatch = afterStart.match(/```/);
  return !closingMatch;
}

const QUICK_ACTIONS = [
  { label: 'Quick Quote', icon: ClipboardList, action: 'quick-quote', highlight: true },
  { label: 'Mail', icon: Mail, action: 'briefing' },
  { label: 'Tasks', icon: CheckSquare, action: 'tasks' },
  { label: 'Research', icon: Search, action: 'research' },
  { label: 'Documents', icon: FileText, action: 'documents' },
  { label: 'Calendar', icon: Calendar, action: 'calendar' },
];

interface Props {
  messages: Message[];
  isStreaming: boolean;
  streamingContent: string;
  streamingModel: string;
  onSend: (msg: string, imageFilename?: string | null) => void;
  onStop: () => void;
  onScreenChange?: (screen: string) => void;
  onProductNavigate?: (product: string, screen?: string) => void;
  setOnMessageComplete?: (cb: ((msg: Message) => void) | null) => void;
  onLoadChat?: (chatId: string) => void;
  onNewChat?: () => void;
}

export default function ChatScreen({ messages, isStreaming, streamingContent, streamingModel, onSend, onStop, onScreenChange, onProductNavigate, setOnMessageComplete, onLoadChat, onNewChat }: Props) {
  const [input, setInput] = useState('');
  const [attachedImage, setAttachedImage] = useState<string | null>(null);
  const [recording, setRecording] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [inputFocused, setInputFocused] = useState(false);
  const [codeMode, setCodeMode] = useState(false);
  const [codeTask, setCodeTask] = useState<any>(null);
  const [voiceMode, setVoiceMode] = useState(false);
  const [ttsPlaying, setTtsPlaying] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState<string>(''); // Recording/uploading/transcribing status
  const [aiStatus, setAiStatus] = useState<string>(''); // Thinking/tool status for all messages
  const [maxStatus, setMaxStatus] = useState<any>(null);
  const [recordingTimer, setRecordingTimer] = useState(0);
  const [showMoreActions, setShowMoreActions] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const msgsEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const codePollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const voiceModeRef = useRef(false);
  const recordingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const ttsAudioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    msgsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent, codeTask]);

  useEffect(() => {
    const fetchMaxStatus = async () => {
      try {
        const res = await fetch(API + '/max/orchestration/status', { signal: AbortSignal.timeout(5000) });
        if (res.ok) setMaxStatus(await res.json());
      } catch { /* status is advisory */ }
    };
    fetchMaxStatus();
    const interval = setInterval(fetchMaxStatus, 60000);
    return () => clearInterval(interval);
  }, []);

  // Keep voiceMode ref in sync
  useEffect(() => { voiceModeRef.current = voiceMode; }, [voiceMode]);

  // AI status pipeline — detect tool calls in streaming content
  const TOOL_STATUS_MAP: Record<string, string> = {
    search_conversations: '🔍 Searching past conversations...',
    search_memories: '🔍 Checking memories...',
    create_quote: '📋 Creating quote...',
    create_quick_quote: '📋 Creating quote...',
    photo_to_quote: '📋 Analyzing photo for quote...',
    search_fabrics: '🔍 Looking up fabrics...',
    calculate_yardage: '🧮 Calculating yardage...',
    generate_pdf: '📄 Generating PDF...',
    sketch_to_drawing: '📐 Generating drawing...',
    send_email: '📧 Sending email...',
    check_email: '📧 Checking inbox...',
    file_read: '📂 Reading files...',
    file_write: '📝 Writing files...',
    file_edit: '📝 Editing files...',
    git_ops: '🔧 Git operations...',
    run_desk_task: '🔧 Working on it...',
    db_query: '🗄️ Querying database...',
    web_search: '🌐 Searching the web...',
  };

  useEffect(() => {
    if (isStreaming) {
      // Check for tool blocks in streaming content
      const toolMatch = streamingContent?.match(/"tool"\s*:\s*"(\w+)"/);
      if (toolMatch) {
        const toolName = toolMatch[1];
        setAiStatus(TOOL_STATUS_MAP[toolName] || '🔧 Working on it...');
      } else if (!streamingContent || streamingContent.length < 5) {
        setAiStatus('🧠 MAX is thinking...');
      } else {
        setAiStatus('');
      }
    } else {
      setAiStatus('');
    }
  }, [isStreaming, streamingContent]);

  // Strip markdown for TTS (remove **, *, ```, tool blocks, links)
  const stripForTTS = (text: string) => {
    return text
      .replace(/```[\s\S]*?```/g, '')  // code blocks
      .replace(/\*\*(.*?)\*\*/g, '$1')  // bold
      .replace(/\*(.*?)\*/g, '$1')  // italic
      .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1')  // links
      .replace(/#+\s/g, '')  // headings
      .replace(/\n{3,}/g, '\n\n')  // excess newlines
      .trim();
  };

  // Auto-play TTS when voice mode is on and AI responds
  const playTTSWithCallback = useCallback(async (text: string, onEnd?: () => void) => {
    const clean = stripForTTS(text);
    if (!clean || clean.length < 3) { onEnd?.(); return; }
    try {
      setTtsPlaying(true);
      const res = await fetch(API + '/max/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: clean.slice(0, 2000), voice: 'rex' }),
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        ttsAudioRef.current = audio;
        audio.onended = () => {
          setTtsPlaying(false);
          ttsAudioRef.current = null;
          URL.revokeObjectURL(url);
          onEnd?.();
        };
        audio.onerror = () => {
          setTtsPlaying(false);
          ttsAudioRef.current = null;
          onEnd?.();
        };
        audio.play();
      } else {
        setTtsPlaying(false);
        onEnd?.();
      }
    } catch {
      setTtsPlaying(false);
      onEnd?.();
    }
  }, []);

  // Start recording for voice mode (returns promise that resolves with transcript)
  const startVoiceCapture = useCallback(() => {
    if (mediaRecorderRef.current?.state === 'recording') return;
    navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      const chunks: Blob[] = [];
      recorder.ondataavailable = e => chunks.push(e.data);
      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        // Stop timer
        if (recordingTimerRef.current) { clearInterval(recordingTimerRef.current); recordingTimerRef.current = null; }
        setRecordingTimer(0);

        setVoiceStatus('📤 Sending audio...');
        const blob = new Blob(chunks, { type: 'audio/webm' });
        const fd = new FormData();
        fd.append('audio', blob, 'recording.webm');
        try {
          setVoiceStatus('🔄 Transcribing...');
          const res = await fetch(`${API}/voice/transcribe`, { method: 'POST', body: fd });
          const data = await res.json();
          if (data.text && voiceModeRef.current) {
            // In voice mode: auto-send the transcript
            onSend(data.text);
            setVoiceStatus('');
          } else if (data.text) {
            setInput(prev => prev + (prev ? ' ' : '') + data.text);
            setVoiceStatus('✅ Review, then tap Send');
            textareaRef.current?.focus();
            // Clear status after 5 seconds
            setTimeout(() => setVoiceStatus(prev => prev === '✅ Review, then tap Send' ? '' : prev), 5000);
          } else {
            setVoiceStatus('');
          }
        } catch (err) {
          console.warn('STT transcription failed:', err);
          setVoiceStatus('❌ Transcription failed');
          setTimeout(() => setVoiceStatus(''), 3000);
        }
        setRecording(false);
      };
      recorder.start();
      mediaRecorderRef.current = recorder;
      setRecording(true);
      setVoiceStatus('🔴 Listening... tap to stop');
      // Start timer
      setRecordingTimer(0);
      recordingTimerRef.current = setInterval(() => setRecordingTimer(t => t + 1), 1000);
    }).catch(() => {
      setVoiceStatus('❌ Microphone access denied');
      setTimeout(() => setVoiceStatus(''), 3000);
    });
  }, [onSend]);

  // Register message complete callback for voice auto-play
  useEffect(() => {
    if (!setOnMessageComplete) return;
    if (voiceMode) {
      setOnMessageComplete((msg: Message) => {
        if (!voiceModeRef.current) return;
        // Auto-play TTS, then auto-listen
        playTTSWithCallback(msg.content, () => {
          if (voiceModeRef.current) {
            // Start listening again for continuous voice loop
            startVoiceCapture();
          }
        });
      });
    } else {
      setOnMessageComplete(null);
    }
    return () => { setOnMessageComplete?.(null); };
  }, [voiceMode, setOnMessageComplete, playTTSWithCallback, startVoiceCapture]);

  // Push-to-talk: spacebar (when textarea not focused)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.code === 'Space' && !inputFocused && !e.repeat && document.activeElement?.tagName !== 'TEXTAREA' && document.activeElement?.tagName !== 'INPUT') {
        e.preventDefault();
        if (!recording) startVoiceCapture();
      }
    };
    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.code === 'Space' && recording && !inputFocused && document.activeElement?.tagName !== 'TEXTAREA' && document.activeElement?.tagName !== 'INPUT') {
        e.preventDefault();
        mediaRecorderRef.current?.stop();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    return () => { window.removeEventListener('keydown', handleKeyDown); window.removeEventListener('keyup', handleKeyUp); };
  }, [recording, inputFocused, startVoiceCapture]);

  // Stop TTS when voice mode turned off
  const toggleVoiceMode = useCallback(() => {
    setVoiceMode(prev => {
      const next = !prev;
      if (!next) {
        // Turning off — stop any playing TTS
        if (ttsAudioRef.current) {
          ttsAudioRef.current.pause();
          ttsAudioRef.current = null;
          setTtsPlaying(false);
        }
        // Stop recording if active
        if (mediaRecorderRef.current?.state === 'recording') {
          mediaRecorderRef.current.stop();
        }
      }
      return next;
    });
  }, []);

  // Poll code task status
  useEffect(() => {
    if (!codeTask || codeTask.state === 'completed' || codeTask.state === 'error') {
      if (codePollRef.current) { clearInterval(codePollRef.current); codePollRef.current = null; }
      return;
    }
    codePollRef.current = setInterval(async () => {
      try {
        const r = await fetch(`${API}/max/code-task/${codeTask.id}/status`);
        if (r.ok) {
          const data = await r.json();
          setCodeTask(data);
          if (data.state === 'completed' || data.state === 'error') {
            if (codePollRef.current) clearInterval(codePollRef.current);
          }
        }
      } catch { /* offline */ }
    }, 2000);
    return () => { if (codePollRef.current) clearInterval(codePollRef.current); };
  }, [codeTask?.id, codeTask?.state]);

  const submitCodeTask = async (prompt: string) => {
    try {
      const r = await fetch(`${API}/max/code-task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, channel: 'web_cc' }),
      });
      if (r.ok) {
        const data = await r.json();
        setCodeTask({ id: data.task_id, state: data.state, prompt, log: [], files_changed: [] });
      } else if (r.status === 403) {
        setCodeMode(false);
      }
    } catch { /* offline */ }
  };

  const handleSend = () => {
    if (!input.trim() && !attachedImage) return;
    if (codeMode) {
      submitCodeTask(input.trim());
      setInput('');
      return;
    }
    onSend(input, attachedImage);
    setInput('');
    setAttachedImage(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const handleQuickAction = (action: string) => {
    switch (action) {
      case 'quick-quote':
        if (attachedImage) {
          onSend('Create a quick quote from this photo. Measure the window, suggest treatments, and generate a quote with pricing.', attachedImage);
          setAttachedImage(null);
        } else {
          // Prompt to attach image first, or just start quote flow
          onSend('I need to create a new quote. Help me start a quick quote — ask me for the customer name, room, and window details.');
        }
        break;
      case 'briefing': onScreenChange?.('inbox'); break;
      case 'tasks': onSend('Show my tasks for today'); break;
      case 'research': onScreenChange?.('research'); break;
      case 'documents': onScreenChange?.('docs'); break;
      case 'calendar': onSend('Show my calendar for today'); break;
      default: break;
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append('file', file);
    try {
      const res = await fetch(API + '/files/upload', { method: 'POST', body: fd });
      const data = await res.json();
      if (data.status === 'success') setAttachedImage(data.filename);
    } catch { /* silent */ }
  };

  const primaryModel = maxStatus?.providers?.cloud?.find((p: any) => p.primary)?.name || streamingModel || 'MAX routing';
  const latestAssistantModel = [...messages].reverse().find(m => m.role === 'assistant' && m.model)?.model;
  const textRoutingModel = streamingModel || latestAssistantModel;
  const drawingRouterActive = textRoutingModel === 'drawing-router';
  const textRoutingFallback = !!textRoutingModel && !drawingRouterActive
    && !primaryModel.toLowerCase().includes(textRoutingModel.split('-')[0].toLowerCase());
  const textRoutingLabel = textRoutingModel
    ? drawingRouterActive
      ? 'Drawing router'
      : `Text ${textRoutingModel}${textRoutingFallback ? ' fallback' : ''}`
    : 'Text routing ready';
  const localVision = maxStatus?.local_vision;
  const localVisionLabel = localVision?.online
    ? `Vision ${localVision.primary || 'moondream'} -> ${localVision.fallback || 'llava'}`
    : 'Vision offline';
  const voiceLabel = maxStatus?.voice?.tts?.last_status === 'failed'
    ? 'Voice STT ready · TTS blocked'
    : maxStatus?.capabilities?.voice_input && maxStatus?.capabilities?.voice_output
      ? 'Voice configured'
      : maxStatus ? 'Voice partial' : 'Voice checking';
  const openClawOnline = !!maxStatus?.capabilities?.openclaw_delegation;
  const openClawQueueTotal = maxStatus?.providers?.local?.find((p: any) => p.id === 'openclaw')?.queue_stats?.total;
  const codeModeLabel = maxStatus?.code_mode?.available
    ? `Code Mode ${maxStatus.code_mode.executor || 'CodeForge'}`
    : 'Code Mode unavailable';
  const selfHealLabel = maxStatus?.self_heal?.full_autonomous_repair_verified
    ? 'Self-heal autonomous'
    : 'Self-heal guided';

  const toggleRecording = useCallback(async () => {
    if (recording) {
      mediaRecorderRef.current?.stop();
      return;
    }
    startVoiceCapture();
  }, [recording, startVoiceCapture]);

  const playTTS = async (text: string) => {
    playTTSWithCallback(text);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', background: 'var(--chat-bg)' }}>

      {/* MAX Header — compact bold line */}
      <div style={{
        padding: '6px 12px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexShrink: 0,
        borderBottom: '1px solid var(--border)',
        background: 'var(--card-bg)',
      }}>
        <div style={{ width: 44 }} />
        <span style={{
          fontSize: 14,
          fontWeight: 900,
          letterSpacing: 2,
          color: 'var(--text)',
          fontFamily: "'Inter', sans-serif",
        }}>
          MAX
        </span>
        <button
          onClick={() => setHistoryOpen(prev => !prev)}
          title="Chat History"
          style={{
            background: historyOpen ? '#d4a017' : 'none',
            border: historyOpen ? 'none' : '1px solid var(--border)',
            borderRadius: 6,
            color: historyOpen ? '#000' : 'var(--text-muted)',
            cursor: 'pointer',
            padding: 6,
            minHeight: 44, minWidth: 44,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
        >
          <Clock size={16} />
        </button>
        {voiceMode && (
          <span style={{
            fontSize: 11,
            fontWeight: 600,
            color: '#7c3aed',
            marginLeft: 10,
            display: 'inline-flex',
            alignItems: 'center',
            gap: 5,
          }}>
            <Headphones size={12} />
            {ttsPlaying ? 'Speaking...' : recording ? 'Listening...' : 'Voice Mode'}
            {' · '}
            <button
              onClick={toggleVoiceMode}
              style={{
                background: 'none', border: 'none', color: '#7c3aed',
                cursor: 'pointer', fontSize: 11, fontWeight: 600, textDecoration: 'underline',
                padding: 0,
              }}
            >
              Stop
            </button>
          </span>
        )}
      </div>

      {maxStatus && (
        <div
          data-testid="max-orchestration-status"
          style={{
            flexShrink: 0,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '7px 12px',
            borderBottom: '1px solid var(--border)',
            background: '#faf9f7',
            overflowX: 'auto',
          }}
        >
          <span style={{ fontSize: 11, fontWeight: 800, color: 'var(--text)', whiteSpace: 'nowrap' }}>
            Founder {'>'} MAX
          </span>
          <StatusChip label={primaryModel} tone="dark" />
          <StatusChip label={textRoutingLabel} tone={textRoutingFallback ? 'warn' : 'ok'} />
          <StatusChip label={localVisionLabel} tone={localVision?.online ? 'ok' : 'warn'} />
          <StatusChip label={voiceLabel} tone={maxStatus?.voice?.tts?.last_status === 'failed' ? 'warn' : maxStatus.capabilities?.voice_input ? 'ok' : 'warn'} />
          <StatusChip label={`OpenClaw ${openClawOnline ? 'online' : 'offline'}${Number.isFinite(openClawQueueTotal) ? ` · ${openClawQueueTotal} tasks` : ''}`} tone={openClawOnline ? 'ok' : 'warn'} />
          <StatusChip label={codeModeLabel} tone={maxStatus?.code_mode?.available ? 'ok' : 'warn'} />
          <StatusChip label={selfHealLabel} tone="warn" />
          <button
            data-testid="max-desks-status-button"
            onClick={() => onScreenChange?.('desks')}
            style={{
              border: '1px solid #d8d3cb',
              background: '#fff',
              borderRadius: 8,
              padding: '3px 8px',
              fontSize: 11,
              fontWeight: 700,
              color: 'var(--text)',
              whiteSpace: 'nowrap',
              cursor: 'pointer',
            }}
          >
            {maxStatus.desks?.count || 0} desks subordinate
          </button>
          <button
            data-testid="max-memory-bank-button"
            onClick={() => onScreenChange?.('memory-bank')}
            style={{
              border: '1px solid #d8d3cb',
              background: '#fff',
              borderRadius: 8,
              padding: '3px 8px',
              fontSize: 11,
              fontWeight: 700,
              color: 'var(--text)',
              whiteSpace: 'nowrap',
              cursor: 'pointer',
            }}
          >
            Memory Bank
          </button>
          <button
            data-testid="max-relistapp-button"
            onClick={() => onProductNavigate?.('relist', 'dashboard')}
            style={{
              border: '1px solid #d8d3cb',
              background: '#fff',
              borderRadius: 8,
              padding: '3px 8px',
              fontSize: 11,
              fontWeight: 700,
              color: 'var(--text)',
              whiteSpace: 'nowrap',
              cursor: 'pointer',
            }}
          >
            RelistApp
          </button>
          <a
            data-testid="max-public-page-link"
            href="/max"
            style={{
              border: '1px solid #d8d3cb',
              background: '#fff',
              borderRadius: 8,
              padding: '3px 8px',
              fontSize: 11,
              fontWeight: 700,
              color: 'var(--text)',
              whiteSpace: 'nowrap',
              textDecoration: 'none',
            }}
          >
            Public MAX
          </a>
          <StatusChip label="Upload image/doc" tone="ok" />
        </div>
      )}

      <ContinuityPanel />

      {/* Messages */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '8px 10px',
      }}
      className="sm:!px-9 sm:!py-6 pb-10 md:!pb-6">
        {messages.map((msg, i) => (
          <div key={msg.id || i} style={{
            marginBottom: 16,
            maxWidth: '90%',
            marginLeft: msg.role === 'user' ? 'auto' : undefined,
            marginRight: msg.role === 'user' ? 0 : 'auto',
          }}>
            {(() => {
              const { cleanContent, toolCalls } = msg.role === 'assistant'
                ? parseToolBlocks(msg.content)
                : { cleanContent: msg.content, toolCalls: [] };
              return (
                <>
                  {cleanContent && (
                    <div style={{
                      padding: '14px 18px',
                      fontSize: 14,
                      lineHeight: 1.65,
                      whiteSpace: 'pre-wrap',
                      ...(msg.role === 'user' ? {
                        background: 'var(--text)',
                        color: '#fff',
                        borderRadius: '14px 14px 6px 14px',
                      } : {
                        background: '#fff',
                        color: 'var(--text)',
                        border: '1px solid var(--border)',
                        borderRadius: '14px 14px 14px 6px',
                      }),
                    }}>
                      {renderContent(cleanContent, onScreenChange)}
                    </div>
                  )}
                  {/* Inline tool call cards (from message content) */}
                  {toolCalls.map((tc, k) => {
                    const isQuoteTool = tc.tool === 'create_quick_quote' || tc.tool === 'photo_to_quote';
                    if (isQuoteTool) {
                      return (
                        <div key={`tc-${k}`} style={{
                          marginTop: 10, padding: '14px 18px',
                          borderRadius: 14, border: '1.5px solid #f0e6c0',
                          background: '#fffdf7',
                        }}>
                          <div style={{ fontSize: 12, fontWeight: 700, color: '#b8960c', marginBottom: 4 }}>
                            Generating Quote...
                          </div>
                          <div style={{ fontSize: 13, color: '#555' }}>
                            {tc.customer_name && <span><strong>Customer:</strong> {tc.customer_name}</span>}
                            {tc.rooms?.[0]?.name && <span> · <strong>Room:</strong> {tc.rooms[0].name}</span>}
                            {tc.rooms?.[0]?.windows?.length && <span> · {tc.rooms[0].windows.length} window{tc.rooms[0].windows.length > 1 ? 's' : ''}</span>}
                          </div>
                          {tc.rooms?.[0]?.windows && (
                            <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                              {tc.rooms[0].windows.slice(0, 6).map((w: any, wi: number) => (
                                <span key={wi} style={{
                                  fontSize: 10, padding: '3px 8px', borderRadius: 6,
                                  background: '#fdf8eb', border: '1px solid #f0e6c0', color: '#96750a',
                                }}>
                                  {w.name}: {w.width}&quot;×{w.height}&quot; · {w.treatmentType}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    }
                    // Generic tool call display
                    return (
                      <div key={`tc-${k}`} style={{
                        marginTop: 10, padding: '12px 16px', borderRadius: 14,
                        border: '1px solid var(--border)', background: '#faf9f7', fontSize: 12,
                      }}>
                        <strong style={{ color: '#555' }}>Tool: {tc.tool}</strong>
                      </div>
                    );
                  })}
                </>
              );
            })()}
            <div style={{
              fontSize: 10,
              color: 'var(--muted)',
              marginTop: 4,
              fontFamily: "'Inter', monospace",
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              ...(msg.role === 'user' ? { justifyContent: 'flex-end' } : {}),
            }} suppressHydrationWarning>
              {msg.timestamp}
              {msg.model && <span style={{ opacity: 0.7 }}>{msg.model}</span>}
              {msg.role === 'assistant' && msg.quality && (
                <span
                  title={`${msg.quality.label}${msg.quality.warnings?.length ? '\n' + msg.quality.warnings.join('\n') : ''}`}
                  style={{
                    fontSize: 10,
                    padding: '1px 6px',
                    borderRadius: 6,
                    background: msg.quality.color + '18',
                    color: msg.quality.color,
                    fontWeight: 600,
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {msg.quality.icon} {msg.quality.label}
                </span>
              )}
              {msg.role === 'assistant' && msg.content.length > 20 && (
                <button
                  onClick={() => playTTS(msg.content)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--muted)',
                    cursor: 'pointer',
                    padding: 2,
                    display: 'inline-flex',
                    alignItems: 'center',
                    transition: 'color 0.15s',
                  }}
                  onMouseEnter={e => (e.currentTarget.style.color = 'var(--gold)')}
                  onMouseLeave={e => (e.currentTarget.style.color = 'var(--muted)')}
                >
                  <Volume2 size={12} />
                </button>
              )}
            </div>
            {/* Tool results from SSE stream */}
            {msg.toolResults?.map((tr, j) => {
              if ((tr.tool === 'create_quick_quote' || tr.tool === 'photo_to_quote') && tr.success && tr.result) {
                return (
                  <QuoteCard
                    key={j}
                    result={tr.result}
                    onScreenChange={onScreenChange}
                    onSend={onSend}
                  />
                );
              }
              if (tr.tool === 'sketch_to_drawing' && tr.success && tr.result?.svg) {
                return <InlineDrawing key={j} result={tr.result} />;
              }
              return null;
            })}
          </div>
        ))}

        {/* Code Task progress card */}
        {codeTask && codeTask.state !== 'dismissed' && (
          <div style={{
            marginBottom: 16,
            maxWidth: '90%',
            borderRadius: 14,
            border: codeTask.state === 'error' ? '1.5px solid var(--red)' : '1.5px solid #b8960c',
            background: codeTask.state === 'error' ? '#fef2f2' : '#fffdf7',
            overflow: 'hidden',
          }}>
            {/* Header */}
            <div style={{
              padding: '10px 16px',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              borderBottom: '1px solid #f0e6c0',
              background: codeTask.state === 'error' ? '#fef2f2' : '#fdf8eb',
            }}>
              <Terminal size={14} style={{ color: codeTask.state === 'error' ? '#dc2626' : '#b8960c' }} />
              <span style={{ fontSize: 12, fontWeight: 700, color: codeTask.state === 'error' ? '#dc2626' : '#b8960c', flex: 1 }}>
                MAX Code Mode — CodeForge / Atlas — {codeTask.state === 'queued' ? 'Queued' : codeTask.state === 'running' ? 'Working...' : codeTask.state === 'completed' ? 'Verified / Done' : 'Error'}
              </span>
              {(codeTask.state === 'running' || codeTask.state === 'queued') && (
                <Loader2 size={14} style={{ color: '#b8960c', animation: 'spin 1s linear infinite' }} />
              )}
              {(codeTask.state === 'completed' || codeTask.state === 'error') && (
                <button onClick={() => setCodeTask({ ...codeTask, state: 'dismissed' })} style={{
                  background: 'none', border: 'none', cursor: 'pointer', fontSize: 10, fontWeight: 600, color: '#999',
                }}>Dismiss</button>
              )}
            </div>

            {/* Prompt */}
            <div style={{ padding: '8px 16px', fontSize: 11, color: '#888', borderBottom: '1px solid #f5f0e0' }}>
              {codeTask.prompt?.slice(0, 120)}{codeTask.prompt?.length > 120 ? '...' : ''}
            </div>

            {/* Live log */}
            {codeTask.log?.length > 0 && (
              <div style={{ padding: '8px 16px', maxHeight: 120, overflowY: 'auto' }}>
                {codeTask.log.slice(-5).map((l: any, i: number) => (
                  <div key={i} style={{ fontSize: 10, color: '#666', display: 'flex', gap: 6, marginBottom: 3 }}>
                    <span style={{ color: '#b8960c', fontWeight: 700, textTransform: 'uppercase', fontSize: 9, minWidth: 50 }}>{l.action}</span>
                    <span>{l.detail}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Result */}
            {codeTask.state === 'completed' && codeTask.result && (
              <div style={{ padding: '10px 16px', fontSize: 13, color: '#333', lineHeight: 1.6, whiteSpace: 'pre-wrap', maxHeight: 300, overflowY: 'auto', borderTop: '1px solid #f0e6c0' }}>
                {codeTask.result}
              </div>
            )}

            {/* Files changed */}
            {codeTask.state === 'completed' && codeTask.files_changed?.length > 0 && (
              <div style={{ padding: '8px 16px', borderTop: '1px solid #f0e6c0', display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {codeTask.files_changed.map((f: string, i: number) => (
                  <span key={i} style={{ fontSize: 9, padding: '2px 8px', borderRadius: 6, background: '#f0fdf4', border: '1px solid #bbf7d0', color: '#16a34a', fontFamily: 'monospace' }}>{f}</span>
                ))}
              </div>
            )}

            {/* Error */}
            {codeTask.state === 'error' && (
              <div style={{ padding: '10px 16px' }}>
                <div style={{ fontSize: 12, color: '#dc2626', marginBottom: 6 }}>{codeTask.error}</div>
                <button
                  onClick={() => { setCodeTask(null); submitCodeTask(codeTask.prompt); }}
                  style={{ fontSize: 11, fontWeight: 600, color: '#b8960c', background: 'none', border: '1px solid #b8960c', borderRadius: 8, padding: '4px 12px', cursor: 'pointer' }}
                >
                  Retry
                </button>
              </div>
            )}
          </div>
        )}

        {/* Streaming indicator */}
        {isStreaming && (
          <div style={{ marginBottom: 16, maxWidth: '75%' }}>
            <div style={{
              padding: '14px 18px',
              fontSize: 14,
              lineHeight: 1.65,
              whiteSpace: 'pre-wrap',
              background: '#fff',
              color: 'var(--text)',
              border: '1px solid var(--border)',
              borderRadius: '14px 14px 14px 6px',
            }}>
              {streamingContent || '...'}
            </div>
            <div style={{
              fontSize: 10,
              color: 'var(--muted)',
              marginTop: 4,
              fontFamily: "'Inter', monospace",
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}>
              {streamingModel && <span>{streamingModel}</span>}
              <span style={{ opacity: 0.6 }}>typing...</span>
              <button
                onClick={onStop}
                style={{
                  marginLeft: 4,
                  color: 'var(--red)',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: 10,
                  fontWeight: 600,
                  padding: 0,
                }}
              >
                Stop
              </button>
            </div>
          </div>
        )}
        <div ref={msgsEndRef} />
      </div>

      {/* Input area */}
      <div className="px-3 pt-2 pb-1 md:px-3 md:pt-3 md:pb-2" style={{
        flexShrink: 0,
        background: 'var(--chat-bg)',
      }}>
        <input ref={fileInputRef} type="file" style={{ display: 'none' }} accept="image/*,.pdf,.txt,.md,.csv,.json" onChange={handleFileUpload} />

        {/* Attached file indicator */}
        {attachedImage && (
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            padding: '6px 12px',
            background: 'var(--gold-light)',
            border: '1px solid var(--gold)',
            borderRadius: 10,
            fontSize: 11,
            color: 'var(--gold)',
            fontWeight: 500,
            marginBottom: 10,
          }}>
            <Paperclip size={12} />
            {attachedImage}
            <button
              onClick={() => setAttachedImage(null)}
              style={{
                marginLeft: 4,
                fontWeight: 700,
                cursor: 'pointer',
                background: 'none',
                border: 'none',
                color: 'var(--gold)',
                fontSize: 13,
                lineHeight: 1,
              }}
            >
              x
            </button>
          </div>
        )}

        {/* Voice Mode banner */}
        {voiceMode && (
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
            padding: '8px 16px', borderRadius: 10, marginBottom: 8,
            background: '#1a0a2e', border: '1.5px solid #7c3aed',
          }}>
            <Headphones size={14} style={{ color: '#7c3aed' }} />
            <span style={{ color: '#c4b5fd', fontSize: 12, fontWeight: 600 }}>
              Voice Mode ON {ttsPlaying ? '— Speaking...' : recording ? '— Listening...' : '— Ready'}
            </span>
            <button onClick={toggleVoiceMode} style={{
              background: 'none', border: 'none', color: '#7c3aed', cursor: 'pointer',
              fontSize: 12, fontWeight: 600, textDecoration: 'underline', marginLeft: 8,
            }}>Turn Off</button>
          </div>
        )}

        {/* Status bar — voice status + AI status */}
        {(voiceStatus || aiStatus) && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '6px 14px', marginBottom: 6,
            fontSize: 13, fontWeight: 500, color: 'var(--dim)',
            background: 'var(--card-bg)', borderRadius: 8,
            border: '1px solid var(--border)',
            animation: 'pulse 2s infinite',
          }}>
            {voiceStatus && <span>{voiceStatus}{recording ? ` (${recordingTimer}s)` : ''}</span>}
            {voiceStatus && aiStatus && <span style={{ color: 'var(--border)' }}>|</span>}
            {aiStatus && <span>{aiStatus}</span>}
          </div>
        )}

        {/* Input row: [Attach] [More] [Input] [Mic] [Send] */}
        <div style={{
          display: 'flex',
          alignItems: 'flex-end',
          gap: 8,
          position: 'relative',
        }}>
          {/* Attach button */}
          <button
            onClick={() => fileInputRef.current?.click()}
            style={{
              width: 44, height: 44, borderRadius: 12,
              background: 'var(--card-bg)', border: '1px solid var(--border)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer', color: 'var(--dim)', flexShrink: 0, transition: 'all 0.2s',
            }}
          >
            <Paperclip size={17} />
          </button>

          {/* More button — opens quick actions popup */}
          <button
            onClick={() => setShowMoreActions(!showMoreActions)}
            style={{
              width: 44, height: 44, borderRadius: 12,
              background: showMoreActions ? '#fdf8eb' : 'var(--card-bg)',
              border: showMoreActions ? '1.5px solid #b8960c' : '1px solid var(--border)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer', color: showMoreActions ? '#b8960c' : 'var(--dim)',
              flexShrink: 0, transition: 'all 0.2s',
            }}
            title="More actions"
          >
            {showMoreActions ? <X size={17} /> : <MoreHorizontal size={17} />}
          </button>

          {/* Text input */}
          <div style={{
            flex: 1,
            background: codeMode ? '#fdf8eb' : voiceMode ? '#f5f0ff' : '#fff',
            border: `1.5px solid ${codeMode ? '#b8960c' : voiceMode ? '#7c3aed' : inputFocused ? 'var(--gold)' : 'var(--border)'}`,
            borderRadius: 14,
            transition: 'border-color 0.2s, box-shadow 0.2s, background 0.2s',
            boxShadow: codeMode ? '0 0 0 3px rgba(184,150,12,0.12)' : inputFocused ? '0 0 0 3px rgba(184,150,12,0.1)' : 'none',
            display: 'flex',
            alignItems: 'flex-end',
          }}>
            <textarea
              ref={textareaRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              onFocus={() => setInputFocused(true)}
              onBlur={() => setInputFocused(false)}
              placeholder={codeMode ? 'Code Mode — describe what to build or fix...' : 'Message MAX...'}
              rows={1}
              style={{
                flex: 1, padding: '13px 18px', border: 'none', outline: 'none',
                fontSize: 14, fontFamily: "'Inter', sans-serif", resize: 'none',
                minHeight: 44, maxHeight: 120, background: 'transparent',
                color: 'var(--text)', lineHeight: 1.5,
              }}
            />
          </div>

          {/* Mic button — primary, next to send */}
          <button
            onClick={toggleRecording}
            title={recording ? 'Tap to stop recording' : 'Tap to record voice'}
            style={{
              width: 44, height: 44, borderRadius: 12,
              background: recording ? '#ef4444' : 'var(--card-bg)',
              border: `1.5px solid ${recording ? '#ef4444' : 'var(--border)'}`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer', color: recording ? '#fff' : 'var(--dim)',
              flexShrink: 0, transition: 'all 0.2s',
              animation: recording ? 'pulse 1.5s infinite' : 'none',
              position: 'relative',
            }}
          >
            {recording ? <MicOff size={18} /> : <Mic size={18} />}
          </button>

          {/* Send button */}
          <button
            onClick={handleSend}
            disabled={isStreaming}
            style={{
              width: 44, height: 44, borderRadius: 12,
              background: 'var(--text)', border: 'none',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: isStreaming ? 'not-allowed' : 'pointer',
              color: '#fff', flexShrink: 0,
              opacity: isStreaming ? 0.5 : 1, transition: 'all 0.2s',
            }}
            onMouseEnter={e => { if (!isStreaming) e.currentTarget.style.background = 'var(--gold)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'var(--text)'; }}
          >
            <ArrowUp size={20} />
          </button>
        </div>

        {/* Secondary controls row: Voice Mode + Code Mode */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          gap: 16, marginTop: 8, paddingBottom: 2,
        }}>
          <button
            onClick={toggleVoiceMode}
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              fontSize: 12, fontWeight: 600,
              color: voiceMode ? '#7c3aed' : 'var(--dim)',
              display: 'flex', alignItems: 'center', gap: 5,
            }}
          >
            <Headphones size={13} />
            {voiceMode ? 'Voice Mode ON' : 'Voice Mode'}
          </button>
          <span style={{ color: 'var(--border)', fontSize: 10 }}>·</span>
          <button
            onClick={() => {
              setCodeMode(!codeMode);
            }}
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              fontSize: 12, fontWeight: 600,
              color: codeMode ? '#b8960c' : 'var(--dim)',
              display: 'flex', alignItems: 'center', gap: 5,
            }}
          >
            <Terminal size={13} />
            {codeMode ? 'MAX Code Mode ON' : 'Code Mode'}
          </button>
        </div>

        {/* More actions popup — fixed position to escape overflow:hidden */}
        {showMoreActions && (
          <>
            <div style={{ position: 'fixed', inset: 0, zIndex: 9990 }} onClick={() => setShowMoreActions(false)} />
            <div style={{
              position: 'fixed', bottom: 120, left: 20, right: 20, maxWidth: 400,
              background: '#fff', border: '1px solid var(--border)', borderRadius: 14,
              boxShadow: '0 8px 32px rgba(0,0,0,0.15)', padding: 10, zIndex: 9999,
              display: 'flex', flexWrap: 'wrap', gap: 6,
            }}>
              {QUICK_ACTIONS.map(qa => {
                const Icon = qa.icon;
                const isHighlight = (qa as any).highlight;
                return (
                  <button
                    key={qa.action}
                    onClick={() => { handleQuickAction(qa.action); setShowMoreActions(false); }}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 7,
                      padding: '10px 16px',
                      background: isHighlight ? '#fdf8eb' : '#faf9f7',
                      border: isHighlight ? '1.5px solid #b8960c' : '1px solid #ece8e0',
                      borderRadius: 10, fontSize: 13,
                      fontWeight: isHighlight ? 700 : 500,
                      color: isHighlight ? '#b8960c' : '#555',
                      cursor: 'pointer', whiteSpace: 'nowrap',
                      transition: 'all 0.15s',
                    }}
                    onMouseEnter={e => { e.currentTarget.style.background = '#fdf8eb'; e.currentTarget.style.borderColor = '#b8960c'; }}
                    onMouseLeave={e => { e.currentTarget.style.background = isHighlight ? '#fdf8eb' : '#faf9f7'; e.currentTarget.style.borderColor = isHighlight ? '#b8960c' : '#ece8e0'; }}
                  >
                    <Icon size={15} />
                    {qa.label}
                  </button>
                );
              })}
            </div>
          </>
        )}
      </div>

      {/* PIN Modal removed — CC is always founder, Code Mode activates directly */}

      {/* Animations */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.7; }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>

      {/* Chat History Panel */}
      <ChatHistoryPanel
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        onLoadChat={(chatId) => { if (onLoadChat) onLoadChat(chatId); }}
        onNewChat={() => { if (onNewChat) onNewChat(); }}
      />
    </div>
  );
}

function StatusChip({ label, tone }: { label: string; tone: 'ok' | 'warn' | 'dark' }) {
  const styles = tone === 'ok'
    ? { background: '#f0fdf4', border: '#bbf7d0', color: '#15803d' }
    : tone === 'warn'
      ? { background: '#fffbeb', border: '#fde68a', color: '#b45309' }
      : { background: '#1a1a1a', border: '#1a1a1a', color: '#fff' };

  return (
    <span
      style={{
        border: `1px solid ${styles.border}`,
        background: styles.background,
        color: styles.color,
        borderRadius: 8,
        padding: '3px 8px',
        fontSize: 11,
        fontWeight: 700,
        whiteSpace: 'nowrap',
      }}
    >
      {label}
    </span>
  );
}

function renderContent(content: string, onScreenChange?: (s: string) => void) {
  return content.split('\n').map((line, i) => {
    // Bold
    let processed = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Italic
    processed = processed.replace(/\*(.*?)\*/g, '<em>$1</em>');
    // Detect QuoteBuilder / quote references and make them clickable
    const hasQuoteRef = /QuoteBuilder|quote.*interface/i.test(processed);
    if (hasQuoteRef && onScreenChange) {
      processed = processed.replace(
        /(QuoteBuilder\s*interface|QuoteBuilder)/gi,
        '<a class="quote-link" style="color:#b8960c;font-weight:600;cursor:pointer;text-decoration:underline;text-underline-offset:2px">$1</a>'
      );
    }
    // Detect quote numbers like EST-2026-027 and make clickable
    processed = processed.replace(
      /(EST-\d{4}-\d{3})/g,
      '<a class="quote-link" style="color:#b8960c;font-weight:600;cursor:pointer;text-decoration:underline;text-underline-offset:2px">$1</a>'
    );
    const html = processed + (i < content.split('\n').length - 1 ? '<br/>' : '');
    return (
      <span
        key={i}
        dangerouslySetInnerHTML={{ __html: html }}
        onClick={(e) => {
          const target = e.target as HTMLElement;
          if (target.classList.contains('quote-link')) {
            onScreenChange?.('quote');
          }
        }}
      />
    );
  });
}
