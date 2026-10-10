'use client';
import MaxDocCard from '../docs/MaxDocCard';
import MaxRecordCard from '../docs/MaxRecordCard';
import { useState, useRef, useEffect, useCallback } from 'react';
import { Paperclip, Mic, MicOff, ArrowUp, Volume2, VolumeX, Mail, CheckSquare, Search, FileText, Calendar, ClipboardList, Loader2, Terminal, Headphones, Clock, MoreHorizontal, X, Copy, Check, ExternalLink } from 'lucide-react';
import ChatHistoryPanel from '../ChatHistoryPanel';
import { Message } from '../../lib/types';
import { splitForView } from '../../hooks/chatQueue';
import { API } from '../../lib/api';
import QuoteCard from '../business/quotes/QuoteCard';
import InlineDrawing from '../InlineDrawing';
import ContinuityPanel from '../ContinuityPanel';
import ViewPdfControl from '../ViewPdfControl';
import ChatChartBlock from '../ChatChartBlock';
import ChatMarkdown from '../chat/ChatMarkdown';
import '../chat/chat.css';
import { chiefEHref } from '../../lib/chiefE';
import { copyTextToClipboard, displayModelLabel, splitChatContent } from '../../lib/chatContent';
import FounderPinCard from '../chat/FounderPinCard';
import { useTranslation } from '../../lib/i18n';
import { composerLooksLikePin } from '../../lib/founderPin';
import { useJob } from '../../hooks/useJob';
import JobFolderModal from '../jobs/JobFolderModal';
import { Briefcase, FolderOpen } from 'lucide-react';
import {
  HOLD_ARM_MS,
  HOLD_LONGER_HINT,
  TRANSCRIBE_FAILED_HINT,
  clipTooShort,
  filenameForMime,
  pointerDownAction,
  recorderFormat,
  shouldStopOnPointerUp,
  sttLanguage,
  transcriptIsFailure,
} from '../../lib/voiceCapture';

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
  streamingSteps?: string[];
  streamingModel: string;
  onSend: (msg: string, imageFilename?: string | null) => void;
  onStop: () => void;
  onScreenChange?: (screen: string) => void;
  onProductNavigate?: (product: string, screen?: string, section?: string) => void;
  setOnMessageComplete?: (cb: ((msg: Message) => void) | null) => void;
  onLoadChat?: (chatId: string) => void;
  onNewChat?: () => void;
  onSubmitPin?: (messageId: string, resumeId: string, pin: string) => Promise<void> | void;
  onCancelPin?: (messageId: string, resumeId: string) => void;
  /** Remove a message that is still waiting in the queue (2026-10-08). */
  onCancelQueued?: (messageId: string) => void;
}

export default function ChatScreen({ messages, isStreaming, streamingContent, streamingSteps = [], streamingModel, onSend, onStop, onScreenChange, onProductNavigate, setOnMessageComplete, onLoadChat, onNewChat, onSubmitPin, onCancelPin, onCancelQueued }: Props) {
  // 2026-10-08 queueing: messages sent while Max answers show under the live reply, marked queued.
  const { settled: settledMessages, queued: queuedMessages } = splitForView(messages);
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
  const [voiceDraft, setVoiceDraft] = useState<any>(null);
  const [showMoreActions, setShowMoreActions] = useState(false);
  const [quickQuoteNotice, setQuickQuoteNotice] = useState<string | null>(null);
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const msgsEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const codePollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const voiceModeRef = useRef(false);
  const recordingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const ttsAudioRef = useRef<HTMLAudioElement | null>(null);
  const voiceSessionRef = useRef<string>('');
  const voiceDestinationRef = useRef<'chat' | 'document'>('document');
  const voiceReleaseRef = useRef(false);
  const recordingRef = useRef(false);
  const touchMicRef = useRef(false);
  const holdArmedRef = useRef(false);
  const holdArmTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const recordStartedAtRef = useRef(0);
  const captureEpochRef = useRef(0);
  const micPointerRef = useRef<number | null>(null);
  const spaceCaptureRef = useRef(false);
  const [micToast, setMicToast] = useState<string | null>(null);
  const micToastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { locale } = useTranslation();
  const localeRef = useRef(locale);
  useEffect(() => { localeRef.current = locale; }, [locale]);

  const { activeJob, clearJob } = useJob();
  const [chatFolderOpen, setChatFolderOpen] = useState(false);
  useEffect(() => { recordingRef.current = recording; }, [recording]);
  useEffect(() => {
    const coarse = window.matchMedia('(pointer: coarse)').matches;
    touchMicRef.current = coarse || navigator.maxTouchPoints > 0;
  }, []);

  const showMicToast = useCallback((message: string) => {
    setMicToast(message);
    if (micToastTimerRef.current) clearTimeout(micToastTimerRef.current);
    micToastTimerRef.current = setTimeout(() => setMicToast(null), 3500);
  }, []);

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

  const submitVoiceDocument = useCallback(async (transcript: string) => {
    setVoiceStatus('📋 Building draft...');
    try {
      const res = await fetch(`${API}/voice/documents`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transcript,
          session_id: voiceSessionRef.current || '',
          channel: 'cc',
          edition: 'workroom',
        }),
      });
      const data = await res.json();
      if (data.session_id) voiceSessionRef.current = data.session_id;
      if (data.handled) {
        setVoiceDraft(data);
        setVoiceStatus(data.sent ? '' : 'Draft only — nothing sent');
      } else if (data.transcript || transcript) {
        const text = data.transcript || transcript;
        setInput(prev => prev + (prev ? ' ' : '') + text);
        setVoiceStatus('✅ Review, then tap Send');
        setTimeout(() => setVoiceStatus(prev => prev === '✅ Review, then tap Send' ? '' : prev), 5000);
      } else {
        setVoiceStatus('');
      }
    } catch (err) {
      console.warn('Voice document draft failed:', err);
      setInput(prev => prev + (prev ? ' ' : '') + transcript);
      setVoiceStatus('❌ Draft failed — transcript kept in the box');
      setTimeout(() => setVoiceStatus(''), 4000);
    }
  }, []);

  const finishVoiceDraft = useCallback(() => {
    submitVoiceDocument('done');
  }, [submitVoiceDocument]);

  const chooseVoiceOption = useCallback(async (optionId: string, choiceId: string) => {
    const sessionId = voiceSessionRef.current;
    if (!sessionId) return;
    setVoiceStatus('📋 Updating draft...');
    try {
      const res = await fetch(`${API}/voice/documents/${sessionId}/choose`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ option_id: optionId, choice_id: choiceId }),
      });
      const data = await res.json();
      setVoiceDraft(data);
      setVoiceStatus('Draft only — nothing sent');
    } catch {
      setVoiceStatus('❌ Could not apply that choice');
    }
  }, []);

  const clearHoldArm = useCallback(() => {
    if (holdArmTimerRef.current) {
      clearTimeout(holdArmTimerRef.current);
      holdArmTimerRef.current = null;
    }
  }, []);

  const stopVoiceCapture = useCallback(() => {
    clearHoldArm();
    const live = mediaRecorderRef.current?.state === 'recording';
    if (live) {
      mediaRecorderRef.current?.stop();
      return;
    }
    captureEpochRef.current += 1;
    const elapsed = recordStartedAtRef.current ? Date.now() - recordStartedAtRef.current : 0;
    if (!recordStartedAtRef.current || clipTooShort(elapsed)) {
      showMicToast(HOLD_LONGER_HINT);
    }
    recordingRef.current = false;
    setRecording(false);
  }, [clearHoldArm, showMicToast]);

  // Tap-to-start / tap-to-stop on touch. Hold-to-talk stays available
  // once the press lasts past HOLD_ARM_MS, and for a mouse or spacebar.
  const startVoiceCapture = useCallback((destination: 'chat' | 'document' = 'document') => {
    if (mediaRecorderRef.current?.state === 'recording') return;
    voiceDestinationRef.current = destination;
    const epoch = captureEpochRef.current;
    navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
      if (epoch !== captureEpochRef.current) {
        stream.getTracks().forEach(t => t.stop());
        return;
      }
      const format = recorderFormat(
        navigator.userAgent,
        (mime) => typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(mime),
      );
      let recorder: MediaRecorder;
      try {
        recorder = new MediaRecorder(stream, { mimeType: format.mimeType });
      } catch {
        try {
          recorder = new MediaRecorder(stream, { mimeType: 'audio/mp4' });
        } catch {
          recorder = new MediaRecorder(stream);
        }
      }
      const chunks: Blob[] = [];
      recorder.ondataavailable = e => { if (e.data && e.data.size) chunks.push(e.data); };
      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        if (recordingTimerRef.current) { clearInterval(recordingTimerRef.current); recordingTimerRef.current = null; }
        setRecordingTimer(0);
        recordingRef.current = false;
        setRecording(false);

        const elapsed = recordStartedAtRef.current ? Date.now() - recordStartedAtRef.current : 0;
        const mimeType = recorder.mimeType || format.mimeType;
        const blob = new Blob(chunks, { type: mimeType });
        if (clipTooShort(elapsed) || blob.size < 256) {
          showMicToast(HOLD_LONGER_HINT);
          setVoiceStatus('');
          return;
        }

        const fd = new FormData();
        fd.append('audio', blob, filenameForMime(mimeType));
        const lang = sttLanguage(localeRef.current);
        const url = lang
          ? `${API}/voice/transcribe?language=${encodeURIComponent(lang)}`
          : `${API}/voice/transcribe`;
        try {
          setVoiceStatus('🔄 Transcribing...');
          const res = await fetch(url, { method: 'POST', body: fd });
          const data = await res.json().catch(() => ({}));
          if (!res.ok || transcriptIsFailure(data.text)) {
            showMicToast(TRANSCRIBE_FAILED_HINT);
            setVoiceStatus('');
            return;
          }
          if (data.text && voiceDestinationRef.current === 'document') {
            submitVoiceDocument(data.text);
          } else if (data.text && voiceModeRef.current) {
            onSend(data.text);
            setVoiceStatus('');
          } else if (data.text) {
            setInput(prev => prev + (prev ? ' ' : '') + data.text);
            setVoiceStatus('✅ Review, then tap Send');
            textareaRef.current?.focus();
            setTimeout(() => setVoiceStatus(prev => prev === '✅ Review, then tap Send' ? '' : prev), 5000);
          } else {
            setVoiceStatus('');
          }
        } catch (err) {
          console.warn('STT transcription failed:', err);
          showMicToast(TRANSCRIBE_FAILED_HINT);
          setVoiceStatus('');
        }
      };
      try {
        recorder.start(250);
      } catch {
        recorder.start();
      }
      recordStartedAtRef.current = Date.now();
      mediaRecorderRef.current = recorder;
      recordingRef.current = true;
      setRecording(true);
      const touchTap = touchMicRef.current && !holdArmedRef.current;
      if (voiceReleaseRef.current && !touchTap) {
        recorder.stop();
        return;
      }
      setVoiceStatus(touchMicRef.current && !holdArmedRef.current
        ? '🔴 Tap to stop'
        : '🔴 Release to transcribe');
      setRecordingTimer(0);
      recordingTimerRef.current = setInterval(() => setRecordingTimer(t => t + 1), 1000);
    }).catch(() => {
      recordingRef.current = false;
      setRecording(false);
      showMicToast('Microphone access denied');
    });
  }, [onSend, showMicToast, submitVoiceDocument]);

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
            startVoiceCapture('chat');
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
        if (!recordingRef.current && mediaRecorderRef.current?.state !== 'recording') {
          spaceCaptureRef.current = true;
          voiceReleaseRef.current = false;
          holdArmedRef.current = true;
          startVoiceCapture(voiceModeRef.current ? 'chat' : 'document');
        }
      }
    };
    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.code !== 'Space' || !spaceCaptureRef.current) return;
      if (document.activeElement?.tagName === 'TEXTAREA' || document.activeElement?.tagName === 'INPUT') return;
      e.preventDefault();
      spaceCaptureRef.current = false;
      voiceReleaseRef.current = true;
      if (mediaRecorderRef.current?.state === 'recording') mediaRecorderRef.current.stop();
      else stopVoiceCapture();
    };
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    return () => { window.removeEventListener('keydown', handleKeyDown); window.removeEventListener('keyup', handleKeyUp); };
  }, [inputFocused, startVoiceCapture, stopVoiceCapture]);

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
    const pinCardOpen = messages.some(msg =>
      msg.pinPrompts?.some(prompt => prompt.status === 'needed' || prompt.status === 'error' || prompt.status === 'submitting'),
    );
    if (pinCardOpen && composerLooksLikePin(input)) {
      setInput('');
      showMicToast('Use the PIN card. It is not sent in the chat.');
      return;
    }
    if (codeMode) {
      submitCodeTask(input.trim());
      setInput('');
      return;
    }
    onSend(input, attachedImage);
    setInput('');
    setAttachedImage(null);
  };

  const handleCopyMessage = useCallback(async (msg: Message) => {
    const ok = await copyTextToClipboard(msg.content);
    if (ok) {
      setCopiedMessageId(msg.id);
      window.setTimeout(() => setCopiedMessageId(prev => (prev === msg.id ? null : prev)), 2000);
    }
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const handleQuickAction = (action: string) => {
    switch (action) {
      case 'quick-quote':
        // Open the Workroom quote flow. Do not send a chat prompt — that
        // path reports "Connection error" whenever the assistant backend
        // is offline, and it never reached the quote builder.
        setShowMoreActions(false);
        if (onProductNavigate) {
          onProductNavigate('workroom', 'dashboard', 'quick-quote');
        } else {
          setQuickQuoteNotice('Quick Quote is not wired from this chat. Open Empire Workroom → Quotes.');
        }
        break;
      case 'briefing': onScreenChange?.('inbox'); break;
      case 'tasks': onSend('Show my tasks for today'); break;
      case 'research': onScreenChange?.('research'); break;
      case 'documents': onScreenChange?.('docs'); break;
      case 'calendar': onScreenChange?.('calendar'); break;
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
  const selfHealLabel = maxStatus?.self_heal?.full_autonomous_repair_verified
    ? 'Self-heal autonomous'
    : 'Self-heal guided';

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
        <ViewPdfControl mode="print" title="Opens the browser print dialog for this conversation. Chat has no quote PDF of its own." />
        <span style={{
          fontSize: 14,
          fontWeight: 900,
          letterSpacing: 2,
          color: 'var(--text)',
          fontFamily: "'Inter', sans-serif",
        }}>
          MAX
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <a
          className="cm-chiefe-btn"
          href={chiefEHref([...messages].reverse().find(m => m.role === 'user')?.content)}
          target="_blank"
          rel="noopener noreferrer"
          title="Open Chief e (Grok Bot) with your last question"
        >
          <ExternalLink size={13} /> Ask Chief e
        </a>
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
        </div>
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

      {quickQuoteNotice && (
        <div style={{
          flexShrink: 0,
          background: '#f7f3ea',
          borderBottom: '1px solid #b8912f',
          padding: '8px 12px',
          fontSize: 12,
          color: '#20241f',
        }}>
          {quickQuoteNotice}
        </div>
      )}

      {/* Current Job Chip in Chat Header */}
      {activeJob && (
        <div
          data-testid="chat-current-job-chip"
          style={{
            flexShrink: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 8,
            padding: '6px 14px',
            background: '#121214',
            borderBottom: '2px solid #b8960c',
            color: '#fff',
            fontSize: 11,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
            <span
              style={{
                background: 'linear-gradient(135deg, #b8960c, #d4af37)',
                color: '#121214',
                fontSize: '9px',
                fontWeight: 800,
                padding: '2px 6px',
                borderRadius: '4px',
                whiteSpace: 'nowrap',
              }}
            >
              CURRENT JOB
            </span>
            <span style={{ fontWeight: 700, color: '#f5f2ed', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {activeJob.client_name || 'Client'}
            </span>
            <span style={{ color: '#b8960c', fontFamily: 'monospace', whiteSpace: 'nowrap' }}>
              ({activeJob.job_number || `JOB-${activeJob.id}`})
            </span>
            <span
              style={{
                background: '#222',
                color: '#aaa',
                border: '1px solid #444',
                padding: '1px 6px',
                borderRadius: '4px',
                fontSize: '9px',
                textTransform: 'uppercase',
                whiteSpace: 'nowrap',
              }}
            >
              {activeJob.pipeline_stage || activeJob.status}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
            <button
              type="button"
              onClick={() => setChatFolderOpen(true)}
              style={{
                minHeight: '28px',
                padding: '2px 8px',
                borderRadius: '6px',
                background: '#222',
                border: '1px solid #b8960c',
                color: '#b8960c',
                fontSize: '10px',
                fontWeight: 700,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 4,
              }}
            >
              <FolderOpen size={12} />
              <span>Job Docs</span>
            </button>
            <button
              type="button"
              onClick={clearJob}
              title="Unlink job from Max conversation"
              style={{
                minHeight: '28px',
                background: 'none',
                border: 'none',
                color: '#777',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                padding: '0 4px',
              }}
            >
              <X size={14} />
            </button>
          </div>
        </div>
      )}

      {chatFolderOpen && activeJob && (
        <JobFolderModal
          jobId={activeJob.id}
          isOpen={chatFolderOpen}
          onClose={() => setChatFolderOpen(false)}
        />
      )}

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
          {/* Truthful chip row — see REPORT-command-center-widget-audit.md */}
          {/* TopBar model picker is the single source of truth for provider/model. */}
          {/* Local-vision label only renders when local vision is online; cloud vision via mmx still works. */}
          {localVision?.online && (
            <StatusChip label={localVisionLabel} tone="ok" />
          )}
          <StatusChip label={textRoutingLabel} tone={textRoutingFallback ? 'warn' : 'ok'} />
          <StatusChip label={voiceLabel} tone={maxStatus?.voice?.tts?.last_status === 'failed' ? 'warn' : maxStatus.capabilities?.voice_input ? 'ok' : 'warn'} />
          <StatusChip
            label={`OpenClaw ${openClawOnline ? 'online' : 'offline'}${Number.isFinite(openClawQueueTotal) && openClawQueueTotal > 0 ? ` · ${openClawQueueTotal} queued` : ''}`}
            tone={!openClawOnline ? 'warn' : (Number.isFinite(openClawQueueTotal) && openClawQueueTotal > 0) ? 'warn' : 'ok'}
          />
          {/* Self-heal chip only shown on warn state, not on a healthy system. */}
          {!maxStatus?.self_heal?.full_autonomous_repair_verified && maxStatus?.self_heal?.warning && (
            <StatusChip label={selfHealLabel} tone="warn" />
          )}
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
            {maxStatus.desks?.count || 0} desks
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
          {/* Upload is via the paperclip icon below; chip removed (was a fake non-clickable). */}
          {/* Public MAX marketing link moved out of status row; see System Details / TopBar help. */}
        </div>
      )}

      <ContinuityPanel mode="compact" onOpenContinuity={() => onProductNavigate?.('max-continuity', 'dashboard')} />

      {/* Messages */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '8px 10px',
      }}
      className="sm:!px-9 sm:!py-6 pb-10 md:!pb-6">
        {settledMessages.map((msg, i) => (
          <div key={msg.id || i} className="cm-msg" style={{
            marginBottom: 16,
            maxWidth: '90%',
            marginLeft: msg.role === 'user' ? 'auto' : undefined,
            marginRight: msg.role === 'user' ? 0 : 'auto',
          }}>
            {(() => {
              const { cleanContent, toolCalls } = msg.role === 'assistant'
                ? parseToolBlocks(msg.content)
                : { cleanContent: msg.content, toolCalls: [] };
              const msgImage = msg.imageUrl
                || (msg.image ? `${API}/files/view/images/${encodeURIComponent(msg.image)}` : '');
              return (
                <>
                  {msgImage && (
                    <a href={msgImage} target="_blank" rel="noreferrer" style={{ display: 'block', marginBottom: 6, textAlign: msg.role === 'user' ? 'right' : 'left' }}>
                      <img
                        src={msgImage}
                        alt={msg.image || 'attached image'}
                        loading="lazy"
                        style={{ maxWidth: 240, maxHeight: 240, borderRadius: 10, border: '1px solid var(--border)', objectFit: 'cover' }}
                      />
                    </a>
                  )}
                  {cleanContent && (
                    <div className={`cm-bubble ${msg.role === 'user' ? 'is-user chat-bubble-user' : 'is-assistant chat-bubble-assistant'}`}>
                      {msg.role === 'user'
                        ? cleanContent
                        : renderContent(cleanContent, onScreenChange, [...settledMessages.slice(0, i)].reverse().find(m => m.role === 'user')?.content)}
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
            <div className="cm-meta" style={{
              fontSize: 10,
              marginTop: 4,
              fontFamily: "'Inter', monospace",
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              ...(msg.role === 'user' ? { justifyContent: 'flex-end' } : {}),
            }} suppressHydrationWarning>
              {msg.timestamp}
              {displayModelLabel(msg.model) && (
                <span style={{ opacity: 0.7 }}>{displayModelLabel(msg.model)}</span>
              )}
              {msg.role === 'assistant' && (
                <button
                  type="button"
                  onClick={() => handleCopyMessage(msg)}
                  title="Copy reply"
                  style={{
                    minHeight: 44,
                    minWidth: 44,
                    padding: '8px 10px',
                    margin: '-8px 0',
                    background: 'none',
                    border: 'none',
                    color: copiedMessageId === msg.id ? '#16a34a' : 'var(--muted)',
                    cursor: 'pointer',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 4,
                    fontSize: 10,
                    fontWeight: 600,
                  }}
                >
                  {copiedMessageId === msg.id ? <Check size={14} /> : <Copy size={14} />}
                  {copiedMessageId === msg.id ? 'Copied' : 'Copy'}
                </button>
              )}
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
              if (tr.tool === 'open_final_doc' && tr.success && tr.result?.viewer_url) {
                return <MaxDocCard key={j} result={tr.result} />;
              }
              if (['open_record', 'edit_quote_lines', 'convert_quote_to_invoice'].includes(tr.tool) && tr.result && (tr.result.id || tr.result.needs_confirmation)) {
                return <MaxRecordCard key={j} tool={tr.tool} result={tr.result} />;
              }
              if (tr.tool === 'sketch_to_drawing' && tr.success && tr.result?.svg) {
                return <InlineDrawing key={j} result={tr.result} />;
              }
              {/* MiniMax multimodal tool results */}
              if (tr.success && tr.result) {
                const imageUrl = tr.result.image_url || tr.result.audio_url || tr.result.video_url;
                const imageUrls = tr.result.image_urls || (Array.isArray(tr.result.images) ? tr.result.images.map((i: any) => i.image_url || i.url) : []);
                if (imageUrl || imageUrls.length > 0) {
                  return (
                    <div key={j} style={{ marginTop: 8, borderRadius: 10, overflow: 'hidden', maxWidth: 480 }}>
                      {imageUrls.slice(0, 4).map((url: string, k: number) => (
                        <img key={k} src={url} alt="Generated" style={{ width: '100%', display: 'block', marginBottom: 4, borderRadius: 8 }} />
                      ))}
                      {imageUrl && !imageUrls.length && (
                        <img src={imageUrl} alt="Generated" style={{ width: '100%', borderRadius: 8 }} />
                      )}
                    </div>
                  );
                }
                const audioUrl = tr.result.audio_url;
                if (audioUrl) {
                  return (
                    <div key={j} style={{ marginTop: 8 }}>
                      <audio controls src={audioUrl} style={{ width: '100%' }} />
                    </div>
                  );
                }
                const designBrief = tr.result.design_brief;
                if (designBrief) {
                  return (
                    <div key={j} style={{ marginTop: 8, padding: '10px 14px', background: '#f8f5ff', borderRadius: 8, fontSize: 12, borderLeft: '3px solid #8B5CF6', maxWidth: 480 }}>
                      <div style={{ fontWeight: 600, color: '#8B5CF6', marginBottom: 4 }}>Design Brief</div>
                      <div style={{ whiteSpace: 'pre-wrap', color: '#333' }}>{designBrief}</div>
                    </div>
                  );
                }
              }
              return null;
            })}
            {msg.pinPrompts?.filter(prompt => prompt.status !== 'cancelled').map(prompt => (
              <FounderPinCard
                key={prompt.resumeId}
                prompt={prompt}
                disabled={isStreaming}
                onSubmit={(resumeId, pin) => onSubmitPin?.(msg.id, resumeId, pin)}
                onCancel={(resumeId) => onCancelPin?.(msg.id, resumeId)}
              />
            ))}
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
            {streamingSteps.length > 0 && (
              <div style={{
                marginBottom: 8,
                padding: '10px 14px',
                fontSize: 12,
                lineHeight: 1.5,
                background: '#f8fafc',
                color: '#334155',
                border: '1px solid var(--border)',
                borderRadius: 10,
                fontFamily: "'Inter', system-ui, sans-serif",
              }}>
                {streamingSteps.map((line, i) => (
                  <div key={i} style={{ marginBottom: i < streamingSteps.length - 1 ? 4 : 0 }}>{line}</div>
                ))}
              </div>
            )}
            <div className="cm-msg"><div className="cm-bubble is-assistant chat-bubble-assistant">
              {streamingContent ? renderContent(streamingContent, onScreenChange) : (streamingSteps.length ? '' : '...')}
            </div></div>
            <div style={{
              fontSize: 10,
              color: 'var(--muted)',
              marginTop: 4,
              fontFamily: "'Inter', monospace",
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}>
              {displayModelLabel(streamingModel) && <span>{displayModelLabel(streamingModel)}</span>}
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
        {/* Queued messages: sent while Max was answering; they run in order after the current reply */}
        {queuedMessages.map((msg, k) => (
          <div key={msg.id} className="cm-msg" data-testid="queued-message" style={{ marginBottom: 12, maxWidth: '90%', marginLeft: 'auto', marginRight: 0 }}>
            <div className="cm-bubble is-user chat-bubble-user" style={{ opacity: 0.6 }}>{msg.content}</div>
            <div style={{ fontSize: 10, color: 'var(--muted)', marginTop: 4, textAlign: 'right', fontFamily: "'Inter', monospace" }}>
              <span>Queued{queuedMessages.length > 1 ? ` · ${k + 1} of ${queuedMessages.length}` : ''} · Max answers it next</span>
              {onCancelQueued && (
                <button
                  type="button"
                  onClick={() => onCancelQueued(msg.id)}
                  aria-label="Remove queued message"
                  style={{ marginLeft: 8, background: 'none', border: 'none', cursor: 'pointer', color: 'var(--red)', fontSize: 10, fontWeight: 600, padding: 0 }}
                >
                  Remove
                </button>
              )}
            </div>
          </div>
        ))}
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

        {voiceDraft && (
          <div style={{
            marginBottom: 10, padding: '12px 14px', borderRadius: 12,
            background: '#fff', border: '1px solid var(--border)',
            maxHeight: 280, overflow: 'auto',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, marginBottom: 6 }}>
              <strong style={{ fontSize: 13 }}>
                {voiceDraft.quote_number ? `Draft ${voiceDraft.quote_number}` : 'Voice draft'}
                {' · '}{voiceDraft.sent ? 'sent' : 'not sent'}
              </strong>
              <span style={{ fontSize: 11, color: 'var(--dim)' }}>{voiceDraft.client_brand}</span>
            </div>
            {voiceDraft.latest_transcript && (
              <p style={{ margin: '0 0 8px', fontSize: 12, color: 'var(--dim)' }}>
                Transcript: {voiceDraft.latest_transcript}
              </p>
            )}
            {(voiceDraft.line_items || []).map((item: any, idx: number) => (
              <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, padding: '2px 0' }}>
                <span>{item.description}</span>
                <span>${Number(item.amount || 0).toFixed(2)}</span>
              </div>
            ))}
            {voiceDraft.total != null && (
              <div style={{ fontSize: 13, fontWeight: 700, marginTop: 4 }}>Total ${Number(voiceDraft.total).toFixed(2)}</div>
            )}
            {voiceDraft.drawing?.fabrication?.usable_seat_in != null && (
              <p style={{ margin: '6px 0 0', fontSize: 12 }}>
                Drawing attached. Usable seat {voiceDraft.drawing.fabrication.usable_seat_in}&quot; · cushion {voiceDraft.drawing.fabrication.seat_cushion_thickness_in}&quot; · overhang {voiceDraft.drawing.fabrication.overhang_in}&quot;
                {voiceDraft.drawing.fabrication.vertical_back ? ' · back vertical' : ' · back raked'}
              </p>
            )}
            {(voiceDraft.missing || []).length > 0 && (
              <ul style={{ margin: '8px 0 0', paddingLeft: 18, fontSize: 12 }}>
                {voiceDraft.missing.map((row: any) => <li key={row.id}>{row.label}</li>)}
              </ul>
            )}
            {(voiceDraft.options || []).map((opt: any) => (
              <div key={opt.id} style={{ marginTop: 8 }}>
                <div style={{ fontSize: 12, fontWeight: 600 }}>{opt.prompt}</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 4 }}>
                  {(opt.choices || []).map((choice: any) => (
                    <button
                      key={choice.id}
                      type="button"
                      onClick={() => chooseVoiceOption(opt.id, choice.id)}
                      style={{
                        fontSize: 12, padding: '4px 8px', borderRadius: 8,
                        border: '1px solid var(--border)', background: 'var(--card-bg)', cursor: 'pointer',
                      }}
                    >
                      {choice.label}
                    </button>
                  ))}
                </div>
              </div>
            ))}
            <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
              <button type="button" onClick={finishVoiceDraft} style={{
                fontSize: 12, padding: '6px 10px', borderRadius: 8, border: 'none',
                background: 'var(--text)', color: '#fff', cursor: 'pointer',
              }}>
                Done
              </button>
              <span style={{ fontSize: 11, color: 'var(--dim)', alignSelf: 'center' }}>
                Draft stays here until you confirm a send.
              </span>
            </div>
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
            minWidth: 0,
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
              placeholder={codeMode ? 'Code Mode — describe what to build or fix...' : isStreaming ? 'Max is answering. Type away, it queues...' : 'Message MAX...'}
              rows={1}
              style={{
                flex: 1, padding: '13px 18px', border: 'none', outline: 'none',
                fontSize: 14, fontFamily: "'Inter', sans-serif", resize: 'none',
                minHeight: 44, maxHeight: 120, background: 'transparent',
                color: 'var(--text)', lineHeight: 1.5,
              }}
            />
          </div>

          {micToast && (
            <div
              role="status"
              aria-live="polite"
              style={{
                position: 'absolute',
                left: 12,
                right: 12,
                bottom: '100%',
                marginBottom: 8,
                padding: '10px 14px',
                borderRadius: 12,
                background: '#1a1a1a',
                color: '#fff',
                fontSize: 14,
                fontWeight: 600,
                textAlign: 'center',
                zIndex: 5,
                pointerEvents: 'none',
              }}
            >
              {micToast}
            </div>
          )}

          {/* Mic button — tap to start / tap to stop on touch. Hold is optional. */}
          <button
            type="button"
            aria-label={recording ? 'Stop recording' : 'Start recording'}
            onContextMenu={(e) => e.preventDefault()}
            onPointerDown={(e) => {
              if (e.pointerType === 'mouse' && e.button !== 0) return;
              e.preventDefault();
              const touch = e.pointerType === 'touch' || (e.pointerType !== 'mouse' && touchMicRef.current);
              touchMicRef.current = touch || touchMicRef.current;
              const action = pointerDownAction({
                touchDevice: touch,
                alreadyRecording: recordingRef.current || mediaRecorderRef.current?.state === 'recording',
              });
              if (action === 'stop') {
                stopVoiceCapture();
                return;
              }
              if (action === 'ignore') return;
              micPointerRef.current = e.pointerId;
              voiceReleaseRef.current = false;
              holdArmedRef.current = !touch;
              clearHoldArm();
              if (touch) {
                holdArmTimerRef.current = setTimeout(() => {
                  // A tap already lifted. Do not arm hold-to-talk after the finger is up.
                  if (voiceReleaseRef.current) return;
                  holdArmedRef.current = true;
                  setVoiceStatus('🔴 Release to transcribe');
                }, HOLD_ARM_MS);
              }
              try { e.currentTarget.setPointerCapture(e.pointerId); } catch { /* ignore */ }
              startVoiceCapture(voiceModeRef.current ? 'chat' : 'document');
            }}
            onPointerUp={(e) => {
              if (micPointerRef.current === null || e.pointerId !== micPointerRef.current) return;
              micPointerRef.current = null;
              const touch = e.pointerType === 'touch' || (e.pointerType !== 'mouse' && touchMicRef.current);
              voiceReleaseRef.current = true;
              if (!shouldStopOnPointerUp({ touchDevice: touch, holdArmed: holdArmedRef.current })) {
                clearHoldArm();
                holdArmedRef.current = false;
                return;
              }
              stopVoiceCapture();
            }}
            onPointerCancel={(e) => {
              if (micPointerRef.current === null || e.pointerId !== micPointerRef.current) return;
              micPointerRef.current = null;
              const touch = e.pointerType === 'touch' || (e.pointerType !== 'mouse' && touchMicRef.current);
              voiceReleaseRef.current = true;
              if (!shouldStopOnPointerUp({ touchDevice: touch, holdArmed: holdArmedRef.current })) {
                clearHoldArm();
                holdArmedRef.current = false;
                return;
              }
              stopVoiceCapture();
            }}
            title={recording ? (touchMicRef.current ? 'Tap to stop' : 'Release to transcribe') : 'Tap to talk'}
            style={{
              width: 44, height: 44, borderRadius: 12,
              background: recording ? '#ef4444' : 'var(--card-bg)',
              border: `1.5px solid ${recording ? '#ef4444' : 'var(--border)'}`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer', color: recording ? '#fff' : 'var(--dim)',
              flexShrink: 0, transition: 'all 0.2s',
              animation: recording ? 'pulse 1.5s infinite' : 'none',
              position: 'relative',
              touchAction: 'none',
              WebkitTouchCallout: 'none',
              WebkitUserSelect: 'none',
              userSelect: 'none',
            }}
          >
            {recording ? <MicOff size={18} /> : <Mic size={18} />}
          </button>

          {/* Send button */}
          <button
            type="button"
            aria-label="Send message"
            onClick={handleSend}
            title={isStreaming ? 'Max is answering. This message will be queued and answered next.' : 'Send'}
            style={{
              width: 44, height: 44, borderRadius: 12,
              background: 'var(--text)', border: 'none',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer',
              color: '#fff', flexShrink: 0,
              opacity: 1, transition: 'all 0.2s',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--gold)'; }}
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

function renderContent(content: string, onScreenChange?: (s: string, id?: string) => void, question = '') {
  // Quote numbers resolve to their canonical id via /quotes-v2/by-number/{qn}.
  // Stay silent on a miss: never fall back to "first row of the list" (HOTFIX 4b).
  const openQuoteNumber = (quoteNumber: string) => {
    fetch(`${API}/quotes-v2/by-number/${encodeURIComponent(quoteNumber)}`)
      .then(r => {
        if (r.status === 404) throw new Error(`Quote ${quoteNumber} not found`);
        if (!r.ok) throw new Error(`Resolver returned ${r.status}`);
        return r.json();
      })
      .then((q: any) => { if (q && q.id) onScreenChange?.('quote', q.id); })
      // eslint-disable-next-line no-console
      .catch(err => console.error(`[quote-link] failed to resolve ${quoteNumber}:`, err));
  };
  const segments = splitChatContent(content);
  return segments.map((segment, segIndex) => {
    if (segment.kind === 'chart') {
      return <ChatChartBlock key={`chart-${segIndex}`} chart={segment.chart} />;
    }
    return (
      <ChatMarkdown
        key={`text-${segIndex}`}
        text={segment.text}
        question={question}
        onQuoteNumber={openQuoteNumber}
        onBuilder={() => onScreenChange?.('quote')}
      />
    );
  });
}
