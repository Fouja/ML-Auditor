/**
 * Desktop integration layer for the ML-Auditor Tauri app.
 *
 * This module is the single place where the Next.js frontend talks to the
 * Tauri shell. It detects whether the app is running inside the desktop wrapper
 * and, when it is, asks Rust for the local backend URL instead of using the
 * hard-coded web API URL.
 */

import { invoke } from '@tauri-apps/api/core';

let cachedBackendUrl: string | null = null;

function isTauriAvailable(): boolean {
  return typeof window !== 'undefined' && !!(window as unknown as Record<string, unknown>).__TAURI__;
}

export async function isDesktopMode(): Promise<boolean> {
  if (!isTauriAvailable()) return false;
  try {
    return await invoke<boolean>('is_desktop_mode');
  } catch {
    return false;
  }
}

export async function getBackendUrl(): Promise<string> {
  if (!isTauriAvailable()) {
    return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  }

  if (cachedBackendUrl) return cachedBackendUrl;

  try {
    cachedBackendUrl = await invoke<string>('get_backend_url');
    return cachedBackendUrl;
  } catch {
    return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  }
}

export async function resetLocalDatabase(): Promise<string> {
  if (!isTauriAvailable()) {
    throw new Error('Database reset is only available in the desktop app.');
  }
  return invoke<string>('reset_local_database');
}

export async function checkForAppUpdate(): Promise<string> {
  if (!isTauriAvailable()) {
    throw new Error('App updates are only available in the desktop app.');
  }
  return invoke<string>('check_for_app_update');
}
