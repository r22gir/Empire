'use client';
import { Message, AIModel, ChatSession } from '@/lib/types';
import { LayoutGrid, Plus, ChevronDown, ChevronRight, MessageSquare, Trash2, Pencil, Check, X, Rocket } from 'lucide-react';
import { useState } from 'react';
import MaxSection from './MaxSection';

const SUGGESTIONS = [
  { label: 'Health', prompt: 'Run a full system health check — CPU, RAM, disk, and all services.' },
  { label: 'Tasks', prompt: 'Show me all open and in-progress tasks across all desks.' },
  { label: 'Quote', prompt: 'Help me create a new quote for a client in WorkroomForge.' },
  { label: 'Today', prompt: 'Give me a summary of today\'s activity across all desks.' },
];

interface Props {
  isStreaming: boolean;
  streamingContent: string;
  messages: Message[];
  backendOnline: boolean;
  selectedModel: string;
  models: AIModel[];
  onOpenDeskGrid: () => void;
  conversations: ChatSession[];
  activeConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onNewChat: () => void;
  onDeleteConversation: (id: string) => void;
  onRenameConversation: (id: string, title: string) => void;
  onSuggest: (prompt: string) => void;
  onOpenWorkspaces?: () => void;
  onOpenWorkspace?: (id: string) => void;
}

export default function LeftColumn({
  isStreaming, streamingContent, messages, backendOnline, selectedModel, models,
  onOpenDeskGrid,
  conversations, activeConversationId, onSelectConversation, onNewChat,
  onDeleteConversation, onRenameConversation, onSuggest,
  onOpenWorkspaces, onOpenWorkspace,
}: Props) {
  const [showConvos, setShowConvos] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');

  const startEdit = (id: string, title: string) => { setEditingId(id); setEditTitle(title); };
  const saveEdit = (id: string) => { if (editTitle.trim()) onRenameConversation(id, editTitle.trim()); setEditingId(null); };

  const formatTime = (iso: string) => {
    const d = new Date(iso);
    const diff = Date.now() - d.getTime();
    if (diff < 86_400_000) return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    if (diff < 604_800_000) return d.toLocaleDateString([], { weekday: 'short' });
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  return (
    <div
      className="flex-[2] flex flex-col min-w-0 min-h-0 overflow-hidden"
      style={{ borderRight: '1px solid var(--border)' }}
    >
      {/* MAX Section — fills available space */}
      <MaxSection
        isStreaming={isStreaming}
        streamingContent={streamingContent}
        messages={messages}
        backendOnline={backendOnline}
        selectedModel={selectedModel}
        models={models}
      />

      {/* Bottom toolbar — compact */}
      <div className="shrink-0 px-3 py-2 space-y-2" style={{ borderTop: '1px solid var(--border)' }}>
        {/* Quick actions row + desk + new chat */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={onOpenDeskGrid}
            className="flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-semibold transition"
            style={{ background: 'var(--gold)', color: '#0a0a0a', border: '1px solid var(--gold-bright)' }}
          >
            <LayoutGrid className="w-3 h-3" />
            Desks
          </button>
          {onOpenWorkspaces && (
            <button
              onClick={onOpenWorkspaces}
              className="flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-semibold transition"
              style={{ background: 'var(--purple)', color: '#fff', border: '1px solid var(--purple-border)' }}
            >
              <Rocket className="w-3 h-3" />
              Apps
            </button>
          )}
          <button
            onClick={onNewChat}
            className="flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-medium transition"
            style={{ background: 'var(--surface)', color: 'var(--gold)', border: '1px solid var(--gold-border)' }}
          >
            <Plus className="w-3 h-3" />
            New
          </button>
          <div className="w-px h-4 mx-0.5" style={{ background: 'var(--border)' }} />
          {SUGGESTIONS.map(s => (
            <button
              key={s.label}
              onClick={() => onSuggest(s.prompt)}
              className="px-2 py-1 rounded-lg text-[10px] transition"
              style={{ background: 'var(--raised)', color: 'var(--text-muted)', border: '1px solid var(--border)' }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--gold-border)'; e.currentTarget.style.color = 'var(--text-primary)'; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text-muted)'; }}
            >
              {s.label}
            </button>
          ))}
        </div>

        {/* Conversations — hidden when empty, thin accordion */}
        {conversations.length > 0 && (
          <div>
            <button
              onClick={() => setShowConvos(!showConvos)}
              className="flex items-center gap-1.5 w-full"
            >
              {showConvos
                ? <ChevronDown className="w-2.5 h-2.5" style={{ color: 'var(--text-muted)' }} />
                : <ChevronRight className="w-2.5 h-2.5" style={{ color: 'var(--text-muted)' }} />
              }
              <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
                {conversations.length} conversation{conversations.length !== 1 ? 's' : ''}
              </span>
            </button>
            {showConvos && (
              <div className="mt-1 space-y-0.5 max-h-28 overflow-y-auto">
                {conversations.slice(0, 8).map(c => {
                  const active = activeConversationId === c.id;
                  return (
                    <div
                      key={c.id}
                      onClick={() => { if (editingId !== c.id) onSelectConversation(c.id); }}
                      className="group flex items-center gap-1.5 px-2 py-1 rounded cursor-pointer transition"
                      style={{
                        background: active ? 'var(--gold-pale)' : 'transparent',
                        borderLeft: `2px solid ${active ? 'var(--gold)' : 'transparent'}`,
                      }}
                      onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'var(--hover)'; }}
                      onMouseLeave={e => { if (!active) e.currentTarget.style.background = active ? 'var(--gold-pale)' : 'transparent'; }}
                    >
                      <MessageSquare className="w-2.5 h-2.5 shrink-0" style={{ color: active ? 'var(--gold)' : 'var(--text-muted)' }} />
                      {editingId === c.id ? (
                        <div className="flex items-center gap-1 flex-1">
                          <input
                            value={editTitle}
                            onChange={e => setEditTitle(e.target.value)}
                            onKeyDown={e => { if (e.key === 'Enter') saveEdit(c.id); if (e.key === 'Escape') setEditingId(null); }}
                            className="w-full rounded px-1 py-0.5 text-[10px] outline-none"
                            style={{ background: 'var(--raised)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
                            autoFocus
                            onClick={e => e.stopPropagation()}
                          />
                          <button onClick={e => { e.stopPropagation(); saveEdit(c.id); }} style={{ color: '#22c55e' }}><Check className="w-2.5 h-2.5" /></button>
                          <button onClick={e => { e.stopPropagation(); setEditingId(null); }} style={{ color: 'var(--text-secondary)' }}><X className="w-2.5 h-2.5" /></button>
                        </div>
                      ) : (
                        <>
                          <span className="flex-1 text-[10px] truncate" style={{ color: active ? 'var(--gold)' : 'var(--text-primary)' }}>{c.title}</span>
                          <span className="text-[9px] shrink-0" style={{ color: 'var(--text-muted)' }}>{formatTime(c.updated_at)}</span>
                          <div className="flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                            <button onClick={e => { e.stopPropagation(); startEdit(c.id, c.title); }} className="p-0.5" style={{ color: 'var(--text-muted)' }}><Pencil className="w-2.5 h-2.5" /></button>
                            <button onClick={e => { e.stopPropagation(); if (confirm('Delete?')) onDeleteConversation(c.id); }} className="p-0.5" style={{ color: 'var(--text-muted)' }}><Trash2 className="w-2.5 h-2.5" /></button>
                          </div>
                        </>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
