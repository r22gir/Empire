/**
 * useUIPhase — Shared UI phase flags for v10 modules
 * Phase 1.5 Hardening
 *
 * Single source of truth for prototype/live UI phase flags.
 * Import this hook in screens that need conditional prototype UI.
 *
 * TF-1: Shared UI Phase Hook
 */

'use client';

// ============================================================
// PHASE CONSTANTS
// ============================================================

/**
 * TranscriptForge Phase
 * - 'prototype': local/proofreading UI only, no backend edit persistence
 * - 'live': backend endpoints available for edit save, audio export, speaker sync
 */
export const TRANSCRIPTFORGE_PHASE: 'prototype' | 'live' = 'prototype';

/**
 * ArchiveForge Phase
 * - 'prototype': mock data, no backend integration for valuation/market/bundle
 * - 'live': backend endpoints available for real data
 */
export const ARCHIVEFORGE_PHASE: 'prototype' | 'live' = 'prototype';

/**
 * PHASE alias — used in useArchiveForgePrototype.ts for backward compatibility.
 * Do not use PHASE directly in new code; use ARCHIVEFORGE_PHASE.
 */
export const PHASE: 'prototype' | 'live' = ARCHIVEFORGE_PHASE;

// ============================================================
// HELPERS
// ============================================================

export type ModuleName = 'transcriptforge' | 'archiveforge';

export function isPrototypePhase(moduleName: ModuleName): boolean {
  if (moduleName === 'transcriptforge') return TRANSCRIPTFORGE_PHASE === 'prototype';
  if (moduleName === 'archiveforge') return ARCHIVEFORGE_PHASE === 'prototype';
  return true;
}

// ============================================================
// PROTOTYPE BANNER DATA
// ============================================================

export interface PrototypeBanner {
  label: string;
  message: string;
  href?: string;
}

export function getPrototypeBanner(moduleName: ModuleName): PrototypeBanner | null {
  if (!isPrototypePhase(moduleName)) return null;
  if (moduleName === 'transcriptforge') {
    return {
      label: 'Prototype',
      message: 'Proofreading edits are local-only — not saved to backend',
    };
  }
  if (moduleName === 'archiveforge') {
    return {
      label: 'Prototype',
      message: 'Valuation and market data are mock — not live',
    };
  }
  return null;
}