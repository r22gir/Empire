'use client';
import { Message, AIModel, ChatSession } from '@/lib/types';
import { LayoutGrid, Plus, Crown } from 'lucide-react';
import MaxSection from './MaxSection';
import SideMenu from './SideMenu';

interface Props {
  // Max
  isStreaming: boolean;
  streamingContent: string;
  messages: Message[];
  backendOnline: boolean;
  selectedModel: string;
  models: AIModel[];
  // Desks
  onOpenDeskGrid: () => void;
  // Conversations
  conversations: ChatSession[];
  activeConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onNewChat: () => void;
  onDeleteConversation: (id: string) => void;
  onRenameConversation: (id: string, title: string) => void;
  onSuggest: (prompt: string) => void;
}

export default function LeftColumn({
  isStreaming, streamingContent, messages, backendOnline, selectedModel, models,
  onOpenDeskGrid,
  conversations, activeConversationId, onSelectConversation, onNewChat,
  onDeleteConversation, onRenameConversation, onSuggest,
}: Props) {
  return (
    <div
      className="flex-[2] flex flex-col min-w-0 overflow-hidden"
      style={{ borderRight: '1px solid var(--border)' }}
    >
      {/* Header */}
      <div className="shrink-0 px-6 pt-5 pb-4">
        <div className="flex items-center gap-3 mb-1">
          <Crown className="w-5 h-5" style={{ color: 'var(--gold)' }} />
          <h1 className="font-bold text-lg text-gold-shimmer tracking-wide">FOUNDERS EDITION</h1>
        </div>
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
          Personal command center with access to Empire Box
        </p>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto px-6 pb-4 space-y-4">
        {/* MAX Section */}
        <MaxSection
          isStreaming={isStreaming}
          streamingContent={streamingContent}
          messages={messages}
          backendOnline={backendOnline}
          selectedModel={selectedModel}
          models={models}
        />

        {/* AI Desks button + New Chat */}
        <div className="flex gap-3">
          <button
            onClick={onOpenDeskGrid}
            className="flex-1 flex items-center justify-center gap-2.5 py-3 rounded-xl font-semibold text-sm transition-all"
            style={{
              background: 'var(--gold)',
              color: '#0a0a0a',
              border: '1px solid var(--gold-bright)',
              boxShadow: '0 0 20px rgba(212,175,55,0.15)',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--gold-bright)'; e.currentTarget.style.boxShadow = '0 0 30px rgba(212,175,55,0.25)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'var(--gold)'; e.currentTarget.style.boxShadow = '0 0 20px rgba(212,175,55,0.15)'; }}
          >
            <LayoutGrid className="w-4.5 h-4.5" />
            AI DESKS
          </button>
          <button
            onClick={onNewChat}
            className="flex items-center justify-center gap-2 px-5 py-3 rounded-xl font-semibold text-sm transition"
            style={{
              background: 'var(--surface)',
              color: 'var(--gold)',
              border: '1px solid var(--gold-border)',
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--gold)'; e.currentTarget.style.background = 'var(--gold-pale)'; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--gold-border)'; e.currentTarget.style.background = 'var(--surface)'; }}
          >
            <Plus className="w-4 h-4" />
            New Chat
          </button>
        </div>

        {/* Side Menu */}
        <SideMenu
          conversations={conversations}
          activeConversationId={activeConversationId}
          onSelectConversation={onSelectConversation}
          onNewChat={onNewChat}
          onDeleteConversation={onDeleteConversation}
          onRenameConversation={onRenameConversation}
          onSuggest={onSuggest}
        />
      </div>
    </div>
  );
}
