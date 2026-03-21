'use client';
import { useState, useRef, useCallback, useEffect } from 'react';
import { Message, ToolResult } from '../lib/types';
import { API } from '../lib/api';

const WELCOME: Message = {
  id: 'welcome',
  role: 'assistant',
  content: "Hello! I'm **MAX**, your Empire AI Assistant.\n\n_Tip: Ctrl+V to paste images · Shift+Enter for newlines_",
  timestamp: '',
};

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
  const [streamingModel, setStreamingModel] = useState('');
  const abortRef = useRef<AbortController | null>(null);
  const chatIdRef = useRef<string | null>(null);
  const streamingRef = useRef(false);
  const messagesRef = useRef<Message[]>([WELCOME]);
  const contextPackRef = useRef<string>('');

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

  const loadMessages = useCallback((msgs: Message[], chatId: string | null) => {
    const next = msgs.length > 0 ? msgs : [WELCOME];
    setMessages(next);
    messagesRef.current = next;
    chatIdRef.current = chatId;
  }, []);

  const sendMessage = useCallback(async (
    input: string,
    imageFilename?: string | null,
    desk?: string,
    channel?: string,
  ) => {
    if (!input.trim() || streamingRef.current) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    const current = messagesRef.current;
    const newMsgs = [...current, userMsg];
    updateMessages(newMsgs);
    setIsStreaming(true);
    streamingRef.current = true;
    setStreamingContent('');
    setStreamingModel('');

    const ctrl = new AbortController();
    abortRef.current = ctrl;
    let accumulated = '';
    let modelUsed = '';

    try {
      const historySlice = newMsgs.slice(-20).map(m => ({ role: m.role, content: m.content }));
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

      const response = await fetch(API + '/max/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: ctrl.signal,
      });

      if (!response.body) throw new Error('No response body');
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buf = '';
      const toolResults: ToolResult[] = [];

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
            } else if (ev.type === 'tool_result') {
              toolResults.push({ tool: ev.tool || 'unknown', success: ev.success ?? false, result: ev.result, error: ev.error });
            } else if (ev.type === 'done') {
              modelUsed = ev.model_used || '';
              setStreamingModel(modelUsed);
              if (ev.conversation_id && !chatIdRef.current) chatIdRef.current = ev.conversation_id;
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
        toolResults: toolResults.length > 0 ? toolResults : undefined,
      };
      updateMessages([...newMsgs, assistantMsg]);
      setStreamingContent('');
      if (onMessageCompleteRef.current) onMessageCompleteRef.current(assistantMsg);
    } catch (e: any) {
      if (e.name === 'AbortError') {
        if (accumulated) {
          updateMessages(prev => [...prev, {
            id: (Date.now() + 1).toString(),
            role: 'assistant', content: accumulated + '\n\n*[Stopped]*',
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            model: modelUsed,
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
  }, [updateMessages]);

  const stopStreaming = useCallback(() => { abortRef.current?.abort(); }, []);

  const onMessageCompleteRef = useRef<((msg: Message) => void) | null>(null);
  const setOnMessageComplete = useCallback((cb: ((msg: Message) => void) | null) => {
    onMessageCompleteRef.current = cb;
  }, []);

  return {
    messages, isStreaming, streamingContent, streamingModel,
    sendMessage, stopStreaming, loadMessages, setOnMessageComplete,
    chatId: chatIdRef.current,
  };
}
