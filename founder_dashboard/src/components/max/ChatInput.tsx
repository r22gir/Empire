'use client';
import { useRef, useState, useEffect } from 'react';
import { FolderOpen, Paperclip, Send, Square, Mic } from 'lucide-react';

const FILE_ACCEPT = 'image/*,.m4a,.mp3,.wav,.ogg,.flac,.aac,.pdf,.txt,.md,.csv,.json,.doc,.docx';

function getFileIcon(name: string): string {
  const ext = name.split('.').pop()?.toLowerCase() || '';
  if (['m4a', 'mp3', 'wav', 'ogg', 'flac', 'aac', 'wma'].includes(ext)) return '🎵';
  if (['pdf', 'doc', 'docx'].includes(ext)) return '📄';
  if (['txt', 'md', 'csv', 'json'].includes(ext)) return '📝';
  if (['py', 'js', 'ts', 'tsx', 'jsx', 'html', 'css', 'sh'].includes(ext)) return '💻';
  return '📐';
}

function getFilePlaceholder(name: string): string {
  const ext = name.split('.').pop()?.toLowerCase() || '';
  if (['m4a', 'mp3', 'wav', 'ogg', 'flac', 'aac', 'wma'].includes(ext)) return 'Ask about this audio…';
  if (['pdf', 'doc', 'docx', 'txt', 'md', 'csv', 'json'].includes(ext)) return 'Ask about this document…';
  return 'Ask about this image…';
}

interface ChatInputProps {
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
  onVoice?: () => void;
}

export default function ChatInput({
  onSend, isStreaming, onStop, onOpenBrowser, onFileUpload, uploading,
  pastedPreview, onUploadPasted, onCancelPasted, selectedImage, onClearImage,
  onVoice,
}: ChatInputProps) {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const maxH = Math.max(200, window.innerHeight * 0.22);
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, maxH) + 'px';
    }
  }, [input]);

  const handleSend = () => {
    if (!input.trim() || isStreaming) return;
    onSend(input);
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  return (
    <div
      className="shrink-0"
      style={{
        background: 'linear-gradient(180deg, rgba(5,5,13,0.0) 0%, var(--void) 12%)',
        borderTop: '1px solid var(--border)',
        minHeight: '25vh',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'flex-end',
        padding: '16px 20px 18px',
      }}
    >
      {/* Pasted image preview */}
      {pastedPreview && (
        <div
          className="mb-3 p-3 rounded-xl flex items-center gap-3"
          style={{ background: 'var(--gold-pale)', border: '1px solid var(--gold-border)' }}
        >
          <img src={pastedPreview} alt="Pasted" className="w-14 h-14 object-cover rounded-lg" />
          <div className="flex-1">
            <p className="text-sm font-medium" style={{ color: 'var(--gold)' }}>Image from clipboard</p>
            <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>Upload to attach to message</p>
          </div>
          <button
            onClick={onUploadPasted}
            className="px-3 py-1.5 rounded-lg text-sm font-medium transition"
            style={{ background: 'var(--gold)', color: '#0a0a0a' }}
          >
            Upload
          </button>
          <button onClick={onCancelPasted} className="px-2 text-lg" style={{ color: 'var(--text-secondary)' }}>×</button>
        </div>
      )}

      {/* Selected file indicator */}
      {selectedImage && !pastedPreview && (
        <div
          className="mb-3 px-3 py-2 rounded-xl flex items-center justify-between text-sm"
          style={{ background: 'var(--gold-pale)', border: '1px solid var(--gold-border)' }}
        >
          <span style={{ color: 'var(--gold)' }}>{getFileIcon(selectedImage.name)} {selectedImage.name}</span>
          <button onClick={onClearImage} className="text-lg leading-none" style={{ color: 'var(--text-secondary)' }}>×</button>
        </div>
      )}

      {/* Main input row */}
      <div className="flex gap-3 items-end">
        {/* File action buttons */}
        <div className="flex flex-col gap-1.5">
          <button
            onClick={onOpenBrowser}
            className="w-10 h-10 rounded-xl flex items-center justify-center transition"
            style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
            title="Browse files"
          >
            <FolderOpen className="w-4.5 h-4.5" />
          </button>
          <label
            className="w-10 h-10 rounded-xl flex items-center justify-center cursor-pointer transition"
            style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
            title="Upload file"
          >
            <input type="file" accept={FILE_ACCEPT} onChange={onFileUpload} className="hidden" />
            {uploading ? <span className="text-sm animate-pulse">⏳</span> : <Paperclip className="w-4.5 h-4.5" />}
          </label>
        </div>

        {/* Textarea — premium dark input */}
        <textarea
          ref={textareaRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
          placeholder={selectedImage ? getFilePlaceholder(selectedImage.name) : 'Message MAX…'}
          className="flex-1 resize-none rounded-2xl px-5 py-4 text-sm outline-none transition"
          style={{
            minHeight: '60px',
            maxHeight: `${Math.max(200, 22)}vh`,
            background: 'var(--surface)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border)',
            fontFamily: 'inherit',
            fontSize: '0.95rem',
            lineHeight: '1.65',
          }}
          onFocus={e => { e.currentTarget.style.borderColor = 'rgba(212,175,55,0.35)'; e.currentTarget.style.boxShadow = '0 0 20px rgba(212,175,55,0.08)'; }}
          onBlur={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.boxShadow = 'none'; }}
          rows={2}
        />

        {/* Right side — Voice + Send/Stop stacked */}
        <div className="flex flex-col items-center gap-2">
          {/* Large gold voice button */}
          {onVoice && (
            <button
              onClick={onVoice}
              className="rounded-full flex items-center justify-center transition-all mic-pulse"
              style={{
                width: '60px',
                height: '60px',
                background: 'linear-gradient(135deg, #D4AF37 0%, #C9A025 50%, #B8962E 100%)',
                color: '#0a0a0a',
                border: '2px solid var(--gold-bright)',
                boxShadow: '0 0 24px rgba(212,175,55,0.2)',
              }}
              title="Voice chat"
            >
              <Mic className="w-7 h-7" />
            </button>
          )}

          {/* Send / Stop */}
          {isStreaming ? (
            <button
              onClick={onStop}
              className="w-11 h-11 rounded-xl flex items-center justify-center transition shrink-0"
              style={{ background: '#7f1d1d', border: '1px solid #ef4444', color: '#fca5a5' }}
              title="Stop"
            >
              <Square className="w-4 h-4 fill-current" />
            </button>
          ) : (
            <button
              onClick={handleSend}
              disabled={!input.trim()}
              className="w-11 h-11 rounded-xl flex items-center justify-center transition shrink-0"
              style={{
                background: input.trim() ? 'var(--gold)' : 'var(--raised)',
                color:      input.trim() ? '#0a0a0a'    : 'var(--text-muted)',
                border:     input.trim() ? '1px solid var(--gold-bright)' : '1px solid var(--border)',
              }}
              title="Send"
            >
              <Send className="w-4.5 h-4.5" />
            </button>
          )}
        </div>
      </div>

      <p className="text-center mt-2.5 text-xs" style={{ color: 'var(--text-muted)' }}>
        Shift+Enter for newline · Ctrl+V to paste images · Upload audio, docs & images
      </p>
    </div>
  );
}
