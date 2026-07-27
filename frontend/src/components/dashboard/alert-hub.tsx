'use client';

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useAlerts, useAlertStats, useAcknowledgeAlert, useDismissAlert } from '@/hooks/useApi';
import { AgentAlert } from '@/types';
import { Bell, AlertTriangle, CheckCircle, Clock, XCircle } from 'lucide-react';

export function AlertHub() {
  const { data: alertsData, isLoading } = useAlerts(1, 10, undefined, 'pending');
  const { data: stats } = useAlertStats();
  const acknowledgeAlert = useAcknowledgeAlert();
  const dismissAlert = useDismissAlert();

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'border-l-red-500 bg-red-500/5';
      case 'high':
        return 'border-l-orange-500 bg-orange-500/5';
      case 'medium':
        return 'border-l-yellow-500 bg-yellow-500/5';
      case 'low':
        return 'border-l-blue-500 bg-blue-500/5';
      default:
        return 'border-l-gray-500 bg-gray-500/5';
    }
  };

  return (
    <Card className="h-full">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <Bell className="h-5 w-5" />
          AlertHub
        </CardTitle>
        {stats && stats.pending > 0 && (
          <span className="rounded-full bg-red-500 px-2 py-1 text-xs font-medium text-white">
            {stats.pending}
          </span>
        )}
      </CardHeader>
      <CardContent className="overflow-y-auto">
        {isLoading ? (
          <div className="flex justify-center py-8">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          </div>
        ) : alertsData?.items?.length === 0 ? (
          <div className="py-8 text-center text-muted-foreground">
            <CheckCircle className="mx-auto mb-2 h-12 w-12 text-green-500 opacity-50" />
            <p>No pending alerts</p>
          </div>
        ) : (
          <div className="space-y-3">
            {alertsData?.items?.map((alert: AgentAlert) => (
              <div
                key={alert.id}
                className={`rounded-lg border-l-4 p-3 ${getSeverityColor(alert.severity)}`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <p className="font-medium text-sm">{alert.title}</p>
                    <p className="mt-1 text-xs text-muted-foreground line-clamp-2">
                      {alert.description}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {new Date(alert.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
                <div className="mt-2 flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-7 text-xs"
                    onClick={() => acknowledgeAlert.mutate(alert.id)}
                    disabled={acknowledgeAlert.isPending}
                  >
                    Acknowledge
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-7 text-xs"
                    onClick={() => dismissAlert.mutate(alert.id)}
                    disabled={dismissAlert.isPending}
                  >
                    Dismiss
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
