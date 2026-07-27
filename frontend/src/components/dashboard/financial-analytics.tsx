'use client';

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useDataStreams } from '@/hooks/useApi';
import { TrendingUp, TrendingDown, DollarSign, CreditCard } from 'lucide-react';

export function FinancialAnalytics() {
  const { data: dataStreams } = useDataStreams(1, 100);

  // Calculate financial stats from data streams
  const plaidStreams = dataStreams?.items?.filter(
    (stream) => stream.source_type === 'plaid'
  ) || [];

  const totalStreams = plaidStreams.length;
  const recentStreams = plaidStreams.filter(
    (stream) =>
      new Date(stream.created_at) >
      new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
  ).length;

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <DollarSign className="h-5 w-5" />
          Financial Analytics
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Summary Stats */}
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-lg border p-3">
              <div className="flex items-center gap-2">
                <CreditCard className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">Transactions</span>
              </div>
              <p className="mt-1 text-2xl font-bold">{totalStreams}</p>
            </div>
            <div className="rounded-lg border p-3">
              <div className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-green-500" />
                <span className="text-sm text-muted-foreground">This Week</span>
              </div>
              <p className="mt-1 text-2xl font-bold">{recentStreams}</p>
            </div>
          </div>

          {/* Placeholder for chart */}
          <div className="rounded-lg border p-4">
            <div className="flex h-32 items-center justify-center text-muted-foreground">
              <div className="text-center">
                <TrendingUp className="mx-auto mb-2 h-8 w-8 opacity-50" />
                <p className="text-sm">Financial charts coming soon</p>
                <p className="text-xs">Connect Plaid to see your data</p>
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="space-y-2">
            <button className="flex w-full items-center gap-3 rounded-lg border p-3 text-left transition-colors hover:bg-accent">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-green-500/10">
                <TrendingUp className="h-4 w-4 text-green-500" />
              </div>
              <div>
                <p className="text-sm font-medium">View Transactions</p>
                <p className="text-xs text-muted-foreground">See all financial data</p>
              </div>
            </button>
            <button className="flex w-full items-center gap-3 rounded-lg border p-3 text-left transition-colors hover:bg-accent">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-red-500/10">
                <TrendingDown className="h-4 w-4 text-red-500" />
              </div>
              <div>
                <p className="text-sm font-medium">Anomaly Detection</p>
                <p className="text-xs text-muted-foreground">Check for unusual activity</p>
              </div>
            </button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
