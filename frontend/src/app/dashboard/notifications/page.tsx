'use client';

import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';

interface NotificationPrefs {
  email_notifications: boolean;
  push_notifications: boolean;
  webhook_url: string;
  alert_email_enabled: boolean;
  alert_push_enabled: boolean;
}

const SEVERITY_INFO = [
  { level: 'critical', label: 'Critical', description: 'Immediate action required', color: 'bg-red-500', channels: ['Email', 'Push', 'WebSocket'] },
  { level: 'high', label: 'High', description: 'Action within 1 hour', color: 'bg-orange-500', channels: ['Email', 'WebSocket'] },
  { level: 'medium', label: 'Medium', description: 'Action within 24 hours', color: 'bg-yellow-500', channels: ['WebSocket'] },
  { level: 'low', label: 'Low', description: 'Informational', color: 'bg-green-500', channels: [] },
];

export default function NotificationsPage() {
  const queryClient = useQueryClient();
  const [saved, setSaved] = useState(false);

  const { data: prefs, isLoading } = useQuery<NotificationPrefs>({
    queryKey: ['notificationPrefs'],
    queryFn: async () => {
      const res = await api.get('/agents/notifications/preferences');
      return res.data;
    },
  });

  const updateMutation = useMutation({
    mutationFn: async (updates: Partial<NotificationPrefs>) => {
      const res = await api.put('/agents/notifications/preferences', updates);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notificationPrefs'] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    },
  });

  const testMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post('/agents/notifications/test');
      return res.data;
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Notifications</h1>
        <div className="animate-pulse space-y-4">
          {[1, 2, 3].map((i) => (
            <Card key={i}><CardContent className="h-20 bg-muted rounded" /></Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Notifications</h1>
        <p className="text-muted-foreground">Manage how you receive alerts and notifications.</p>
      </div>

      {/* Delivery channels */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Delivery Channels</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <Label>Email Notifications</Label>
              <p className="text-xs text-muted-foreground">Receive alerts via email</p>
            </div>
            <button
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                prefs?.email_notifications ? 'bg-primary' : 'bg-muted'
              }`}
              onClick={() => updateMutation.mutate({ email_notifications: !prefs?.email_notifications })}
            >
              <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                prefs?.email_notifications ? 'translate-x-6' : 'translate-x-1'
              }`} />
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
              onClick={() => updateMutation.mutate({ push_notifications: !prefs?.push_notifications })}
            >
              <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                prefs?.push_notifications ? 'translate-x-6' : 'translate-x-1'
              }`} />
            </button>
          </div>
        </CardContent>
      </Card>

      {/* Severity rules */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Alert Severity Rules</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {SEVERITY_INFO.map((s) => (
              <div key={s.level} className="flex items-center gap-3 p-3 border rounded">
                <div className={`w-3 h-3 rounded-full ${s.color}`} />
                <div className="flex-1">
                  <p className="text-sm font-medium">{s.label}</p>
                  <p className="text-xs text-muted-foreground">{s.description}</p>
                </div>
                <div className="flex gap-1">
                  {s.channels.map((ch) => (
                    <span key={ch} className="text-xs bg-muted px-2 py-0.5 rounded">
                      {ch}
                    </span>
                  ))}
                  {s.channels.length === 0 && (
                    <span className="text-xs text-muted-foreground">No notifications</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Test */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Test Notifications</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center gap-4">
          <Button
            variant="outline"
            size="sm"
            disabled={testMutation.isPending}
            onClick={() => testMutation.mutate()}
          >
            {testMutation.isPending ? 'Sending...' : 'Send Test Notification'}
          </Button>
          {testMutation.data && (
            <p className="text-sm text-green-600">Test sent! Check your channels.</p>
          )}
          {saved && (
            <p className="text-sm text-green-600">Preferences saved!</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
