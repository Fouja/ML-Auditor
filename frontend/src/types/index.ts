export interface User {
  id: string;
  email: string;
  username: string;
  first_name?: string;
  last_name?: string;
  phone_number?: string;
  avatar_url?: string;
  email_notifications: boolean;
  push_notifications: boolean;
  created_at: string;
}

export interface TokenResponse {
  access: string;
  refresh: string;
  token_type: string;
}

export interface DataStream {
  id: string;
  source_type: string;
  payload: Record<string, unknown>;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  created_at: string;
  processed_at?: string;
  error_message?: string;
}

export interface AgentAlert {
  id: string;
  title: string;
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'pending' | 'acknowledged' | 'executed' | 'dismissed';
  source_type?: string;
  source_id?: string;
  action_payload?: Record<string, unknown>;
  created_at: string;
  acknowledged_at?: string;
  executed_at?: string;
}

export interface DocumentChunk {
  id: string;
  content: string;
  cluster_category: string;
  chunk_index: number;
  total_chunks: number;
  metadata?: Record<string, unknown>;
  created_at: string;
  stream_id: string;
}

export interface AlertStats {
  total: number;
  pending: number;
  acknowledged: number;
  executed: number;
  dismissed: number;
  by_severity: Record<string, number>;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pages: number;
}

export interface Agent {
  name: string;
  type: string;
  status: string;
  description: string;
}

export interface AgentStatus {
  agents: Agent[];
  active_tasks: number;
  completed_tasks: number;
}

// Integration types
export interface IntegrationStatus {
  email: { imap_connected: boolean; gmail_connected: boolean; provider: string };
  calendar: { connected: boolean };
  plaid: { connected: boolean };
  canva: { connected: boolean };
  kijiji: { connected: boolean };
  jira: { connected: boolean };
}

export interface IntegrationConnection {
  id: string;
  service: string;
  status: 'active' | 'error' | 'expired' | 'disconnected';
  last_synced: string | null;
  last_error: string;
  items_synced: number;
}

export interface EmailMessage {
  id: string;
  subject: string;
  from: string;
  date: string;
  snippet: string;
}

export interface CalendarEvent {
  id: string;
  summary: string;
  description: string;
  location: string;
  start: string;
  end: string;
  attendees: string[];
  html_link: string;
}

export interface PlaidAccount {
  id: string;
  name: string;
  official_name: string;
  type: string;
  subtype: string;
  balances: {
    available: number;
    current: number;
    limit: number | null;
  };
}

export interface PlaidTransaction {
  id: string;
  name: string;
  amount: number;
  date: string;
  category: string[];
  account_id: string;
}

export interface KijijiListing {
  id: string;
  title: string;
  price: number;
  location: string;
  image_url: string;
  url: string;
}
