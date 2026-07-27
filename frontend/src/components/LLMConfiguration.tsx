'use client';

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';

const LLM_PROVIDERS = {
  openai: { label: 'OpenAI (GPT-4, etc.)', models: ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo'] },
  anthropic: { label: 'Anthropic (Claude)', models: ['claude-3-opus', 'claude-3-sonnet', 'claude-3-haiku'] },
  nvidia: { label: 'NVIDIA NIM', models: ['meta/llama-3.3-70b-instruct', 'mistralai/mixtral-8x7b-instruct-v0.1'] },
  ollama: { label: 'Ollama (Local)', models: ['llama2', 'mistral', 'neural-chat'] },
  huggingface: { label: 'Hugging Face', models: ['tiiuae/falcon-7b-instruct', 'meta-llama/Llama-2-7b'] },
  custom: { label: 'Custom API', models: [] },
};

interface LLMConfig {
  id: string;
  provider: string;
  name: string;
  model_name: string;
  is_active: boolean;
  created_at: string;
}

export default function LLMConfiguration() {
  const [llms, setLlms] = useState<LLMConfig[]>([]);
  const [activeLlm, setActiveLlm] = useState<LLMConfig | null>(null);
  const [formData, setFormData] = useState({
    provider: 'openai',
    name: '',
    api_key: '',
    model_name: 'gpt-4',
    api_endpoint: '',
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    fetchLLMs();
  }, []);

  const fetchLLMs = async () => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        setMessage('✗ Token not found. Please log in.');
        return;
      }

      const headers = {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      };

      const listResponse = await fetch('http://localhost:8000/api/integrations/llm-configurations/', { headers });
      if (!listResponse.ok) {
        console.error('Failed to fetch LLMs:', listResponse.status);
        setLlms([]);
        return;
      }

      const data = await listResponse.json();
      if (Array.isArray(data)) {
        setLlms(data);
      } else {
        console.error('Response is not an array:', data);
        setLlms([]);
      }

      const activeResponse = await fetch('http://localhost:8000/api/integrations/llm-configurations/active/', { headers });
      if (activeResponse.ok) {
        setActiveLlm(await activeResponse.json());
      }
    } catch (error) {
      console.error('Error fetching LLMs:', error);
      setLlms([]);
    }
  };

  const handleAddLLM = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('http://localhost:8000/api/integrations/llm-configurations/', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          provider: formData.provider,
          name: formData.name,
          api_key: formData.api_key,
          model_name: formData.model_name,
          api_endpoint: formData.api_endpoint || null,
        }),
      });

      if (response.ok) {
        setMessage('✓ LLM configuré avec succès');
        setFormData({ provider: 'openai', name: '', api_key: '', model_name: 'gpt-4', api_endpoint: '' });
        await fetchLLMs();
      } else {
        const error = await response.json();
        setMessage(`✗ Erreur: ${error.error || 'Unknown error'}`);
      }
    } catch (error: any) {
      setMessage(`✗ Erreur: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleTestLLM = async (id: string) => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `http://localhost:8000/api/integrations/llm-configurations/${id}/test/`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );
      const data = await response.json();
      if (response.ok) {
        setMessage(`✓ ${data.status}`);
      } else {
        setMessage(`✗ Erreur: ${data.error}`);
      }
    } catch (error: any) {
      setMessage(`✗ Erreur: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSetActive = async (id: string) => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `http://localhost:8000/api/integrations/llm-configurations/${id}/set-active/`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );
      const data = await response.json();
      if (response.ok) {
        setMessage(`✓ ${data.status}`);
        await fetchLLMs();
      } else {
        setMessage(`✗ Erreur: ${data.error}`);
      }
    } catch (error: any) {
      setMessage(`✗ Erreur: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteLLM = async (id: string) => {
    if (!confirm('Êtes-vous sûr de vouloir supprimer cette configuration?')) return;

    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `http://localhost:8000/api/integrations/llm-configurations/${id}/`,
        {
          method: 'DELETE',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );
      if (response.ok) {
        setMessage('✓ Configuration supprimée');
        await fetchLLMs();
      } else {
        const data = await response.json();
        setMessage(`✗ Erreur: ${data.error}`);
      }
    } catch (error: any) {
      setMessage(`✗ Erreur: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const selectedModels = (LLM_PROVIDERS as any)[formData.provider]?.models || [];

  if (!mounted) {
    return <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-6">Chargement...</div>;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">⚙️ Configuration des LLMs</h1>

        {message && (
          <div className={`p-4 mb-6 rounded-lg ${message.startsWith('✓') ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
            {message}
          </div>
        )}

        {/* Add LLM Form */}
        <Card className="p-6 mb-8">
          <h2 className="text-xl font-bold mb-4">Ajouter un LLM</h2>
          <form onSubmit={handleAddLLM} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Provider</label>
                <select
                  value={formData.provider}
                  onChange={(e) => {
                    setFormData({
                      ...formData,
                      provider: e.target.value,
                      model_name: (LLM_PROVIDERS as any)[e.target.value].models[0] || '',
                    });
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {Object.entries(LLM_PROVIDERS).map(([key, val]: any) => (
                    <option key={key} value={key}>{val.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Nom</label>
                <Input
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="ex: Mon OpenAI GPT-4"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Clef API</label>
                <Input
                  type="password"
                  value={formData.api_key}
                  onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                  placeholder="sk-... ou votre clef API"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Modèle</label>
                {selectedModels.length > 0 ? (
                  <select
                    value={formData.model_name}
                    onChange={(e) => setFormData({ ...formData, model_name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {selectedModels.map((model: string) => (
                      <option key={model} value={model}>{model}</option>
                    ))}
                  </select>
                ) : (
                  <Input
                    value={formData.model_name}
                    onChange={(e) => setFormData({ ...formData, model_name: e.target.value })}
                    placeholder="ex: mon-modele-v1"
                    required
                  />
                )}
              </div>

              {(formData.provider === 'custom' || formData.provider === 'ollama') && (
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">URL API (optionnel)</label>
                  <Input
                    value={formData.api_endpoint}
                    onChange={(e) => setFormData({ ...formData, api_endpoint: e.target.value })}
                    placeholder="https://api.example.com/v1 ou http://localhost:11434"
                  />
                </div>
              )}
            </div>

            <Button type="submit" disabled={loading} className="w-full">
              {loading ? '⏳ Ajout en cours...' : '➕ Ajouter LLM'}
            </Button>
          </form>
        </Card>

        {/* LLMs List */}
        <Card className="p-6">
          <h2 className="text-xl font-bold mb-4">LLMs Configurés</h2>
          {llms.length === 0 ? (
            <p className="text-gray-500">Aucun LLM configuré. Ajoutez-en un ci-dessus.</p>
          ) : (
            <div className="space-y-2">
              {llms.map((llm) => (
                <div
                  key={llm.id}
                  className={`p-4 border rounded-lg ${llm.is_active ? 'border-green-500 bg-green-50' : 'border-gray-300'}`}
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="font-bold text-lg">{llm.name}</h3>
                      <p className="text-sm text-gray-600">
                        {(LLM_PROVIDERS as any)[llm.provider]?.label || llm.provider} • {llm.model_name}
                      </p>
                      {llm.is_active && <p className="text-xs text-green-700 font-semibold">✓ Actif</p>}
                    </div>
                    <div className="flex gap-2">
                      <Button
                        onClick={() => handleTestLLM(llm.id)}
                        disabled={loading}
                        variant="outline"
                        size="sm"
                      >
                        🔌 Test
                      </Button>
                      {!llm.is_active && (
                        <Button
                          onClick={() => handleSetActive(llm.id)}
                          disabled={loading}
                          variant="outline"
                          size="sm"
                        >
                          ⭐ Activer
                        </Button>
                      )}
                      <Button
                        onClick={() => handleDeleteLLM(llm.id)}
                        disabled={loading}
                        variant="outline"
                        size="sm"
                        className="text-red-600 hover:bg-red-50"
                      >
                        🗑️ Supprimer
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
