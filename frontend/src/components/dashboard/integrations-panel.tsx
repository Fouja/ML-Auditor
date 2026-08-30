'use client';

import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { isDesktopMode } from '@/lib/desktop';
import { toast } from '@/hooks/use-toast';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  IntegrationStatus,
  IntegrationAccount,
  CalendarEvent,
  PlaidAccount,
  PlaidTransaction,
} from '@/types';
import { ApiKeyManager } from './api-key-manager';
import { IntegrationLogs } from './integration-logs';
import { HowItWorks } from './how-it-works';
import { IntegrationConnectTabs } from './integration-connect-tabs';
import { InlineApiKeyForm } from './inline-api-key-form';

// ─── Status badges ──────────────────────────────────────────────────

function StatusBadge({ connected }: { connected: boolean }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
        connected
          ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
          : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'
      }`}
    >
      {connected ? 'Connected' : 'Not connected'}
    </span>
  );
}

// ─── Integration card wrapper ───────────────────────────────────────

function IntegrationCard({
  title,
  description,
  connected,
  icon,
  children,
}: {
  title: string;
  description: string;
  connected: boolean;
  icon: string;
  children: React.ReactNode;
}) {
  return (
    <Card className="panel-gilded">
      <CardHeader className="flex flex-row items-center gap-3 pb-2">
        <div className="text-2xl">{icon}</div>
        <div className="flex-1">
          <CardTitle className="text-base font-display tracking-wide">{title}</CardTitle>
          <p className="text-xs text-muted-foreground">{description}</p>
        </div>
        <StatusBadge connected={connected} />
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

// ─── Email (IMAP/SMTP — Any Provider) ───────────────────────────────

function EmailSection() {
  const queryClient = useQueryClient();
  const [provider, setProvider] = useState('gmail');
  const [imapHost, setImapHost] = useState('');
  const [smtpHost, setSmtpHost] = useState('');
  const [password, setPassword] = useState('');
  const [showConfig, setShowConfig] = useState(false);
  const [syncing, setSyncing] = useState(false);

  const { data: statusData } = useQuery({
    queryKey: ['emailStatus'],
    queryFn: async () => {
      const res = await api.get('/integrations/email/status');
      return res.data;
    },
  });

  const { data: clusterData, isLoading: clustersLoading } = useQuery({
    queryKey: ['emailClusters'],
    queryFn: async () => {
      const res = await api.get('/integrations/email/clusters');
      return res.data as { clusters: { category: string; count: number; label: string; image_url: string }[]; total: number; connected: boolean };
    },
    enabled: !!statusData?.connected,
    retry: false,
  });

  const configureMutation = useMutation({
    mutationFn: async () => {
      const providerMap: Record<string, { imap: string; smtp: string }> = {
        gmail: { imap: 'imap.gmail.com', smtp: 'smtp.gmail.com' },
        outlook: { imap: 'outlook.office365.com', smtp: 'smtp.office365.com' },
        yahoo: { imap: 'imap.mail.yahoo.com', smtp: 'smtp.mail.yahoo.com' },
        custom: { imap: imapHost, smtp: smtpHost },
      };
      const hosts = providerMap[provider] || providerMap.custom;
      const res = await api.post('/integrations/email/configure', {
        provider,
        imap_host: hosts.imap,
        imap_port: 993,
        smtp_host: hosts.smtp,
        smtp_port: 587,
        password,
        use_ssl: true,
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['emailStatus'] });
      queryClient.invalidateQueries({ queryKey: ['emailClusters'] });
      setShowConfig(false);
      setPassword('');
      toast({ title: 'Connected', description: 'Email configured — syncing clusters', variant: 'success' });
      syncClusters();
    },
    onError: () => {
      toast({ title: 'Error', description: 'Failed to configure email', variant: 'error' });
    },
  });

  const syncClusters = async () => {
    setSyncing(true);
    try {
      const res = await api.get('/integrations/email/sync', { params: { folder: 'INBOX', limit: 100 } });
      queryClient.invalidateQueries({ queryKey: ['emailClusters'] });
      const count = (res.data as { count?: number })?.count ?? 0;
      if (count > 0) {
        toast({ title: 'Emails synced', description: `${count} messages indexed into clusters`, variant: 'success' });
      }
    } catch {
      toast({ title: 'Sync failed', description: 'Could not sync email clusters', variant: 'error' });
    } finally {
      setSyncing(false);
    }
  };

  const connected = statusData?.connected;

  return (
    <IntegrationCard
      title="Email (Any Provider)"
      description="IMAP/SMTP — syncs into dashboard clusters"
      connected={!!connected}
      icon="✉️"
    >
      {connected ? (
        <div className="space-y-3">
          <p className="text-xs text-muted-foreground">
            Connected via {statusData?.provider} ({statusData?.imap_host})
          </p>
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-muted-foreground">Email clusters</p>
            <Button size="sm" variant="outline" className="h-7 text-xs" disabled={syncing} onClick={syncClusters}>
              {syncing ? 'Syncing…' : 'Sync inbox'}
            </Button>
          </div>
          {clustersLoading ? (
            <p className="text-sm text-muted-foreground">Loading clusters…</p>
          ) : (clusterData?.clusters ?? []).length === 0 ? (
            <p className="text-sm text-muted-foreground">No clusters yet. Click “Sync inbox” to index your emails.</p>
          ) : (
            <div className="space-y-1.5 max-h-48 overflow-y-auto">
              {(clusterData?.clusters ?? []).slice(0, 10).map((c) => (
                <div key={c.category} className="flex items-center justify-between border rounded p-1.5 text-sm">
                  <span className="capitalize">{c.label}</span>
                  <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary">{c.count}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : showConfig ? (
        <div className="space-y-3">
          <div>
            <Label className="text-xs">Provider</Label>
            <select
              className="w-full rounded border bg-transparent px-3 py-2 text-sm"
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
            >
              <option value="gmail">Gmail</option>
              <option value="outlook">Outlook / Microsoft 365</option>
              <option value="yahoo">Yahoo Mail</option>
              <option value="custom">Custom IMAP/SMTP</option>
            </select>
          </div>
          {provider === 'custom' && (
            <>
              <div>
                <Label className="text-xs">IMAP Host</Label>
                <Input placeholder="imap.example.com" value={imapHost} onChange={(e) => setImapHost(e.target.value)} />
              </div>
              <div>
                <Label className="text-xs">SMTP Host</Label>
                <Input placeholder="smtp.example.com" value={smtpHost} onChange={(e) => setSmtpHost(e.target.value)} />
              </div>
            </>
          )}
          <div>
            <Label className="text-xs">App Password / Token</Label>
            <Input type="password" placeholder="Your password or app password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          <p className="text-xs text-muted-foreground">
            For Gmail, use an App Password. For Outlook, use your regular password or app password.
          </p>
          <div className="flex gap-2">
            <Button size="sm" disabled={!password || configureMutation.isPending} onClick={() => configureMutation.mutate()}>
              {configureMutation.isPending ? 'Connecting...' : 'Connect'}
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setShowConfig(false)}>Cancel</Button>
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">
            Connect any email provider via IMAP/SMTP. Emails are indexed into clusters so Argus can answer mail questions.
          </p>
          <Button size="sm" onClick={() => setShowConfig(true)}>Configure Email</Button>
        </div>
      )}
    </IntegrationCard>
  );
}

// ─── Gmail (Google API) ─────────────────────────────────────────────

function GmailSection({ connected, accounts }: { connected: boolean; accounts: IntegrationAccount[] }) {
  const queryClient = useQueryClient();
  const [syncingAll, setSyncingAll] = useState(false);
  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [connectTab, setConnectTab] = useState<'oauth' | 'apikey'>('oauth');

  const { data: clusterData, isLoading: clustersLoading } = useQuery({
    queryKey: ['emailClusters'],
    queryFn: async () => {
      const res = await api.get('/integrations/email/clusters');
      return res.data as { clusters: { category: string; count: number; label: string; image_url: string }[]; total: number; connected: boolean };
    },
    enabled: connected,
    retry: false,
  });

  const syncAccount = async (connectionId: string, silent = false) => {
    setSyncingId(connectionId);
    try {
      const res = await api.post(`/integrations/accounts/${connectionId}/sync`);
      queryClient.invalidateQueries({ queryKey: ['emailClusters'] });
      queryClient.invalidateQueries({ queryKey: ['integrationStatus'] });
      if (!silent) {
        toast({ title: 'Gmail sync queued', description: 'Sync job started for selected account.', variant: 'success' });
      }
      return res.data;
    } catch {
      if (!silent) toast({ title: 'Sync failed', description: 'Could not sync Gmail account', variant: 'error' });
    } finally {
      setSyncingId(null);
    }
  };

  const syncClusters = async (silent = false) => {
    setSyncingAll(true);
    try {
      const res = await api.post('/integrations/gmail/sync-clusters');
      queryClient.invalidateQueries({ queryKey: ['emailClusters'] });
      queryClient.invalidateQueries({ queryKey: ['integrationStatus'] });
      const totalSynced = (res.data as { total_synced?: number })?.total_synced ?? 0;
      if (!silent && totalSynced > 0) {
        toast({ title: 'Gmail synced', description: `${totalSynced} messages indexed into clusters`, variant: 'success' });
      }
    } catch {
      if (!silent) toast({ title: 'Sync failed', description: 'Could not sync Gmail clusters', variant: 'error' });
    } finally {
      setSyncingAll(false);
    }
  };

  const disconnectAccount = async (connectionId: string) => {
    try {
      await api.delete(`/integrations/accounts/${connectionId}`);
      queryClient.invalidateQueries({ queryKey: ['integrationStatus'] });
      toast({ title: 'Account disconnected', description: 'Gmail account removed.', variant: 'success' });
    } catch {
      toast({ title: 'Error', description: 'Failed to disconnect account', variant: 'error' });
    }
  };

  useEffect(() => {
    if (connected && accounts.length > 0) {
      syncClusters(true);
    }
  }, [connected, accounts.length]);

  const connectOAuth = async () => {
    const res = await api.get('/integrations/oauth/google');
    window.location.href = res.data.url;
  };

  return (
    <IntegrationCard title="Gmail (OAuth2)" description="One-click Google OAuth — syncs mail into dashboard clusters" connected={connected} icon="📧">
      {connected ? (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-muted-foreground">{accounts.length} account(s)</p>
            <Button size="sm" variant="outline" className="h-7 text-xs" disabled={syncingAll} onClick={() => syncClusters(false)}>
              {syncingAll ? 'Syncing…' : 'Sync all Gmail'}
            </Button>
          </div>

          {accounts.length > 0 && (
            <div className="space-y-1.5 max-h-40 overflow-y-auto">
              {accounts.map((acc) => (
                <div key={acc.id} className="flex items-center justify-between border rounded p-1.5 text-sm">
                  <span className="truncate max-w-[140px]" title={acc.label}>{acc.label}</span>
                  <div className="flex items-center gap-1">
                    <Button size="sm" variant="ghost" className="h-6 px-2 text-xs" disabled={syncingId === acc.id} onClick={() => syncAccount(acc.id)}>
                      {syncingId === acc.id ? '…' : 'Sync'}
                    </Button>
                    <Button size="sm" variant="ghost" className="h-6 px-2 text-xs text-destructive" onClick={() => disconnectAccount(acc.id)}>
                      Remove
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}

          <Button size="sm" variant="outline" className="w-full h-8 text-xs" onClick={connectOAuth}>
            + Add another Gmail account
          </Button>

          {clustersLoading ? (
            <p className="text-sm text-muted-foreground">Loading clusters…</p>
          ) : (clusterData?.clusters ?? []).length === 0 ? (
            <p className="text-sm text-muted-foreground">No clusters yet. Click “Sync all Gmail” to index your inboxes — Argus will then be able to answer mail questions.</p>
          ) : (
            <div className="space-y-1.5 max-h-40 overflow-y-auto">
              {(clusterData?.clusters ?? []).slice(0, 10).map((c) => (
                <div key={c.category} className="flex items-center justify-between border rounded p-1.5 text-sm">
                  <span className="capitalize">{c.label}</span>
                  <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary">{c.count}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">
            Connect one or more Gmail accounts so Argus can retrieve mail, build email clusters, and answer questions about your inboxes.
          </p>
          <IntegrationConnectTabs active={connectTab} onChange={setConnectTab} />
          {connectTab === 'oauth' ? (
            <div className="space-y-2">
              <div className="rounded border border-slate-300 bg-slate-50 dark:bg-slate-800/60 p-2 text-xs text-muted-foreground space-y-1">
                <p>If you see <code className="font-mono">access_denied</code> or <code className="font-mono">redirect_uri_mismatch</code>, in the Google Cloud console (APIs &amp; Services → Credentials → OAuth 2.0 Web client):</p>
                <p>1) Add your Google account as a <strong>Test user</strong> on the OAuth consent screen.</p>
                <p>2) Add this Authorized redirect URI:</p>
                <code className="font-mono text-[11px] break-all">{'http://localhost:8000/api/integrations/oauth/google/callback'}</code>
                <p>3) Enable the Gmail + Calendar APIs in the same project.</p>
              </div>
              <Button size="sm" onClick={connectOAuth}>Connect with Google OAuth2</Button>
            </div>
          ) : (
            <InlineApiKeyForm
              service="gmail"
              label="Gmail API token"
              placeholder="Paste Google access token"
            />
          )}
        </div>
      )}
    </IntegrationCard>
  );
}

// ─── Calendar ───────────────────────────────────────────────────────

function CalendarSection({ connected }: { connected: boolean }) {
  const [summary, setSummary] = useState('');
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState('');
  const [connectTab, setConnectTab] = useState<'oauth' | 'apikey'>('oauth');

  const { data: calData, isLoading } = useQuery({
    queryKey: ['calendarEvents'],
    queryFn: async () => {
      const res = await api.get('/integrations/calendar/events', { params: { hours: 168 } });
      return res.data as { events: CalendarEvent[]; count: number; error?: string };
    },
    enabled: connected,
    retry: false,
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post('/integrations/calendar/events', { summary, start_time: startTime, end_time: endTime });
      return res.data;
    },
    onSuccess: () => { setSummary(''); setStartTime(''); setEndTime(''); },
  });

  return (
    <IntegrationCard title="Google Calendar" description="View and create events" connected={connected} icon="📅">
      {connected ? (
        <div className="space-y-4">
          {isLoading ? <p className="text-sm text-muted-foreground">Loading events...</p> : (
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {(calData?.events ?? []).slice(0, 10).map((ev) => (
                <div key={ev.id} className="border rounded p-2 text-sm">
                  <p className="font-medium">{ev.summary}</p>
                  <p className="text-xs text-muted-foreground">{new Date(ev.start).toLocaleString()} — {new Date(ev.end).toLocaleString()}</p>
                  {ev.location && <p className="text-xs text-muted-foreground">{ev.location}</p>}
                </div>
              ))}
              {calData?.events.length === 0 && <p className="text-sm text-muted-foreground">No upcoming events.</p>}
            </div>
          )}
          <div className="border-t pt-3 space-y-2">
            <p className="text-xs font-medium text-muted-foreground">Create event</p>
            <Input placeholder="Event name" value={summary} onChange={(e) => setSummary(e.target.value)} />
            <div className="grid grid-cols-2 gap-2">
              <div><Label className="text-xs">Start</Label><Input type="datetime-local" value={startTime} onChange={(e) => setStartTime(e.target.value)} /></div>
              <div><Label className="text-xs">End</Label><Input type="datetime-local" value={endTime} onChange={(e) => setEndTime(e.target.value)} /></div>
            </div>
            <Button size="sm" disabled={!summary || !startTime || !endTime || createMutation.isPending} onClick={() => createMutation.mutate()}>
              {createMutation.isPending ? 'Creating...' : 'Create Event'}
            </Button>
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">Connect your Google account to view and manage calendar events.</p>
          <IntegrationConnectTabs active={connectTab} onChange={setConnectTab} />
          {connectTab === 'oauth' ? (
            <Button size="sm" onClick={async () => { const res = await api.get('/integrations/oauth/google'); window.location.href = res.data.url; }}>Connect Calendar with OAuth2</Button>
          ) : (
            <InlineApiKeyForm
              service="google_calendar"
              label="Google Calendar API token"
              placeholder="Paste Google access token"
            />
          )}
        </div>
      )}
    </IntegrationCard>
  );
}

// ─── Plaid (Banking) ────────────────────────────────────────────────

function PlaidSection({ connected, accounts }: { connected: boolean; accounts: IntegrationAccount[] }) {
  const queryClient = useQueryClient();
  const [linking, setLinking] = useState(false);
  const [connectTab, setConnectTab] = useState<'oauth' | 'apikey'>('oauth');
  const [plaidClientId, setPlaidClientId] = useState('');
  const [plaidSecret, setPlaidSecret] = useState('');
  const [plaidEnv, setPlaidEnv] = useState('sandbox');

  const { data: plaidMode } = useQuery({
    queryKey: ['plaidMode'],
    queryFn: async () => {
      const res = await api.get('/integrations/plaid/mode');
      return res.data as { mode: string; real_bank_supported: boolean; configured: boolean };
    },
    retry: false,
  });

  const { data: accountData, isLoading: accountsLoading } = useQuery({
    queryKey: ['plaidAccounts'],
    queryFn: async () => { const res = await api.get('/integrations/plaid/accounts'); return res.data as { accounts: PlaidAccount[]; count: number; error?: string; errors?: string[] }; },
    enabled: connected,
    retry: false,
  });

  const { data: txData, isLoading: txLoading } = useQuery({
    queryKey: ['plaidTransactions'],
    queryFn: async () => { const res = await api.get('/integrations/plaid/transactions', { params: { days: 14, count: 20 } }); return res.data as { transactions: PlaidTransaction[]; count: number; error?: string; errors?: string[] }; },
    enabled: connected,
    retry: false,
  });

  const handleConnect = async (label?: string) => {
    setLinking(true);
    try {
      const res = await api.get('/integrations/plaid/link-token');
      const { link_token, error } = res.data;
      if (!link_token) {
        console.error('Plaid link token missing:', error);
        alert(error || 'Failed to create Plaid link token. Check PLAID_* env vars.');
        return;
      }
      if (typeof window === 'undefined' || !(window as any).Plaid) {
        alert('Plaid Link SDK not loaded. Refresh the page and try again.');
        return;
      }
      const handler = (window as any).Plaid.create({
        token: link_token,
        onSuccess: async (publicToken: string, metadata?: any) => {
          const institution = metadata?.institution?.name || label || `Bank ${accounts.length + 1}`;
          await api.post('/integrations/plaid/exchange', {
            public_token: publicToken,
            account_label: institution,
          });
          queryClient.invalidateQueries({ queryKey: ['integrationStatus'] });
          queryClient.invalidateQueries({ queryKey: ['plaidAccounts'] });
          queryClient.invalidateQueries({ queryKey: ['plaidTransactions'] });
          queryClient.invalidateQueries({ queryKey: ['plaidClusters'] });
          toast({ title: 'Bank connected', description: `${institution} linked successfully.`, variant: 'success' });
        },
        onExit: (err: any) => {
          if (err) console.error('Plaid Link exit:', err);
        },
      });
      handler.open();
    } catch (err) {
      console.error('Plaid Link init failed:', err);
      alert('Plaid Link failed to start. Check console for details.');
    } finally {
      setLinking(false);
    }
  };

  const disconnectAccount = async (connectionId: string) => {
    try {
      await api.delete(`/integrations/accounts/${connectionId}`);
      queryClient.invalidateQueries({ queryKey: ['integrationStatus'] });
      queryClient.invalidateQueries({ queryKey: ['plaidAccounts'] });
      queryClient.invalidateQueries({ queryKey: ['plaidTransactions'] });
      toast({ title: 'Account disconnected', description: 'Bank account removed.', variant: 'success' });
    } catch {
      toast({ title: 'Error', description: 'Failed to disconnect account', variant: 'error' });
    }
  };

  return (
    <IntegrationCard title="Plaid (Banking)" description="View accounts and transactions" connected={connected} icon="🏦">
      {connected ? (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-muted-foreground">{accounts.length} bank account(s)</p>
            <Button size="sm" variant="outline" className="h-7 text-xs" disabled={linking} onClick={() => handleConnect()}>
              {linking ? 'Linking…' : '+ Add bank account'}
            </Button>
          </div>

          {accounts.length > 0 && (
            <div className="space-y-1.5 max-h-32 overflow-y-auto">
              {accounts.map((acc) => (
                <div key={acc.id} className="flex items-center justify-between border rounded p-1.5 text-sm">
                  <span className="truncate max-w-[140px]" title={acc.label}>{acc.label}</span>
                  <Button size="sm" variant="ghost" className="h-6 px-2 text-xs text-destructive" onClick={() => disconnectAccount(acc.id)}>
                    Remove
                  </Button>
                </div>
              ))}
            </div>
          )}

          {accountData?.error && (
            <p className="text-xs text-red-500 bg-red-50 dark:bg-red-900/20 rounded p-2">
              {accountData.error}
            </p>
          )}
          {accountsLoading ? <p className="text-sm text-muted-foreground">Loading accounts...</p> : (
            <div className="space-y-2">
              {(accountData?.accounts ?? []).map((acc) => (
                <div key={acc.id} className="border rounded p-2 text-sm flex justify-between">
                  <div><p className="font-medium">{acc.name}</p><p className="text-xs text-muted-foreground">{acc.type} / {acc.subtype}</p></div>
                  <div className="text-right"><p className="font-medium">${acc.balances.current?.toFixed(2)}</p></div>
                </div>
              ))}
            </div>
          )}
          <div className="border-t pt-3">
            <p className="text-xs font-medium text-muted-foreground mb-2">Recent transactions</p>
            {txLoading ? <p className="text-sm text-muted-foreground">Loading...</p> : (
              <div className="space-y-1 max-h-32 overflow-y-auto">
                {(txData?.transactions ?? []).slice(0, 10).map((tx) => (
                  <div key={tx.id} className="flex justify-between text-sm"><span className="truncate">{tx.name}</span><span className="text-muted-foreground">${tx.amount?.toFixed(2)}</span></div>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">Link one or more bank accounts securely via Plaid. All accounts feed the same transaction clusters, chatbot and RAG pipeline.</p>
          <IntegrationConnectTabs active={connectTab} onChange={setConnectTab} oauthLabel="Plaid Link" apiKeyLabel="Own Credentials" />
          {connectTab === 'oauth' ? (
            <div className="space-y-2">
              {plaidMode && !plaidMode.real_bank_supported && (
                <div className="rounded border border-amber-300 bg-amber-50 dark:bg-amber-900/20 p-2 text-xs text-amber-800 dark:text-amber-200 space-y-1">
                  <p className="font-medium">Plaid is in {plaidMode.mode} mode — real bank logins won't work here.</p>
                  <p>Plaid Link in sandbox only accepts fake test credentials (user_good / pass_good). To connect your real bank account, switch to development/production keys.</p>
                </div>
              )}
              <Button size="sm" onClick={() => handleConnect()} disabled={linking}>
                {linking ? 'Linking…' : 'Connect Bank Account'}
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              <div>
                <Label className="text-xs">Environment</Label>
                <select
                  className="w-full rounded border bg-transparent px-3 py-2 text-sm"
                  value={plaidEnv}
                  onChange={(e) => setPlaidEnv(e.target.value)}
                >
                  <option value="sandbox">Sandbox</option>
                  <option value="development">Development</option>
                  <option value="production">Production</option>
                </select>
              </div>
              <InlineApiKeyForm
                service="plaid"
                label="My Plaid credentials"
                requireSecret
                secretLabel="Plaid Secret"
                placeholder="Plaid Client ID"
                secretPlaceholder="Plaid Secret"
                extraFields={null}
                onSuccess={() => { setPlaidClientId(''); setPlaidSecret(''); }}
              />
            </div>
          )}
        </div>
      )}
    </IntegrationCard>
  );
}

// ─── Canva ──────────────────────────────────────────────────────────

function CanvaSection({ connected }: { connected: boolean }) {
  const [keywords, setKeywords] = useState('');
  const queryClient = useQueryClient();
  const [connectTab, setConnectTab] = useState<'oauth' | 'apikey'>('oauth');

  const { data: designsData, isLoading } = useQuery({
    queryKey: ['canvaDesigns'],
    queryFn: async () => { const res = await api.get('/integrations/canva/designs'); return res.data as { designs: any[]; count: number; error?: string }; },
    enabled: connected,
    retry: false,
  });

  const competitorMutation = useMutation({
    mutationFn: async (kw: string[]) => {
      const res = await api.post('/integrations/canva/competitor-monitor', { keywords: kw, max_results: 15 });
      return res.data;
    },
  });

  return (
    <IntegrationCard title="Canva" description="Designs and competitor monitoring" connected={connected} icon="🎨">
      {connected ? (
        <div className="space-y-4">
          {designsData?.error && (
            <p className="text-xs text-red-500 bg-red-50 dark:bg-red-900/20 rounded p-2">
              {designsData.error}
            </p>
          )}
          {isLoading ? <p className="text-sm text-muted-foreground">Loading designs...</p> : (
            <div className="space-y-2 max-h-40 overflow-y-auto">
              {(designsData?.designs ?? []).slice(0, 8).map((d: any) => (
                <div key={d.id} className="border rounded p-2 text-sm flex items-center gap-2">
                  <div className="w-10 h-10 bg-muted rounded flex-shrink-0" />
                  <div className="flex-1 min-w-0"><p className="font-medium truncate">{d.title}</p><p className="text-xs text-muted-foreground">{d.status}</p></div>
                </div>
              ))}
            </div>
          )}
          <div className="border-t pt-3 space-y-2">
            <p className="text-xs font-medium text-muted-foreground">Competitor Monitoring</p>
            <Input
              placeholder="Competitor keywords (comma-separated)"
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
            />
            <Button
              size="sm"
              disabled={!keywords.trim() || competitorMutation.isPending}
              onClick={() => competitorMutation.mutate(keywords.split(',').map(k => k.trim()))}
            >
              {competitorMutation.isPending ? 'Monitoring...' : 'Monitor Trends'}
            </Button>
            {competitorMutation.data?.templates?.length > 0 && (
              <div className="space-y-1 max-h-32 overflow-y-auto mt-2">
                {competitorMutation.data.templates.map((t: any) => (
                  <div key={t.id} className="text-sm flex justify-between">
                    <span className="truncate">{t.title}</span>
                    <span className="text-xs text-muted-foreground">{t.tags?.join(', ')}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">Connect Canva to access designs and monitor competitor trends.</p>
          <IntegrationConnectTabs active={connectTab} onChange={setConnectTab} />
          {connectTab === 'oauth' ? (
            <Button size="sm" onClick={async () => { const res = await api.get('/integrations/oauth/canva'); window.location.href = res.data.url; }}>Connect Canva with OAuth2</Button>
          ) : (
            <InlineApiKeyForm
              service="canva"
              label="Canva access token"
              placeholder="Paste Canva access token"
            />
          )}
        </div>
      )}
    </IntegrationCard>
  );
}

// ─── Kijiji ─────────────────────────────────────────────────────────

function KijijiSection() {
  const [query, setQuery] = useState('');
  const searchMutation = useMutation({
    mutationFn: async (q: string) => { const res = await api.post('/integrations/kijiji/search', { query: q }); return res.data as { listings: any[]; count: number; error?: string }; },
  });

  return (
    <IntegrationCard title="Kijiji" description="Marketplace listings search" connected={true} icon="🛒">
      <div className="space-y-3">
        <div className="flex gap-2">
          <Input placeholder="Search Kijiji..." value={query} onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && query.trim()) searchMutation.mutate(query); }} />
          <Button size="sm" disabled={!query.trim() || searchMutation.isPending} onClick={() => searchMutation.mutate(query)}>
            {searchMutation.isPending ? 'Searching...' : 'Search'}
          </Button>
        </div>
        {searchMutation.data?.error && (
          <p className="text-xs text-red-500 bg-red-50 dark:bg-red-900/20 rounded p-2">
            {searchMutation.data.error}
          </p>
        )}
        {searchMutation.data?.listings && searchMutation.data.listings.length > 0 && (
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {searchMutation.data.listings.map((listing: any) => (
              <div key={listing.id} className="border rounded p-2 text-sm">
                <p className="font-medium">{listing.title}</p>
                <p className="text-xs text-muted-foreground">{listing.price ? `$${listing.price}` : 'No price'} · {listing.location}</p>
                {listing.url && <a href={listing.url} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-500 hover:underline">View on Kijiji</a>}
              </div>
            ))}
          </div>
        )}
        {searchMutation.data?.listings && searchMutation.data.listings.length === 0 && !searchMutation.data?.error && (
          <p className="text-sm text-muted-foreground">No listings found.</p>
        )}
      </div>
    </IntegrationCard>
  );
}

// ─── Jira ──────────────────────────────────────────────────────────

function JiraSection({ connected }: { connected: boolean }) {
  const queryClient = useQueryClient();
  const [siteUrl, setSiteUrl] = useState('');
  const [jiraEmail, setJiraEmail] = useState('');
  const [apiToken, setApiToken] = useState('');
  const [showConfig, setShowConfig] = useState(false);
  const [selectedProject, setSelectedProject] = useState('');
  const [jql, setJql] = useState('');
  const [connectTab, setConnectTab] = useState<'oauth' | 'apikey'>('oauth');

  const { data: projectsData, isLoading: projectsLoading } = useQuery({
    queryKey: ['jiraProjects'],
    queryFn: async () => { const res = await api.get('/integrations/jira/projects'); return res.data as { projects: any[]; count: number; error?: string }; },
    enabled: connected,
    retry: false,
  });

  const { data: issuesData, isLoading: issuesLoading, refetch: refetchIssues } = useQuery({
    queryKey: ['jiraIssues', selectedProject],
    queryFn: async () => {
      const res = await api.post('/integrations/jira/issues', { project_key: selectedProject || undefined, max_results: 20 });
      return res.data as { issues: any[]; count: number; error?: string };
    },
    enabled: connected && !!selectedProject,
    retry: false,
  });

  const [jiraError, setJiraError] = useState('');
  const configureMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post('/integrations/jira/configure', { site_url: siteUrl, email: jiraEmail, api_token: apiToken });
      return res.data;
    },
    onSuccess: (data) => {
      if (data.success) {
        queryClient.invalidateQueries({ queryKey: ['integrationStatus'] });
        queryClient.invalidateQueries({ queryKey: ['jiraProjects'] });
        setShowConfig(false);
        setApiToken('');
        setJiraError('');
        toast({ title: 'Connected', description: 'Jira configured successfully', variant: 'success' });
      } else {
        setJiraError(data.error || 'Connection failed');
      }
    },
    onError: (err: any) => {
      setJiraError(err?.response?.data?.detail || err?.response?.data?.error || 'Failed to connect to Jira');
    },
  });

  const syncMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post('/integrations/jira/sync', { project_key: selectedProject || undefined, max_results: 50 });
      return res.data;
    },
    onSuccess: (data) => {
      if (data.success) {
        toast({ title: 'Synced', description: `Synced ${data.issues_synced} issues to RAG`, variant: 'success' });
      } else {
        toast({ title: 'Sync failed', description: data.error || 'Unknown error', variant: 'error' });
      }
    },
    onError: () => {
      toast({ title: 'Sync failed', description: 'Sync request failed', variant: 'error' });
    },
  });

  return (
    <IntegrationCard title="Jira" description="Project management issues and sprints" connected={connected} icon="⬣">
      {connected ? (
        <div className="space-y-4">
          {projectsLoading ? (
            <p className="text-sm text-muted-foreground">Loading projects...</p>
          ) : (
            <div className="space-y-2">
              <select
                className="w-full rounded border bg-transparent px-3 py-2 text-sm"
                value={selectedProject}
                onChange={(e) => setSelectedProject(e.target.value)}
              >
                <option value="">Select a project...</option>
                {(projectsData?.projects ?? []).map((p: any) => (
                  <option key={p.id} value={p.key}>{p.name} ({p.key})</option>
                ))}
              </select>
          {issuesData?.error && (
            <p className="text-xs text-red-500 bg-red-50 dark:bg-red-900/20 rounded p-2">{issuesData.error}</p>
          )}
          {selectedProject && (
                <>
                  {issuesLoading ? (
                    <p className="text-sm text-muted-foreground">Loading issues...</p>
                  ) : (
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {(issuesData?.issues ?? []).slice(0, 10).map((issue: any) => (
                        <div key={issue.id} className="border rounded p-2 text-sm">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-mono text-muted-foreground">{issue.key}</span>
                            <span className={`text-xs px-1.5 py-0.5 rounded ${
                              issue.priority === 'Highest' || issue.priority === 'High' ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' :
                              issue.priority === 'Lowest' || issue.priority === 'Low' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
                              'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                            }`}>{issue.priority}</span>
                          </div>
                          <p className="font-medium truncate">{issue.summary}</p>
                          <p className="text-xs text-muted-foreground">
                            {issue.status} · {issue.assignee_display || 'Unassigned'}
                          </p>
                        </div>
                      ))}
                      {issuesData?.issues?.length === 0 && (
                        <p className="text-sm text-muted-foreground">No issues found.</p>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          )}
          <div className="flex gap-2 border-t pt-3">
            <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => refetchIssues()}>
              Refresh
            </Button>
            <Button size="sm" variant="outline" className="h-7 text-xs" disabled={syncMutation.isPending} onClick={() => syncMutation.mutate()}>
              {syncMutation.isPending ? 'Syncing...' : 'Sync to RAG'}
            </Button>
            <Button
              size="sm" variant="ghost" className="h-7 text-xs text-destructive ml-auto"
              onClick={async () => {
                await api.post('/integrations/jira/configure', { site_url: '', email: '', api_token: '' });
                queryClient.invalidateQueries({ queryKey: ['integrationStatus'] });
              }}
            >
              Disconnect
            </Button>
          </div>
        </div>
      ) : showConfig ? (
        <div className="space-y-3">
          <div>
            <Label className="text-xs">Jira Site URL</Label>
            <Input placeholder="https://your-domain.atlassian.net" value={siteUrl} onChange={(e) => setSiteUrl(e.target.value)} />
          </div>
          <div>
            <Label className="text-xs">Email</Label>
            <Input placeholder="your@email.com" value={jiraEmail} onChange={(e) => setJiraEmail(e.target.value)} />
          </div>
          <div>
            <Label className="text-xs">API Token</Label>
            <Input type="password" placeholder="From https://id.atlassian.com/manage/api-tokens" value={apiToken} onChange={(e) => setApiToken(e.target.value)} />
          </div>
          {jiraError && (
            <p className="text-xs text-red-500 bg-red-50 dark:bg-red-900/20 rounded p-2">{jiraError}</p>
          )}
          <div className="flex gap-2">
            <Button size="sm" disabled={!siteUrl || !jiraEmail || !apiToken || configureMutation.isPending} onClick={() => configureMutation.mutate()}>
              {configureMutation.isPending ? 'Testing...' : 'Connect'}
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setShowConfig(false)}>Cancel</Button>
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">Connect Jira to browse projects, view issues, and sync them into the RAG knowledge base.</p>
          <IntegrationConnectTabs active={connectTab} onChange={setConnectTab} />
          {connectTab === 'oauth' ? (
            <Button size="sm" onClick={async () => { const res = await api.get('/integrations/oauth/jira'); window.location.href = res.data.url; }}>Connect Jira with OAuth2</Button>
          ) : (
            <Button size="sm" onClick={() => setShowConfig(true)}>Configure Jira with API Token</Button>
          )}
        </div>
      )}
    </IntegrationCard>
  );
}

// ─── Web Tools microservice (Agent-Reach) ───────────────────────────

function WebToolsSection() {
  const queryClient = useQueryClient();
  const { data: status, isLoading } = useQuery({
    queryKey: ['webToolsStatus'],
    queryFn: async () => {
      const res = await api.get('/agents/web-tools/status');
      return res.data as {
        connected: boolean;
        health?: { status: string; search_provider?: string };
        error?: string;
      };
    },
  });

  const { data: pref, isLoading: prefLoading } = useQuery({
    queryKey: ['webToolsPreference'],
    queryFn: async () => {
      const res = await api.get('/integrations/web-tools/preference');
      return res.data as { enabled: boolean };
    },
  });

  const toggleMutation = useMutation({
    mutationFn: async (enabled: boolean) => {
      const res = await api.post('/integrations/web-tools/preference', { enabled });
      return res.data as { enabled: boolean };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webToolsPreference'] });
    },
  });

  const provider =
    status?.health?.search_provider === 'exa'
      ? 'Exa AI'
      : 'DuckDuckGo (keyless)';
  const enabled = !!pref?.enabled;

  return (
    <IntegrationCard
      title="Web Tools (Agent Reach)"
      description="Live web search, page fetch & RSS — feeds the chatbot with real-time information when activated."
      connected={!!status?.connected && enabled}
      icon="🌐"
    >
      <div className="space-y-3">
        {isLoading || prefLoading ? (
          <p className="text-sm text-muted-foreground">Checking microservice...</p>
        ) : (
          <>
            <div className="flex flex-wrap gap-2">
              <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs ${
                enabled
                  ? 'border-accent/40 bg-accent/20 text-accent-foreground'
                  : 'border-border bg-muted text-muted-foreground'
              }`}>
                {enabled ? 'Activated for chat' : 'Deactivated'}
              </span>
              {status?.connected && (
                <span className="inline-flex items-center rounded-full border border-border bg-muted px-2.5 py-0.5 text-xs text-muted-foreground">
                  {provider}
                </span>
              )}
            </div>
            <p className="text-sm text-muted-foreground leading-relaxed">
              When activated, the assistant can search the web and fetch live pages.
              When off, live-info questions will tell you to enable this toggle.
            </p>
            {!status?.connected && (
              <p className="text-xs text-amber-600">
                Microservice unreachable — start{' '}
                <code className="rounded bg-muted px-1">mlauditor_web_tools</code>.
              </p>
            )}
            <Button
              size="sm"
              variant={enabled ? 'outline' : 'default'}
              disabled={toggleMutation.isPending || !status?.connected}
              onClick={() => toggleMutation.mutate(!enabled)}
            >
              {toggleMutation.isPending
                ? 'Saving…'
                : enabled
                  ? 'Deactivate Web Tools'
                  : 'Activate Web Tools'}
            </Button>
          </>
        )}
      </div>
    </IntegrationCard>
  );
}

// ─── JobChameleon microservice (job intelligence) ──────────────────

function JobChameleonSection() {
  const [desktop, setDesktop] = useState(false);

  useEffect(() => {
    isDesktopMode().then(setDesktop);
  }, []);

  // JobChameleon requires the Docker microservice, so it is hidden in the
  // self-contained desktop build.
  if (desktop) return null;

  const { data: status, isLoading } = useQuery({
    queryKey: ['jobchameleonStatus'],
    queryFn: async () => {
      const res = await api.get('/agents/jobchameleon/status');
      return res.data as {
        connected?: boolean;
        llm_provider?: string;
        llm_model?: string;
        error?: string;
      };
    },
  });

  const launchMutation = useMutation({
    mutationFn: async () => {
      const res = await api.get('/agents/jobchameleon/launch');
      return res.data as {
        url: string;
        token: string;
        success?: boolean;
        error?: string;
        console_url?: string;
      };
    },
    onSuccess: (data) => {
      if (data.success === false || !data.url) {
        const fallback = data.console_url;
        if (fallback) window.open(fallback, '_blank', 'noopener,noreferrer');
        toast({
          title: 'Workbench not available',
          description: data.error || 'The full workbench could not be started. Opening the gateway console instead.',
          variant: 'error',
        });
        return;
      }
      const target = `${data.url}${data.url.includes('?') ? '&' : '?'}token=${encodeURIComponent(data.token)}`;
      window.open(target, '_blank', 'noopener,noreferrer');
      toast({
        title: 'JOBchameleon launched',
        description: 'The full app opened on its own port in a new tab. MCP is connected automatically.',
        variant: 'success',
      });
    },
    onError: () => {
      toast({ title: 'Launch failed', description: 'Check that the JOBchameleon container is running.', variant: 'error' });
    },
  });

  return (
    <IntegrationCard
      title="JobChameleon (Job Intelligence)"
      description="Dedicated AI hiring workbench — job-fit scoring, lead quality, lead intel, chat-driven clusters."
      connected={!!status?.connected}
      icon="🦎"
    >
      <div className="space-y-3">
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Checking microservice...</p>
        ) : status?.connected ? (
          <>
            <p className="text-sm text-muted-foreground leading-relaxed">
              JOBchameleon is a standalone job-intelligence app. Launch the full
              workbench from here — it opens on its own port in a new tab and
              connects to Argus over MCP automatically.
            </p>
            <Button
              className="w-full sm:w-auto"
              onClick={() => launchMutation.mutate()}
              disabled={launchMutation.isPending}
            >
              {launchMutation.isPending ? 'Launching…' : 'Launch JOBchameleon'}
            </Button>
          </>
        ) : (
          <p className="text-sm text-muted-foreground">
            The JobChameleon microservice is not reachable. Make sure the{' '}
            <code className="text-xs bg-muted px-1 rounded">mlauditor_jobchameleon</code>{' '}
            container is running.
          </p>
        )}
      </div>
    </IntegrationCard>
  );
}

// ─── Mock data (demo content) ──────────────────────────────────────

function MockDataSection() {
  const queryClient = useQueryClient();
  const { data: status, isLoading } = useQuery({
    queryKey: ['mockDataStatus'],
    queryFn: async () => {
      const res = await api.get('/integrations/mock/status');
      return res.data as { enabled: boolean; streams: number; chunks: number; alerts: number };
    },
  });

  const toggleMutation = useMutation({
    mutationFn: async (enabled: boolean) => {
      const res = await api.post('/integrations/mock', { enabled });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mockDataStatus'] });
      queryClient.invalidateQueries({ queryKey: ['integrationStatus'] });
      queryClient.invalidateQueries({ queryKey: ['emailClusters'] });
      queryClient.invalidateQueries({ queryKey: ['plaidClusters'] });
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      toast({
        title: status?.enabled ? 'Mock data deactivated' : 'Mock data activated',
        description: status?.enabled
          ? 'Placeholder data removed — real data untouched.'
          : 'Demo content injected into clusters, alerts and RAG.',
        variant: status?.enabled ? 'default' : 'success',
      });
    },
    onError: () => {
      toast({ title: 'Error', description: 'Failed to toggle mock data', variant: 'error' });
    },
  });

  const enabled = !!status?.enabled;

  return (
    <IntegrationCard
      title="Mock Data (Demo)"
      description="Activate placeholder content so clusters, notifications, analytics and the chatbot have sample data to work with."
      connected={enabled}
      icon="🧪"
    >
      <div className="space-y-3">
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Checking status...</p>
        ) : (
          <>
            <div className="flex flex-wrap gap-2">
              <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs ${
                enabled
                  ? 'border-accent/40 bg-accent/20 text-accent-foreground'
                  : 'border-border bg-muted text-muted-foreground'
              }`}>
                {enabled ? 'Active' : 'Deactivated'}
              </span>
              {enabled && (
                <span className="inline-flex items-center rounded-full border border-border bg-muted px-2.5 py-0.5 text-xs text-muted-foreground">
                  {status.chunks} chunks · {status.alerts} alerts
                </span>
              )}
            </div>
            <p className="text-sm text-muted-foreground leading-relaxed">
              {enabled
                ? 'Mock content is live in your dashboard. Deactivate any time to remove it and keep only your real data.'
                : 'Great for exploring the dashboard: injects sample job alerts, emails, transactions and RAG documents.'}
            </p>
            <Button
              size="sm"
              variant={enabled ? 'outline' : 'default'}
              disabled={toggleMutation.isPending}
              onClick={() => toggleMutation.mutate(!enabled)}
            >
              {toggleMutation.isPending
                ? 'Saving…'
                : enabled
                  ? 'Deactivate Mock Data'
                  : 'Activate Mock Data'}
            </Button>
          </>
        )}
      </div>
    </IntegrationCard>
  );
}

// ─── Main panel ─────────────────────────────────────────────────────

export function IntegrationsPanel() {
  const queryClient = useQueryClient();
  const { data: status, isLoading, isError } = useQuery<IntegrationStatus>({
    queryKey: ['integrationStatus'],
    queryFn: async () => { const res = await api.get('/integrations/status'); return res.data; },
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i} className="animate-pulse"><CardHeader><div className="h-4 bg-muted rounded w-1/3" /></CardHeader><CardContent><div className="h-20 bg-muted rounded" /></CardContent></Card>
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center justify-center h-48">
        <p className="text-sm text-red-500 bg-red-50 dark:bg-red-900/20 rounded-lg px-4 py-3">
          Failed to load integration status. Check your connection and try again.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* AI & Web Tools */}
      <div>
        <SectionHeading>AI &amp; Web Tools</SectionHeading>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <WebToolsSection />
          <JobChameleonSection />
          <MockDataSection />
        </div>
      </div>

      {/* Primary integrations */}
      <div>
        <SectionHeading>Primary</SectionHeading>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <EmailSection />
          <CalendarSection connected={status?.calendar?.connected ?? false} />
          <PlaidSection connected={status?.plaid?.connected ?? false} accounts={status?.plaid?.accounts ?? []} />
          <GmailSection connected={status?.gmail?.connected ?? false} accounts={status?.gmail?.accounts ?? []} />
        </div>
      </div>

      {/* Secondary integrations */}
      <div>
        <SectionHeading>Marketplace, Design &amp; Dev</SectionHeading>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <CanvaSection connected={status?.canva?.connected ?? false} />
          <JiraSection connected={status?.jira?.connected ?? false} />
          <KijijiSection />
        </div>
      </div>

      {/* API key management */}
      <div>
        <SectionHeading>API Key Manager</SectionHeading>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <ApiKeyManager />
          <IntegrationLogs />
        </div>
      </div>

      {/* How it works */}
      <div>
        <SectionHeading>How It Works</SectionHeading>
        <HowItWorks />
      </div>
    </div>
  );
}

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <div className="mb-4 flex items-center gap-3">
      <hr className="accent-rule flex-1" />
      <h3 className="font-display text-sm uppercase tracking-[0.3em] text-accent-foreground">
        {children}
      </h3>
      <hr className="accent-rule flex-1" />
    </div>
  );
}
