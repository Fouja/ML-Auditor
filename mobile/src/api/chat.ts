import api from './client';

export interface ChatResponse {
  response: string;
  conversation_id?: string;
}

export async function sendMessage(message: string, conversationId?: string): Promise<ChatResponse> {
  const res = await api.post<ChatResponse>('/agents/chat', {
    content: message,
    agent_type: 'general',
    conversation_id: conversationId,
  });
  return res.data;
}

export interface ChatHistoryItem {
  role: 'user' | 'assistant';
  content: string;
}

export async function getChatHistory(): Promise<ChatHistoryItem[]> {
  const res = await api.get('/agents/chat/history');
  const data = res.data;
  return data?.messages ?? (Array.isArray(data) ? data : []);
}
