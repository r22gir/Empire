/**
 * useArchiveForgePrototype — Central Mock Data Hook
 * Phase 1 Prototype — provides all mock data with simulated async delay
 * PHASE constant controls whether we hit real APIs or return mock data
 */

import { useState, useEffect, useCallback } from 'react';
import type {
  ValuationResult,
  MarketIntelligence,
  PlatformRecommendations,
  FounderReviewItem,
  ConditionGradeResult,
  BundleSuggestion,
  ComparableSale,
} from '../schemas/archiveforge-schemas';
import {
  MOCK_VALUATION_DEFAULT,
  MOCK_MARKET_TRENDS,
  MOCK_PLATFORM_RECOMMENDATIONS,
  MOCK_FOUNDER_REVIEW_QUEUE,
  MOCK_CONDITION_GRADES,
  MOCK_BUNDLE_SUGGESTIONS,
  MOCK_COMPARABLE_SALES_SPARKLINE,
} from '../config/archiveforge-mock';
import { ARCHIVEFORGE_PHASE } from './useUIPhase';

// ============================================================
// PHASE TOGGLE — change to 'live' when backend APIs are ready
// ============================================================

const PHASE: 'prototype' | 'live' = ARCHIVEFORGE_PHASE;

// ============================================================
// SIMULATED DELAY (prototype mode only)
// ============================================================

function simulateDelay(ms: number = 600): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// ============================================================
// HOOK: useValuationData
// ============================================================

export function useValuationData(itemKey?: string) {
  const [data, setData] = useState<ValuationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchValuation = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (PHASE === 'prototype') {
        await simulateDelay(800);
        setData(MOCK_VALUATION_DEFAULT);
      } else {
        const res = await fetch(`/api/v1/archiveforge/valuation/estimate?item=${itemKey}`);
        if (!res.ok) throw new Error('Failed to fetch valuation');
        setData(await res.json());
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [itemKey]);

  useEffect(() => {
    fetchValuation();
  }, [fetchValuation]);

  return { data, loading, error, refetch: fetchValuation };
}

// ============================================================
// HOOK: useMarketTrends
// ============================================================

export function useMarketTrends(category?: string) {
  const [data, setData] = useState<MarketIntelligence | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchMarket = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (PHASE === 'prototype') {
        await simulateDelay(700);
        setData(MOCK_MARKET_TRENDS);
      } else {
        const res = await fetch(`/api/v1/archiveforge/market/trends?category=${category}`);
        if (!res.ok) throw new Error('Failed to fetch market trends');
        setData(await res.json());
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [category]);

  useEffect(() => {
    fetchMarket();
  }, [fetchMarket]);

  return { data, loading, error, refetch: fetchMarket };
}

// ============================================================
// HOOK: usePlatformRecommendations
// ============================================================

export function usePlatformRecommendations(category?: string) {
  const [data, setData] = useState<PlatformRecommendations | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPlatform = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (PHASE === 'prototype') {
        await simulateDelay(500);
        setData(MOCK_PLATFORM_RECOMMENDATIONS);
      } else {
        const res = await fetch('/api/v1/archiveforge/market/recommend', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ category }),
        });
        if (!res.ok) throw new Error('Failed to fetch platform recommendations');
        setData(await res.json());
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [category]);

  useEffect(() => {
    fetchPlatform();
  }, [fetchPlatform]);

  return { data, loading, error, refetch: fetchPlatform };
}

// ============================================================
// HOOK: useFounderQueue
// ============================================================

export function useFounderQueue() {
  const [items, setItems] = useState<FounderReviewItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchFounderQueue = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (PHASE === 'prototype') {
        await simulateDelay(600);
        setItems(MOCK_FOUNDER_REVIEW_QUEUE);
      } else {
        const res = await fetch('/api/v1/archiveforge/founder-queue/list');
        if (!res.ok) throw new Error('Failed to fetch founder queue');
        setItems(await res.json());
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  const flagItem = useCallback(async (itemId: string, notes?: string) => {
    if (PHASE === 'prototype') {
      const flagged = JSON.parse(localStorage.getItem('archiveforge_flagged_items') || '[]');
      if (!flagged.includes(itemId)) {
        flagged.push(itemId);
        localStorage.setItem('archiveforge_flagged_items', JSON.stringify(flagged));
      }
      setItems((prev) =>
        prev.map((item) =>
          item.id === itemId
            ? { ...item, status: 'flagged' as const, notes: notes || item.notes }
            : item
        )
      );
      return;
    }
    const res = await fetch('/api/v1/archiveforge/founder-queue/flag', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ itemId, notes }),
    });
    if (!res.ok) throw new Error('Failed to flag item');
    await fetchFounderQueue();
  }, [fetchFounderQueue]);

  const approveItem = useCallback(async (itemId: string) => {
    if (PHASE === 'prototype') {
      setItems((prev) =>
        prev.map((item) =>
          item.id === itemId ? { ...item, status: 'approved' as const } : item
        )
      );
      return;
    }
    const res = await fetch('/api/v1/archiveforge/founder-queue/approve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ itemId }),
    });
    if (!res.ok) throw new Error('Failed to approve item');
    await fetchFounderQueue();
  }, [fetchFounderQueue]);

  useEffect(() => {
    fetchFounderQueue();
  }, [fetchFounderQueue]);

  return { items, loading, error, refetch: fetchFounderQueue, flagItem, approveItem };
}

// ============================================================
// HOOK: useConditionGrade
// ============================================================

export function useConditionGrade() {
  const [result, setResult] = useState<ConditionGradeResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const grade = useCallback(async (answers: Record<string, unknown>) => {
    setLoading(true);
    setError(null);
    try {
      if (PHASE === 'prototype') {
        await simulateDelay(1000);
        // Deterministic mock based on binding score
        const bindingScore = (answers.binding as number) || 7;
        const gradeKey = bindingScore >= 8 ? 'C9' : 'C7';
        setResult(MOCK_CONDITION_GRADES[gradeKey] || MOCK_CONDITION_GRADES['C7']);
      } else {
        const res = await fetch('/api/v1/archiveforge/condition/grade', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(answers),
        });
        if (!res.ok) throw new Error('Failed to grade condition');
        setResult(await res.json());
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return { result, loading, error, grade, reset };
}

// ============================================================
// HOOK: useBundleSuggestions
// ============================================================

export function useBundleSuggestions(itemIds?: string[]) {
  const [data, setData] = useState<BundleSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchBundle = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (PHASE === 'prototype') {
        await simulateDelay(700);
        setData(MOCK_BUNDLE_SUGGESTIONS);
      } else {
        const res = await fetch('/api/v1/archiveforge/bundle/suggest', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ itemIds }),
        });
        if (!res.ok) throw new Error('Failed to fetch bundle suggestions');
        setData(await res.json());
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [itemIds]);

  useEffect(() => {
    if (itemIds) fetchBundle();
  }, [fetchBundle, itemIds]);

  return { data, loading, error, refetch: fetchBundle };
}

// ============================================================
// HOOK: useComparableSales
// ============================================================

export function useComparableSales(itemKey?: string) {
  const [data, setData] = useState<ComparableSale[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchComparables = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (PHASE === 'prototype') {
        await simulateDelay(400);
        setData(MOCK_COMPARABLE_SALES_SPARKLINE);
      } else {
        const res = await fetch(`/api/v1/archiveforge/collection/comparables?item=${itemKey}`);
        if (!res.ok) throw new Error('Failed to fetch comparables');
        setData(await res.json());
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [itemKey]);

  useEffect(() => {
    fetchComparables();
  }, [fetchComparables]);

  return { data, loading, error, refetch: fetchComparables };
}
