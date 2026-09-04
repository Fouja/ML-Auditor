import api from './client';
import { Tokens, User } from '../types';

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  username: string;
  password: string;
}

interface TokenPayload {
  access: string;
  refresh: string;
}

async function buildSession(payload: TokenPayload): Promise<{ tokens: Tokens; user: User }> {
  const tokens: Tokens = { access: payload.access, refresh: payload.refresh };
  const res = await api.get('/users/me', {
    headers: { Authorization: `Bearer ${payload.access}` },
  });
  return { tokens, user: res.data };
}

export async function login(credentials: LoginCredentials): Promise<{ tokens: Tokens; user: User }> {
  const res = await api.post<TokenPayload>('/users/login', credentials);
  return buildSession(res.data);
}

export async function register(data: RegisterData): Promise<{ tokens: Tokens; user: User }> {
  const res = await api.post<TokenPayload>('/users/register', data);
  return buildSession(res.data);
}

export async function getMe(): Promise<User> {
  const res = await api.get('/users/me');
  return res.data;
}

export async function registerPushToken(token: string, platform: string): Promise<void> {
  await api.post('/users/push-token', { token, platform });
}
