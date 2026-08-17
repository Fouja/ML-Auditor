'use client';

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Loader2, Plus, Trash2, Play, Star, Pencil, Check } from 'lucide-react';
import api from '@/lib/api';

const LLM_PROVIDERS: Record<
  string,
  { label: string; endpoint: string; models: string[]; keyless?: boolean }
> = {
  openai: {
    label: 'OpenAI (GPT-4, etc.)',
    endpoint: 'https://api.openai.com/v1',
    models: ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo'],
  },
  anthropic: {
    label: 'Anthropic (Claude)',
    endpoint: 'https://api.anthropic.com',
    models: ['claude-3-5-sonnet-latest', 'claude-3-opus-latest', 'claude-3-haiku'],
  },
  nvidia: {
    label: 'NVIDIA NIM (Free)',
    endpoint: 'https://integrate.api.nvidia.com/v1',
    models: [
      // Meta Llama
      'meta/llama-3.1-8b-instruct',
      'meta/llama-3.1-70b-instruct',
      'meta/llama-3.2-1b-instruct',
      'meta/llama-3.2-3b-instruct',
      'meta/llama-3.2-11b-vision-instruct',
      'meta/llama-3.2-90b-vision-instruct',
      'meta/llama-3.3-70b-instruct',
      'meta/llama-guard-4-12b',
      'meta/llama2-70b',
      'meta/codellama-70b',
      'meta/muse-glimmer-30b',
      // Mistral
      'mistralai/mistral-7b-instruct-v0.3',
      'mistralai/mistral-large',
      'mistralai/mistral-large-2-instruct',
      'mistralai/mistral-nemotron',
      'mistralai/mixtral-8x22b-v0.1',
      'mistralai/codestral-22b-instruct-v0.1',
      'nv-mistralai/mistral-nemo-12b-instruct',
      // NVIDIA Nemotron
      'nvidia/llama-3.1-nemotron-nano-8b-v1',
      'nvidia/llama-3.1-nemotron-51b-instruct',
      'nvidia/llama-3.1-nemotron-70b-instruct',
      'nvidia/llama-3.1-nemotron-nano-vl-8b-v1',
      'nvidia/llama-3.1-nemotron-ultra-253b-v1',
      'nvidia/llama-3.3-nemotron-super-49b-v1',
      'nvidia/llama-3.3-nemotron-super-49b-v1.5',
      'nvidia/llama3-chatqa-1.5-70b',
      'nvidia/mistral-nemo-minitron-8b-8k-instruct',
      'nvidia/nemotron-3-nano-30b-a3b',
      'nvidia/nemotron-3-nano-omni-30b-a3b-reasoning',
      'nvidia/nemotron-3-super-120b-a12b',
      'nvidia/nemotron-3-ultra-550b-a55b',
      'nvidia/nemotron-3.5-lightning-30b-a3b',
      'nvidia/nemotron-4-340b-instruct',
      'nvidia/nemotron-mini-4b-instruct',
      'nvidia/nemotron-nano-3-30b-a3b',
      'nvidia/nemotron-nano-12b-v2-vl',
      'nvidia/nvidia-nemotron-nano-9b-v2',
      'nvidia/neva-22b',
      'nvidia/vila',
      // Google Gemma
      'google/gemma-2b',
      'google/gemma-3-4b-it',
      'google/gemma-3-12b-it',
      'google/gemma-4-31b-it',
      'google/codegemma-1.1-7b',
      'google/codegemma-7b',
      'google/diffusiongemma-26b-a4b-it',
      'google/recurrentgemma-2b',
      // Microsoft
      'microsoft/phi-3.5-moe-instruct',
      'microsoft/phi-3-vision-128k-instruct',
      'microsoft/kosmos-2',
      // IBM Granite
      'ibm/granite-3.0-3b-a800m-instruct',
      'ibm/granite-3.0-8b-instruct',
      'ibm/granite-34b-code-instruct',
      'ibm/granite-8b-code-instruct',
      // DeepSeek
      'deepseek-ai/deepseek-coder-6.7b-instruct',
      'deepseek-ai/deepseek-v4-flash-0731',
      // OpenAI
      'openai/gpt-oss-20b',
      'openai/gpt-oss-120b',
      // Other providers hosted on NVIDIA NIM
      'thinkingmachines/inkling',
      'poolside/laguna-xs-2.1',
      'z-ai/glm-5.2',
      '01-ai/yi-large',
      '01-ai/yi-34b-chat',
      'stepfun-ai/step-3.7-flash',
      'ai21labs/jamba-1.5-large-instruct',
      'moonshotai/kimi-k2.6',
      'writer/palmyra-creative-122b',
      'writer/palmyra-fin-70b-32k',
      'writer/palmyra-med-70b',
      'writer/palmyra-med-70b-32k',
      'zyphra/zamba2-7b-instruct',
      'aisingapore/sea-lion-7b-instruct',
      'minimaxai/minimax-m3',
      'databricks/dbrx-instruct',
      'adept/fuyu-8b',
    ],
  },
  ollama: {
    label: 'Ollama (Local)',
    endpoint: 'http://localhost:11434',
    models: ['llama2', 'mistral', 'neural-chat'],
    keyless: true,
  },
  huggingface: {
    label: 'Hugging Face',
    endpoint: 'https://api-inference.huggingface.co',
    models: ['tiiuae/falcon-7b-instruct', 'meta-llama/Llama-2-7b'],
  },
  groq: {
    label: 'Groq (Free)',
    endpoint: 'https://api.groq.com/openai/v1',
    models: [
      'llama-3.3-70b-versatile',
      'llama-3.1-8b-instant',
      'mixtral-8x7b-32768',
      'gemma2-9b-it',
      'llama-3.2-90b-vision-preview',
    ],
  },
  openrouter: {
    label: 'OpenRouter (Free models)',
    endpoint: 'https://openrouter.ai/api/v1',
    models: [
      'meta-llama/llama-3.3-70b-instruct',
      'deepseek/deepseek-chat-v3',
      'mistralai/mistral-small-3.1',
      'qwen/qwen-2.5-72b-instruct',
    ],
  },
  mistral: {
    label: 'Mistral AI',
    endpoint: 'https://api.mistral.ai/v1',
    models: ['open-mistral-nemo', 'mistral-small-latest', 'mistral-medium-latest'],
  },
  gemini: {
    label: 'Google Gemini (Free)',
    endpoint: 'https://generativelanguage.googleapis.com/v1beta/openai',
    models: ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-pro'],
  },
  deepseek: {
    label: 'DeepSeek',
    endpoint: 'https://api.deepseek.com/v1',
    models: ['deepseek-chat', 'deepseek-reasoner'],
  },
  glm: {
    label: 'Zhipu AI (GLM)',
    endpoint: 'https://open.bigmodel.cn/api/paas/v4',
    models: ['glm-4-plus', 'glm-4', 'glm-4-air', 'glm-4-airx', 'glm-4-flash', 'glm-4v', 'glm-4v-plus'],
  },
  together: {
    label: 'Together AI',
    endpoint: 'https://api.together.xyz/v1',
    models: [
      'meta-llama/Llama-3.3-70B-Instruct-Turbo',
      'mistralai/Mixtral-8x7B-Instruct-v0.1',
      'Qwen/Qwen2.5-72B-Instruct-Turbo',
    ],
  },
  lmstudio: {
    label: 'LM Studio (Local)',
    endpoint: 'http://localhost:1234/v1',
    models: [],
    keyless: true,
  },
  custom: { label: 'Custom API', endpoint: '', models: [] },
};

interface LLMConfig {
  id: string;
  provider: string;
  name: string;
  model_name: string;
  api_endpoint?: string | null;
  is_active: boolean;
  created_at: string;
}

const EMPTY_FORM = {
  provider: 'openai',
  name: '',
  api_key: '',
  model_name: 'gpt-4',
  api_endpoint: '',
};

export default function LLMConfiguration() {
  const [llms, setLlms] = useState<LLMConfig[]>([]);
  const [activeLlm, setActiveLlm] = useState<LLMConfig | null>(null);
  const [formData, setFormData] = useState(EMPTY_FORM);
  const [editId, setEditId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [message, setMessage] = useState<{ text: string; ok: boolean } | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    fetchLLMs();
  }, []);

  const notify = (text: string, ok: boolean) => {
    setMessage({ text, ok });
    if (ok) {
      window.setTimeout(() => setMessage(null), 4000);
    }
  };

  const fetchLLMs = async () => {
    try {
      const [listRes, activeRes] = await Promise.all([
        api.get('/integrations/llm-configurations/'),
        api.get('/integrations/llm-configurations/active/').catch(() => null),
      ]);
      setLlms(listRes.data as LLMConfig[]);
      setActiveLlm(activeRes?.data ?? null);
    } catch (error) {
      console.error('Failed to fetch LLMs:', error);
      setLlms([]);
    }
  };

  const handleProviderChange = (provider: string) => {
    const p = LLM_PROVIDERS[provider];
    setFormData({
      ...formData,
      provider,
      model_name: p.models[0] || '',
      api_endpoint: p.endpoint || formData.api_endpoint,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setMessage(null);
    try {
      const endpoint = formData.api_endpoint.trim() || LLM_PROVIDERS[formData.provider].endpoint || '';
      const payload = {
        provider: formData.provider,
        name: formData.name,
        api_key: formData.api_key,
        model_name: formData.model_name,
        api_endpoint: endpoint || null,
      };

      if (editId) {
        await api.put(`/integrations/llm-configurations/${editId}/`, {
          name: payload.name,
          api_key: payload.api_key,
          api_endpoint: payload.api_endpoint,
        });
        notify('Configuration updated', true);
      } else {
        await api.post('/integrations/llm-configurations/', payload);
        notify('LLM configured successfully', true);
      }
      setFormData({ ...EMPTY_FORM, provider: formData.provider });
      setEditId(null);
      await fetchLLMs();
    } catch (error: any) {
      notify(
        `Error: ${error?.response?.data?.error || error?.response?.data?.detail || error.message || 'Unknown error'}`,
        false
      );
    } finally {
      setBusy(false);
    }
  };

  const handleTestLLM = async (id: string) => {
    setTestingId(id);
    setMessage(null);
    try {
      const response = await api.post(`/integrations/llm-configurations/${id}/test/`);
      notify(`${response.data.status}${response.data.model ? ` — ${response.data.model}` : ''}`, true);
    } catch (error: any) {
      notify(`${error?.response?.data?.error || 'Unknown error'}`, false);
    } finally {
      setTestingId(null);
    }
  };

  const handleSetActive = async (id: string) => {
    setBusy(true);
    setMessage(null);
    try {
      const response = await api.post(`/integrations/llm-configurations/${id}/set-active/`);
      notify(`${response.data.status}`, true);
      await fetchLLMs();
    } catch (error: any) {
      notify(`${error?.response?.data?.error || 'Unknown error'}`, false);
    } finally {
      setBusy(false);
    }
  };

  const handleDeleteLLM = async (id: string) => {
    if (!confirm('Are you sure you want to delete this configuration?')) return;
    setBusy(true);
    setMessage(null);
    try {
      await api.delete(`/integrations/llm-configurations/${id}/`);
      notify('Configuration deleted', true);
      await fetchLLMs();
    } catch (error: any) {
      notify(`${error?.response?.data?.error || 'Unknown error'}`, false);
    } finally {
      setBusy(false);
    }
  };

  const handleEdit = (llm: LLMConfig) => {
    setEditId(llm.id);
    setFormData({
      provider: llm.provider,
      name: llm.name,
      api_key: '',
      model_name: llm.model_name,
      api_endpoint: llm.api_endpoint || LLM_PROVIDERS[llm.provider]?.endpoint || '',
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  if (!mounted) {
    return <div className="p-6 text-muted-foreground">Loading...</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">LLM Configuration</h1>
        <p className="text-muted-foreground">
          Configure the language models used by the assistant, activate them, and test the connection.
        </p>
      </div>

      {message && (
        <div
          className={`rounded-md border p-4 text-sm ${
            message.ok
              ? 'border-green-500/40 bg-green-500/10 text-green-400'
              : 'border-red-500/40 bg-red-500/10 text-red-400'
          }`}
        >
          {message.text}
        </div>
      )}

      {/* Add / Edit LLM Form */}
      <Card>
        <CardHeader>
          <CardTitle>{editId ? 'Edit configuration' : 'Add LLM'}</CardTitle>
          <CardDescription>
            Choose a provider, an available model for your key, and an API URL.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label>Provider</Label>
                <select
                  value={formData.provider}
                  onChange={(e) => handleProviderChange(e.target.value)}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {Object.entries(LLM_PROVIDERS).map(([key, val]) => (
                    <option key={key} value={key}>
                      {val.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                <Label>Name</Label>
                <Input
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g. My OpenAI GPT-4"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label>API Key</Label>
                <Input
                  type="password"
                  value={formData.api_key}
                  onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                  placeholder={editId ? 'Leave empty to keep the current key' : 'sk-... or your API key'}
                  required={!editId && !LLM_PROVIDERS[formData.provider]?.keyless}
                />
                {LLM_PROVIDERS[formData.provider]?.keyless && (
                  <p className="text-xs text-muted-foreground">
                    No API key required for this local provider.
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label>Model</Label>
                {LLM_PROVIDERS[formData.provider].models.length > 0 ? (
                  <select
                    value={formData.model_name}
                    onChange={(e) => setFormData({ ...formData, model_name: e.target.value })}
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {LLM_PROVIDERS[formData.provider].models.map((model) => (
                      <option key={model} value={model}>
                        {model}
                      </option>
                    ))}
                  </select>
                ) : (
                  <Input
                    value={formData.model_name}
                    onChange={(e) => setFormData({ ...formData, model_name: e.target.value })}
                    placeholder="e.g. my-model-v1"
                    required
                  />
                )}
              </div>

              <div className="space-y-2 md:col-span-2">
                <Label>API URL (endpoint)</Label>
                <Input
                  value={formData.api_endpoint}
                  onChange={(e) => setFormData({ ...formData, api_endpoint: e.target.value })}
                  placeholder={LLM_PROVIDERS[formData.provider].endpoint || 'https://api.example.com/v1'}
                />
                <p className="text-xs text-muted-foreground">
                  The URL used for test calls. Leave empty to use the provider&apos;s default endpoint.
                </p>
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button type="submit" disabled={busy}>
                {busy ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : editId ? (
                  <Check className="mr-2 h-4 w-4" />
                ) : (
                  <Plus className="mr-2 h-4 w-4" />
                )}
                {editId ? 'Save' : 'Add LLM'}
              </Button>
              {editId && (
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => {
                    setEditId(null);
                    setFormData(EMPTY_FORM);
                  }}
                >
                  Cancel
                </Button>
              )}
            </div>
          </form>
        </CardContent>
      </Card>

      {/* LLMs List */}
      <Card>
        <CardHeader>
          <CardTitle>Configured LLMs</CardTitle>
          <CardDescription>
            {activeLlm
              ? `Active: ${activeLlm.name} (${activeLlm.model_name})`
              : 'No active LLM at the moment.'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {llms.length === 0 ? (
            <p className="text-muted-foreground">No LLM configured. Add one above.</p>
          ) : (
            <div className="space-y-3">
              {llms.map((llm) => (
                <div
                  key={llm.id}
                  className={`rounded-lg border p-4 ${
                    llm.is_active
                      ? 'border-green-500/50 bg-green-500/5'
                      : 'border-border bg-card'
                  }`}
                >
                  <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="truncate font-bold">{llm.name}</h3>
                        {llm.is_active && (
                          <span className="inline-flex items-center rounded-full bg-green-500/15 px-2 py-0.5 text-xs font-medium text-green-400">
                            Active
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {LLM_PROVIDERS[llm.provider]?.label || llm.provider} • {llm.model_name}
                      </p>
                      {llm.api_endpoint && (
                        <p className="mt-0.5 truncate font-mono text-xs text-muted-foreground">
                          {llm.api_endpoint}
                        </p>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        onClick={() => handleTestLLM(llm.id)}
                        disabled={busy || testingId !== null}
                        variant="outline"
                        size="sm"
                      >
                        {testingId === llm.id ? (
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        ) : (
                          <Play className="mr-2 h-4 w-4" />
                        )}
                        Test
                      </Button>
                      {!llm.is_active && (
                        <Button
                          onClick={() => handleSetActive(llm.id)}
                          disabled={busy}
                          variant="outline"
                          size="sm"
                        >
                          <Star className="mr-2 h-4 w-4" />
                          Set active
                        </Button>
                      )}
                      <Button
                        onClick={() => handleEdit(llm)}
                        disabled={busy}
                        variant="outline"
                        size="sm"
                      >
                        <Pencil className="mr-2 h-4 w-4" />
                        Edit
                      </Button>
                      <Button
                        onClick={() => handleDeleteLLM(llm.id)}
                        disabled={busy}
                        variant="outline"
                        size="sm"
                        className="text-destructive hover:bg-destructive/10"
                      >
                        <Trash2 className="mr-2 h-4 w-4" />
                        Delete
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
