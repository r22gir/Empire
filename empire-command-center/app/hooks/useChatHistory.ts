'use client';
import { useState, useEffect, useCallback } from 'react';
import { API } from '../lib/api';
import { Conversation, BusinessTab } from '../lib/types';

export function useChatHistory() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchConversations = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(API + '/chats');
      if (res.ok) {
        const data = await res.json();
        const convs = (data.chats || data || []).map((c: any) => ({
          id: c.id,
          title: c.title || 'Untitled',
          preview: c.preview || c.last_message || '',
          timestamp: c.updated_at || c.created_at || '',
          business: c.business || c.desk || undefined,
        }));
        setConversations(convs);
      }
    } catch { /* silent */ }
    setLoading(false);
  }, []);

  const createConversation = useCallback(async (title?: string) => {
    try {
      const res = await fetch(API + '/chats', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: title || 'New Chat' }),
      });
      if (res.ok) {
        await fetchConversations();
        return (await res.json()).id;
      }
    } catch { /* silent */ }
    return null;
  }, [fetchConversations]);

  const filterByBusiness = useCallback((tab: BusinessTab): Conversation[] => {
    if (tab === 'max') return conversations;
    return conversations.filter(c => c.business === tab);
  }, [conversations]);

  useEffect(() => { fetchConversations(); }, [fetchConversations]);

  return { conversations, loading, fetchConversations, createConversation, filterByBusiness };
}
