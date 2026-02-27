'use client';
import { useRef, useState, useEffect } from 'react';
import { FolderOpen, Paperclip, Send, Square } from 'lucide-react';

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
}

export default function ChatInput({
  onSend, isStreaming, onStop, onOpenBrowser, onFileUpload, uploading,
  pastedPreview, onUploadPasted, onCancelPasted, selectedImage, onClearImage,
}: ChatInputProps) {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

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
    <div
      className="p-4 shrink-0"
      style={{
        background: 'var(--void)',
        borderTop: '1px solid var(--border)',
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

      {/* Selected image indicator */}
      {selectedImage && !pastedPreview && (
        <div
          className="mb-3 px-3 py-2 rounded-xl flex items-center justify-between text-sm"
          style={{ background: 'var(--gold-pale)', border: '1px solid var(--gold-border)' }}
        >
          <span style={{ color: 'var(--gold)' }}>📐 {selectedImage.name}</span>
          <button onClick={onClearImage} className="text-lg leading-none" style={{ color: 'var(--text-secondary)' }}>×</button>
        </div>
      )}

      <div className="flex gap-2 items-end">
        {/* File action buttons */}
        <div className="flex flex-col gap-1.5">
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
            <input type="file" onChange={onFileUpload} className="hidden" />
            {uploading ? <span className="text-sm animate-pulse">⏳</span> : <Paperclip className="w-4 h-4" />}
          </label>
        </div>

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
          placeholder={selectedImage ? 'Ask about this image…' : 'Message MAX…'}
          className="flex-1 resize-none rounded-xl px-4 py-2.5 text-sm outline-none transition"
          style={{
            minHeight: '44px',
            maxHeight: '200px',
            background: 'var(--surface)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border)',
            fontFamily: 'inherit',
          }}
          onFocus={e => { e.currentTarget.style.borderColor = 'var(--gold-border)'; }}
          onBlur={e => { e.currentTarget.style.borderColor = 'var(--border)'; }}
          rows={1}
        />

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
              color:      input.trim() ? '#0a0a0a'    : 'var(--text-muted)',
              border:     '1px solid transparent',
            }}
            title="Send"
          >
            <Send className="w-4 h-4" />
          </button>
        )}
      </div>

      <p className="text-center mt-2 text-xs" style={{ color: 'var(--text-muted)' }}>
        Shift+Enter for newline · Ctrl+V to paste images
      </p>
    </div>
  );
}
