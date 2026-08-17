'use client';

import React from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Loader2,
  Mail,
  Landmark,
  RefreshCw,
  Sparkles,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface ClusterItem {
  category: string;
  count: number;
  image_url: string;
  label: string;
}

interface ClusterResponse {
  clusters: ClusterItem[];
  total: number;
  connected: boolean;
}

interface ClusterMessage {
  id: string;
  subject: string;
  sender: string;
  date: string;
  content: string;
  category: string;
  mock: boolean;
}

function ClusterMessageRow({ message }: { message: ClusterMessage }) {
  const [open, setOpen] = React.useState(false);
  return (
    <div className="rounded-lg border border-border/60 bg-card">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left"
      >
        <div className="min-w-0">
          <p className="truncate text-sm font-medium">{message.subject || '(no subject)'}</p>
          <p className="truncate text-xs text-muted-foreground">
            {message.sender}
            {message.date ? ` · ${message.date}` : ''}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {message.mock && (
            <span className="rounded-full bg-accent/20 px-2 py-0.5 text-[10px] uppercase tracking-wide text-accent-foreground">
              Mock
            </span>
          )}
          {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </div>
      </button>
      {open && (
        <div className="border-t border-border/60 px-3 py-3">
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground/90">
            {message.content}
          </p>
        </div>
      )}
    </div>
  );
}

function ClusterDetailDialog({
  category,
  label,
  onClose,
}: {
  category: string;
  label: string;
  onClose: () => void;
}) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['emailCluster', category],
    queryFn: async () => {
      const res = await api.get(`/integrations/email/clusters/${category}`);
      return res.data as { messages: ClusterMessage[]; count: number };
    },
    enabled: Boolean(category),
  });

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-h-[80vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{label}</DialogTitle>
          <DialogDescription>
            {data ? `${data.count} email${data.count === 1 ? '' : 's'} in this cluster` : 'Emails in this cluster'}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          {isLoading ? (
            <div className="flex h-24 items-center justify-center text-muted-foreground">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading emails…
            </div>
          ) : isError ? (
            <p className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
              Failed to load emails for this cluster.
            </p>
          ) : !data?.messages?.length ? (
            <p className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
              No emails in this cluster yet. Sync your inbox or generate mock data.
            </p>
          ) : (
            data.messages.map((m) => <ClusterMessageRow key={m.id} message={m} />)
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

function ClusterGrid({
  title,
  icon,
  data,
  isLoading,
  emptyHint,
  onRefresh,
  refreshing,
  onSelect,
}: {
  title: string;
  icon: React.ReactNode;
  data?: ClusterResponse;
  isLoading: boolean;
  emptyHint: string;
  onRefresh?: () => void;
  refreshing?: boolean;
  onSelect: (category: string, label: string) => void;
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {icon}
          <h3 className="font-display text-lg tracking-wide">{title}</h3>
          {typeof data?.total === 'number' && (
            <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
              {data.total} items
            </span>
          )}
        </div>
        {onRefresh && (
          <Button size="sm" variant="outline" onClick={onRefresh} disabled={refreshing}>
            {refreshing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
            Sync
          </Button>
        )}
      </div>

      {isLoading ? (
        <div className="flex h-32 items-center justify-center text-muted-foreground">
          <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading clusters…
        </div>
      ) : !data?.connected ? (
        <p className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground">{emptyHint}</p>
      ) : !data.clusters?.length ? (
        <p className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
          No clusters yet. Sync your data to populate this board.
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.clusters.map((c) => (
            <button
              type="button"
              key={c.category}
              onClick={() => onSelect(c.category, c.label)}
              className="group overflow-hidden rounded-xl border border-border/60 bg-card text-left shadow-sm transition hover:border-accent/50"
            >
              <div
                className="h-28 bg-cover bg-center"
                style={{ backgroundImage: `url(${c.image_url})` }}
              />
              <div className="flex items-center justify-between p-3">
                <div>
                  <p className="font-medium">{c.label}</p>
                  <p className="text-xs text-muted-foreground">{c.category}</p>
                </div>
                <span className="rounded-full bg-primary/10 px-2.5 py-1 text-sm font-semibold text-primary">
                  {c.count}
                </span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function ClusterBoard() {
  const queryClient = useQueryClient();
  const [selected, setSelected] = React.useState<{ category: string; label: string } | null>(null);
  const [generatingMock, setGeneratingMock] = React.useState(false);

  const emailQuery = useQuery({
    queryKey: ['emailClusters'],
    queryFn: async () => {
      const res = await api.get('/integrations/email/clusters');
      return res.data as ClusterResponse;
    },
  });

  const plaidQuery = useQuery({
    queryKey: ['plaidClusters'],
    queryFn: async () => {
      const res = await api.get('/integrations/plaid/clusters');
      return res.data as ClusterResponse;
    },
  });

  const mockQuery = useQuery({
    queryKey: ['mockDataStatus'],
    queryFn: async () => {
      const res = await api.get('/integrations/mock/status');
      return res.data as { enabled: boolean };
    },
  });

  const [syncingPlaid, setSyncingPlaid] = React.useState(false);

  const syncPlaid = async () => {
    setSyncingPlaid(true);
    try {
      await api.post('/integrations/plaid/sync-clusters');
      await plaidQuery.refetch();
    } catch (e) {
      console.error(e);
    } finally {
      setSyncingPlaid(false);
    }
  };

  const refreshAll = () => {
    emailQuery.refetch();
    plaidQuery.refetch();
    mockQuery.refetch();
  };

  const toggleMock = async (enabled: boolean) => {
    setGeneratingMock(true);
    try {
      await api.post('/integrations/mock', { enabled });
      queryClient.invalidateQueries({ queryKey: ['mockDataStatus'] });
      refreshAll();
    } catch (e) {
      console.error(e);
    } finally {
      setGeneratingMock(false);
    }
  };

  const mockEnabled = !!mockQuery.data?.enabled;
  const isEmpty = !emailQuery.data?.clusters?.length && !plaidQuery.data?.clusters?.length;

  return (
    <div className="space-y-10 p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="font-display text-xl tracking-wide">Clusters</h2>
          <p className="text-sm text-muted-foreground">
            Click a cluster to view the emails inside it.
          </p>
        </div>
        <Button
          size="sm"
          variant={mockEnabled ? 'outline' : 'default'}
          disabled={generatingMock}
          onClick={() => toggleMock(!mockEnabled)}
        >
          {generatingMock ? (
            <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
          ) : (
            <Sparkles className="mr-2 h-3.5 w-3.5" />
          )}
          {mockEnabled ? 'Deactivate mock data' : 'Generate mock data'}
        </Button>
      </div>

      {isEmpty && (
        <p className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
          No data yet. Click <span className="font-medium text-primary">Generate mock data</span> above to inject sample
          emails and transactions, or connect your real integrations.
        </p>
      )}

      <ClusterGrid
        title="Email Clusters"
        icon={<Mail className="h-5 w-5 text-primary" />}
        data={emailQuery.data}
        isLoading={emailQuery.isLoading}
        emptyHint="Connect email (OAuth Gmail or IMAP) under Integrations, then sync inbox."
        onSelect={(category, label) => setSelected({ category, label })}
      />
      <ClusterGrid
        title="Bank Transaction Clusters"
        icon={<Landmark className="h-5 w-5 text-primary" />}
        data={plaidQuery.data}
        isLoading={plaidQuery.isLoading}
        emptyHint="Connect your bank via Plaid under Integrations."
        onRefresh={syncPlaid}
        refreshing={syncingPlaid}
        onSelect={() => {}}
      />

      {selected && (
        <ClusterDetailDialog
          category={selected.category}
          label={selected.label}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
