'use client';

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useDataStreams, useAgentStatus } from '@/hooks/useApi';
import { Database, Mail, Calendar, CreditCard, ShoppingCart, Bot } from 'lucide-react';

export function ActivityMap() {
  const { data: dataStreams } = useDataStreams(1, 100);
  const { data: agentStatus } = useAgentStatus();

  const sources = [
    {
      name: 'Gmail',
      icon: Mail,
      color: 'text-red-500',
      bgColor: 'bg-red-500/10',
      type: 'gmail',
    },
    {
      name: 'Calendar',
      icon: Calendar,
      color: 'text-blue-500',
      bgColor: 'bg-blue-500/10',
      type: 'google_calendar',
    },
    {
      name: 'Plaid',
      icon: CreditCard,
      color: 'text-green-500',
      bgColor: 'bg-green-500/10',
      type: 'plaid',
    },
    {
      name: 'Kijiji',
      icon: ShoppingCart,
      color: 'text-purple-500',
      bgColor: 'bg-purple-500/10',
      type: 'kijiji',
    },
  ];

  const streamsBySource = dataStreams?.items?.reduce(
    (acc, stream) => {
      acc[stream.source_type] = (acc[stream.source_type] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  ) || {};

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Database className="h-5 w-5" />
          Activity Map
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Connected Services */}
          <div className="grid grid-cols-2 gap-3">
            {sources.map((source) => (
              <div
                key={source.type}
                className="flex items-center gap-3 rounded-lg border p-3"
              >
                <div className={`flex h-8 w-8 items-center justify-center rounded-full ${source.bgColor}`}>
                  <source.icon className={`h-4 w-4 ${source.color}`} />
                </div>
                <div>
                  <p className="text-sm font-medium">{source.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {streamsBySource[source.type] || 0} items
                  </p>
                </div>
              </div>
            ))}
          </div>

          {/* Agents Status */}
          <div className="rounded-lg border p-3">
            <div className="flex items-center gap-2 mb-3">
              <Bot className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">Active Agents</span>
            </div>
            <div className="space-y-2">
              {agentStatus?.agents?.map((agent) => (
                <div
                  key={agent.type}
                  className="flex items-center justify-between"
                >
                  <span className="text-sm text-muted-foreground">
                    {agent.name}
                  </span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs ${
                      agent.status === 'ready'
                        ? 'bg-green-500/10 text-green-500'
                        : 'bg-yellow-500/10 text-yellow-500'
                    }`}
                  >
                    {agent.status}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Recent Activity */}
          <div className="rounded-lg border p-3">
            <p className="text-sm font-medium mb-3">Recent Activity</p>
            <div className="space-y-2">
              {dataStreams?.items?.slice(0, 3).map((stream) => (
                <div
                  key={stream.id}
                  className="flex items-center justify-between text-sm"
                >
                  <span className="capitalize text-muted-foreground">
                    {stream.source_type.replace('_', ' ')}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {new Date(stream.created_at).toLocaleTimeString()}
                  </span>
                </div>
              ))}
              {dataStreams?.items?.length === 0 && (
                <p className="text-center text-xs text-muted-foreground py-2">
                  No activity yet
                </p>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
