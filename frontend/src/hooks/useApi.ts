'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import {
  DataStream,
  AgentAlert,
  DocumentChunk,
  AlertStats,
  PaginatedResponse,
  AgentStatus,
} from '@/types';

// Data Streams hooks
export function useDataStreams(page = 1, pageSize = 20) {
  return useQuery<PaginatedResponse<DataStream>>({
    queryKey: ['dataStreams', page, pageSize],
    queryFn: async () => {
      const response = await api.get('/data-streams/', {
        params: { page, page_size: pageSize },
      });
      return response.data;
    },
  });
}

export function useCreateDataStream() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: { source_type: string; payload: Record<string, unknown> }) => {
      const response = await api.post('/data-streams/', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataStreams'] });
    },
  });
}

// Alerts hooks
export function useAlerts(page = 1, pageSize = 20, severity?: string, status?: string) {
  return useQuery<PaginatedResponse<AgentAlert>>({
    queryKey: ['alerts', page, pageSize, severity, status],
    queryFn: async () => {
      const params: Record<string, unknown> = { page, page_size: pageSize };
      if (severity) params.severity = severity;
      if (status) params.status = status;
      const response = await api.get('/alerts/', { params });
      return response.data;
    },
  });
}

export function useAlertStats() {
  return useQuery<AlertStats>({
    queryKey: ['alertStats'],
    queryFn: async () => {
      const response = await api.get('/alerts/stats');
      return response.data;
    },
  });
}

export function useAcknowledgeAlert() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (alertId: string) => {
      const response = await api.post(`/alerts/${alertId}/acknowledge`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      queryClient.invalidateQueries({ queryKey: ['alertStats'] });
    },
  });
}

export function useDismissAlert() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (alertId: string) => {
      const response = await api.post(`/alerts/${alertId}/dismiss`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      queryClient.invalidateQueries({ queryKey: ['alertStats'] });
    },
  });
}

// Document Chunks hooks
export function useDocumentChunks(page = 1, pageSize = 20, category?: string) {
  return useQuery<PaginatedResponse<DocumentChunk>>({
    queryKey: ['documentChunks', page, pageSize, category],
    queryFn: async () => {
      const params: Record<string, unknown> = { page, page_size: pageSize };
      if (category) params.cluster_category = category;
      const response = await api.get('/document-chunks/', { params });
      return response.data;
    },
  });
}

export function useSearchDocuments() {
  return useMutation({
    mutationFn: async (data: { query: string; limit?: number; cluster_category?: string }) => {
      const response = await api.post('/document-chunks/search', data);
      return response.data;
    },
  });
}

// Agent hooks
export function useAgentStatus() {
  return useQuery<AgentStatus>({
    queryKey: ['agentStatus'],
    queryFn: async () => {
      const response = await api.get('/agents/status');
      return response.data;
    },
  });
}

export function useAgentChat() {
  return useMutation({
    mutationFn: async (data: { content: string; agent_type?: string }) => {
      const response = await api.post('/agents/chat', data);
      return response.data;
    },
  });
}
