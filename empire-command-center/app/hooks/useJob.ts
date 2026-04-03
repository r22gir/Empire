'use client';
import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import React from 'react';
import { API } from '../lib/api';

export interface Job {
  id: number;
  job_number: string;
  client_name: string;
  client_email?: string;
  client_phone?: string;
  client_address?: string;
  business_unit: string;
  title?: string;
  description?: string;
  room?: string;
  status: string;
  pipeline_stage: string;
  customer_id?: number;
  quote_id?: number;
  invoice_id?: number;
  design_session_id?: number;
  photos?: string[];
  measurements?: Record<string, any>;
  items?: any[];
  drawings?: string[];
  estimated_value?: number;
  quoted_amount?: number;
  invoiced_amount?: number;
  paid_amount?: number;
  created_at?: string;
  updated_at?: string;
}

interface JobContextType {
  activeJob: Job | null;
  setActiveJob: (job: Job | null) => void;
  loadJob: (id: number) => Promise<void>;
  clearJob: () => void;
  isLoading: boolean;
}

const JobContext = createContext<JobContextType>({
  activeJob: null,
  setActiveJob: () => {},
  loadJob: async () => {},
  clearJob: () => {},
  isLoading: false,
});

const STORAGE_KEY = 'empire-active-job-id';

export function JobProvider({ children }: { children: ReactNode }) {
  const [activeJob, setActiveJobState] = useState<Job | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const loadJob = useCallback(async (id: number) => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API}/jobs/${id}`);
      if (res.ok) {
        const job = await res.json();
        setActiveJobState(job);
        localStorage.setItem(STORAGE_KEY, String(id));
      }
    } catch { /* silent */ }
    setIsLoading(false);
  }, []);

  const setActiveJob = useCallback((job: Job | null) => {
    setActiveJobState(job);
    if (job) {
      localStorage.setItem(STORAGE_KEY, String(job.id));
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  }, []);

  const clearJob = useCallback(() => {
    setActiveJobState(null);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  // Restore from localStorage on mount
  useEffect(() => {
    const savedId = localStorage.getItem(STORAGE_KEY);
    if (savedId) {
      loadJob(Number(savedId));
    }
  }, [loadJob]);

  return React.createElement(JobContext.Provider,
    { value: { activeJob, setActiveJob, loadJob, clearJob, isLoading } },
    children
  );
}

export function useJob() {
  return useContext(JobContext);
}

export { JobContext };
