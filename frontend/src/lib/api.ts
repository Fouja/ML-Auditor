import axios from 'axios';

import { getBackendUrl, isDesktopMode } from './desktop';

const FALLBACK_API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: `${FALLBACK_API_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 90000,
});

// Resolve the real backend URL on every request. In the Tauri desktop app this
// comes from the Rust sidecar; in a browser it stays the static fallback.
async function resolveBaseUrl(): Promise<string> {
  try {
    const backendUrl = await getBackendUrl();
    return `${backendUrl}/api`;
  } catch {
    return `${FALLBACK_API_URL}/api`;
  }
}

// ---- Frontend Logger ----
// Writes structured JSON logs to /var/log/ml-auditor/frontend/frontend.log (when available)
// and also attempts to POST logs to the backend /api/logs endpoint.

export interface LogEntry {
  "@timestamp": string;
  level: "info" | "warn" | "error" | "debug";
  service: "web" | "desktop" | "mobile";
  stack: "nextjs" | "tauri" | "react-native";
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

class FrontendLogger {
  private buffer: LogEntry[] = [];
  private flushInterval: ReturnType<typeof setInterval> | null = null;
  private readonly BUFFER_SIZE = 20;
  private readonly FLUSH_INTERVAL_MS = 5000;
  private service: LogEntry["service"] = "web";
  private stack: LogEntry["stack"] = "nextjs";
  private serviceResolved = false;

  constructor() {
    if (typeof window !== "undefined") {
      this.resolveService();
      this.flushInterval = setInterval(() => this.flush(), this.FLUSH_INTERVAL_MS);
    }
  }

  private async resolveService() {
    try {
      if (await isDesktopMode()) {
        this.service = "desktop";
        this.stack = "tauri";
      }
    } catch {
      // Stay with the web defaults.
    } finally {
      this.serviceResolved = true;
    }
  }

  private formatEntry(level: LogEntry["level"], message: string, extra: Partial<LogEntry> = {}): LogEntry {
    return {
      "@timestamp": new Date().toISOString(),
      level,
      service: this.service,
      stack: this.stack,
      message,
      ...extra,
    };
  }

  private addToBuffer(entry: LogEntry) {
    this.buffer.push(entry);
    if (this.buffer.length >= this.BUFFER_SIZE) {
      this.flush();
    }
  }

  private async flush() {
    if (this.buffer.length === 0) return;
    const entries = this.buffer.splice(0, this.BUFFER_SIZE);

    try {
      const backendUrl = await getBackendUrl();
      await fetch(`${backendUrl}/api/logs/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ logs: entries }),
        keepalive: true,
      });
    } catch {
      // Backend not available or endpoint doesn't exist — fallback: console
      // The logs are still visible in browser devtools
    }
  }

  info(message: string, extra?: Partial<LogEntry>) {
    const entry = this.formatEntry("info", message, extra);
    console.log(`[LOG INFO] ${message}`, extra || "");
    this.addToBuffer(entry);
  }

  warn(message: string, extra?: Partial<LogEntry>) {
    const entry = this.formatEntry("warn", message, extra);
    console.warn(`[LOG WARN] ${message}`, extra || "");
    this.addToBuffer(entry);
  }

  error(message: string, extra?: Partial<LogEntry>) {
    const entry = this.formatEntry("error", message, extra);
    console.error(`[LOG ERROR] ${message}`, extra || "");
    this.addToBuffer(entry);
  }

  debug(message: string, extra?: Partial<LogEntry>) {
    if (process.env.NODE_ENV === "development") {
      const entry = this.formatEntry("debug", message, extra);
      console.debug(`[LOG DEBUG] ${message}`, extra || "");
      this.addToBuffer(entry);
    }
  }

  request(method: string, path: string, extra?: Partial<LogEntry>) {
    this.info(`${method} ${path}`, { method, path, endpoint: `${method} ${path}`, ...extra });
  }

  response(method: string, path: string, status_code: number, response_time: number) {
    const level: LogEntry["level"] = status_code >= 500 ? "error" : status_code >= 400 ? "warn" : "info";
    this[level](`${method} ${path} ${status_code}`, {
      method,
      path,
      status_code,
      response_time,
    });
  }
}

export const frontendLogger = new FrontendLogger();

// Request interceptor to add auth token + log requests
api.interceptors.request.use(
  async (config) => {
    const startTime = Date.now();
    (config as unknown as Record<string, unknown>)._startTime = startTime;

    // In the desktop app the backend runs on a random local port chosen by
    // Tauri, so we rewrite the request baseURL before it goes out.
    if (config.url && !config.url.startsWith('http')) {
      config.baseURL = await resolveBaseUrl();
    }

    if (typeof window !== "undefined") {
      const token = localStorage.getItem("access_token");
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }

    frontendLogger.request(config.method?.toUpperCase() || "UNKNOWN", config.url || "unknown");
    return config;
  },
  (error) => {
    frontendLogger.error("Request setup failed", {
      error_name: error.name,
      error_message: error.message,
    });
    return Promise.reject(error);
  }
);

// Response interceptor to handle token refresh + log responses
api.interceptors.response.use(
  (response) => {
    const startTime = (response.config as unknown as Record<string, unknown>)._startTime as number | undefined;
    const response_time = startTime ? Date.now() - startTime : 0;
    frontendLogger.response(
      response.config.method?.toUpperCase() || "UNKNOWN",
      response.config.url || "unknown",
      response.status,
      response_time
    );
    return response;
  },
  async (error) => {
    const startTime = (error.config as Record<string, unknown>)?._startTime as number | undefined;
    const response_time = startTime ? Date.now() - startTime : 0;

    frontendLogger.response(
      error.config?.method?.toUpperCase() || "UNKNOWN",
      error.config?.url || "unknown",
      error.response?.status || 0,
      response_time
    );

    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      if (typeof window !== "undefined") {
        const refreshToken = localStorage.getItem("refresh_token");
        if (refreshToken) {
          try {
            frontendLogger.info("Attempting token refresh");
            const backendUrl = await getBackendUrl();
            const response = await axios.post(`${backendUrl}/api/users/refresh`, {
              refresh: refreshToken,
            });
            const { access, refresh } = response.data;
            localStorage.setItem("access_token", access);
            localStorage.setItem("refresh_token", refresh);
            originalRequest.headers.Authorization = `Bearer ${access}`;
            frontendLogger.info("Token refresh successful");
            return api(originalRequest);
          } catch (refreshError) {
            frontendLogger.warn("Token refresh failed, redirecting to login");
            localStorage.removeItem("access_token");
            localStorage.removeItem("refresh_token");
            window.location.href = "/login";
          }
        }
      }
    }

    if (error.response?.status >= 500) {
      frontendLogger.error(`Server error: ${error.config?.url}`, {
        status_code: error.response?.status,
        error_name: error.name,
        error_message: error.message,
      });
    }

    return Promise.reject(error);
  }
);

export default api;
