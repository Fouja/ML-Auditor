'use client';

import { useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import {
  isDesktopMode,
  requestNotificationPermission,
  sendNotification,
  playNotificationSound,
} from '@/lib/desktop';

interface Reminder {
  id: string;
  title: string;
  due_date: string | null;
  type: 'boot' | 'one_hour';
}

interface RemindersResponse {
  boot: Reminder[];
  one_hour: Reminder[];
}

const POLL_INTERVAL_MS = 60_000; // Check every minute.

export function TaskReminderPoller() {
  const queryClient = useQueryClient();
  const lastPollRef = useRef<number>(0);

  const notify = async (reminders: Reminder[]) => {
    if (reminders.length === 0) return;

    const desktop = await isDesktopMode();
    if (desktop) {
      await requestNotificationPermission();
    }

    // Play the classical chime once, then show one grouped notification.
    await playNotificationSound();

    const titles = reminders.map((r) => r.title).join(', ');
    const body =
      reminders.length === 1
        ? `Reminder: ${titles}`
        : `${reminders.length} tasks need attention: ${titles}`;

    if (desktop) {
      await sendNotification('ML-Auditor Reminder', body);
    } else {
      // Web fallback: use the browser Notification API.
      if ('Notification' in window && Notification.permission === 'granted') {
        new Notification('ML-Auditor Reminder', { body });
      }
    }
  };

  const checkReminders = async () => {
    const now = Date.now();
    if (now - lastPollRef.current < POLL_INTERVAL_MS) return;
    lastPollRef.current = now;

    try {
      const res = await api.get<RemindersResponse>('/workspace/tasks/reminders');
      const { boot, one_hour } = res.data;
      const all = [...boot, ...one_hour];
      if (all.length > 0) {
        await notify(all);
        // Refresh task lists so the UI reflects any state changes.
        queryClient.invalidateQueries({ queryKey: ['tasks'] });
      }
    } catch {
      // Backend may not be ready yet; retry on next poll.
    }
  };

  useEffect(() => {
    let mounted = true;

    const runLoop = async () => {
      if (!mounted) return;
      await checkReminders();
      setTimeout(runLoop, POLL_INTERVAL_MS);
    };

    // Initial check shortly after mount.
    const timeout = setTimeout(runLoop, 5000);

    return () => {
      mounted = false;
      clearTimeout(timeout);
    };
  }, [queryClient]);

  return null;
}
