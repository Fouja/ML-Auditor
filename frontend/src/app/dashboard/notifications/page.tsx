'use client';

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { toast } from '@/hooks/use-toast';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import {
  Bell,
  BellRing,
  CheckCircle,
  Clock,
  ExternalLink,
  Filter,
  Loader2,
  XCircle,
} from 'lucide-react';

interface UnifiedItem {
  id: string;
  source: 'agent' | 'jira';
  title: string;
  description: string;
  severity: string;
  status: string;
  created_at: string;
  url: string | null;
}

interface UnifiedResponse {
  items: UnifiedItem[];
  total: number;
  jira_connected: boolean;
  jira_error: string | null;
}

interface NotificationPrefs {
  email_notifications: boolean;
  push_notifications: boolean;
  webhook_url: string;
  alert_email_enabled: boolean;
  alert_push_enabled: boolean;
}

const SEVERITY_STYLES: Record<string, string> = {
  critical: 'bg-red-500/10 text-red-500 border-red-500/50',
  high: 'bg-orange-500/10 text-orange-500 border-orange-500/50',
  medium: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/50',
  low: 'bg-blue-500/10 text-blue-500 border-blue-500/50',
};

function severityBadge(severity: string) {
  return (
    <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${SEVERITY_STYLES[severity] || SEVERITY_STYLES.medium}`}>
      {severity}
    </span>
  );
}

function SourceBadge({ source }: { source: string }) {
  return source === 'jira' ? (
    <span className="rounded-full border border-blue-500/40 bg-blue-500/10 px-2 py-0.5 text-xs text-blue-500">
      Jira
    </span>
  ) : (
    <span className="rounded-full border border-primary/40 bg-primary/10 px-2 py-0.5 text-xs text-primary">
      Argus alert
    </span>
  );
}

function formatDate(value: string) {
  try {
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return value;
    return d.toLocaleString();
  } catch {
    return value;
  }
}

export default function NotificationsPage() {
  const queryClient = useQueryClient();
  const [severityFilter, setSeverityFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const { data: feed, isLoading: feedLoading } = useQuery<UnifiedResponse>({
    queryKey: ['unifiedAlerts'],
    queryFn: async () => {
      const res = await api.get('/alerts/unified', { params: { limit: 50 } });
      return res.data;
    },
  });

  const { data: prefs, isLoading: prefsLoading } = useQuery<NotificationPrefs>({
    queryKey: ['notificationPrefs'],
    queryFn: async () => {
      const res = await api.get('/agents/notifications/preferences');
      return res.data;
    },
  });

  const updatePrefsMutation = useMutation({
    mutationFn: async (updates: Partial<NotificationPrefs>) => {
      const res = await api.put('/agents/notifications/preferences', updates);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notificationPrefs'] });
      toast({ title: 'Saved', description: 'Notification preferences updated', variant: 'default' });
    },
  });

  const acknowledgeMutation = useMutation({
    mutationFn: async (id: string) => {
      const res = await api.post(`/alerts/${id}/acknowledge`);
      return res.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['unifiedAlerts'] }),
  });

  const dismissMutation = useMutation({
    mutationFn: async (id: string) => {
      const res = await api.post(`/alerts/${id}/dismiss`);
      return res.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['unifiedAlerts'] }),
  });

  const filtered = (feed?.items ?? []).filter((item) => {
    if (severityFilter && item.severity !== severityFilter) return false;
    if (statusFilter && item.status !== statusFilter) return false;
    return true;
  });

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Alerts &amp; Notifications</h1>
          <p className="text-muted-foreground">
            Agent alerts and Jira tickets in one feed, plus your delivery preferences.
          </p>
        </div>

        {/* Feed */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <div className="flex items-center gap-2">
              <Bell className="h-5 w-5 text-muted-foreground" />
              <CardTitle className="text-base">Activity Feed</CardTitle>
            </div>
            <span className="rounded-full bg-muted px-2.5 py-0.5 text-xs text-muted-foreground">
              {feed?.total ?? 0} items
            </span>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Filters */}
            <div className="flex flex-wrap items-center gap-3">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                className="rounded-md border bg-background px-3 py-1.5 text-sm"
              >
                <option value="">All severities</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="rounded-md border bg-background px-3 py-1.5 text-sm"
              >
                <option value="">All statuses</option>
                <option value="pending">Pending</option>
                <option value="acknowledged">Acknowledged</option>
                <option value="executed">Executed</option>
                <option value="dismissed">Dismissed</option>
              </select>
              {feed?.jira_error && (
                <span className="text-xs text-amber-600">Jira: {feed.jira_error}</span>
              )}
            </div>

            {feedLoading ? (
              <div className="flex justify-center py-10">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : filtered.length === 0 ? (
              <div className="py-10 text-center text-sm text-muted-foreground">
                No alerts or tickets to show.
              </div>
            ) : (
              <div className="space-y-3">
                {filtered.map((item) => (
                  <div key={`${item.source}-${item.id}`} className="flex items-start justify-between rounded-lg border p-4">
                    <div className="flex items-start gap-3">
                      {item.source === 'jira' ? (
                        <ExternalLink className="mt-0.5 h-4 w-4 text-blue-500" />
                      ) : item.status === 'dismissed' ? (
                        <XCircle className="mt-0.5 h-4 w-4 text-gray-500" />
                      ) : item.status === 'acknowledged' || item.status === 'executed' ? (
                        <CheckCircle className="mt-0.5 h-4 w-4 text-green-500" />
                      ) : (
                        <Clock className="mt-0.5 h-4 w-4 text-yellow-500" />
                      )}
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="text-sm font-medium">{item.title}</p>
                          {severityBadge(item.severity)}
                          <SourceBadge source={item.source} />
                        </div>
                        {item.description && (
                          <p className="mt-1 text-sm text-muted-foreground">{item.description}</p>
                        )}
                        <p className="mt-1 text-xs text-muted-foreground">
                          {formatDate(item.created_at)} · status: {item.status}
                        </p>
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      {item.source === 'jira' && item.url ? (
                        <a
                          href={item.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-blue-500 hover:underline"
                        >
                          Open in Jira
                        </a>
                      ) : item.status === 'pending' ? (
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-7 text-xs"
                            onClick={() => acknowledgeMutation.mutate(item.id)}
                            disabled={acknowledgeMutation.isPending}
                          >
                            Acknowledge
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-7 text-xs"
                            onClick={() => dismissMutation.mutate(item.id)}
                            disabled={dismissMutation.isPending}
                          >
                            Dismiss
                          </Button>
                        </div>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Delivery preferences */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <BellRing className="h-5 w-5" />
              <CardTitle className="text-base">Delivery Channels</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {prefsLoading ? (
              <p className="text-sm text-muted-foreground">Loading preferences...</p>
            ) : (
              <>
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Email Notifications</Label>
                    <p className="text-xs text-muted-foreground">Receive alerts via email</p>
                  </div>
                  <button
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      prefs?.email_notifications ? 'bg-primary' : 'bg-muted'
                    }`}
                    onClick={() =>
                      updatePrefsMutation.mutate({ email_notifications: !prefs?.email_notifications })
                    }
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        prefs?.email_notifications ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Push Notifications</Label>
                    <p className="text-xs text-muted-foreground">Browser push notifications</p>
                  </div>
                  <button
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      prefs?.push_notifications ? 'bg-primary' : 'bg-muted'
                    }`}
                    onClick={() =>
                      updatePrefsMutation.mutate({ push_notifications: !prefs?.push_notifications })
                    }
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        prefs?.push_notifications ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
