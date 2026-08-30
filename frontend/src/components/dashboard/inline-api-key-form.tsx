'use client';

import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { toast } from '@/hooks/use-toast';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface InlineApiKeyFormProps {
  service: string;
  label: string;
  requireSecret?: boolean;
  secretLabel?: string;
  placeholder?: string;
  secretPlaceholder?: string;
  extraFields?: React.ReactNode;
  onSuccess?: () => void;
}

export function InlineApiKeyForm({
  service,
  label,
  requireSecret = false,
  secretLabel = 'API Secret',
  placeholder = 'Paste API key / token',
  secretPlaceholder = 'Paste API secret',
  extraFields,
  onSuccess,
}: InlineApiKeyFormProps) {
  const queryClient = useQueryClient();
  const [name, setName] = useState('');
  const [key, setKey] = useState('');
  const [secret, setSecret] = useState('');

  const createMutation = useMutation({
    mutationFn: async () => {
      const payload: Record<string, unknown> = {
        service,
        label: name || label,
        api_key: key,
      };
      if (requireSecret) payload.api_secret = secret;
      const res = await api.post('/integrations/api-keys', payload);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['apiKeyIntegrations'] });
      queryClient.invalidateQueries({ queryKey: ['integrationStatus'] });
      setName('');
      setKey('');
      setSecret('');
      toast({ title: 'Connected', description: 'API key saved and encrypted.', variant: 'success' });
      onSuccess?.();
    },
    onError: (err: any) => {
      toast({ title: 'Error', description: err?.response?.data?.detail || 'Failed to save API key', variant: 'error' });
    },
  });

  const canSubmit = name.trim() && key.trim() && (!requireSecret || secret.trim());

  return (
    <div className="space-y-3">
      <div>
        <Label className="text-xs">Label</Label>
        <Input placeholder={label} value={name} onChange={(e) => setName(e.target.value)} />
      </div>
      <div>
        <Label className="text-xs">API Key / Token</Label>
        <Input type="password" placeholder={placeholder} value={key} onChange={(e) => setKey(e.target.value)} />
      </div>
      {requireSecret && (
        <div>
          <Label className="text-xs">{secretLabel}</Label>
          <Input type="password" placeholder={secretPlaceholder} value={secret} onChange={(e) => setSecret(e.target.value)} />
        </div>
      )}
      {extraFields}
      <Button size="sm" disabled={!canSubmit || createMutation.isPending} onClick={() => createMutation.mutate()}>
        {createMutation.isPending ? 'Saving…' : 'Connect with API Key'}
      </Button>
    </div>
  );
}
