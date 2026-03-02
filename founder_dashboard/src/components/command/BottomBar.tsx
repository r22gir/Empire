'use client';
import { useState, useRef, useEffect } from 'react';
import { FolderOpen, Paperclip, Send, Square, Mic, Sparkles, BarChart3, ChevronUp, ChevronDown, GripVertical } from 'lucide-react';
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
  onToggleStats?: () => void;
}

export default function BottomBar({
  onSend, isStreaming, onStop, onOpenBrowser, onFileUpload, uploading,
  pastedPreview, onUploadPasted, onCancelPasted, selectedImage, onClearImage,
  backendOnline, selectedModel, models, onModelChange,
  suggestedInput, onClearSuggestion, onToggleStats,
}: Props) {
  const [input, setInput] = useState('');
  const [showVoice, setShowVoice] = useState(false);
  const [showModel, setShowModel] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  /* ── Drag & Drop handler ────────────────────────────── */
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      const dt = new DataTransfer();
      for (let i = 0; i < files.length; i++) dt.items.add(files[i]);
      const input = document.createElement('input');
      input.type = 'file';
      input.files = dt.files;
      onFileUpload({ target: input } as any);
    }
  };

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
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px';
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
      <div className="shrink-0 px-4 pb-3 pt-0" style={{ background: 'transparent' }}>
        {/* Collapse / Expand toggle */}
        <div className="flex justify-center">
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="flex items-center gap-1.5 px-4 py-1 rounded-t-lg text-[10px] font-medium transition-all"
            style={{
              background: 'rgba(255,255,255,0.04)',
              color: 'var(--cyan)',
              border: '1px solid var(--glass-border)',
              borderBottom: 'none',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--cyan-pale)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }}
            title={collapsed ? 'Expand command bar' : 'Collapse command bar'}
          >
            {collapsed ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            {collapsed ? 'MAX' : 'Collapse'}
          </button>
        </div>

        {collapsed ? (
          /* ── Collapsed mini bar ── */
          <div
            className="command-bar flex items-center justify-between px-4 py-2 cursor-pointer"
            onClick={() => setCollapsed(false)}
          >
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4" style={{ color: 'var(--cyan)' }} />
              <span className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>Ask MAX anything...</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full" style={{ background: backendOnline ? 'var(--cyan)' : '#ef4444', boxShadow: backendOnline ? '0 0 6px var(--cyan-pale)' : '0 0 6px rgba(239,68,68,0.3)' }} />
              <span className="text-[10px] font-mono" style={{ color: 'var(--purple)' }}>
                {models.find(m => m.id === selectedModel)?.name || selectedModel}
              </span>
            </div>
          </div>
        ) : (
          /* ── Full expanded bar ── */
          <>
            {/* Pasted preview — floats above command bar */}
            {pastedPreview && (
              <div
                className="mb-2 p-3 rounded-xl flex items-center gap-3 glass-card"
                style={{ borderColor: 'var(--gold-border)' }}
              >
                <img src={pastedPreview} alt="Pasted" className="w-12 h-12 object-cover rounded-lg" />
                <div className="flex-1">
                  <p className="text-sm font-medium" style={{ color: 'var(--gold)' }}>Image from clipboard</p>
                </div>
                <button onClick={onUploadPasted} className="px-3 py-1.5 rounded-lg text-sm font-medium" style={{ background: 'var(--gold)', color: '#0a0a0a' }}>Upload</button>
                <button onClick={onCancelPasted} className="text-lg" style={{ color: 'var(--text-secondary)' }}>×</button>
              </div>
            )}

            {/* Selected file indicator */}
            {selectedImage && !pastedPreview && (
              <div
                className="mb-2 px-3 py-2 rounded-xl flex items-center justify-between text-sm glass-card"
                style={{ borderColor: 'var(--gold-border)' }}
              >
                <span style={{ color: 'var(--gold)' }}>📐 {selectedImage.name}</span>
                <button onClick={onClearImage} className="text-lg leading-none" style={{ color: 'var(--text-secondary)' }}>×</button>
              </div>
            )}

            {/* Command Palette Bar — with drag & drop */}
            <div
              className={`command-bar flex items-end gap-2 px-3 py-2.5 ${dragOver ? 'drag-over' : ''}`}
              onDragOver={e => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
            >
              {/* Left actions */}
              <div className="flex gap-1 pb-0.5">
                <button
                  onClick={onOpenBrowser}
                  className="w-11 h-11 rounded-lg flex items-center justify-center transition"
                  style={{ color: 'var(--text-muted)' }}
                  onMouseEnter={e => { e.currentTarget.style.color = 'var(--cyan)'; e.currentTarget.style.background = 'var(--cyan-pale)'; }}
                  onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-muted)'; e.currentTarget.style.background = 'transparent'; }}
                  title="Browse files"
                >
                  <FolderOpen className="w-5 h-5" />
                </button>
                <label
                  className="w-11 h-11 rounded-lg flex items-center justify-center cursor-pointer transition"
                  style={{ color: 'var(--text-muted)' }}
                  onMouseEnter={e => { e.currentTarget.style.color = 'var(--cyan)'; e.currentTarget.style.background = 'var(--cyan-pale)'; }}
                  onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-muted)'; e.currentTarget.style.background = 'transparent'; }}
                  title="Upload file — or drag & drop"
                >
                  <input type="file" accept={FILE_ACCEPT} onChange={onFileUpload} className="hidden" />
                  {uploading ? <span className="text-lg animate-pulse">⏳</span> : <Paperclip className="w-5 h-5" />}
                </label>
                {onToggleStats && (
                  <button
                    onClick={onToggleStats}
                    className="w-11 h-11 rounded-lg flex items-center justify-center transition"
                    style={{ color: 'var(--text-muted)' }}
                    onMouseEnter={e => { e.currentTarget.style.color = 'var(--cyan)'; e.currentTarget.style.background = 'var(--cyan-pale)'; }}
                    onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-muted)'; e.currentTarget.style.background = 'transparent'; }}
                    title="Toggle stats"
                  >
                    <BarChart3 className="w-5 h-5" />
                  </button>
                )}
              </div>

              {/* Central input */}
              <div className="flex-1 relative">
                <div className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color: 'var(--cyan)', opacity: input.trim() ? 0 : 0.4 }}>
                  <Sparkles className="w-4 h-4" />
                </div>
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                  placeholder={selectedImage ? 'Ask about this file...' : 'Ask MAX anything...'}
                  className="w-full resize-none rounded-xl px-4 py-3 outline-none transition"
                  style={{
                    minHeight: '100px',
                    maxHeight: '200px',
                    fontSize: '16px',
                    background: 'transparent',
                    color: 'var(--text-primary)',
                    border: 'none',
                    fontFamily: 'inherit',
                    lineHeight: '1.6',
                    paddingLeft: input.trim() ? '16px' : '36px',
                  }}
                  rows={3}
                />
              </div>

              {/* Right actions */}
              <div className="flex items-center gap-1 pb-0.5">
                {/* Model selector */}
                <div className="relative">
                  <button
                    onClick={() => setShowModel(!showModel)}
                    className="px-2 py-1.5 rounded-lg text-[10px] font-mono transition"
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
                      className="absolute bottom-full mb-2 right-0 rounded-xl p-2 min-w-[180px] glass-card"
                      style={{ zIndex: 60 }}
                    >
                      <ModelSelector models={models} selectedModel={selectedModel} onSelect={(m) => { onModelChange(m); setShowModel(false); }} />
                    </div>
                  )}
                </div>

                {/* Voice button */}
                <button
                  onClick={() => setShowVoice(true)}
                  className="w-12 h-12 rounded-full flex items-center justify-center transition-all shrink-0"
                  style={{
                    background: 'linear-gradient(135deg, var(--cyan) 0%, var(--cyan-dim) 100%)',
                    color: '#0a0a0a',
                    border: '2px solid rgba(24,224,255,0.4)',
                    boxShadow: '0 0 12px var(--cyan-pale)',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.boxShadow = '0 0 20px var(--cyan-glow)'; }}
                  onMouseLeave={e => { e.currentTarget.style.boxShadow = '0 0 12px var(--cyan-pale)'; }}
                  title="Voice chat"
                >
                  <Mic className="w-5 h-5" />
                </button>

                {/* Send / Stop */}
                {isStreaming ? (
                  <button
                    onClick={onStop}
                    className="w-12 h-12 rounded-xl flex items-center justify-center transition shrink-0"
                    style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.3)', color: '#fca5a5' }}
                    title="Stop"
                  >
                    <Square className="w-4 h-4 fill-current" />
                  </button>
                ) : (
                  <button
                    onClick={handleSend}
                    disabled={!input.trim()}
                    className="w-12 h-12 rounded-xl flex items-center justify-center transition shrink-0"
                    style={{
                      background: input.trim() ? 'var(--cyan)' : 'rgba(255,255,255,0.04)',
                      color: input.trim() ? '#0a0a0a' : 'var(--text-muted)',
                      border: input.trim() ? '1px solid rgba(24,224,255,0.4)' : '1px solid var(--glass-border)',
                      boxShadow: input.trim() ? '0 0 12px var(--cyan-pale)' : 'none',
                    }}
                    title="Send"
                  >
                    <Send className="w-5 h-5" />
                  </button>
                )}
              </div>
            </div>

            {/* Status line */}
            <div className="flex items-center justify-center gap-3 mt-1.5">
              <span className="text-[9px]" style={{ color: 'var(--text-muted)' }}>
                Shift+Enter newline · Ctrl+V paste
              </span>
              <div className="w-1 h-1 rounded-full" style={{ background: backendOnline ? 'var(--cyan)' : '#ef4444', boxShadow: backendOnline ? '0 0 6px var(--cyan-pale)' : '0 0 6px rgba(239,68,68,0.3)' }} />
              <span className="text-[9px]" style={{ color: backendOnline ? 'var(--cyan)' : '#ef4444' }}>
                {backendOnline ? 'Connected' : 'Offline'}
              </span>
            </div>
          </>
        )}
      </div>

      {/* Voice agent modal */}
      {showVoice && <VoiceAgent onClose={() => setShowVoice(false)} />}
    </>
  );
}
