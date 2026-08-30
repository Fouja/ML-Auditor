'use client';

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { IntegrationLog } from '@/types';
import { ScrollText, Filter } from 'lucide-react';

const SERVICES = [
  { value: '', label: 'All services' },
  { value: 'plaid', label: 'Plaid' },
  { value: 'gmail', label: 'Gmail' },
  { value: 'google_calendar', label: 'Google Calendar' },
  { value: 'canva', label: 'Canva' },
  { value: 'jira', label: 'Jira' },
  { value: 'email', label: 'Email (IMAP)' },
];

const LEVEL_COLORS: Record<string, string> = {
  info: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  success: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  warning: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  error: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
};

export function IntegrationLogs() {
  const [service, setService] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['integrationLogs', service],
    queryFn: async () => {
      const res = await api.get('/integrations/logs', { params: { service, limit: 100 } });
      return res.data as IntegrationLog[];
    },
  });

  return (
    <Card className="panel-gilded">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <div className="flex items-center gap-3">
          <div className="text-2xl"><ScrollText className="h-6 w-6" /></div>
          <div>
            <CardTitle className="text-base font-display tracking-wide">Integration State Logs</CardTitle>
            <p className="text-xs text-muted-foreground">Recent events, tests, and sync status for your integrations.</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <select
            className="rounded border bg-transparent px-2 py-1 text-xs"
            value={service}
            onChange={(e) => setService(e.target.value)}
          >
            {SERVICES.map((s) => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading logs…</p>
        ) : (data ?? []).length === 0 ? (
          <p className="text-sm text-muted-foreground">No logs yet. Add or test an integration to see state updates.</p>
        ) : (
          <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
            {(data ?? []).map((log) => (
              <div key={log.id} className="flex items-start gap-3 border rounded p-2 text-sm">
                <Badge className={`text-xs ${LEVEL_COLORS[log.level] || LEVEL_COLORS.info}`}>
                  {log.level}
                </Badge>
                <div className="flex-1 min-w-0 space-y-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium capitalize">{log.service.replace('_', ' ')}</span>
                    <span className="text-xs text-muted-foreground whitespace-nowrap">{new Date(log.created_at).toLocaleString()}</span>
                  </div>
                  <p className="text-muted-foreground">{log.message}</p>
                  {log.metadata && Object.keys(log.metadata).length > 0 && (
                    <pre className="text-xs bg-muted rounded p-2 overflow-x-auto">
                      {JSON.stringify(log.metadata, null, 2)}
                    </pre>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
