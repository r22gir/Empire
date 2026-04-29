/**
 * ArchiveForge Mock Data Configuration
 * Phase 1 Prototype — all mock data for UI development
 */

import type {
  ValuationResult,
  MarketIntelligence,
  PlatformRecommendations,
  FounderReviewItem,
  ConditionGradeResult,
  BundleSuggestion,
  ComparableSale,
  MarketTrend,
} from '../schemas/archiveforge-schemas';

// ============================================================
// DISCLAIMER
// ============================================================

export const ARCHIVEFORGE_PROTOTYPE_DISCLAIMER =
  'Prototype data — not live valuation yet';

// ============================================================
// VALUATION MOCK DATA
// ============================================================

const MOCK_COMPARABLE_SALES_LIFE: ComparableSale[] = [
  { date: '2025-03-15', price: 185, platform: 'eBay', condition: 'C8', title: 'LIFE Magazine Aug 1945' },
  { date: '2025-02-20', price: 220, platform: 'eBay', condition: 'C9', title: 'LIFE Magazine Aug 1945' },
  { date: '2025-01-08', price: 165, platform: 'Whatnot', condition: 'C7', title: 'LIFE Magazine Aug 1945' },
  { date: '2024-12-12', price: 195, platform: 'eBay', condition: 'C8', title: 'LIFE Magazine Aug 1945' },
  { date: '2024-11-30', price: 210, platform: 'eBay', condition: 'C9', title: 'LIFE Magazine Aug 1945' },
];

export const MOCK_VALUATIONS: Record<string, ValuationResult> = {
  'life-aug-1945': {
    itemTitle: 'LIFE Magazine — August 1945',
    issueYear: 1945,
    issueMonth: 8,
    valuationRange: { low: 150, median: 195, high: 275, currency: 'USD' },
    confidence: 78,
    comparableSales: MOCK_COMPARABLE_SALES_LIFE,
    lastUpdated: '2026-04-15',
    dataSource: 'eBay + Whatnot (mock)',
  },
  'life-dec-1944': {
    itemTitle: 'LIFE Magazine — December 1944',
    issueYear: 1944,
    issueMonth: 12,
    valuationRange: { low: 120, median: 160, high: 210, currency: 'USD' },
    confidence: 72,
    comparableSales: MOCK_COMPARABLE_SALES_LIFE.slice(0, 4),
    lastUpdated: '2026-04-10',
    dataSource: 'eBay (mock)',
  },
};

export const MOCK_VALUATION_DEFAULT: ValuationResult = {
  itemTitle: 'LIFE Magazine — Selected Issue',
  valuationRange: { low: 50, median: 125, high: 350, currency: 'USD' },
  confidence: 60,
  comparableSales: MOCK_COMPARABLE_SALES_LIFE.slice(0, 3),
  lastUpdated: '2026-04-20',
  dataSource: 'Aggregated (mock)',
};

// ============================================================
// MARKET INTELLIGENCE MOCK DATA
// ============================================================

const MOCK_TRENDS_2024_2025: MarketTrend[] = [
  { date: '2024-07-01', avgPrice: 142, volume: 18, trend: 'up', platformBreakdown: { eBay: 12, Whatnot: 4, Heritage: 2 } },
  { date: '2024-08-01', avgPrice: 138, volume: 22, trend: 'down', platformBreakdown: { eBay: 14, Whatnot: 6, Heritage: 2 } },
  { date: '2024-09-01', avgPrice: 145, volume: 25, trend: 'up', platformBreakdown: { eBay: 16, Whatnot: 7, Heritage: 2 } },
  { date: '2024-10-01', avgPrice: 152, volume: 30, trend: 'up', platformBreakdown: { eBay: 19, Whatnot: 8, Heritage: 3 } },
  { date: '2024-11-01', avgPrice: 160, volume: 35, trend: 'up', platformBreakdown: { eBay: 22, Whatnot: 10, Heritage: 3 } },
  { date: '2024-12-01', avgPrice: 175, volume: 42, trend: 'up', platformBreakdown: { eBay: 26, Whatnot: 12, Heritage: 4 } },
  { date: '2025-01-01', avgPrice: 168, volume: 28, trend: 'down', platformBreakdown: { eBay: 18, Whatnot: 8, Heritage: 2 } },
  { date: '2025-02-01', avgPrice: 172, volume: 32, trend: 'up', platformBreakdown: { eBay: 20, Whatnot: 9, Heritage: 3 } },
  { date: '2025-03-01', avgPrice: 188, volume: 38, trend: 'up', platformBreakdown: { eBay: 24, Whatnot: 11, Heritage: 3 } },
  { date: '2025-04-01', avgPrice: 195, volume: 41, trend: 'stable', platformBreakdown: { eBay: 26, Whatnot: 12, Heritage: 3 } },
];

export const MOCK_MARKET_TRENDS: MarketIntelligence = {
  trends: MOCK_TRENDS_2024_2025,
  hotThreshold: 35,
  marketTemperature: 'hot',
  lastUpdated: '2026-04-28',
};

// ============================================================
// PLATFORM RECOMMENDATIONS MOCK DATA
// ============================================================

export const MOCK_PLATFORM_RECOMMENDATIONS: PlatformRecommendations = {
  scores: [
    {
      platform: 'eBay',
      score: 92,
      fees: 13.25,
      reach: 'high',
      bestFor: ['Vintage magazines', 'Rare issues', 'Authenticated collectibles'],
      listingsPerMonth: 850,
    },
    {
      platform: 'Whatnot',
      score: 85,
      fees: 10.5,
      reach: 'medium',
      bestFor: ['Live auction format', 'Collector community', 'Fast sales'],
      listingsPerMonth: 320,
    },
    {
      platform: 'Mercari',
      score: 68,
      fees: 10.0,
      reach: 'medium',
      bestFor: ['Quick flips', 'Mass market items'],
      listingsPerMonth: 1200,
    },
    {
      platform: 'Heritage Auctions',
      score: 74,
      fees: 19.5,
      reach: 'low',
      bestFor: ['High-value rarities', 'Authenticated grading', 'Premium lots'],
      listingsPerMonth: 45,
    },
  ],
  recommended: ['eBay', 'Whatnot'],
  reasoning: 'eBay offers the broadest collector reach with established pricing for vintage magazines. Whatnot provides live auction momentum and collector-to-collector sales at slightly lower fees.',
};

// ============================================================
// FOUNDER REVIEW QUEUE MOCK DATA
// ============================================================

export const MOCK_FOUNDER_REVIEW_QUEUE: FounderReviewItem[] = [
  {
    id: 'fq-001',
    itemTitle: 'LIFE Magazine — August 1945 (V-J Day Edition)',
    issueRef: 'life-aug-1945',
    estimatedValue: 275,
    condition: 'C8 (Near Mint)',
    priority: 'high',
    submittedAt: '2026-04-28T14:22:00Z',
    status: 'pending',
    notes: 'Flagged for founder review due to estimated value > $200',
  },
  {
    id: 'fq-002',
    itemTitle: 'LIFE Magazine — December 1944',
    issueRef: 'life-dec-1944',
    estimatedValue: 185,
    condition: 'C7 (Very Good+)',
    priority: 'medium',
    submittedAt: '2026-04-27T09:15:00Z',
    status: 'pending',
  },
  {
    id: 'fq-003',
    itemTitle: 'LIFE Magazine — March 1943 (War Coverage)',
    issueRef: 'life-mar-1943',
    estimatedValue: 95,
    condition: 'C6 (Very Good)',
    priority: 'low',
    submittedAt: '2026-04-25T16:40:00Z',
    status: 'pending',
  },
];

// ============================================================
// CONDITION GRADING MOCK DATA
// ============================================================

export const MOCK_CONDITION_GRADES: Record<string, ConditionGradeResult> = {
  'C9': {
    overallGrade: 'C9',
    numericScore: 92,
    scores: [
      { dimension: 'binding', score: 9, notes: 'Tight binding, no splits' },
      { dimension: 'covers', score: 9, notes: 'Bright color, minor corner wear' },
      { dimension: 'pages', score: 9, notes: 'Clean pages, no tears or foxing' },
      { dimension: 'centerStaple', score: 9, notes: 'Original staples intact, no rust' },
    ],
    expertNotes: 'Near Mint condition. Minor shelf wear only. A choice copy for the serious collector.',
    isComplete: true,
  },
  'C7': {
    overallGrade: 'C7',
    numericScore: 72,
    scores: [
      { dimension: 'binding', score: 7, notes: 'Light spine stress but solid' },
      { dimension: 'covers', score: 7, notes: 'Some fading, corner bumps' },
      { dimension: 'pages', score: 7, notes: 'Small crease top corner, no tears' },
      { dimension: 'centerStaple', score: 7, notes: 'Staples secure, light surface oxidation' },
    ],
    expertNotes: 'Very Good+ condition. Presentable copy with expected aging. Suitable for most collectors.',
    isComplete: true,
  },
};

// ============================================================
// BUNDLE SUGGESTIONS MOCK DATA
// ============================================================

export const MOCK_BUNDLE_SUGGESTIONS: BundleSuggestion[] = [
  {
    id: 'bundle-001',
    bundleName: 'WWII Year Bundle (1943–1945)',
    items: ['life-mar-1943', 'life-aug-1944', 'life-aug-1945'],
    individualTotal: 485,
    bundleValue: 425,
    savings: 60,
    score: 88,
    reasoning: 'WWII-era LIFE magazines sell as a curated set to museums, educators, and serious collectors. Bundling creates a premium historical package worth 12% more than individual sales.',
    action: 'recommend',
  },
  {
    id: 'bundle-002',
    bundleName: 'Postwar Prosperity Collection (1946–1948)',
    items: ['life-jan-1946', 'life-jun-1947', 'life-1948'],
    individualTotal: 290,
    bundleValue: 265,
    savings: 25,
    score: 76,
    reasoning: 'Postwar issues show strong demand from baby-boomer collectors. A 3-issue set appeals to buyers who want a snapshot of the era without collecting individually.',
    action: 'recommend',
  },
  {
    id: 'bundle-003',
    bundleName: '1950s Americana Bundle',
    items: ['life-1950', 'life-1952', 'life-1955'],
    individualTotal: 195,
    bundleValue: 175,
    savings: 20,
    score: 65,
    reasoning: '1950s issues are popular but individually lower value. Bundling increases average order value but platform fees reduce net benefit.',
    action: 'consider',
  },
];

// ============================================================
// COMPARABLE SALES SPARKLINE DATA
// ============================================================

export const MOCK_COMPARABLE_SALES_SPARKLINE: ComparableSale[] = MOCK_COMPARABLE_SALES_LIFE;
