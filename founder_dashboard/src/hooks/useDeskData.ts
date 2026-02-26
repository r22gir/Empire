'use client';
import { useState, useEffect, useCallback, useRef } from 'react';
import { Task } from '@/lib/types';
import { taskApi } from '@/lib/api';
import type { DeskId } from '@/lib/deskData';

interface UseDeskDataReturn {
  tasks: Task[];
  total: number;
  isOnline: boolean;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
  createTask: (data: {
    title: string; description?: string; priority?: string;
    assigned_to?: string; due_date?: string; tags?: string[];
    metadata?: Record<string, unknown>;
  }) => Promise<Task | null>;
  updateTask: (id: string, data: Partial<{
    title: string; description: string; status: string;
    priority: string; assigned_to: string; due_date: string;
    tags: string[]; metadata: Record<string, unknown>;
  }>) => Promise<Task | null>;
  deleteTask: (id: string) => Promise<boolean>;
}

const CACHE_PREFIX = 'empire_tasks_';

function getCached(desk: string): Task[] {
  try {
    const raw = localStorage.getItem(CACHE_PREFIX + desk);
    if (raw) return JSON.parse(raw);
  } catch { /* ignore */ }
  return [];
}

function setCache(desk: string, tasks: Task[]) {
  try {
    localStorage.setItem(CACHE_PREFIX + desk, JSON.stringify(tasks));
    localStorage.setItem('empire_last_sync_' + desk, new Date().toISOString());
  } catch { /* ignore */ }
}

export function useDeskData(desk: DeskId): UseDeskDataReturn {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [total, setTotal] = useState(0);
  const [isOnline, setIsOnline] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchTasks = useCallback(async () => {
    try {
      const res = await taskApi.list({ desk, limit: 200 });
      setTasks(res.tasks);
      setTotal(res.total);
      setIsOnline(true);
      setError(null);
      setCache(desk, res.tasks);
    } catch {
      setIsOnline(false);
      const cached = getCached(desk);
      if (cached.length) {
        setTasks(cached);
        setTotal(cached.length);
      }
      setError('Backend offline');
    } finally {
      setIsLoading(false);
    }
  }, [desk]);

  useEffect(() => {
    setIsLoading(true);
    fetchTasks();
    pollRef.current = setInterval(fetchTasks, 30_000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [fetchTasks]);

  const createTask = useCallback(async (data: {
    title: string; description?: string; priority?: string;
    assigned_to?: string; due_date?: string; tags?: string[];
    metadata?: Record<string, unknown>;
  }): Promise<Task | null> => {
    try {
      const res = await taskApi.create({ ...data, desk });
      await fetchTasks();
      return res.task;
    } catch {
      setError('Failed to create task');
      return null;
    }
  }, [desk, fetchTasks]);

  const updateTask = useCallback(async (id: string, data: Partial<{
    title: string; description: string; status: string;
    priority: string; assigned_to: string; due_date: string;
    tags: string[]; metadata: Record<string, unknown>;
  }>): Promise<Task | null> => {
    // Optimistic update
    setTasks(prev => prev.map(t => t.id === id ? { ...t, ...data } as Task : t));
    try {
      const res = await taskApi.update(id, data);
      await fetchTasks();
      return res.task;
    } catch {
      await fetchTasks(); // revert
      setError('Failed to update task');
      return null;
    }
  }, [fetchTasks]);

  const deleteTask = useCallback(async (id: string): Promise<boolean> => {
    setTasks(prev => prev.filter(t => t.id !== id));
    try {
      await taskApi.delete(id);
      await fetchTasks();
      return true;
    } catch {
      await fetchTasks();
      setError('Failed to delete task');
      return false;
    }
  }, [fetchTasks]);

  return {
    tasks, total, isOnline, isLoading, error,
    refetch: fetchTasks, createTask, updateTask, deleteTask,
  };
}
