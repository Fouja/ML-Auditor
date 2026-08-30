import api from './client';
import { Task, CalendarEvent } from '../types';

export async function getTasks(status?: string): Promise<Task[]> {
  const res = await api.get('/workspace/tasks', { params: { status } });
  return res.data;
}

export async function createTask(task: Partial<Task>): Promise<Task> {
  const res = await api.post('/workspace/tasks', task);
  return res.data;
}

export async function updateTask(id: string, task: Partial<Task>): Promise<Task> {
  const res = await api.put(`/workspace/tasks/${id}`, task);
  return res.data;
}

export async function deleteTask(id: string): Promise<void> {
  await api.delete(`/workspace/tasks/${id}`);
}

export async function getEvents(): Promise<CalendarEvent[]> {
  const res = await api.get('/workspace/events');
  return res.data;
}

export async function getIntegrationStatus(): Promise<any> {
  const res = await api.get('/integrations/status');
  return res.data;
}
