'use client';
import { useState, useRef, useEffect, useCallback } from 'react';
import { Paperclip, Mic, MicOff, ArrowRight, Volume2 } from 'lucide-react';
import { Message } from '../../lib/types';
import { API } from '../../lib/api';

const QUICK_ACTIONS = [
  { label: '📸 Photo Quote', action: 'photo-quote' },
  { label: '💰 Quick Quote', action: 'quick-quote' },
  { label: '📊 Report', action: 'report' },
  { label: '📋 Briefing', action: 'briefing' },
  { label: '📱 TG', action: 'telegram' },
  { label: '🔍 Search', action: 'search' },
];

interface Props {
  messages: Message[];
  isStreaming: boolean;
  streamingContent: string;
  streamingModel: string;
  onSend: (msg: string, imageFilename?: string | null) => void;
  onStop: () => void;
  onScreenChange?: (screen: string) => void;
}

export default function ChatScreen({ messages, isStreaming, streamingContent, streamingModel, onSend, onStop, onScreenChange }: Props) {
  const [input, setInput] = useState('');
  const [attachedImage, setAttachedImage] = useState<string | null>(null);
  const [recording, setRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const msgsEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    msgsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  const handleSend = () => {
    if (!input.trim() && !attachedImage) return;
    onSend(input, attachedImage);
    setInput('');
    setAttachedImage(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const handleQuickAction = (action: string) => {
    switch (action) {
      case 'briefing': onSend('Give me today\'s briefing'); break;
      case 'telegram': onSend('Check Telegram messages'); break;
      case 'search': onScreenChange?.('research'); break;
      case 'report': onSend('Generate a daily report'); break;
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

  const toggleRecording = useCallback(async () => {
    if (recording) {
      mediaRecorderRef.current?.stop();
      setRecording(false);
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      const chunks: Blob[] = [];
      recorder.ondataavailable = e => chunks.push(e.data);
      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        const blob = new Blob(chunks, { type: 'audio/webm' });
        const fd = new FormData();
        fd.append('audio', blob, 'recording.webm');
        try {
          const res = await fetch(API.replace('/api/v1', '') + '/api/transcribe', { method: 'POST', body: fd });
          const data = await res.json();
          if (data.success && data.text) {
            setInput(prev => prev + (prev ? ' ' : '') + data.text);
            textareaRef.current?.focus();
          }
        } catch { /* silent */ }
      };
      recorder.start();
      mediaRecorderRef.current = recorder;
      setRecording(true);
    } catch { /* mic permission denied */ }
  }, [recording]);

  const playTTS = async (text: string) => {
    try {
      const res = await fetch(API + '/max/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text.slice(0, 2000), voice: 'rex' }),
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        new Audio(url).play();
      }
    } catch { /* silent */ }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Quick actions */}
      <div className="flex gap-[5px] px-3 py-[7px] border-b border-[#ece8e1] shrink-0 overflow-x-auto">
        {QUICK_ACTIONS.map(qa => (
          <button key={qa.action} onClick={() => handleQuickAction(qa.action)}
            className="px-4 py-2 text-[12px] font-semibold rounded-[8px] border border-[#d8d3cb] bg-white cursor-pointer text-[#555] min-h-[40px] whitespace-nowrap hover:bg-[#fdf8eb] hover:border-[#b8960c] hover:text-[#b8960c] shadow-[0_1px_2px_rgba(0,0,0,0.05)] transition-all">
            {qa.label}
          </button>
        ))}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-5 py-4">
        {messages.map((msg, i) => (
          <div key={msg.id || i} className={`mb-3.5 max-w-[80%] ${msg.role === 'user' ? 'ml-auto' : ''}`}>
            <div className={`px-[15px] py-[11px] rounded-[13px] text-[13px] leading-[1.55] whitespace-pre-wrap
              ${msg.role === 'user'
                ? 'bg-[#b8960c] text-white rounded-br-[3px]'
                : 'bg-white border border-[#ece8e1] rounded-bl-[3px] text-[#1a1a1a]'}`}>
              {renderContent(msg.content, onScreenChange)}
            </div>
            <div className="text-[9px] text-[#aaa] mt-[3px] font-mono flex items-center gap-2">
              {msg.timestamp}
              {msg.model && <span>· {msg.model}</span>}
              {msg.role === 'assistant' && msg.content.length > 20 && (
                <button onClick={() => playTTS(msg.content)} className="hover:text-[#b8960c] cursor-pointer"><Volume2 size={10} /></button>
              )}
            </div>
            {/* Tool results */}
            {msg.toolResults?.map((tr, j) => {
              if (tr.tool === 'create_quick_quote' && tr.success && tr.result?.pdf_url) {
                return (
                  <div key={j} className="mt-2 p-2.5 rounded-lg border border-[#ece8e1] bg-[#fdf8eb] text-xs">
                    <strong>Quote {tr.result.quote_number}</strong> — {tr.result.customer_name}
                    <div className="flex gap-2 mt-1.5">
                      {tr.result.proposal_totals && Object.entries(tr.result.proposal_totals).map(([k, v]) => (
                        <span key={k} className="px-2 py-1 rounded bg-white border border-[#e5e0d8] text-[10px] font-mono">
                          {k}: ${Number(v).toLocaleString()}
                        </span>
                      ))}
                    </div>
                    <button onClick={() => onScreenChange?.('quote')}
                      className="mt-2 text-[#b8960c] font-semibold text-[11px] hover:underline cursor-pointer">
                      → Review Proposals
                    </button>
                  </div>
                );
              }
              return null;
            })}
          </div>
        ))}

        {/* Streaming indicator */}
        {isStreaming && (
          <div className="mb-3.5 max-w-[80%]">
            <div className="px-[15px] py-[11px] rounded-[13px] rounded-bl-[3px] text-[13px] leading-[1.55] bg-white border border-[#ece8e1] text-[#1a1a1a] whitespace-pre-wrap">
              {streamingContent || '...'}
            </div>
            <div className="text-[9px] text-[#aaa] mt-[3px] font-mono">
              {streamingModel && `${streamingModel} · `}typing...
              <button onClick={onStop} className="ml-2 text-red-500 hover:underline cursor-pointer">Stop</button>
            </div>
          </div>
        )}
        <div ref={msgsEndRef} />
      </div>

      {/* Input */}
      <div className="px-3.5 py-2.5 border-t border-[#ece8e1] bg-white shrink-0 flex gap-[7px] items-end">
        <input ref={fileInputRef} type="file" className="hidden" accept="image/*" onChange={handleFileUpload} />
        <button onClick={() => fileInputRef.current?.click()} className="chat-ib"><Paperclip size={17} /></button>
        <button onClick={toggleRecording}
          className={`chat-ib ${recording ? '!bg-red-500 !border-red-500 !text-white animate-pulse' : ''}`}>
          {recording ? <MicOff size={17} /> : <Mic size={17} />}
        </button>
        {attachedImage && (
          <div className="px-2 py-1 bg-[#fdf8eb] border border-[#b8960c] rounded text-[10px] text-[#b8960c] flex items-center gap-1">
            📎 {attachedImage}
            <button onClick={() => setAttachedImage(null)} className="ml-1 font-bold cursor-pointer">×</button>
          </div>
        )}
        <textarea ref={textareaRef} value={input} onChange={e => setInput(e.target.value)} onKeyDown={handleKeyDown}
          className="flex-1 px-3 py-[11px] border border-[#e5e0d8] rounded-[9px] text-[13px] resize-none outline-none min-h-[42px] bg-[#f5f3ef] focus:border-[#b8960c] focus:shadow-[0_0_0_3px_#f5ecd0]"
          placeholder="Message MAX..." rows={1} />
        <button onClick={handleSend} disabled={isStreaming}
          className="w-[46px] h-[46px] rounded-[10px] bg-[#b8960c] border-[#b8960c] border-2 text-white flex items-center justify-center cursor-pointer text-lg hover:bg-[#a08509] active:scale-[0.92] disabled:opacity-50 shadow-[0_2px_6px_rgba(184,150,12,0.3)]">
          <ArrowRight size={20} />
        </button>
      </div>
    </div>
  );
}

function renderContent(content: string, onScreenChange?: (s: string) => void) {
  // Simple markdown-ish rendering
  return content.split('\n').map((line, i) => {
    // Bold
    let processed = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Italic
    processed = processed.replace(/\*(.*?)\*/g, '<em>$1</em>');
    // Links to quote review
    if (processed.includes('Review proposals') || processed.includes('→ Review')) {
      return <span key={i} dangerouslySetInnerHTML={{ __html: processed }} />;
    }
    return <span key={i} dangerouslySetInnerHTML={{ __html: processed + (i < content.split('\n').length - 1 ? '<br/>' : '') }} />;
  });
}
