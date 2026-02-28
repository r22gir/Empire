'use client';
import { useState, useRef, useEffect } from 'react';
import { FolderOpen, Paperclip, Send, Square, Mic } from 'lucide-react';
import { AIModel } from '@/lib/types';
import VoiceAgent from '../max/VoiceAgent';
import ModelSelector from '../max/ModelSelector';

const FILE_ACCEPT = 'image/*,.m4a,.mp3,.wav,.ogg,.flac,.aac,.pdf,.txt,.md,.csv,.json,.doc,.docx';

interface Props {
  onSend: (input: string) => void;
  isStreaming: boolean;
  onStop: () => void;
  onOpenBrowser: () => void;
  onFileUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
  uploading: boolean;
  pastedPreview: string | null;
  onUploadPasted: () => void;
  onCancelPasted: () => void;
  selectedImage: { name: string; category: string } | null;
  onClearImage: () => void;
  backendOnline: boolean;
  selectedModel: string;
  models: AIModel[];
  onModelChange: (m: string) => void;
  suggestedInput?: string;
  onClearSuggestion?: () => void;
}

export default function BottomBar({
  onSend, isStreaming, onStop, onOpenBrowser, onFileUpload, uploading,
  pastedPreview, onUploadPasted, onCancelPasted, selectedImage, onClearImage,
  backendOnline, selectedModel, models, onModelChange,
  suggestedInput, onClearSuggestion,
}: Props) {
  const [input, setInput] = useState('');
  const [showVoice, setShowVoice] = useState(false);
  const [showModel, setShowModel] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Handle suggested input from Quick Actions
  useEffect(() => {
    if (suggestedInput) {
      setInput(suggestedInput);
      onClearSuggestion?.();
      textareaRef.current?.focus();
    }
  }, [suggestedInput, onClearSuggestion]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 120) + 'px';
    }
  }, [input]);

  const handleSend = () => {
    if (!input.trim() || isStreaming) return;
    onSend(input);
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  return (
    <>
      <div
        className="shrink-0"
        style={{
          background: 'var(--void)',
          borderTop: '1px solid var(--border)',
        }}
      >
        {/* Pasted preview */}
        {pastedPreview && (
          <div
            className="mx-4 mt-3 p-3 rounded-xl flex items-center gap-3"
            style={{ background: 'var(--gold-pale)', border: '1px solid var(--gold-border)' }}
          >
            <img src={pastedPreview} alt="Pasted" className="w-12 h-12 object-cover rounded-lg" />
            <div className="flex-1">
              <p className="text-sm font-medium" style={{ color: 'var(--gold)' }}>Image from clipboard</p>
            </div>
            <button onClick={onUploadPasted} className="px-3 py-1.5 rounded-lg text-sm font-medium" style={{ background: 'var(--gold)', color: '#0a0a0a' }}>Upload</button>
            <button onClick={onCancelPasted} className="text-lg" style={{ color: 'var(--text-secondary)' }}>×</button>
          </div>
        )}

        {/* Selected file */}
        {selectedImage && !pastedPreview && (
          <div
            className="mx-4 mt-3 px-3 py-2 rounded-xl flex items-center justify-between text-sm"
            style={{ background: 'var(--gold-pale)', border: '1px solid var(--gold-border)' }}
          >
            <span style={{ color: 'var(--gold)' }}>📐 {selectedImage.name}</span>
            <button onClick={onClearImage} className="text-lg leading-none" style={{ color: 'var(--text-secondary)' }}>×</button>
          </div>
        )}

        {/* Main input row */}
        <div className="flex items-end gap-2 px-4 py-3">
          {/* File actions */}
          <div className="flex gap-1.5 pb-1">
            <button
              onClick={onOpenBrowser}
              className="w-9 h-9 rounded-xl flex items-center justify-center transition"
              style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
              title="Browse files"
            >
              <FolderOpen className="w-4 h-4" />
            </button>
            <label
              className="w-9 h-9 rounded-xl flex items-center justify-center cursor-pointer transition"
              style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
              title="Upload file"
            >
              <input type="file" accept={FILE_ACCEPT} onChange={onFileUpload} className="hidden" />
              {uploading ? <span className="text-sm animate-pulse">⏳</span> : <Paperclip className="w-4 h-4" />}
            </label>
          </div>

          {/* Textarea */}
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
              placeholder={selectedImage ? 'Ask about this file...' : 'Message MAX...'}
              className="w-full resize-none rounded-2xl px-4 py-3 text-sm outline-none transition"
              style={{
                minHeight: '44px',
                maxHeight: '120px',
                background: 'var(--surface)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border)',
                fontFamily: 'inherit',
                lineHeight: '1.5',
              }}
              onFocus={e => { e.currentTarget.style.borderColor = 'rgba(212,175,55,0.35)'; e.currentTarget.style.boxShadow = '0 0 20px rgba(212,175,55,0.08)'; }}
              onBlur={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.boxShadow = 'none'; }}
              rows={1}
            />
          </div>

          {/* Voice button */}
          <button
            onClick={() => setShowVoice(true)}
            className="rounded-full flex items-center justify-center transition-all mic-pulse shrink-0"
            style={{
              width: '44px',
              height: '44px',
              background: 'linear-gradient(135deg, #D4AF37 0%, #B8962E 100%)',
              color: '#0a0a0a',
              border: '2px solid var(--gold-bright)',
            }}
            title="Voice chat"
          >
            <Mic className="w-5 h-5" />
          </button>

          {/* Send / Stop */}
          {isStreaming ? (
            <button
              onClick={onStop}
              className="w-10 h-10 rounded-xl flex items-center justify-center transition shrink-0"
              style={{ background: '#7f1d1d', border: '1px solid #ef4444', color: '#fca5a5' }}
              title="Stop"
            >
              <Square className="w-4 h-4 fill-current" />
            </button>
          ) : (
            <button
              onClick={handleSend}
              disabled={!input.trim()}
              className="w-10 h-10 rounded-xl flex items-center justify-center transition shrink-0"
              style={{
                background: input.trim() ? 'var(--gold)' : 'var(--raised)',
                color: input.trim() ? '#0a0a0a' : 'var(--text-muted)',
                border: input.trim() ? '1px solid var(--gold-bright)' : '1px solid var(--border)',
              }}
              title="Send"
            >
              <Send className="w-4 h-4" />
            </button>
          )}

          {/* Model selector toggle */}
          <div className="relative pb-1">
            <button
              onClick={() => setShowModel(!showModel)}
              className="px-2 py-1 rounded-lg text-[10px] font-mono transition"
              style={{
                background: 'var(--purple-pale)',
                color: 'var(--purple)',
                border: '1px solid var(--purple-border)',
              }}
            >
              {models.find(m => m.id === selectedModel)?.name || selectedModel}
            </button>
            {showModel && (
              <div
                className="absolute bottom-full mb-2 right-0 rounded-xl p-2 min-w-[180px]"
                style={{ background: 'var(--surface)', border: '1px solid var(--border)', zIndex: 60 }}
              >
                <ModelSelector models={models} selectedModel={selectedModel} onSelect={(m) => { onModelChange(m); setShowModel(false); }} />
              </div>
            )}
          </div>
        </div>

        {/* Bottom help text */}
        <p className="text-center pb-2 text-[10px]" style={{ color: 'var(--text-muted)' }}>
          Shift+Enter newline · Ctrl+V paste images · Upload audio, docs, images · {backendOnline ? 'Backend online' : 'Backend offline'}
        </p>
      </div>

      {/* Voice agent modal */}
      {showVoice && <VoiceAgent onClose={() => setShowVoice(false)} />}
    </>
  );
}
