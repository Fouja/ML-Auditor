import * as FileSystem from 'expo-file-system/legacy';

import { API_URL } from '../config/api';

export type LogLevel = 'info' | 'warn' | 'error' | 'debug';

export interface MobileLogEntry {
  '@timestamp': string;
  level: LogLevel;
  service: 'mobile';
  stack: 'react-native';
  message: string;
  method?: string;
  path?: string;
  status_code?: number;
  response_time?: number;
  endpoint?: string;
  error_name?: string;
  error_message?: string;
  stack_trace?: string;
  user_id?: string;
  [key: string]: unknown;
}

const OFFLINE_LOG_PATH = `${FileSystem.documentDirectory}ml-auditor-logs.jsonl`;
const BUFFER_SIZE = 20;
const FLUSH_INTERVAL_MS = 5000;
const MAX_OFFLINE_LINES = 200;

/**
 * Mobile logger for ML-Auditor.
 *
 * Batches structured JSON logs and flushes them to the backend `/api/logs/`
 * endpoint. When the backend is unreachable, logs are buffered on-device using
 * Expo FileSystem and replayed on the next successful flush.
 */
class MobileLogger {
  private buffer: MobileLogEntry[] = [];
  private flushTimer: ReturnType<typeof setInterval> | null = null;

  constructor() {
    this.flushTimer = setInterval(() => this.flush(), FLUSH_INTERVAL_MS);
  }

  private formatEntry(level: LogLevel, message: string, extra: Partial<MobileLogEntry> = {}): MobileLogEntry {
    return {
      '@timestamp': new Date().toISOString(),
      level,
      service: 'mobile',
      stack: 'react-native',
      message,
      ...extra,
    };
  }

  private add(level: LogLevel, message: string, extra?: Partial<MobileLogEntry>) {
    const entry = this.formatEntry(level, message, extra);
    this.buffer.push(entry);
    if (this.buffer.length >= BUFFER_SIZE) {
      this.flush();
    }
  }

  info(message: string, extra?: Partial<MobileLogEntry>) {
    this.add('info', message, extra);
  }

  warn(message: string, extra?: Partial<MobileLogEntry>) {
    this.add('warn', message, extra);
  }

  error(message: string, extra?: Partial<MobileLogEntry>) {
    this.add('error', message, extra);
  }

  debug(message: string, extra?: Partial<MobileLogEntry>) {
    if (__DEV__) {
      this.add('debug', message, extra);
    }
  }

  request(method: string, path: string, extra?: Partial<MobileLogEntry>) {
    this.info(`${method} ${path}`, { method, path, endpoint: `${method} ${path}`, ...extra });
  }

  response(method: string, path: string, statusCode: number, responseTime: number, extra?: Partial<MobileLogEntry>) {
    const level: LogLevel = statusCode >= 500 ? 'error' : statusCode >= 400 ? 'warn' : 'info';
    this.add(level, `${method} ${path} ${statusCode}`, {
      method,
      path,
      status_code: statusCode,
      response_time: responseTime,
      ...extra,
    });
  }

  async flush() {
    if (this.buffer.length === 0 && !(await this.hasOfflineLogs())) {
      return;
    }

    const entries = this.buffer.splice(0, BUFFER_SIZE);
    const offlineLines = await this.readOfflineLogs();
    const payload = [...entries, ...offlineLines];

    if (payload.length === 0) {
      return;
    }

    try {
      const response = await fetch(`${API_URL}/api/logs/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ logs: payload }),
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      // Only clear offline buffer after a successful shipment.
      await this.clearOfflineLogs();
    } catch {
      // Backend unreachable — persist the current batch offline for replay.
      await this.appendOffline(payload);
    }
  }

  private async hasOfflineLogs(): Promise<boolean> {
    const info = await FileSystem.getInfoAsync(OFFLINE_LOG_PATH);
    return info.exists && info.size > 0;
  }

  private async readOfflineLogs(): Promise<MobileLogEntry[]> {
    try {
      const info = await FileSystem.getInfoAsync(OFFLINE_LOG_PATH);
      if (!info.exists) return [];
      const raw = await FileSystem.readAsStringAsync(OFFLINE_LOG_PATH);
      await FileSystem.deleteAsync(OFFLINE_LOG_PATH, { idempotent: true });
      return raw
        .split('\n')
        .filter(Boolean)
        .map((line) => {
          try {
            return JSON.parse(line) as MobileLogEntry;
          } catch {
            return null;
          }
        })
        .filter((entry): entry is MobileLogEntry => entry !== null);
    } catch {
      return [];
    }
  }

  private async appendOffline(entries: MobileLogEntry[]) {
    try {
      const lines = entries.map((e) => JSON.stringify(e)).join('\n') + '\n';
      await FileSystem.makeDirectoryAsync(FileSystem.documentDirectory!, { intermediates: true });
      const current = await FileSystem.readAsStringAsync(OFFLINE_LOG_PATH).catch(() => '');
      const combined = (current + lines).split('\n').filter(Boolean);
      const trimmed = combined.slice(-MAX_OFFLINE_LINES).join('\n') + '\n';
      await FileSystem.writeAsStringAsync(OFFLINE_LOG_PATH, trimmed);
    } catch {
      // Best-effort offline persistence.
    }
  }

  private async clearOfflineLogs() {
    try {
      const info = await FileSystem.getInfoAsync(OFFLINE_LOG_PATH);
      if (info.exists) {
        await FileSystem.deleteAsync(OFFLINE_LOG_PATH, { idempotent: true });
      }
    } catch {
      // Ignore cleanup errors.
    }
  }
}

export const mobileLogger = new MobileLogger();

export function logRequest(method: string, url: string, startTime?: number) {
  mobileLogger.request(method, url);
}

export function logResponse(method: string, url: string, statusCode: number, startTime: number) {
  const responseTime = Date.now() - startTime;
  mobileLogger.response(method, url, statusCode, responseTime);
}

export function logError(context: string, error: any) {
  mobileLogger.error(context, {
    error_name: error?.name || 'Error',
    error_message: error?.message || String(error),
    stack_trace: error?.stack,
  });
}

export function getApiBaseUrl(): string {
  return API_URL;
}
