import api from './client';

export interface ChatResponse {
  response: string;
  conversation_id?: string;
}

export async function sendMessage(message: string, conversationId?: string): Promise<ChatResponse> {
  const res = await api.post('/agents/chat', {
    message,
    conversation_id: conversationId,
  });
  return res.data;
}

export async function getChatHistory(): Promise<any[]> {
  const res = await api.get('/agents/chat/history');
  return res.data;
}
