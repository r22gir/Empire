'use client';
import { useState, useEffect, useCallback } from 'react';
import { ChatSession, Message } from '@/lib/types';
import { API_URL } from '@/lib/api';

/* ── localStorage helpers ────────────────────────────────────── */
const LS_SESSIONS = 'empire-chat-sessions';
const lsMsgKey    = (id: string) => `empire-chat-msgs-${id}`;

function lsGetSessions(): ChatSession[] {
  try { return JSON.parse(localStorage.getItem(LS_SESSIONS) || '[]'); } catch { return []; }
}
function lsSetSessions(s: ChatSession[]) {
  try { localStorage.setItem(LS_SESSIONS, JSON.stringify(s)); } catch {}
}
function lsGetMsgs(id: string): Message[] {
  try { return JSON.parse(localStorage.getItem(lsMsgKey(id)) || '[]'); } catch { return []; }
}
function lsSetMsgs(id: string, msgs: Message[]) {
  try { localStorage.setItem(lsMsgKey(id), JSON.stringify(msgs)); } catch {}
}
function lsDelSession(id: string) {
  try {
    localStorage.removeItem(lsMsgKey(id));
    lsSetSessions(lsGetSessions().filter(s => s.id !== id));
  } catch {}
}

/* ── timed fetch helper ──────────────────────────────────────── */
async function apiFetch(url: string, opts?: RequestInit): Promise<Response | null> {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), 4000);
  try {
    const r = await fetch(url, { ...opts, signal: ctrl.signal });
    clearTimeout(t);
    return r.ok ? r : null;
  } catch {
    clearTimeout(t);
    return null;
  }
}

export function useChatHistory() {
  const [conversations, setConversations] = useState<ChatSession[]>([]);
  const [activeId,      setActiveId]      = useState<string | null>(null);

  const fetchConversations = useCallback(async () => {
    const r = await apiFetch(API_URL + '/chats/list');
    if (r) {
      const d = await r.json();
      setConversations(d.chats || []);
    } else {
      setConversations(lsGetSessions());
    }
  }, []);

  useEffect(() => { fetchConversations(); }, [fetchConversations]);

  const loadConversation = useCallback(async (id: string): Promise<Message[]> => {
    setActiveId(id);
    const r = await apiFetch(API_URL + '/chats/' + id);
    if (r) {
      const d = await r.json();
      return (d.messages || []) as Message[];
    }
    return lsGetMsgs(id);
  }, []);

  const saveConversation = useCallback(async (messages: Message[], chatId: string | null): Promise<string | null> => {
    const firstUser = messages.find(m => m.role === 'user');
    const title = firstUser
      ? firstUser.content.slice(0, 50) + (firstUser.content.length > 50 ? '…' : '')
      : 'New Chat';
    const now = new Date().toISOString();

    /* try API */
    const r = chatId
      ? await apiFetch(API_URL + '/chats/' + chatId, {
          method: 'PUT', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ messages }),
        })
      : await apiFetch(API_URL + '/chats/save', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ messages, title }),
        });

    if (r) {
      const newId = chatId || (await r.json()).chat_id;
      setActiveId(newId);
      fetchConversations();
      return newId;
    }

    /* offline: localStorage */
    const id = chatId || ('local-' + Date.now());
    lsSetMsgs(id, messages);
    const sessions = lsGetSessions();
    const idx = sessions.findIndex(s => s.id === id);
    if (idx >= 0) {
      sessions[idx] = { ...sessions[idx], updated_at: now, message_count: messages.length };
    } else {
      sessions.unshift({ id, title, updated_at: now, message_count: messages.length });
    }
    lsSetSessions(sessions);
    setActiveId(id);
    setConversations([...sessions]);
    return id;
  }, [fetchConversations]);

  const deleteConversation = useCallback(async (id: string) => {
    await apiFetch(API_URL + '/chats/' + id, { method: 'DELETE' });
    lsDelSession(id);
    if (activeId === id) setActiveId(null);
    fetchConversations();
  }, [activeId, fetchConversations]);

  const renameConversation = useCallback(async (id: string, title: string) => {
    const r = await apiFetch(API_URL + '/chats/' + id + '/title', {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    });
    if (!r) {
      const sessions = lsGetSessions().map(s => s.id === id ? { ...s, title } : s);
      lsSetSessions(sessions);
      setConversations([...sessions]);
      return;
    }
    fetchConversations();
  }, [fetchConversations]);

  const startNewChat = useCallback(() => { setActiveId(null); }, []);

  return {
    conversations, activeId, setActiveId,
    loadConversation, saveConversation,
    deleteConversation, renameConversation,
    startNewChat, fetchConversations,
  };
}
