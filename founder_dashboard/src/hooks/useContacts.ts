'use client';
import { useState, useEffect, useCallback, useRef } from 'react';
import { Contact } from '@/lib/types';
import { contactApi } from '@/lib/api';

interface UseContactsReturn {
  contacts: Contact[];
  total: number;
  isOnline: boolean;
  isLoading: boolean;
  error: string | null;
  search: string;
  setSearch: (q: string) => void;
  refetch: () => void;
  createContact: (data: {
    name: string; type: string; phone?: string; email?: string;
    address?: string; notes?: string; metadata?: Record<string, unknown>;
  }) => Promise<Contact | null>;
  updateContact: (id: string, data: Partial<{
    name: string; type: string; phone: string; email: string;
    address: string; notes: string; metadata: Record<string, unknown>;
  }>) => Promise<Contact | null>;
  deleteContact: (id: string) => Promise<boolean>;
}

const CACHE_KEY = 'empire_contacts';

function getCached(type?: string): Contact[] {
  try {
    const raw = localStorage.getItem(CACHE_KEY + (type ? '_' + type : ''));
    if (raw) return JSON.parse(raw);
  } catch { /* ignore */ }
  return [];
}

function setCache(contacts: Contact[], type?: string) {
  try {
    localStorage.setItem(CACHE_KEY + (type ? '_' + type : ''), JSON.stringify(contacts));
  } catch { /* ignore */ }
}

export function useContacts(type?: 'client' | 'contractor' | 'vendor' | 'other'): UseContactsReturn {
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [total, setTotal] = useState(0);
  const [isOnline, setIsOnline] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const searchRef = useRef(search);
  searchRef.current = search;

  const fetchContacts = useCallback(async () => {
    try {
      const res = await contactApi.list({
        type,
        search: searchRef.current || undefined,
        limit: 200,
      });
      setContacts(res.contacts);
      setTotal(res.total);
      setIsOnline(true);
      setError(null);
      if (!searchRef.current) setCache(res.contacts, type);
    } catch {
      setIsOnline(false);
      const cached = getCached(type);
      if (cached.length) {
        setContacts(cached);
        setTotal(cached.length);
      }
      setError('Backend offline');
    } finally {
      setIsLoading(false);
    }
  }, [type]);

  useEffect(() => {
    setIsLoading(true);
    fetchContacts();
    pollRef.current = setInterval(fetchContacts, 30_000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [fetchContacts]);

  // Debounced search
  useEffect(() => {
    const t = setTimeout(fetchContacts, 300);
    return () => clearTimeout(t);
  }, [search, fetchContacts]);

  const createContact = useCallback(async (data: {
    name: string; type: string; phone?: string; email?: string;
    address?: string; notes?: string; metadata?: Record<string, unknown>;
  }): Promise<Contact | null> => {
    try {
      const res = await contactApi.create(data);
      await fetchContacts();
      return res.contact;
    } catch {
      setError('Failed to create contact');
      return null;
    }
  }, [fetchContacts]);

  const updateContact = useCallback(async (id: string, data: Partial<{
    name: string; type: string; phone: string; email: string;
    address: string; notes: string; metadata: Record<string, unknown>;
  }>): Promise<Contact | null> => {
    setContacts(prev => prev.map(c => c.id === id ? { ...c, ...data } as Contact : c));
    try {
      const res = await contactApi.update(id, data);
      await fetchContacts();
      return res.contact;
    } catch {
      await fetchContacts();
      setError('Failed to update contact');
      return null;
    }
  }, [fetchContacts]);

  const deleteContact = useCallback(async (id: string): Promise<boolean> => {
    setContacts(prev => prev.filter(c => c.id !== id));
    try {
      await contactApi.delete(id);
      await fetchContacts();
      return true;
    } catch {
      await fetchContacts();
      setError('Failed to delete contact');
      return false;
    }
  }, [fetchContacts]);

  return {
    contacts, total, isOnline, isLoading, error,
    search, setSearch, refetch: fetchContacts,
    createContact, updateContact, deleteContact,
  };
}
