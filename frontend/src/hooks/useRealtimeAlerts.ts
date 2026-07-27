'use client';

import { useEffect, useState, useCallback } from 'react';
import { useWebSocket } from './useWebSocket';
import { AgentAlert } from '@/types';

interface UseRealtimeAlertsOptions {
  onNewAlert?: (alert: AgentAlert) => void;
  onAlertUpdate?: (alert: AgentAlert) => void;
}

export function useRealtimeAlerts(options: UseRealtimeAlertsOptions = {}) {
  const { onNewAlert, onAlertUpdate } = options;
  const [alerts, setAlerts] = useState<AgentAlert[]>([]);

  const handleMessage = useCallback(
    (data: unknown) => {
      const message = data as { type: string; alert?: AgentAlert };

      switch (message.type) {
        case 'new_alert':
          if (message.alert) {
            setAlerts((prev) => [message.alert!, ...prev]);
            onNewAlert?.(message.alert);
          }
          break;
        case 'alert_update':
          if (message.alert) {
            setAlerts((prev) =>
              prev.map((a) => (a.id === message.alert!.id ? message.alert! : a))
            );
            onAlertUpdate?.(message.alert);
          }
          break;
      }
    },
    [onNewAlert, onAlertUpdate]
  );

  const { isConnected, send } = useWebSocket(
    `${process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'}/ws/alerts/`,
    {
      onMessage: handleMessage,
    }
  );

  const subscribe = useCallback(
    (alertType: string = 'all') => {
      send({ type: 'subscribe', alert_type: alertType });
    },
    [send]
  );

  return {
    alerts,
    setAlerts,
    isConnected,
    subscribe,
  };
}
