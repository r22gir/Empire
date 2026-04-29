# ArchiveForge Data Contract Specification — Phase 2

**Created:** 2026-04-29
**Status:** Phase 2 API Contracts (NOT YET IMPLEMENTED)
**Lane:** v10 test (port 3010) — `~/empire-repo-v10`

---

## OVERVIEW

Phase 1 provides a working prototype UI with mock data. Phase 2 implements the backend APIs that power real valuation, market intelligence, and bundling logic.

**PHASE Toggle:** `useArchiveForgePrototype.ts` PHASE constant — change from `'prototype'` to `'live'` to switch from mock data to live API calls.

---

## API BASE

```
API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
AG_API = ${API}/archiveforge
```

---

## CONTRACTS

### POST `/api/v1/archiveforge/valuation/estimate`

**Purpose:** Get valuation range for an identified item.

**Request:**
```typescript
{
  itemKey: string;          // e.g. 'life-aug-1945'
  issueYear?: number;
  issueMonth?: number;
  conditionGrade?: string;  // e.g. 'C8'
  platformContext?: string;
}
```

**Response:**
```typescript
{
  itemTitle: string;
  issueYear?: number;
  issueMonth?: number;
  valuationRange: {
    low: number;
    median: number;
    high: number;
    currency: string;
  };
  confidence: number;       // 0-100
  comparableSales: {
    date: string;
    price: number;
    platform: string;
    condition: string;
    title: string;
    sourceUrl?: string;
  }[];
  lastUpdated: string;
  dataSource: string;
}
```

**Error Responses:** 400 (invalid itemKey), 404 (item not found), 500 (upstream error)

---

### GET `/api/v1/archiveforge/market/trends`

**Query Params:** `category` (optional, default `'vintage_magazines'`)

**Response:**
```typescript
{
  trends: {
    date: string;           // ISO date (monthly)
    avgPrice: number;
    volume: number;
    trend: 'up' | 'down' | 'stable';
    platformBreakdown: Record<string, number>;
  }[];
  hotThreshold: number;
  marketTemperature: 'hot' | 'warm' | 'cool' | 'cold';
  lastUpdated: string;
}
```

---

### POST `/api/v1/archiveforge/market/recommend`

**Request:**
```typescript
{
  category?: string;         // e.g. 'vintage_magazines'
  itemCount?: number;
  estimatedValueRange?: { min: number; max: number };
}
```

**Response:**
```typescript
{
  scores: {
    platform: string;
    score: number;           // 0-100
    fees: number;            // percentage
    reach: 'high' | 'medium' | 'low';
    bestFor: string[];
    listingsPerMonth?: number;
  }[];
  recommended: string[];     // platform names
  reasoning: string;
}
```

---

### POST `/api/v1/archiveforge/bundle/suggest`

**Request:**
```typescript
{
  itemIds: string[];         // collection item identifiers
}
```

**Response:**
```typescript
{
  suggestions: {
    id: string;
    bundleName: string;
    items: string[];
    individualTotal: number;
    bundleValue: number;
    savings: number;
    score: number;           // 0-100
    reasoning: string;
    action: 'recommend' | 'consider' | 'caution';
  }[];
}
```

---

### POST `/api/v1/archiveforge/condition/grade`

**Request:**
```typescript
{
  binding: number;           // 1-10
  covers: number;            // 1-10
  pages: number;             // 1-10
  centerStaple: number;      // 1-10
  photoUrls?: string[];
}
```

**Response:**
```typescript
{
  overallGrade: string;      // e.g. 'C8', 'VG6', 'FN10'
  numericScore: number;      // 1-100
  scores: {
    dimension: 'binding' | 'covers' | 'pages' | 'centerStaple';
    score: number;
    notes?: string;
  }[];
  expertNotes: string;
  isComplete: boolean;
}
```

---

### POST `/api/v1/archiveforge/founder-queue/flag`

**Request:**
```typescript
{
  itemId: string;
  notes?: string;
  priority?: 'high' | 'medium' | 'low';
}
```

**Response:**
```typescript
{
  success: boolean;
  itemId: string;
  status: 'flagged';
  flaggedAt: string;
}
```

---

### GET `/api/v1/archiveforge/collection/comparables`

**Query Params:** `item` (item identifier)

**Response:**
```typescript
{
  comparables: {
    date: string;
    price: number;
    platform: string;
    condition: string;
    title: string;
    sourceUrl?: string;
  }[];
}
```

---

## DATABASE TABLES

Phase 2 may require new tables or columns in the ArchiveForge SQLite database (`ag_*.db`):

```sql
-- Valuation cache
CREATE TABLE ag_valuation_cache (
  item_key TEXT PRIMARY KEY,
  low INTEGER,
  median INTEGER,
  high INTEGER,
  confidence INTEGER,
  last_updated TEXT,
  data_source TEXT
);

-- Founder review queue
CREATE TABLE ag_founder_queue (
  id TEXT PRIMARY KEY,
  item_key TEXT,
  estimated_value INTEGER,
  condition TEXT,
  priority TEXT,
  status TEXT,
  notes TEXT,
  submitted_at TEXT
);

-- Condition grade history
CREATE TABLE ag_condition_grades (
  id TEXT PRIMARY KEY,
  item_key TEXT,
  overall_grade TEXT,
  numeric_score INTEGER,
  binding_score INTEGER,
  covers_score INTEGER,
  pages_score INTEGER,
  center_staple_score INTEGER,
  graded_at TEXT
);
```

---

## IMPLEMENTATION NOTES

- Use existing `ag_api_client` pattern from `archiveforge.py`
- Market data sourced from eBay API + Whatnot public APIs (requires API keys)
- Valuation model: weighted comparable sales with condition adjustment factor
- Bundle intelligence: k-nearest-items algorithm with co-purchase clustering
- All endpoints should be cached for 1 hour (redis or in-memory)
