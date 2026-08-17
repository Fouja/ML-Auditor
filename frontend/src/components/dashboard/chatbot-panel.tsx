'use client';

import React, { useState, useRef, useEffect } from 'react';
import api from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Send, Check, X, Loader2, User, Key, CheckCircle, AlertCircle, Download, ThumbsUp, ThumbsDown, ExternalLink, Trash2 } from 'lucide-react';
import { TactileThinkingSliders } from '@/components/studio/TactileThinkingSliders';
import { ArgusAvatar } from '@/components/dashboard/argus-avatar';
import { useAiStudio } from '@/stores/aiStudioStore';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface SourceLink {
  title: string;
  url: string;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  action?: ActionProposal;
  fileUrl?: string;
  userPrompt?: string;
  sources?: SourceLink[];
}

interface ActionProposal {
  type: string;
  params: Record<string, any>;
  description: string;
}

interface ChatbotPanelProps {
  onWidgetUpdate: (widgetId: string, updates: any) => void;
}

export function ChatbotPanel({ onWidgetUpdate }: ChatbotPanelProps) {
  const welcomeMessage: Message = {
    id: 'welcome-1',
    role: 'assistant',
    content: "I'm Argus — your watchful AI assistant. I keep an eye on your emails, calendar, bank, notes and news. Ask me anything, like 'do I have new job emails?'",
    timestamp: new Date(),
  };
  const [messages, setMessages] = useState<Message[]>([welcomeMessage]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [pendingAction, setPendingAction] = useState<{
    message: Message;
    action: ActionProposal;
  } | null>(null);
  const [ratedMessages, setRatedMessages] = useState<Record<string, 'up' | 'down'>>({});
  const [showApiKeyDialog, setShowApiKeyDialog] = useState(false);
  const [chameleonFrame, setChameleonFrame] = useState<string | null>(null);
  const [apiKeyForm, setApiKeyForm] = useState({
    provider: 'nvidia',
    name: '',
    api_key: '',
    model_name: 'meta/llama-3.3-70b-instruct',
  });
  const [apiKeySaving, setApiKeySaving] = useState(false);
  const [apiKeyMessage, setApiKeyMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messageIdCounter = useRef(0);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Restore the persisted conversation from the backend on mount.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await api.get('/agents/chat/history', {
          params: { agent_type: 'general', limit: 50 },
        });
        const history = (res.data?.messages ?? []) as { role: string; content: string }[];
        if (cancelled || history.length === 0) return;
        setMessages(
          history.map((m) => ({
            id: `msg-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
            role: m.role === 'user' ? ('user' as const) : ('assistant' as const),
            content: m.content,
            timestamp: new Date(),
          }))
        );
      } catch {
        // Backend unavailable — keep the welcome message.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleClearHistory = async () => {
    try {
      await api.delete('/agents/chat/history', { params: { agent_type: 'general' } });
      setMessages([welcomeMessage]);
    } catch {
      console.error('Failed to clear chat history');
    }
  };

  const API_KEY_PROVIDERS: Record<string, { label: string; models: { value: string; label: string }[]; keyless?: boolean }> = {
    nvidia: {
      label: 'NVIDIA NIM (Free)',
      models: [
        { value: 'meta/llama-3.3-70b-instruct', label: 'Llama 3.3 70B' },
        { value: 'mistralai/mistral-medium-3.5-128b', label: 'Mistral Medium 3.5 128B' },
        { value: 'mistralai/mixtral-8x7b-instruct-v0.1', label: 'Mixtral 8x7B' },
      ],
    },
    openai: {
      label: 'OpenAI',
      models: [
        { value: 'gpt-4', label: 'GPT-4' },
        { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
        { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo' },
      ],
    },
    anthropic: {
      label: 'Anthropic (Claude)',
      models: [
        { value: 'claude-3-opus', label: 'Claude 3 Opus' },
        { value: 'claude-3-sonnet', label: 'Claude 3 Sonnet' },
        { value: 'claude-3-haiku', label: 'Claude 3 Haiku' },
      ],
    },
    ollama: {
      label: 'Ollama (Local)',
      models: [
        { value: 'llama2', label: 'Llama 2' },
        { value: 'mistral', label: 'Mistral' },
        { value: 'neural-chat', label: 'Neural Chat' },
      ],
      keyless: true,
    },
    groq: {
      label: 'Groq (Free)',
      models: [
        { value: 'llama-3.3-70b-versatile', label: 'Llama 3.3 70B Versatile' },
        { value: 'llama-3.1-8b-instant', label: 'Llama 3.1 8B Instant' },
        { value: 'mixtral-8x7b-32768', label: 'Mixtral 8x7B' },
        { value: 'gemma2-9b-it', label: 'Gemma 2 9B' },
      ],
    },
    openrouter: {
      label: 'OpenRouter (Free models)',
      models: [
        { value: 'meta-llama/llama-3.3-70b-instruct', label: 'Llama 3.3 70B' },
        { value: 'deepseek/deepseek-chat-v3', label: 'DeepSeek Chat V3' },
        { value: 'mistralai/mistral-small-3.1', label: 'Mistral Small 3.1' },
      ],
    },
    mistral: {
      label: 'Mistral AI',
      models: [
        { value: 'open-mistral-nemo', label: 'Open Mistral Nemo' },
        { value: 'mistral-small-latest', label: 'Mistral Small' },
        { value: 'mistral-medium-latest', label: 'Mistral Medium' },
      ],
    },
    gemini: {
      label: 'Google Gemini (Free)',
      models: [
        { value: 'gemini-2.0-flash', label: 'Gemini 2.0 Flash' },
        { value: 'gemini-1.5-flash', label: 'Gemini 1.5 Flash' },
        { value: 'gemini-1.5-pro', label: 'Gemini 1.5 Pro' },
      ],
    },
    deepseek: {
      label: 'DeepSeek',
      models: [
        { value: 'deepseek-chat', label: 'DeepSeek Chat' },
        { value: 'deepseek-reasoner', label: 'DeepSeek Reasoner' },
      ],
    },
    together: {
      label: 'Together AI',
      models: [
        { value: 'meta-llama/Llama-3.3-70B-Instruct-Turbo', label: 'Llama 3.3 70B' },
        { value: 'mistralai/Mixtral-8x7B-Instruct-v0.1', label: 'Mixtral 8x7B' },
        { value: 'Qwen/Qwen2.5-72B-Instruct-Turbo', label: 'Qwen 2.5 72B' },
      ],
    },
    lmstudio: {
      label: 'LM Studio (Local)',
      models: [
        { value: 'local-model', label: 'Loaded model (any)' },
      ],
      keyless: true,
    },
  };

  const handleSaveApiKey = async () => {
    const keyless = API_KEY_PROVIDERS[apiKeyForm.provider as keyof typeof API_KEY_PROVIDERS]?.keyless;
    if (!apiKeyForm.api_key.trim() && !keyless) {
      setApiKeyMessage({ type: 'error', text: 'Please enter an API key.' });
      return;
    }
    if (!apiKeyForm.name.trim()) {
      setApiKeyForm(prev => ({ ...prev, name: `${API_KEY_PROVIDERS[apiKeyForm.provider as keyof typeof API_KEY_PROVIDERS]?.label || apiKeyForm.provider} - ${apiKeyForm.model_name}` }));
    }
    setApiKeySaving(true);
    setApiKeyMessage(null);

    try {
      const name = apiKeyForm.name.trim() || `${API_KEY_PROVIDERS[apiKeyForm.provider as keyof typeof API_KEY_PROVIDERS]?.label || apiKeyForm.provider} - ${apiKeyForm.model_name}`;

      const response = await api.post('/integrations/llm-configurations/', {
        provider: apiKeyForm.provider,
        name,
        api_key: apiKeyForm.api_key,
        model_name: apiKeyForm.model_name,
        api_endpoint:
          apiKeyForm.provider === 'ollama'
            ? 'http://localhost:11434'
            : apiKeyForm.provider === 'lmstudio'
              ? 'http://localhost:1234/v1'
              : null,
      });

      setApiKeyMessage({ type: 'success', text: 'AI model configured successfully! You can now use the chatbot.' });
      setShowApiKeyDialog(false);
      setMessages(prev => [
        ...prev,
        {
          id: generateId(),
          role: 'assistant',
          content: `✅ AI model "${name}" has been configured and activated! You can now ask me anything.`,
          timestamp: new Date(),
        },
      ]);
    } catch (error: any) {
      const msg = error?.response?.data?.error || error?.response?.data?.detail || error.message || 'Failed to save configuration';
      setApiKeyMessage({ type: 'error', text: `Error: ${msg}` });
    } finally {
      setApiKeySaving(false);
    }
  };

  const handleProviderChange = (provider: string) => {
    const providerConfig = API_KEY_PROVIDERS[provider as keyof typeof API_KEY_PROVIDERS];
    setApiKeyForm({
      provider,
      name: '',
      api_key: apiKeyForm.api_key,
      model_name: providerConfig?.models[0]?.value || '',
    });
  };

  const generateId = () => {
    messageIdCounter.current += 1;
    return `msg-${Date.now()}-${messageIdCounter.current}`;
  };

  const describeAction = (tool: string, args: Record<string, any>): string => {
    switch (tool) {
      case 'create_task':
        return `Create task "${args.title || ''}"`;
      case 'create_note':
        return `Create note "${args.title || ''}"`;
      case 'create_calendar_event':
        return `Create calendar event "${args.summary || ''}"`;
      case 'send_email':
        return `Send email to ${args.to || '(no recipient)'} — subject: ${args.subject || ''}`;
      case 'update_note':
        return `Update note ${args.note_id || ''}`;
      case 'organize_notes':
        return `Organize ${(args.note_ids || []).length} notes into ${args.target_format || 'a document'}`;
      case 'draft_email_reply':
        return `Draft email reply: ${args.original_subject || ''}`;
      case 'jobchameleon_launch':
        return `Launch JOBchameleon (${args.provider || 'gmail'}) and open the workbench with cluster access`;
      default:
        return `Execute ${tool}`;
    }
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const studio = useAiStudio.getState();
    studio.retrieveStarted();

    const userMessage: Message = {
      id: generateId(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    const prompt = input;
    setInput('');
    setIsLoading(true);

    try {
      const res = await api.post('/agents/chat', {
        content: prompt,
        agent_type: 'general',
        creativity: studio.knobs.creativity,
        creativity_level: studio.creativityLevel,
        context_depth: studio.knobs.contextDepth,
        token_budget: studio.knobs.tokenBudget,
      });
      const data = res.data;

      studio.retrieveDone();
      studio.beginResponse();

      let action: ActionProposal | undefined;
      const pending = data.pending_actions?.[0];
      if (pending && pending.tool) {
        action = {
          type: pending.tool,
          params: pending.args || {},
          description: describeAction(pending.tool, pending.args || {}),
        };
      }

      const fileUrl: string | undefined =
        typeof data.metadata?.file_url === 'string' ? data.metadata.file_url : undefined;

      const rawSources = data.metadata?.sources;
      const sources: SourceLink[] = Array.isArray(rawSources)
        ? rawSources
            .filter((s: any) => s && typeof s.url === 'string')
            .map((s: any) => ({
              title: typeof s.title === 'string' && s.title ? s.title : s.url,
              url: s.url,
            }))
        : [];

      const assistantMessage: Message = {
        id: generateId(),
        role: 'assistant',
        content: data.response,
        timestamp: new Date(),
        action,
        fileUrl,
        userPrompt: prompt,
        sources: sources.length ? sources : undefined,
      };
      setMessages(prev => [...prev, assistantMessage]);

      if (action) {
        setPendingAction({ message: assistantMessage, action });
      }

      const meta = data.metadata || {};
      const model = typeof meta.model === 'string' ? meta.model : '';
      const latency = typeof meta.latency_ms === 'number' ? meta.latency_ms : 0;
      const completionTokens = typeof meta.completion_tokens === 'number' ? meta.completion_tokens : 0;
      studio.setLastLlmMetrics(model, latency, completionTokens);
      studio.consumeTokens(completionTokens || Math.max(6, Math.round(latency / 200)));

      studio.endResponse();
    } catch (error: any) {
      useAiStudio.getState().retrieveDone();
      useAiStudio.getState().endResponse();
      const errorMsg = error?.response?.data?.detail || 'Sorry, I encountered an error. Please try again.';
      setMessages(prev => [
        ...prev,
        {
          id: generateId(),
          role: 'assistant',
          content: errorMsg,
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirmAction = async () => {
    if (!pendingAction) return;

    const { action } = pendingAction;

    // jobchameleon_launch is handled client-side: it opens the JWT bearer
    // launch endpoint and either embeds the JOBchameleon workbench inside an
    // in-chat iframe (default — so chat can drive all features including
    // clusters) or opens it in a new tab.
    if (action.type === 'jobchameleon_launch') {
      try {
        const res = await api.get('/agents/jobchameleon/launch');
        const data = res.data as {
          url: string;
          token: string;
          email_connected: boolean;
          provider: string;
          success?: boolean;
          error?: string;
          console_url?: string;
        };
        if (data.success === false || !data.url) {
          setMessages(prev => [
            ...prev,
            {
              id: generateId(),
              role: 'assistant',
              content:
                data.error || 'The full JOBchameleon workbench could not be started. Check the Docker image and try again.',
              timestamp: new Date(),
            },
          ]);
        } else if (!data.email_connected) {
          setMessages(prev => [
            ...prev,
            {
              id: generateId(),
              role: 'assistant',
              content:
                'Before launching JOBchameleon, you need to connect your email provider via OAuth2. Redirecting now — connexion only, JOBchameleon will never send email on your behalf.',
              timestamp: new Date(),
            },
          ]);
          window.location.href = '/api/integrations/oauth/google';
        } else {
          const target = `${data.url}${data.url.includes('?') ? '&' : '?'}token=${encodeURIComponent(data.token)}`;
          const openIn: string = (action.params?.open_in as string) || 'iframe';
          if (openIn === 'tab') {
            window.open(target, '_blank', 'noopener,noreferrer');
          } else {
            setChameleonFrame(target);
          }
          setMessages(prev => [
            ...prev,
            {
              id: generateId(),
              role: 'assistant',
              content:
                'JOBchameleon launched. The chat inside the workbench can access every feature including lead clusters.',
              timestamp: new Date(),
            },
          ]);
        }
      } catch {
        setMessages(prev => [
          ...prev,
          {
            id: generateId(),
            role: 'assistant',
            content: 'Failed to launch JOBchameleon. Is the container running?',
            timestamp: new Date(),
          },
        ]);
      }
      setPendingAction(null);
      return;
    }

    try {
      const res = await api.post('/agents/execute-tool', {
        tool: action.type,
        args: action.params,
      });
      const outcome = res.data;
      if (outcome.success) {
        setMessages(prev => [
          ...prev,
          {
            id: generateId(),
            role: 'assistant',
            content: 'Action completed successfully!',
            timestamp: new Date(),
          },
        ]);
      } else {
        const errMsg = outcome.result?.error || 'The action could not be completed.';
        setMessages(prev => [
          ...prev,
          {
            id: generateId(),
            role: 'assistant',
            content: `I couldn't complete that: ${errMsg}`,
            timestamp: new Date(),
          },
        ]);
      }
    } catch (error) {
      setMessages(prev => [
        ...prev,
        {
          id: generateId(),
          role: 'assistant',
          content: 'Failed to execute action. Please try again.',
          timestamp: new Date(),
        },
      ]);
    }

    setPendingAction(null);
  };

  const handleRejectAction = () => {
    setMessages(prev => [
      ...prev,
      {
        id: generateId(),
        role: 'assistant',
        content: 'Action cancelled. What else can I help you with?',
        timestamp: new Date(),
      },
    ]);
    setPendingAction(null);
  };

  const handleFeedback = async (messageId: string, rating: 'up' | 'down', prompt: string) => {
    if (ratedMessages[messageId]) return;
    setRatedMessages(prev => ({ ...prev, [messageId]: rating }));

    const msg = messages.find(m => m.id === messageId);
    if (!msg) return;

    let comment = '';
    if (rating === 'down') {
      comment = window.prompt('What could the assistant have done better? (optional)') || '';
    }

    try {
      await api.post('/agents/feedback', {
        rating: rating === 'up' ? 5 : 1,
        comment,
        agent_type: 'general',
        user_message: msg.userPrompt || '',
        agent_response: msg.content,
      });
    } catch (e) {
      console.error('Failed to submit feedback:', e);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b border-border/60 bg-background/60 p-3 backdrop-blur">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-full border border-accent/40 bg-accent/10 overflow-hidden">
            <ArgusAvatar size={30} />
          </div>
          <span className="font-display text-base font-semibold tracking-wide text-accent-foreground">
            Argus
          </span>
          <div className="ml-auto flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleClearHistory}
              className="h-7 text-xs gap-1 text-muted-foreground hover:text-destructive"
              title="Clear conversation history"
            >
              <Trash2 className="h-3 w-3" />
              Clear
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowApiKeyDialog(true)}
              className="h-7 text-xs gap-1"
              title="Add API Key"
            >
              <Key className="h-3 w-3" />
              Add API Key
            </Button>
          </div>
        </div>
      </div>

      {/* Thinking dials — pulse while the agent retrieves or generates */}
      <div className="border-b border-border/60 p-2.5">
        <TactileThinkingSliders />
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-auto p-3 space-y-3">
        {messages.map(message => (
          <div
            key={message.id}
            className={`flex gap-2 ${message.role === 'user' ? 'justify-end' : ''}`}
          >
            {message.role === 'assistant' && (
              <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 overflow-hidden">
                <ArgusAvatar size={26} />
              </div>
            )}
            <div
              className={`max-w-[80%] rounded-lg p-2 text-sm ${
                message.role === 'user'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted'
              }`}
            >
              <p className="whitespace-pre-wrap">{message.content}</p>

              {/* Feedback thumbs */}
              {message.role === 'assistant' && message.userPrompt && (
                <div className="mt-2 flex items-center gap-1">
                  {!ratedMessages[message.id] ? (
                    <>
                      <button
                        onClick={() => handleFeedback(message.id, 'up', '')}
                        className="inline-flex h-6 w-6 items-center justify-center rounded text-muted-foreground hover:text-green-600 hover:bg-green-50"
                        title="Good answer"
                      >
                        <ThumbsUp className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={() => handleFeedback(message.id, 'down', '')}
                        className="inline-flex h-6 w-6 items-center justify-center rounded text-muted-foreground hover:text-red-600 hover:bg-red-50"
                        title="Bad answer"
                      >
                        <ThumbsDown className="h-3.5 w-3.5" />
                      </button>
                    </>
                  ) : (
                    <span className="text-xs text-muted-foreground flex items-center gap-1">
                      {ratedMessages[message.id] === 'up' ? (
                        <><ThumbsUp className="h-3 w-3 text-green-600" /> Thanks!</>
                      ) : (
                        <><ThumbsDown className="h-3 w-3 text-red-600" /> Noted</>
                      )}
                    </span>
                  )}
                </div>
              )}

              {message.sources && message.sources.length > 0 && (
                <div className="mt-2 space-y-1 border-t border-border/40 pt-2">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
                    Sources
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {message.sources.map((src, idx) => (
                      <a
                        key={`${src.url}-${idx}`}
                        href={src.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex max-w-full items-center gap-1 rounded-full border border-border bg-background/70 px-2 py-0.5 text-[11px] text-primary hover:bg-background"
                        title={src.url}
                      >
                        <ExternalLink className="h-3 w-3 shrink-0" />
                        <span className="truncate">{src.title}</span>
                      </a>
                    ))}
                  </div>
                </div>
              )}

              {message.fileUrl && (
                <a
                  href={`${API_BASE}${message.fileUrl}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2 inline-flex items-center gap-1 text-xs text-primary underline"
                >
                  <Download className="h-3 w-3" />
                  Download bank statement (PDF)
                </a>
              )}

              {message.action && (
                <div className="mt-2 p-2 bg-background/50 rounded border">
                  <p className="text-xs text-muted-foreground mb-2">
                    Proposed action:
                  </p>
                  <p className="text-sm font-medium mb-2">
                    {message.action.description}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      onClick={handleConfirmAction}
                      className="h-7"
                    >
                      <Check className="h-3 w-3 mr-1" />
                      Confirm
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleRejectAction}
                      className="h-7"
                    >
                      <X className="h-3 w-3 mr-1" />
                      Cancel
                    </Button>
                  </div>
                </div>
              )}
            </div>
            {message.role === 'user' && (
              <div className="h-6 w-6 rounded-full bg-muted flex items-center justify-center flex-shrink-0">
                <User className="h-3 w-3" />
              </div>
            )}
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-2">
            <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center overflow-hidden">
              <ArgusAvatar size={26} />
            </div>
            <div className="bg-muted rounded-lg p-2 flex items-center">
              <Loader2 className="h-4 w-4 animate-spin" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Embedded JOBchameleon workbench — opened when an assistant action
          launches JOBchameleon so the chat can drive all workbench features
          (lead discovery, scoring, ranking, clusters). */}
      {chameleonFrame && (
        <div className="border-t border-border/60 flex flex-col" style={{ height: '50vh' }}>
          <div className="flex items-center justify-between border-b border-border/40 px-3 py-1.5 bg-muted/40">
            <span className="text-xs font-medium text-muted-foreground">
              JOBchameleon workbench (full app — chat-driven clusters)
            </span>
            <Button
              size="sm"
              variant="ghost"
              className="h-6 text-xs"
              onClick={() => setChameleonFrame(null)}
              title="Close workbench"
            >
              <X className="h-3 w-3 mr-1" />
              Close
            </Button>
          </div>
          <iframe
            src={chameleonFrame}
            title="JOBchameleon workbench"
            className="flex-1 w-full border-0"
          />
        </div>
      )}

      {/* Input */}
      <div className="border-t p-3">
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Type a message..."
            disabled={isLoading}
          />
          <Button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            size="icon"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* API Key Dialog */}
      <Dialog open={showApiKeyDialog} onOpenChange={setShowApiKeyDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Add AI Model</DialogTitle>
            <DialogDescription>
              Configure an AI model to enable the chatbot. Get a free NVIDIA NIM API key at{' '}
              <a href="https://build.nvidia.com" target="_blank" rel="noopener noreferrer" className="underline text-primary">
                build.nvidia.com
              </a>
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="provider">Provider</Label>
              <select
                id="provider"
                value={apiKeyForm.provider}
                onChange={(e) => handleProviderChange(e.target.value)}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                {Object.entries(API_KEY_PROVIDERS).map(([key, config]) => (
                  <option key={key} value={key}>{config.label}</option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="model">Model</Label>
              <select
                id="model"
                value={apiKeyForm.model_name}
                onChange={(e) => setApiKeyForm(prev => ({ ...prev, model_name: e.target.value }))}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                {API_KEY_PROVIDERS[apiKeyForm.provider as keyof typeof API_KEY_PROVIDERS]?.models.map(m => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </select>
            </div>

            {API_KEY_PROVIDERS[apiKeyForm.provider as keyof typeof API_KEY_PROVIDERS]?.keyless ? (
              <p className="text-xs text-muted-foreground">
                No API key needed for this local provider. Make sure it&apos;s running
                locally (Ollama on 11434, LM Studio on 1234).
              </p>
            ) : (
              <div className="space-y-2">
                <Label htmlFor="api_key">API Key</Label>
                <Input
                  id="api_key"
                  type="password"
                  value={apiKeyForm.api_key}
                  onChange={(e) => setApiKeyForm(prev => ({ ...prev, api_key: e.target.value }))}
                  placeholder={apiKeyForm.provider === 'nvidia' ? 'nvapi-...' : 'sk-...'}
                />
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="name">Name (optional)</Label>
              <Input
                id="name"
                value={apiKeyForm.name}
                onChange={(e) => setApiKeyForm(prev => ({ ...prev, name: e.target.value }))}
                placeholder={`${API_KEY_PROVIDERS[apiKeyForm.provider as keyof typeof API_KEY_PROVIDERS]?.label || ''} - ${apiKeyForm.model_name}`}
              />
            </div>

            {apiKeyMessage && (
              <div className={`flex items-center gap-2 text-sm p-2 rounded-md ${
                apiKeyMessage.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
              }`}>
                {apiKeyMessage.type === 'success' ? <CheckCircle className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
                {apiKeyMessage.text}
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowApiKeyDialog(false)} disabled={apiKeySaving}>
              Cancel
            </Button>
            <Button onClick={handleSaveApiKey} disabled={apiKeySaving}>
              {apiKeySaving ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Check className="h-4 w-4 mr-1" />}
              {apiKeySaving ? 'Saving...' : 'Save & Activate'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
