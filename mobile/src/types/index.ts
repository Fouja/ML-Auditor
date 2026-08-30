export interface User {
  id: string;
  email: string;
  username: string;
  first_name?: string;
  last_name?: string;
}

export interface Tokens {
  access: string;
  refresh: string;
}

export interface Task {
  id: string;
  title: string;
  description: string;
  status: 'todo' | 'in_progress' | 'review' | 'done';
  priority: 'low' | 'medium' | 'high' | 'critical';
  due_date?: string;
  tags: string[];
  position: number;
}

export interface CalendarEvent {
  id: string;
  title: string;
  description: string;
  location: string;
  start_time: string;
  end_time: string;
  all_day: boolean;
}

export interface IntegrationStatus {
  email: { imap_connected: boolean; gmail_connected: boolean; provider: string };
  gmail: { connected: boolean };
  calendar: { connected: boolean };
  plaid: { connected: boolean };
  canva: { connected: boolean };
  kijiji: { connected: boolean };
  jira: { connected: boolean };
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export interface PushToken {
  token: string;
  platform: string;
}
