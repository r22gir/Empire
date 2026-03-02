'use client';
import { useState, useRef, useCallback } from 'react';
import { Message, StreamEvent, ToolResult } from '@/lib/types';
import { API_URL } from '@/lib/api';

interface UseDeskChatOptions {
  deskId: string;
}

export function useDeskChat({ deskId }: UseDeskChatOptions) {
  const [messages,         setMessages]         = useState<Message[]>([]);
  const [isStreaming,      setIsStreaming]       = useState(false);
  const [streamingContent, setStreamingContent]  = useState('');
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(async (input: string) => {
    if (!input.trim() || isStreaming) return;

    const userMsg: Message = { role: 'user', content: input };
    const newMsgs = [...messages, userMsg];
    setMessages(newMsgs);
    setIsStreaming(true);
    setStreamingContent('');

    const ctrl = new AbortController();
    abortRef.current = ctrl;

    try {
      const body = {
        message: input,
        desk: deskId,
        history: newMsgs.slice(-10).map(m => ({ role: m.role, content: m.content })),
      };

      const response = await fetch(API_URL + '/max/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: ctrl.signal,
      });

      if (!response.body) throw new Error('No response body');

      const reader  = response.body.getReader();
      const decoder = new TextDecoder();
      let accumulated = '';
      let modelUsed   = '';
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
      setMessages(prev => [...prev, assistantMsg]);
      setStreamingContent('');
    } catch (e: unknown) {
      if (e instanceof Error && e.name === 'AbortError') {
        /* stopped by user */
      } else {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: '*Could not reach MAX. Is the backend running?*',
        }]);
      }
      setStreamingContent('');
    } finally {
      setIsStreaming(false);
      abortRef.current = null;
    }
  }, [messages, isStreaming, deskId]);

  const stopStreaming  = useCallback(() => { abortRef.current?.abort(); }, []);
  const clearMessages  = useCallback(() => { setMessages([]); }, []);

  return { messages, isStreaming, streamingContent, sendMessage, stopStreaming, clearMessages };
}
