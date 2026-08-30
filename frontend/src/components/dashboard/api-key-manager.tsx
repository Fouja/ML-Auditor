'use client';

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { toast } from '@/hooks/use-toast';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { ApiKeyIntegration } from '@/types';
import { KeyRound, Pencil, Trash2, RefreshCw, Plus } from 'lucide-react';

const SERVICE_OPTIONS = [
  { value: 'plaid', label: 'Plaid', hasSecret: true },
  { value: 'gmail', label: 'Gmail / Google API', hasSecret: false },
  { value: 'google_calendar', label: 'Google Calendar', hasSecret: false },
  { value: 'canva', label: 'Canva', hasSecret: false },
  { value: 'jira', label: 'Jira', hasSecret: false },
  { value: 'openai', label: 'OpenAI', hasSecret: false },
  { value: 'anthropic', label: 'Anthropic', hasSecret: false },
  { value: 'nvidia', label: 'NVIDIA NIM', hasSecret: false },
  { value: 'custom', label: 'Custom API', hasSecret: false },
];

function StatusBadge({ status }: { status: ApiKeyIntegration['status'] }) {
  const variants: Record<string, string> = {
    active: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    error: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    disabled: 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400',
    unknown: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${variants[status] || variants.unknown}`}>
      {status}
    </span>
  );
}

export function ApiKeyManager() {
  const queryClient = useQueryClient();
  const [isOpen, setIsOpen] = useState(false);
  const [editing, setEditing] = useState<ApiKeyIntegration | null>(null);
  const [service, setService] = useState('plaid');
  const [label, setLabel] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');
  const [siteUrl, setSiteUrl] = useState('');
  const [email, setEmail] = useState('');
  const [environment, setEnvironment] = useState('sandbox');

  const { data, isLoading } = useQuery({
    queryKey: ['apiKeyIntegrations'],
    queryFn: async () => {
      const res = await api.get('/integrations/api-keys');
      return res.data as ApiKeyIntegration[];
    },
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      const extra: Record<string, unknown> = {};
      if (service === 'plaid') extra.environment = environment;
      if (service === 'jira') {
        extra.site_url = siteUrl;
        extra.email = email;
      }
      const res = await api.post('/integrations/api-keys', {
        service,
        label,
        api_key: apiKey,
        api_secret: apiSecret,
        extra_data: extra,
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['apiKeyIntegrations'] });
      resetForm();
      setIsOpen(false);
      toast({ title: 'API key saved', description: 'Your credentials have been encrypted and stored.', variant: 'success' });
    },
    onError: (err: any) => {
      toast({ title: 'Error', description: err?.response?.data?.detail || 'Failed to save API key', variant: 'error' });
    },
  });

  const updateMutation = useMutation({
    mutationFn: async () => {
      const extra: Record<string, unknown> = {};
      if (service === 'plaid') extra.environment = environment;
      if (service === 'jira') {
        extra.site_url = siteUrl;
        extra.email = email;
      }
      const payload: Record<string, unknown> = { label, extra_data: extra };
      if (apiKey) payload.api_key = apiKey;
      if (apiSecret) payload.api_secret = apiSecret;
      const res = await api.patch(`/integrations/api-keys/${editing?.id}`, payload);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['apiKeyIntegrations'] });
      resetForm();
      setIsOpen(false);
      setEditing(null);
      toast({ title: 'API key updated', description: 'Changes saved.', variant: 'success' });
    },
    onError: (err: any) => {
      toast({ title: 'Error', description: err?.response?.data?.detail || 'Failed to update API key', variant: 'error' });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/integrations/api-keys/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['apiKeyIntegrations'] });
      toast({ title: 'Deleted', description: 'API key removed.', variant: 'success' });
    },
    onError: () => {
      toast({ title: 'Error', description: 'Failed to delete API key', variant: 'error' });
    },
  });

  const testMutation = useMutation({
    mutationFn: async (id: string) => {
      const res = await api.post(`/integrations/api-keys/${id}/test`);
      return res.data as { success: boolean; status: string; error?: string };
    },
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['apiKeyIntegrations'] });
      if (result.success) {
        toast({ title: 'Test passed', description: 'The API key is working.', variant: 'success' });
      } else {
        toast({ title: 'Test failed', description: result.error || 'Could not validate credentials.', variant: 'error' });
      }
    },
    onError: () => {
      toast({ title: 'Test failed', description: 'Could not reach the service.', variant: 'error' });
    },
  });

  const resetForm = () => {
    setService('plaid');
    setLabel('');
    setApiKey('');
    setApiSecret('');
    setSiteUrl('');
    setEmail('');
    setEnvironment('sandbox');
  };

  const openCreate = () => {
    resetForm();
    setEditing(null);
    setIsOpen(true);
  };

  const openEdit = (key: ApiKeyIntegration) => {
    setEditing(key);
    setService(key.service);
    setLabel(key.label);
    setApiKey('');
    setApiSecret('');
    setSiteUrl((key.extra_data?.site_url as string) || '');
    setEmail((key.extra_data?.email as string) || '');
    setEnvironment((key.extra_data?.environment as string) || 'sandbox');
    setIsOpen(true);
  };

  const serviceInfo = SERVICE_OPTIONS.find((s) => s.value === service);
  const showSecret = serviceInfo?.hasSecret ?? false;
  const showJira = service === 'jira';

  return (
    <Card className="panel-gilded">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <div className="flex items-center gap-3">
          <div className="text-2xl"><KeyRound className="h-6 w-6" /></div>
          <div>
            <CardTitle className="text-base font-display tracking-wide">API Key Integrations</CardTitle>
            <p className="text-xs text-muted-foreground">Manage API keys and tokens for external services.</p>
          </div>
        </div>
        <Button size="sm" onClick={openCreate}>
          <Plus className="h-4 w-4 mr-1" /> Add Key
        </Button>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading API keys…</p>
        ) : (data ?? []).length === 0 ? (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">No API keys saved yet. Add keys for Plaid, Google, Jira, and more.</p>
            <Button size="sm" onClick={openCreate}>Add your first API key</Button>
          </div>
        ) : (
          <div className="space-y-2">
            {(data ?? []).map((key) => (
              <div key={key.id} className="flex items-center justify-between border rounded p-3">
                <div className="space-y-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-sm truncate">{key.label || key.service}</span>
                    <StatusBadge status={key.status} />
                    {!key.is_active && <Badge variant="outline" className="text-xs">Disabled</Badge>}
                  </div>
                  <p className="text-xs text-muted-foreground capitalize">{key.service.replace('_', ' ')}</p>
                  <p className="text-xs font-mono text-muted-foreground">Key: {key.api_key_masked || '—'}</p>
                  {key.last_tested && (
                    <p className="text-xs text-muted-foreground">
                      Last tested: {new Date(key.last_tested).toLocaleString()}
                    </p>
                  )}
                  {key.last_error && key.status === 'error' && (
                    <p className="text-xs text-red-500">{key.last_error}</p>
                  )}
                </div>
                <div className="flex items-center gap-1 ml-2">
                  <Button size="sm" variant="ghost" className="h-8 w-8 p-0" onClick={() => testMutation.mutate(key.id)} disabled={testMutation.isPending}>
                    <RefreshCw className={`h-4 w-4 ${testMutation.isPending ? 'animate-spin' : ''}`} />
                  </Button>
                  <Button size="sm" variant="ghost" className="h-8 w-8 p-0" onClick={() => openEdit(key)}>
                    <Pencil className="h-4 w-4" />
                  </Button>
                  <Button size="sm" variant="ghost" className="h-8 w-8 p-0 text-destructive" onClick={() => deleteMutation.mutate(key.id)} disabled={deleteMutation.isPending}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}

        <Dialog open={isOpen} onOpenChange={setIsOpen}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>{editing ? 'Edit API Key' : 'Add API Key'}</DialogTitle>
              <DialogDescription>
                Credentials are encrypted at rest. Only you can view or use them.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-3 pt-2">
              <div>
                <Label className="text-xs">Service</Label>
                <select
                  className="w-full rounded border bg-transparent px-3 py-2 text-sm"
                  value={service}
                  onChange={(e) => setService(e.target.value)}
                  disabled={!!editing}
                >
                  {SERVICE_OPTIONS.map((s) => (
                    <option key={s.value} value={s.value}>{s.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <Label className="text-xs">Label</Label>
                <Input placeholder="e.g. Production Plaid" value={label} onChange={(e) => setLabel(e.target.value)} />
              </div>
              <div>
                <Label className="text-xs">API Key / Token {editing && '(leave blank to keep current)'}</Label>
                <Input type="password" placeholder="Paste key here" value={apiKey} onChange={(e) => setApiKey(e.target.value)} />
              </div>
              {showSecret && (
                <div>
                  <Label className="text-xs">API Secret {editing && '(leave blank to keep current)'}</Label>
                  <Input type="password" placeholder="Paste secret here" value={apiSecret} onChange={(e) => setApiSecret(e.target.value)} />
                </div>
              )}
              {service === 'plaid' && (
                <div>
                  <Label className="text-xs">Environment</Label>
                  <select
                    className="w-full rounded border bg-transparent px-3 py-2 text-sm"
                    value={environment}
                    onChange={(e) => setEnvironment(e.target.value)}
                  >
                    <option value="sandbox">Sandbox</option>
                    <option value="development">Development</option>
                    <option value="production">Production</option>
                  </select>
                </div>
              )}
              {showJira && (
                <>
                  <div>
                    <Label className="text-xs">Site URL</Label>
                    <Input placeholder="https://your-domain.atlassian.net" value={siteUrl} onChange={(e) => setSiteUrl(e.target.value)} />
                  </div>
                  <div>
                    <Label className="text-xs">Email</Label>
                    <Input placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} />
                  </div>
                </>
              )}
              <div className="flex gap-2 pt-2">
                <Button
                  size="sm"
                  disabled={!label || !apiKey || createMutation.isPending || updateMutation.isPending}
                  onClick={() => (editing ? updateMutation.mutate() : createMutation.mutate())}
                >
                  {createMutation.isPending || updateMutation.isPending ? 'Saving…' : editing ? 'Update' : 'Save'}
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setIsOpen(false)}>Cancel</Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  );
}
