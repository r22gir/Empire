/**
 * usePricingAudit — localStorage-backed pricing audit tracking
 * Phase 1.5 frontend-only prototype
 *
 * Tracks manual overrides, AI assumptions, measurement approval,
 * and pricing approval state per draft session.
 */

import { useState, useCallback, useEffect } from 'react';

export interface PricingAuditEntry {
  draftId: string;
  pricingReviewedAt?: string;
  pricingReviewedBy: 'founder' | 'local';
  dimensionsSource: 'ai_estimate' | 'manual' | 'unknown';
  measurementsApproved: boolean;
  pricingApproved: boolean;
  selectedTier?: 'A' | 'B' | 'C' | null;
  renderTierConfirmed?: boolean;
  manualOverrides: {
    field: string;
    original: unknown;
    override: unknown;
  }[];
  aiAssumptions: {
    field: string;
    value: unknown;
    confidence?: number | null;
  }[];
  approvalNotes?: string;
}

const STORAGE_KEY = 'transcriptforge_pricing_audit'; // reuse existing prefix pattern
const MAX_ENTRIES = 50;

function generateDraftId(): string {
  return `pricing_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function loadStore(): PricingAuditEntry[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveStore(entries: PricingAuditEntry[]): void {
  try {
    // Trim to MAX_ENTRIES most recent
    const trimmed = entries.slice(-MAX_ENTRIES);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
  } catch (e) {
    console.warn('[PricingAudit] localStorage quota exceeded — audit will not persist', e);
  }
}

export function usePricingAudit() {
  const [currentEntry, setCurrentEntry] = useState<PricingAuditEntry | null>(null);

  // ── Initialise a new draft audit entry ──────────────────────────────────
  const initAudit = useCallback((initialData?: Partial<PricingAuditEntry>): PricingAuditEntry => {
    const entry: PricingAuditEntry = {
      draftId: generateDraftId(),
      pricingReviewedBy: 'local',
      dimensionsSource: 'unknown',
      measurementsApproved: false,
      pricingApproved: false,
      selectedTier: null,
      renderTierConfirmed: false,
      manualOverrides: [],
      aiAssumptions: [],
      ...initialData,
    };
    setCurrentEntry(entry);
    return entry;
  }, []);

  // ── Persist current entry to localStorage ────────────────────────────────
  const persistEntry = useCallback((entry: PricingAuditEntry) => {
    const store = loadStore();
    const existingIdx = store.findIndex(e => e.draftId === entry.draftId);
    if (existingIdx >= 0) {
      store[existingIdx] = entry;
    } else {
      store.push(entry);
    }
    saveStore(store);
  }, []);

  // ── Record an AI assumption ──────────────────────────────────────────────
  const recordAiAssumption = useCallback((
    field: string,
    value: unknown,
    confidence?: number | null,
  ) => {
    if (!currentEntry) return;
    setCurrentEntry(prev => {
      if (!prev) return prev;
      const updated: PricingAuditEntry = {
        ...prev,
        aiAssumptions: [
          ...prev.aiAssumptions.filter(a => a.field !== field),
          { field, value, confidence },
        ],
      };
      persistEntry(updated);
      return updated;
    });
  }, [currentEntry, persistEntry]);

  // ── Record a manual override ─────────────────────────────────────────────
  const recordOverride = useCallback((
    field: string,
    original: unknown,
    override: unknown,
  ) => {
    if (!currentEntry) return;
    setCurrentEntry(prev => {
      if (!prev) return prev;
      const updated: PricingAuditEntry = {
        ...prev,
        manualOverrides: [
          ...prev.manualOverrides.filter(o => o.field !== field),
          { field, original, override },
        ],
        // Note: approval invalidation is handled by the caller (PricingControlPanel)
        // to allow selective reset (measurements vs pricing vs labor).
      };
      persistEntry(updated);
      return updated;
    });
  }, [currentEntry, persistEntry]);

  // ── Approve measurements ───────────────────────────────────────────────────
  const approveMeasurements = useCallback((notes?: string) => {
    if (!currentEntry) return;
    setCurrentEntry(prev => {
      if (!prev) return prev;
      const updated: PricingAuditEntry = {
        ...prev,
        measurementsApproved: true,
        pricingReviewedAt: new Date().toISOString(),
        pricingReviewedBy: 'founder',
        approvalNotes: notes || prev.approvalNotes,
      };
      persistEntry(updated);
      return updated;
    });
  }, [currentEntry, persistEntry]);

  // ── Approve pricing ────────────────────────────────────────────────────────
  const approvePricing = useCallback((notes?: string) => {
    if (!currentEntry) return;
    setCurrentEntry(prev => {
      if (!prev) return prev;
      const updated: PricingAuditEntry = {
        ...prev,
        pricingApproved: true,
        pricingReviewedAt: new Date().toISOString(),
        pricingReviewedBy: 'founder',
        approvalNotes: notes || prev.approvalNotes,
      };
      persistEntry(updated);
      return updated;
    });
  }, [currentEntry, persistEntry]);

  // ── Reset all approvals ─────────────────────────────────────────────────────
  const resetApprovals = useCallback(() => {
    if (!currentEntry) return;
    setCurrentEntry(prev => {
      if (!prev) return prev;
      const updated: PricingAuditEntry = {
        ...prev,
        measurementsApproved: false,
        pricingApproved: false,
      };
      persistEntry(updated);
      return updated;
    });
  }, [currentEntry, persistEntry]);

  // ── Set dimensions source ─────────────────────────────────────────────────
  const setDimensionsSource = useCallback((source: PricingAuditEntry['dimensionsSource']) => {
    if (!currentEntry) return;
    setCurrentEntry(prev => {
      if (!prev) return prev;
      const updated: PricingAuditEntry = { ...prev, dimensionsSource: source };
      persistEntry(updated);
      return updated;
    });
  }, [currentEntry, persistEntry]);

  // ── Set tier ──────────────────────────────────────────────────────────────
  const setSelectedTier = useCallback((tier: 'A' | 'B' | 'C' | null) => {
    if (!currentEntry) return;
    setCurrentEntry(prev => {
      if (!prev) return prev;
      const updated: PricingAuditEntry = { ...prev, selectedTier: tier };
      persistEntry(updated);
      return updated;
    });
  }, [currentEntry, persistEntry]);

  // ── Confirm render tier ───────────────────────────────────────────────────
  const confirmRenderTier = useCallback(() => {
    if (!currentEntry) return;
    setCurrentEntry(prev => {
      if (!prev) return prev;
      const updated: PricingAuditEntry = { ...prev, renderTierConfirmed: true };
      persistEntry(updated);
      return updated;
    });
  }, [currentEntry, persistEntry]);

  // ── Load entry by draftId ─────────────────────────────────────────────────
  const loadEntry = useCallback((draftId: string) => {
    const store = loadStore();
    const entry = store.find(e => e.draftId === draftId);
    if (entry) setCurrentEntry(entry);
    return entry ?? null;
  }, []);

  // ── Clear current entry ────────────────────────────────────────────────────
  const clearEntry = useCallback(() => {
    setCurrentEntry(null);
  }, []);

  return {
    currentEntry,
    initAudit,
    recordAiAssumption,
    recordOverride,
    approveMeasurements,
    approvePricing,
    resetApprovals,
    setDimensionsSource,
    setSelectedTier,
    confirmRenderTier,
    loadEntry,
    clearEntry,
  };
}
