'use client';
import { useState, useRef, useCallback } from 'react';
import { Message, StreamEvent, ToolResult } from '@/lib/types';
import { API_URL } from '@/lib/api';

const FALLBACK_NOTICE = '*[Using Grok direct — FastAPI backend offline]*\n\n';

interface UseChatOptions {
  onSave?: (messages: Message[], chatId: string | null) => Promise<string | null>;
}

const WELCOME: Message = {
  role: 'assistant',
  content: "Hello! I'm **MAX**, your Empire AI Assistant.\n\n_Tip: Ctrl+V to paste images · Shift+Enter for newlines_",
};

export function useChat({ onSave }: UseChatOptions = {}) {
  const [messages,        setMessages]        = useState<Message[]>([WELCOME]);
  const [isStreaming,     setIsStreaming]      = useState(false);
  const [streamingContent,setStreamingContent]= useState('');
  const [streamingModel,  setStreamingModel]  = useState('');
  const abortRef  = useRef<AbortController | null>(null);
  const chatIdRef = useRef<string | null>(null);

  const setChatId   = useCallback((id: string | null) => { chatIdRef.current = id; }, []);

  const loadMessages = useCallback((msgs: Message[], chatId: string | null) => {
    setMessages(msgs.length > 0 ? msgs : [WELCOME]);
    chatIdRef.current = chatId;
  }, []);

  const sendMessage = useCallback(async (
    input: string,
    selectedModel: string,
    selectedImage?: { name: string; category: string } | null,
    history?: Message[],
    desk?: string,
  ) => {
    if (!input.trim() || isStreaming) return;

    const userMsg: Message = { role: 'user', content: input, image: selectedImage?.name };
    const current   = history || messages;
    const newMsgs   = [...current, userMsg];
    setMessages(newMsgs);
    setIsStreaming(true);
    setStreamingContent('');
    setStreamingModel('');

    const ctrl = new AbortController();
    abortRef.current = ctrl;

    try {
      const body: Record<string, unknown> = {
        message: input,
        model:   selectedModel,
        history: newMsgs.slice(-20).map(m => ({ role: m.role, content: m.content })),
      };
      if (desk) body.desk = desk;
      if (selectedImage) {
        body.image_filename = selectedImage.name;
        body.image_category = selectedImage.category;
      }

      let response: Response;
      let usingFallback = false;

      try {
        response = await fetch(API_URL + '/max/chat/stream', {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify(body),
          signal:  ctrl.signal,
        });
        if (!response.ok) throw new Error(`Backend ${response.status}`);
      } catch (backendErr: any) {
        if (backendErr.name === 'AbortError') throw backendErr;
        // Backend unreachable — fall back to local Grok route
        usingFallback = true;
        response = await fetch('/api/chat', {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify({ message: input, history: body.history, desk }),
          signal:  ctrl.signal,
        });
      }

      if (!response.body) throw new Error('No response body');

      const reader  = response.body.getReader();
      const decoder = new TextDecoder();
      let accumulated = usingFallback ? FALLBACK_NOTICE : '';
      let modelUsed   = '';
      let buf = '';
      const toolResults: ToolResult[] = [];

      if (usingFallback) setStreamingContent(accumulated);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split('\n');
        buf = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const ev: StreamEvent = JSON.parse(line.slice(6));
            if (ev.type === 'text' && ev.content) {
              accumulated += ev.content;
              setStreamingContent(accumulated);
            } else if (ev.type === 'tool_result') {
              toolResults.push({
                tool: ev.tool || 'unknown',
                success: ev.success ?? false,
                result: ev.result,
                error: ev.error,
              });
            } else if (ev.type === 'done') {
              modelUsed = ev.model_used || '';
            } else if (ev.type === 'error') {
              accumulated += '\n\n*Error: ' + (ev.content || 'Unknown error') + '*';
              setStreamingContent(accumulated);
            }
          } catch { /* skip malformed */ }
        }
      }

      const assistantMsg: Message = {
        role: 'assistant',
        content: accumulated || 'No response.',
        model: modelUsed,
        ...(toolResults.length > 0 ? { toolResults } : {}),
      };
      const finalMsgs = [...newMsgs, assistantMsg];
      setMessages(finalMsgs);
      setStreamingContent('');

      if (onSave) {
        const savedId = await onSave(finalMsgs, chatIdRef.current);
        if (savedId) chatIdRef.current = savedId;
      }
    } catch (e: any) {
      if (e.name === 'AbortError') {
        if (streamingContent) {
          setMessages(prev => [...prev, {
            role: 'assistant',
            content: streamingContent + '\n\n*[Stopped]*',
            model: streamingModel,
          }]);
        }
      } else {
        setMessages(prev => [...prev, { role: 'assistant', content: '**⚡ All chat routes unavailable.** Both the FastAPI backend and Grok fallback failed.' }]);
      }
      setStreamingContent('');
    } finally {
      setIsStreaming(false);
      abortRef.current = null;
    }
  }, [messages, isStreaming, onSave, streamingContent, streamingModel]);

  const stopStreaming = useCallback(() => { abortRef.current?.abort(); }, []);

  return {
    messages, setMessages, isStreaming,
    streamingContent, streamingModel,
    sendMessage, stopStreaming,
    loadMessages, setChatId,
    chatId: chatIdRef.current,
  };
}
