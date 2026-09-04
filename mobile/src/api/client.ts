import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

import { API_URL } from '../config/api';
import { logError, logRequest, logResponse } from '../utils/logger';

export { API_URL };

export const api = axios.create({
  baseURL: `${API_URL}/api`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
  const tokens = await AsyncStorage.getItem('tokens');
  if (tokens) {
    const { access } = JSON.parse(tokens);
    if (access) {
      config.headers.Authorization = `Bearer ${access}`;
    }
  }

  // Avoid recursive logging of the log-shipping request itself.
  if (config.url && !config.url.endsWith('/logs/')) {
    (config as any)._startTime = Date.now();
    logRequest(config.method?.toUpperCase() || 'UNKNOWN', config.url);
  }

  return config;
});

api.interceptors.response.use(
  (response) => {
    const config = response.config as any;
    if (config.url && !config.url.endsWith('/logs/')) {
      const startTime = config._startTime || 0;
      logResponse(
        response.config.method?.toUpperCase() || 'UNKNOWN',
        response.config.url || 'unknown',
        response.status,
        startTime ? Date.now() - startTime : 0
      );
    }
    return response;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean; _startTime?: number };

    if (originalRequest.url && !originalRequest.url.endsWith('/logs/')) {
      const startTime = originalRequest._startTime || 0;
      logResponse(
        originalRequest.method?.toUpperCase() || 'UNKNOWN',
        originalRequest.url || 'unknown',
        error.response?.status || 0,
        startTime ? Date.now() - startTime : 0
      );
    }

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        const tokens = await AsyncStorage.getItem('tokens');
        if (tokens) {
          const { refresh } = JSON.parse(tokens);
          const res = await axios.post(`${API_URL}/api/users/refresh`, { refresh });
          const newTokens = res.data;
          await AsyncStorage.setItem('tokens', JSON.stringify(newTokens));
          originalRequest.headers.Authorization = `Bearer ${newTokens.access}`;
          return api(originalRequest);
        }
      } catch {
        await AsyncStorage.removeItem('tokens');
        await AsyncStorage.removeItem('user');
      }
    }

    if (error.response && originalRequest.url && !originalRequest.url.endsWith('/logs/')) {
      logError(`API error on ${originalRequest.url}`, error);
    }

    return Promise.reject(error);
  }
);

export default api;
