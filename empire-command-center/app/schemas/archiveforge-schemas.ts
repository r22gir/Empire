/**
 * ArchiveForge TypeScript Schemas
 * Phase 1 Prototype — interfaces only (no Zod)
 * Phase 2: Add Zod validation schemas
 */

// ============================================================
// VALUATION
// ============================================================

export interface ValuationRange {
  low: number;
  median: number;
  high: number;
  currency: string;
}

export interface ComparableSale {
  date: string; // ISO date
  price: number;
  platform: string;
  condition: string;
  title: string;
  sourceUrl?: string;
}

export interface ValuationResult {
  itemTitle: string;
  issueYear?: number;
  issueMonth?: number;
  valuationRange: ValuationRange;
  confidence: number; // 0-100
  comparableSales: ComparableSale[];
  lastUpdated: string; // ISO date
  dataSource: string;
}

// ============================================================
// MARKET INTELLIGENCE
// ============================================================

export interface MarketTrend {
  date: string; // ISO date (monthly)
  avgPrice: number;
  volume: number; // number of sales
  trend: 'up' | 'down' | 'stable';
  platformBreakdown: Record<string, number>;
}

export interface MarketIntelligence {
  trends: MarketTrend[];
  hotThreshold: number; // volume threshold for "hot"
  marketTemperature: 'hot' | 'warm' | 'cool' | 'cold';
  lastUpdated: string; // ISO date
}

// ============================================================
// PLATFORM RECOMMENDATIONS
// ============================================================

export interface PlatformScore {
  platform: string;
  score: number; // 0-100
  fees: number; // percentage
  reach: 'high' | 'medium' | 'low';
  bestFor: string[];
  listingsPerMonth?: number;
}

export interface PlatformRecommendations {
  scores: PlatformScore[];
  recommended: string[]; // platform names
  reasoning: string;
}

// ============================================================
// FOUNDER REVIEW QUEUE
// ============================================================

export interface FounderReviewItem {
  id: string;
  itemTitle: string;
  issueRef?: string;
  estimatedValue: number;
  condition: string;
  priority: 'high' | 'medium' | 'low';
  submittedAt: string; // ISO date
  status: 'pending' | 'flagged' | 'approved' | 'rejected';
  notes?: string;
}

// ============================================================
// CONDITION GRADING
// ============================================================

export type GradingDimension = 'binding' | 'covers' | 'pages' | 'centerStaple';

export interface GradingScore {
  dimension: GradingDimension;
  score: number; // 1-10
  notes?: string;
}

// ============================================================
// CONDITION GRADING RESULT
// AF-2: Draft Phase 2 request body for backend condition grading endpoint.
// This is not persisted to backend in Phase 1.5.
// ============================================================

export interface ConditionGradeResult {
  overallGrade: string; // e.g., "C8", "VG6", "FN10"
  numericScore: number; // 1-100
  scores: GradingScore[];
  expertNotes: string;
  isComplete: boolean;
}

// ============================================================
// BUNDLE INTELLIGENCE
// ============================================================

export interface BundleSuggestion {
  id: string;
  bundleName: string;
  items: string[]; // item identifiers
  individualTotal: number;
  bundleValue: number;
  savings: number; // dollar savings vs individual
  score: number; // 0-100
  reasoning: string;
  action: 'recommend' | 'consider' | 'caution';
}

// ============================================================
// WIZARD STEP TYPES (extends existing)
// ============================================================

export type ArchiveForgeWizardStep =
  | 'intake'
  | 'reference'
  | 'photos'
  | 'archive'
  | 'condition'
  | 'listing'
  | 'review'
  | 'inventory'
  | 'valuation'       // NEW
  | 'market'          // NEW
  | 'platform'        // NEW
  | 'founder'         // NEW
  | 'grading'         // NEW
  | 'bundle';         // NEW
