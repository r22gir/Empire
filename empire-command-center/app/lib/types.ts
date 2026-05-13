// Ecosystem product = left nav item
export type EcosystemProduct = 'owner' | 'workroom' | 'craft' | 'social' | 'platform' | 'openclaw' | 'vendorops' | 'recovery' | 'luxe' | 'hardware' | 'system' | 'tokens' | 'max-continuity' | 'market' | 'contractor' | 'support' | 'lead' | 'ship' | 'crm' | 'relist' | 'llc' | 'apost' | 'assist' | 'pay' | 'amp' | 'vetforge' | 'petforge' | 'vision' | 'max-avatar' | 'dev' | 'drawings' | 'construction' | 'storefront' | 'archive' | 'transcript';

// Legacy BusinessTab mapping (for hooks/data that still reference it)
export type BusinessTab = 'max' | 'workroom' | 'craft' | 'social' | 'platform' | 'tickets' | 'shipping';

// What's shown in center content area
export type ScreenMode = 'chat' | 'quote' | 'docs' | 'research' | 'video' | 'dashboard' | 'desks' | 'inbox' | 'memory-bank' | 'report' | 'tickets' | 'shipping' | 'costs' | 'mail' | 'tasks' | 'calendar' | 'telegram' | 'product-docs' | 'pricing' | 'business-profile' | 'presentation' | 'dev' | 'jobs' | 'invoices';

export type SidebarIcon = 'chat' | 'dashboard' | 'desks' | 'inbox' | 'files' | 'search' | 'voice' | 'settings';
export type RightTab = 'desks' | 'inbox' | 'system' | 'memory';

export interface QualityBadge {
  icon: string;
  color: string;
  label: string;
  checks?: string[];
  warnings?: string[];
  validation_time_ms?: number;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  model?: string;
  latency?: string;
  toolResults?: ToolResult[];
  quality?: QualityBadge;
  metadata?: {
    registry_version: string;
    surface: string;
    response_at: string;
    skill_used: string | null;
  };
  artifacts?: MaxArtifact[];
}

export interface ToolResult {
  tool: string;
  success: boolean;
  result?: any;
  error?: string;
}

export interface Conversation {
  id: string;
  title: string;
  preview: string;
  timestamp: string;
  business?: BusinessTab;
}

export interface Desk {
  id: string;
  name: string;
  persona: string;
  icon: string;
  status: string;
  description?: string;
}

export interface Quote {
  id: string;
  quote_number: string;
  customer_name: string;
  total: number;
  status: string;
  design_proposals?: any[];
  rooms?: any[];
  photos?: { filename: string; path?: string; type?: string; data_uri?: string }[];
  created_at?: string;
}

// ── ArchiveForge / Comps Types ────────────────────────────────────────────────

export interface CompsListing {
  price: number;
  condition: string;
  sold_date: string;
  title?: string;
  url?: string;
}

export interface CompsResult {
  google_books_id: string;
  source: 'fixture' | 'apify';
  base_avg_sold: number;
  suggested_min: number;
  suggested_max: number;
  condition_multiplier: number;
  comps: CompsListing[];
  last_updated: string;
}

export interface LifeReferenceIssue {
  google_books_id: string;
  date: string;
  volume: string;
  issue: string;
  cover_subject: string;
  reference_cover_url: string;
}

// ── MAX Artifact Types ─────────────────────────────────────────────────────────

export type ArtifactType = 'plain_text' | 'markdown_report' | 'html_artifact' | 'react_component_proposal';
export type ArtifactMode = 'review_only' | 'approval_required' | 'approved' | 'rejected' | 'changes_requested';
export type ArtifactFormat = 'text' | 'markdown' | 'html' | 'json' | 'tsx';

export interface ArtifactSafety {
  scripts_allowed: boolean;
  external_network_allowed: boolean;
  sandboxed: boolean;
  sanitized: boolean;
}

export interface MaxArtifact {
  id: string;
  artifact_type: ArtifactType;
  title: string;
  description?: string;
  content_format: ArtifactFormat;
  content: string;
  source: 'max' | 'openclaw' | 'hermes' | 'founder';
  mode: ArtifactMode;
  requires_approval: boolean;
  allowed_actions: ('approve' | 'reject' | 'request_changes' | 'export_html' | 'copy_source' | 'open_fullscreen')[];
  safety: ArtifactSafety;
  metadata?: Record<string, unknown>;
}
