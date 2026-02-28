export interface ToolResult {
  tool: string;
  success: boolean;
  result?: Record<string, unknown>;
  error?: string;
}

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  model?: string;
  image?: string;
  toolResults?: ToolResult[];
}

export interface ChatSession {
  id: string;
  title: string;
  updated_at: string;
  message_count: number;
}

export interface Desk {
  id: string;
  name: string;
  description: string;
  status: string;
}

export interface AIModel {
  id: string;
  name: string;
  available: boolean;
  primary?: boolean;
  type?: string;
}

export interface UploadedFile {
  name: string;
  category: string;
  size: number;
}

export interface BrowseFile {
  name: string;
  path: string;
  isDir: boolean;
  size: number;
}

export interface Task {
  id: string;
  title: string;
  description: string | null;
  status: 'todo' | 'in_progress' | 'waiting' | 'done' | 'cancelled';
  priority: 'urgent' | 'high' | 'normal' | 'low';
  desk: string;
  assigned_to: string | null;
  created_by: string;
  due_date: string | null;
  tags: string[];
  metadata: Record<string, unknown>;
  parent_task_id: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface TaskListResponse {
  tasks: Task[];
  total: number;
  limit: number;
  offset: number;
}

export interface TaskDashboard {
  desks: Record<string, { todo: number; in_progress: number; waiting: number; done: number }>;
  totals: Record<string, number>;
}

export interface Contact {
  id: string;
  name: string;
  type: 'client' | 'contractor' | 'vendor' | 'other';
  phone: string | null;
  email: string | null;
  address: string | null;
  notes: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ContactListResponse {
  contacts: Contact[];
  total: number;
}

export interface Reminder {
  id: string;
  text: string;
  dueDate: string;
  priority: 'low' | 'medium' | 'high';
  completed: boolean;
  createdAt: string;
}

export interface AINotification {
  id: string;
  source: string;
  type: string;
  title: string;
  message: string;
  priority: string;
  action_url: string;
  read: boolean;
  created_at: string;
  context?: { options?: string[]; [key: string]: any };
}

export interface ServiceHealth {
  backend:       boolean;
  workroomforge: boolean;
  luxeforge:     boolean;
  homepage:      boolean;
  amp:           boolean;
  socialforge:   boolean;
}

export interface SystemStats {
  cpu:    { percent: number; cores: number; freq_mhz: number | null };
  memory: { total_gb: number; used_gb: number; percent: number };
  disk:   { total_gb: number; used_gb: number; percent: number };
  temperatures: Record<string, { label: string; current: number; high: number | null; critical: number | null }[]>;
}

export interface StreamEvent {
  type: 'text' | 'done' | 'error' | 'tool_result';
  content?: string;
  model_used?: string;
  tool?: string;
  success?: boolean;
  result?: Record<string, unknown>;
  error?: string;
}

export interface BrainStatus {
  brain_online: boolean;
  storage: {
    path: string;
    external_drive: boolean;
    db_path: string;
  };
  memories: {
    total: number;
  };
  ollama: {
    online: boolean;
    url: string;
    models: string[];
  };
  conversations: {
    active: number;
  };
}

export interface TokenModelBreakdown {
  model: string;
  provider: string;
  input_tokens: number;
  output_tokens: number;
  cost: number;
  requests: number;
}

export interface TokenDailyUsage {
  day: string;
  input_tokens: number;
  output_tokens: number;
  cost: number;
  requests: number;
}

export interface TokenStats {
  period_days: number;
  total: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
    cost_usd: number;
    requests: number;
  };
  today: {
    input_tokens: number;
    output_tokens: number;
    cost_usd: number;
    requests: number;
  };
  by_model: TokenModelBreakdown[];
  daily: TokenDailyUsage[];
  budget: {
    monthly_limit: number;
    monthly_spent: number;
    percent_used: number;
    alert: boolean;
    auto_switch_to_local: boolean;
    auto_switch_threshold: number;
  };
}

/** Legacy task shape from /max/tasks endpoint (used by useSystemData) */
export interface MaxTask {
  id: string;
  title: string;
  description: string;
  desk_id: string;
  status: string;
  priority: number;
  created_at: string;
}
