'use client';

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  IntegrationStatus,
  EmailMessage,
  CalendarEvent,
  PlaidAccount,
  PlaidTransaction,
} from '@/types';

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
    <Card>
      <CardHeader className="flex flex-row items-center gap-3 pb-2">
        <div className="text-2xl">{icon}</div>
        <div className="flex-1">
          <CardTitle className="text-base">{title}</CardTitle>
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
  const [to, setTo] = useState('');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');

  const { data: statusData } = useQuery({
    queryKey: ['emailStatus'],
    queryFn: async () => {
      const res = await api.get('/integrations/email/status');
      return res.data;
    },
  });

  const { data: emailData, isLoading, error: emailError } = useQuery({
    queryKey: ['emailMessages'],
    queryFn: async () => {
      const res = await api.get('/integrations/email/sync', { params: { folder: 'INBOX', limit: 20 } });
      return res.data as { messages: EmailMessage[]; count: number; error?: string };
    },
    enabled: statusData?.connected,
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
      setShowConfig(false);
      setPassword('');
    },
  });

  const sendMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post('/integrations/email/send', { to, subject, body });
      return res.data;
    },
    onSuccess: () => { setTo(''); setSubject(''); setBody(''); },
  });

  const connected = statusData?.connected;

  return (
    <IntegrationCard
      title="Email (Any Provider)"
      description="IMAP/SMTP — Gmail, Outlook, Yahoo, or custom"
      connected={!!connected}
      icon="✉️"
    >
      {connected ? (
        <div className="space-y-4">
          <p className="text-xs text-muted-foreground">
            Connected via {statusData?.provider} ({statusData?.imap_host})
          </p>
          {emailData?.error && (
            <p className="text-xs text-red-500 bg-red-50 dark:bg-red-900/20 rounded p-2">
              {emailData.error}
            </p>
          )}
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading messages...</p>
          ) : (
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {(emailData?.messages ?? []).slice(0, 10).map((msg) => (
                <div key={msg.id} className="border rounded p-2 text-sm">
                  <p className="font-medium truncate">{msg.subject}</p>
                  <p className="text-muted-foreground text-xs">From: {msg.from}</p>
                  <p className="text-xs truncate">{msg.snippet}</p>
                </div>
              ))}
              {emailData?.messages.length === 0 && !emailData?.error && (
                <p className="text-sm text-muted-foreground">No messages found.</p>
              )}
            </div>
          )}
          <div className="border-t pt-3 space-y-2">
            <p className="text-xs font-medium text-muted-foreground">Send email</p>
            <Input placeholder="To" value={to} onChange={(e) => setTo(e.target.value)} />
            <Input placeholder="Subject" value={subject} onChange={(e) => setSubject(e.target.value)} />
            <textarea
              className="w-full rounded border bg-transparent px-3 py-2 text-sm resize-none h-20 focus:outline-none focus:ring-1 focus:ring-ring"
              placeholder="Body"
              value={body}
              onChange={(e) => setBody(e.target.value)}
            />
            <Button size="sm" disabled={!to || !subject || sendMutation.isPending} onClick={() => sendMutation.mutate()}>
              {sendMutation.isPending ? 'Sending...' : 'Send'}
            </Button>
          </div>
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
            Connect any email provider via IMAP/SMTP. Works with Gmail, Outlook, Yahoo, and more.
          </p>
          <Button size="sm" onClick={() => setShowConfig(true)}>Configure Email</Button>
        </div>
      )}
    </IntegrationCard>
  );
}

// ─── Gmail (Google API) ─────────────────────────────────────────────

function GmailSection({ connected }: { connected: boolean }) {
  const [to, setTo] = useState('');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');

  const { data: emailData, isLoading } = useQuery({
    queryKey: ['gmailMessages'],
    queryFn: async () => {
      const res = await api.get('/integrations/gmail/sync', { params: { max_results: 20 } });
      return res.data as { messages: EmailMessage[]; count: number; error?: string };
    },
    enabled: connected,
    retry: false,
  });

  const sendMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post('/integrations/gmail/send', { to, subject, body });
      return res.data;
    },
    onSuccess: () => { setTo(''); setSubject(''); setBody(''); },
  });

  return (
    <IntegrationCard title="Gmail (Google API)" description="OAuth2 direct access" connected={connected} icon="📧">
      {connected ? (
        <div className="space-y-4">
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading messages...</p>
          ) : (
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {(emailData?.messages ?? []).map((msg) => (
                <div key={msg.id} className="border rounded p-2 text-sm">
                  <p className="font-medium truncate">{msg.subject}</p>
                  <p className="text-muted-foreground text-xs">From: {msg.from}</p>
                  <p className="text-xs truncate">{msg.snippet}</p>
                </div>
              ))}
            </div>
          )}
          <div className="border-t pt-3 space-y-2">
            <p className="text-xs font-medium text-muted-foreground">Send email</p>
            <Input placeholder="To" value={to} onChange={(e) => setTo(e.target.value)} />
            <Input placeholder="Subject" value={subject} onChange={(e) => setSubject(e.target.value)} />
            <textarea className="w-full rounded border bg-transparent px-3 py-2 text-sm resize-none h-20 focus:outline-none focus:ring-1 focus:ring-ring" placeholder="Body" value={body} onChange={(e) => setBody(e.target.value)} />
            <Button size="sm" disabled={!to || !subject || sendMutation.isPending} onClick={() => sendMutation.mutate()}>
              {sendMutation.isPending ? 'Sending...' : 'Send'}
            </Button>
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">Connect your Google account via OAuth2.</p>
          <Button size="sm" onClick={async () => { const res = await api.get('/integrations/oauth/google'); window.location.href = res.data.url; }}>Connect Gmail</Button>
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
          <Button size="sm" onClick={async () => { const res = await api.get('/integrations/oauth/google'); window.location.href = res.data.url; }}>Connect Calendar</Button>
        </div>
      )}
    </IntegrationCard>
  );
}

// ─── Plaid (Banking) ────────────────────────────────────────────────

function PlaidSection({ connected }: { connected: boolean }) {
  const { data: accountData, isLoading: accountsLoading } = useQuery({
    queryKey: ['plaidAccounts'],
    queryFn: async () => { const res = await api.get('/integrations/plaid/accounts'); return res.data as { accounts: PlaidAccount[]; count: number; error?: string }; },
    enabled: connected,
    retry: false,
  });

  const { data: txData, isLoading: txLoading } = useQuery({
    queryKey: ['plaidTransactions'],
    queryFn: async () => { const res = await api.get('/integrations/plaid/transactions', { params: { days: 14, count: 20 } }); return res.data as { transactions: PlaidTransaction[]; count: number; error?: string }; },
    enabled: connected,
    retry: false,
  });

  const handleConnect = async () => {
    try {
      const res = await api.get('/integrations/plaid/link-token');
      const { link_token } = res.data;
      if (link_token && typeof window !== 'undefined' && (window as any).Plaid) {
        const handler = (window as any).Plaid.create({
          token: link_token,
          onSuccess: async (publicToken: string) => { await api.post('/integrations/plaid/exchange', { public_token: publicToken }); },
        });
        handler.open();
      }
    } catch (err) { console.error('Plaid Link init failed:', err); }
  };

  return (
    <IntegrationCard title="Plaid (Banking)" description="View accounts and transactions" connected={connected} icon="🏦">
      {connected ? (
        <div className="space-y-4">
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
          <p className="text-sm text-muted-foreground">Link your bank account securely via Plaid.</p>
          <Button size="sm" onClick={handleConnect}>Connect Bank Account</Button>
        </div>
      )}
    </IntegrationCard>
  );
}

// ─── Canva ──────────────────────────────────────────────────────────

function CanvaSection({ connected }: { connected: boolean }) {
  const [keywords, setKeywords] = useState('');
  const queryClient = useQueryClient();

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
          <Button size="sm" onClick={async () => { const res = await api.get('/integrations/oauth/canva'); window.location.href = res.data.url; }}>Connect Canva</Button>
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
        {searchMutation.data?.listings?.length > 0 && (
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
        {searchMutation.data?.listings?.length === 0 && !searchMutation.data?.error && (
          <p className="text-sm text-muted-foreground">No listings found.</p>
        )}
      </div>
    </IntegrationCard>
  );
}

// ─── Main panel ─────────────────────────────────────────────────────

export function IntegrationsPanel() {
  const { data: status, isLoading } = useQuery<IntegrationStatus>({
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

  return (
    <div className="space-y-6">
      {/* Primary integrations */}
      <div>
        <h3 className="text-sm font-medium text-muted-foreground mb-3">Primary</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <EmailSection />
          <CalendarSection connected={status?.calendar?.connected ?? false} />
          <PlaidSection connected={status?.plaid?.connected ?? false} />
          <GmailSection connected={status?.email?.gmail_connected ?? false} />
        </div>
      </div>

      {/* Secondary integrations */}
      <div>
        <h3 className="text-sm font-medium text-muted-foreground mb-3">Marketplace & Design</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <CanvaSection connected={status?.canva?.connected ?? false} />
          <KijijiSection />
        </div>
      </div>
    </div>
  );
}
