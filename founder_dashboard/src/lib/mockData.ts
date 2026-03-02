import { Desk, AIModel } from './types';

export const MOCK_DESKS: Desk[] = [
  { id: 'devbot',     name: 'DevBot',     description: 'Development & code',       status: 'idle' },
  { id: 'opsbot',     name: 'OpsBot',     description: 'Infrastructure & ops',     status: 'idle' },
  { id: 'salesbot',   name: 'SalesBot',   description: 'Sales & leads',            status: 'idle' },
  { id: 'supportbot', name: 'SupportBot', description: 'Customer support',         status: 'idle' },
  { id: 'financebot', name: 'FinanceBot', description: 'Finance & billing',        status: 'idle' },
  { id: 'contentbot', name: 'ContentBot', description: 'Marketing & content',      status: 'idle' },
  { id: 'productbot', name: 'ProductBot', description: 'Product & inventory',      status: 'idle' },
  { id: 'qabot',      name: 'QABot',      description: 'Quality assurance',        status: 'idle' },
];

export const MOCK_MODELS: AIModel[] = [
  { id: 'grok',         name: 'xAI Grok',          available: false, primary: true,  type: 'cloud' },
  { id: 'claude',       name: 'Claude 4.6 Sonnet', available: false, primary: false, type: 'cloud' },
];
