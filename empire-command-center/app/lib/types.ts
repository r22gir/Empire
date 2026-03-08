export type BusinessTab = 'max' | 'workroom' | 'craft' | 'platform';
export type ScreenMode = 'chat' | 'quote' | 'docs' | 'research' | 'video' | 'dashboard';
export type SidebarIcon = 'chat' | 'dashboard' | 'desks' | 'inbox' | 'files' | 'search' | 'voice' | 'settings';
export type RightTab = 'desks' | 'inbox' | 'system' | 'memory';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  model?: string;
  latency?: string;
  toolResults?: ToolResult[];
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
  created_at?: string;
}
