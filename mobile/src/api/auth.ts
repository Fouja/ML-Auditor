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

export async function login(credentials: LoginCredentials): Promise<{ tokens: Tokens; user: User }> {
  const res = await api.post('/users/login', credentials);
  return res.data;
}

export async function register(data: RegisterData): Promise<{ tokens: Tokens; user: User }> {
  const res = await api.post('/users/register', data);
  return res.data;
}

export async function getMe(): Promise<User> {
  const res = await api.get('/users/me');
  return res.data;
}

export async function registerPushToken(token: string, platform: string): Promise<void> {
  await api.post('/users/push-token', { token, platform });
}
