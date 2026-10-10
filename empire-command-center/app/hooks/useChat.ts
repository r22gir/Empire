'use client';
import { useState, useRef, useCallback, useEffect } from 'react';
import { insertAfter, historyFor, markActive, dropQueued, nextId, type QueuedTurn } from './chatQueue';
import { Message, PinPrompt, ToolResult } from '../lib/types';
import { API } from '../lib/api';
import { asksForFounderPin, redactSecret, toolResultPreview } from '../lib/founderPin';

const WELCOME: Message = {
  id: 'welcome',
  role: 'assistant',
  content: "Hello! I'm **MAX**, your Empire AI Assistant.\n\n_Tip: Ctrl+V to paste images · Shift+Enter for newlines_",
  timestamp: '',
};

// UI-side error notices. They are shown to Rafael but never sent back to Max
// as history: on 2026-10-06 the old "**Connection error.** Backend may be
// offline." notice was replayed and the model copied it as its answer.
// Keep in sync with _UI_ERROR_PREFIXES in backend/app/routers/max/router.py.
const UI_ERROR_PREFIXES = [
  '**Connection error.**',
  '**Connection dropped.**',
  "**Can't reach the server.**",
  '**Server error.**',
];
const isUiErrorNotice = (m: { role: string; content: string }) =>
  m.role === 'assistant' && UI_ERROR_PREFIXES.some(p => (m.content || '').trimStart().startsWith(p));

class StreamHttpError extends Error {
  status: number;
  constructor(status: number, detail: string) {
    super(detail);
    this.name = 'StreamHttpError';
    this.status = status;
  }
}

async function serverIsUp(): Promise<boolean> {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), 5000);
  try {
    const r = await fetch(API + '/system/health', { cache: 'no-store', signal: ctrl.signal });
    return r.ok;
  } catch {
    return false;
  } finally {
    clearTimeout(t);
  }
}

/** Plain-words notice for a failed reply (instead of a blanket "Backend may be offline"). */
async function describeStreamFailure(e: any): Promise<string> {
  if (e instanceof StreamHttpError) {
    return `**Server error.** The server is up, but this request failed (HTTP ${e.status})`
      + (e.message ? `: ${e.message}` : '.') + ' Please try again.';
  }
  const why = e?.message ? ` (error: "${String(e.message).slice(0, 120)}")` : '';
  if (await serverIsUp()) {
    return '**Connection dropped.** The server is up, but the connection to this screen was cut before '
      + "Max's reply arrived" + why + '. This usually happens when the phone pauses Safari (switching apps '
      + 'or locking the screen) or the network blips. Send it again and keep this screen open until the reply shows.';
  }
  return "**Can't reach the server.** The Empire server did not answer" + why
    + '. Check the internet connection and try again in a minute.';
}

function formatContextPack(data: any): string {
  const parts: string[] = [];
  if (data.recent_summaries?.length)
    parts.push('Recent sessions: ' + data.recent_summaries.map((s: any) => s.summary || '').join(' | '));
  if (data.pending_tasks?.length)
    parts.push('Pending tasks: ' + data.pending_tasks.map((t: any) => t.title || '').join(', '));
  if (data.top_memories?.length)
    parts.push('Key memories: ' + data.top_memories.slice(0, 10).map((m: any) => m.content || '').join(' | '));
  return parts.length ? '[Context from previous sessions]\n' + parts.join('\n') : '';
}

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([WELCOME]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [streamingSteps, setStreamingSteps] = useState<string[]>([]);
  const [streamingModel, setStreamingModel] = useState('');
  const abortRef = useRef<AbortController | null>(null);
  const chatIdRef = useRef<string | null>(null);
  const streamingRef = useRef(false);
  const messagesRef = useRef<Message[]>([WELCOME]);
  const contextPackRef = useRef<string>('');
  // 2026-10-08: messages sent while Max is answering wait here and run in order.
  const queueRef = useRef<QueuedTurn[]>([]);
  const [queuedCount, setQueuedCount] = useState(0);

  // Set welcome timestamp on client only (avoids hydration mismatch)
  useEffect(() => {
    const ts = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    setMessages(prev => prev.map(m => m.id === 'welcome' && !m.timestamp ? { ...m, timestamp: ts } : m));
    messagesRef.current = messagesRef.current.map(m => m.id === 'welcome' && !m.timestamp ? { ...m, timestamp: ts } : m);
  }, []);

  useEffect(() => {
    fetch(API + '/memory/context-pack')
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) contextPackRef.current = formatContextPack(data); })
      .catch(() => {});
  }, []);

  const updateMessages = useCallback((msgs: Message[] | ((prev: Message[]) => Message[])) => {
    setMessages(prev => {
      const next = typeof msgs === 'function' ? msgs(prev) : msgs;
      messagesRef.current = next;
      return next;
    });
  }, []);

  useEffect(() => {
    fetch(API + '/max/self-assessment?channel=web&limit=5', { cache: 'no-store' })
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (!data?.should_run_continuity_audit || !data.message) return;
        const msg: Message = {
          id: `self-assessment-${Date.now()}`,
          role: 'assistant',
          content: data.message,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          model: 'empire-max-continuity-audit',
          toolResults: data.audit ? [{ tool: 'empire_max_continuity_audit', success: true, result: data.audit }] : undefined,
          metadata: {
            registry_version: data.audit?.registry_version || '',
            surface: 'Founder/Web MAX',
            response_at: new Date().toISOString(),
            skill_used: data.skill_used || null,
          },
        };
        updateMessages(prev => [...prev, msg]);
      })
      .catch(() => {});
  }, [updateMessages]);

  const loadMessages = useCallback((msgs: Message[], chatId: string | null) => {
    const next = msgs.length > 0 ? msgs : [WELCOME];
    setMessages(next);
    messagesRef.current = next;
    chatIdRef.current = chatId;
    // another chat opened: queued messages belonged to the old one
    queueRef.current = [];
    setQueuedCount(0);
  }, []);

  const runTurnRef = useRef<((turn: QueuedTurn) => Promise<void>) | null>(null);

  const runNextQueued = useCallback(() => {
    const next = queueRef.current.shift();
    setQueuedCount(queueRef.current.length);
    if (!next || !runTurnRef.current) return;
    updateMessages(prev => markActive(prev, next.msg.id));
    void runTurnRef.current({ ...next, msg: { ...next.msg, queued: false } });
  }, [updateMessages]);

  const sendMessage = useCallback(async (
    input: string,
    imageFilename?: string | null,
    desk?: string,
    channel?: string,
  ) => {
    if (!input.trim()) return;
    const userMsg: Message = {
      id: nextId(),
      role: 'user',
      content: input,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      ...(imageFilename ? { image: imageFilename } : {}),
    };
    if (streamingRef.current || queueRef.current.length > 0) {
      // Max is still answering: never drop or block the message. Show it now, run it next.
      queueRef.current.push({ msg: { ...userMsg, queued: true }, imageFilename, desk, channel });
      setQueuedCount(queueRef.current.length);
      updateMessages(prev => [...prev, { ...userMsg, queued: true }]);
      return;
    }
    updateMessages(prev => [...prev, userMsg]);
    await runTurnRef.current?.({ msg: userMsg, imageFilename, desk, channel });
  }, [updateMessages]);

  const cancelQueued = useCallback((id: string) => {
    queueRef.current = queueRef.current.filter(t => t.msg.id !== id);
    setQueuedCount(queueRef.current.length);
    updateMessages(prev => dropQueued(prev, id));
  }, [updateMessages]);

  const runTurn = useCallback(async ({ msg: userMsg, imageFilename, desk, channel }: QueuedTurn) => {
    const input = userMsg.content;
    // conversation as of this turn (later queued messages are not part of it yet)
    // (messagesRef can lag one render behind the state update that added this turn)
    const base = messagesRef.current.some(m => m.id === userMsg.id) ? messagesRef.current : [...messagesRef.current, userMsg];
    const newMsgs = historyFor(base, userMsg.id);
    setIsStreaming(true);
    streamingRef.current = true;
    setStreamingContent('');
    setStreamingSteps([]);
    setStreamingModel('');

    const ctrl = new AbortController();
    abortRef.current = ctrl;
    let accumulated = '';
    let modelUsed = '';
    let qualityBadge: any = undefined;
    let responseMetadata: any = undefined;

    try {
      const historySlice = newMsgs.filter(m => !isUiErrorNotice(m)).slice(-20).map(m => ({ role: m.role, content: m.content }));
      if (contextPackRef.current && historySlice.filter(m => m.role === 'user').length <= 1) {
        historySlice.unshift({ role: 'user', content: contextPackRef.current });
        historySlice.unshift({ role: 'assistant', content: 'Context loaded. Ready.' });
      }

      const body: Record<string, unknown> = {
        message: input,
        model: 'auto',
        history: historySlice,
        conversation_id: chatIdRef.current || undefined,
        channel: channel || 'dashboard',
      };
      if (desk) body.desk = desk;
      if (imageFilename) body.image_filename = imageFilename;
      try {
        const activeJobId = localStorage.getItem('empire-active-job-id');
        if (activeJobId) {
          body.job_id = activeJobId;
        }
      } catch { /* ignore storage errors */ }

      const response = await fetch(API + '/max/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: ctrl.signal,
      });

      if (!response.ok) {
        let detail = '';
        try {
          const raw = await response.text();
          try { const j = JSON.parse(raw); detail = String(j.detail || j.error || j.message || ''); } catch { detail = raw; }
        } catch { /* ignore */ }
        throw new StreamHttpError(response.status, detail.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 200));
      }
      if (!response.body) throw new Error('No response body');
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buf = '';
      const toolResults: ToolResult[] = [];
      const pinPrompts: PinPrompt[] = [];
      let gotDone = false;
      let gotError = false;

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
            } else if (ev.type === 'progress' && ev.phase === 'tool' && ev.message) {
              setStreamingSteps(prev => (prev.includes(ev.message) ? prev : [...prev, ev.message]));
            } else if (ev.type === 'pin_required' && ev.resume_id) {
              pinPrompts.push({
                resumeId: String(ev.resume_id),
                tool: String(ev.tool || 'tool'),
                status: 'needed',
              });
            } else if (ev.type === 'tool_result') {
              toolResults.push({ tool: ev.tool || 'unknown', success: ev.success ?? false, result: ev.result, error: ev.error });
            } else if (ev.type === 'done') {
              gotDone = true;
              modelUsed = ev.model_used || '';
              setStreamingModel(modelUsed);
              if (ev.quality) qualityBadge = ev.quality;
              if (ev.metadata) responseMetadata = ev.metadata;
              if (ev.conversation_id && !chatIdRef.current) chatIdRef.current = ev.conversation_id;
            } else if (ev.type === 'error') {
              gotError = true;
              accumulated += '\n\n*Error: ' + (ev.content || 'Unknown error') + '*';
              setStreamingContent(accumulated);
            }
          } catch { /* skip */ }
        }
      }

      // The stream closed without Max's "done": the reply was cut off on the way.
      if (!gotDone && !gotError && !accumulated) throw new Error('the reply stream closed early');
      if (!gotDone && !gotError) accumulated += "\n\n*[Reply cut off before Max finished. Send it again to get the rest.]*";

      const assistantId = nextId();
      if (pinPrompts.length === 0 && asksForFounderPin(accumulated)) {
        pinPrompts.push({
          resumeId: `verify:${assistantId}`,
          tool: 'founder PIN',
          status: 'needed',
        });
      }
      const assistantMsg: Message = {
        id: assistantId,
        role: 'assistant',
        content: accumulated || 'No response.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        model: modelUsed,
        toolResults: toolResults.length > 0 ? toolResults : undefined,
        pinPrompts: pinPrompts.length > 0 ? pinPrompts : undefined,
        quality: qualityBadge,
        metadata: responseMetadata,
      };
      updateMessages(prev => insertAfter(prev, userMsg.id, assistantMsg));
      setStreamingContent('');
      setStreamingSteps([]);
      if (onMessageCompleteRef.current) onMessageCompleteRef.current(assistantMsg);
    } catch (e: any) {
      if (e.name === 'AbortError') {
        if (accumulated) {
          updateMessages(prev => insertAfter(prev, userMsg.id, {
            id: nextId(),
            role: 'assistant', content: accumulated + '\n\n*[Stopped]*',
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            model: modelUsed,
          }));
        }
      } else {
        const notice = await describeStreamFailure(e);
        updateMessages(prev => insertAfter(prev, userMsg.id, {
          id: nextId(),
          role: 'assistant',
          // keep any partial reply; the notice goes underneath it
          content: accumulated ? `${accumulated}\n\n${notice.replace(/^\*\*([^*]+)\*\*/, '*$1*')}` : notice,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          model: modelUsed,
        }));
      }
      setStreamingContent('');
    } finally {
      setIsStreaming(false);
      streamingRef.current = false;
      abortRef.current = null;
      // next queued message, in order (Stop ends only the current reply)
      if (queueRef.current.length) setTimeout(runNextQueued, 0);
    }
  }, [updateMessages, runNextQueued]);
  runTurnRef.current = runTurn;

  const submitFounderPin = useCallback(async (messageId: string, resumeId: string, pin: string) => {
    const secret = pin;
    const mark = (patch: Partial<PinPrompt>) => {
      updateMessages(prev => prev.map(msg => {
        if (msg.id !== messageId || !msg.pinPrompts) return msg;
        return {
          ...msg,
          pinPrompts: msg.pinPrompts.map(prompt => (
            prompt.resumeId === resumeId ? { ...prompt, ...patch } : prompt
          )),
        };
      }));
    };
    mark({ status: 'submitting', detail: undefined });
    try {
      const verifyOnly = resumeId.startsWith('verify:');
      const verify = await fetch(API + '/max/verify-pin', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pin: secret }),
      });
      if (verify.status === 403) {
        mark({ status: 'needed', detail: 'That PIN was not accepted.' });
        return;
      }
      if (!verify.ok) {
        mark({ status: 'error', detail: 'PIN check failed. Try again.' });
        return;
      }
      if (verifyOnly) {
        mark({ status: 'done', detail: 'PIN accepted.' });
        return;
      }
      const resume = await fetch(API + '/max/resume-restricted-tool', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resume_id: resumeId, pin: secret }),
      });
      const data = await resume.json().catch(() => ({}));
      if (resume.status === 403) {
        mark({ status: 'needed', detail: 'That PIN was not accepted.' });
        return;
      }
      if (resume.status === 404) {
        mark({ status: 'error', detail: 'That approval expired. Ask Max to run the tool again.' });
        return;
      }
      if (!resume.ok) {
        mark({ status: 'error', detail: 'Could not resume the tool.' });
        return;
      }
      const preview = toolResultPreview(data, secret);
      const toolName = String(data.tool || 'tool');
      const note = redactSecret(`\n\nApproved in the portal. ${toolName} finished.\n${preview}`, secret);
      updateMessages(prev => prev.map(msg => {
        if (msg.id !== messageId) return msg;
        return {
          ...msg,
          content: redactSecret(msg.content, secret) + note,
          pinPrompts: (msg.pinPrompts || []).map(prompt => (
            prompt.resumeId === resumeId
              ? { ...prompt, status: 'done' as const, tool: toolName, detail: preview }
              : prompt
          )),
        };
      }));
    } catch {
      mark({ status: 'error', detail: 'Could not reach the server.' });
    }
  }, [updateMessages]);

  const cancelFounderPin = useCallback((messageId: string, resumeId: string) => {
    updateMessages(prev => prev.map(msg => {
      if (msg.id !== messageId || !msg.pinPrompts) return msg;
      return {
        ...msg,
        pinPrompts: msg.pinPrompts.map(prompt => (
          prompt.resumeId === resumeId ? { ...prompt, status: 'cancelled' as const, detail: undefined } : prompt
        )),
      };
    }));
  }, [updateMessages]);

  const stopStreaming = useCallback(() => { abortRef.current?.abort(); }, []);

  const onMessageCompleteRef = useRef<((msg: Message) => void) | null>(null);
  const setOnMessageComplete = useCallback((cb: ((msg: Message) => void) | null) => {
    onMessageCompleteRef.current = cb;
  }, []);

  return {
    messages, isStreaming, streamingContent, streamingSteps, streamingModel, queuedCount,
    sendMessage, stopStreaming, loadMessages, setOnMessageComplete, submitFounderPin, cancelFounderPin, cancelQueued,
    chatId: chatIdRef.current,
  };
}
