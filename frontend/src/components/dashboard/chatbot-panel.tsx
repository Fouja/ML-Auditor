'use client';

import React, { useState, useRef, useEffect } from 'react';
import api from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Send, Check, X, Loader2, Bot, User } from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  action?: ActionProposal;
}

interface ActionProposal {
  type: 'create_task' | 'create_event' | 'add_feed' | 'delete_task' | 'navigate';
  params: Record<string, any>;
  description: string;
}

interface ChatbotPanelProps {
  onWidgetUpdate: (widgetId: string, updates: any) => void;
}

export function ChatbotPanel({ onWidgetUpdate }: ChatbotPanelProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome-1',
      role: 'assistant',
      content: "Hello! I'm your AI assistant. I can help you manage your tasks, calendar, news feeds, and more. What would you like to do?",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [pendingAction, setPendingAction] = useState<{
    message: Message;
    action: ActionProposal;
  } | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messageIdCounter = useRef(0);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const generateId = () => {
    messageIdCounter.current += 1;
    return `msg-${Date.now()}-${messageIdCounter.current}`;
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: generateId(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const res = await api.post('/agents/chat', {
        content: input,
        agent_type: 'general',
      });
      const data = res.data;

      // Parse tool calls into action proposals
      let action: ActionProposal | undefined;
      if (data.actions_taken && data.actions_taken.length > 0) {
        const lastAction = data.actions_taken[data.actions_taken.length - 1];
        if (lastAction.action && lastAction.status === 'success') {
          action = {
            type: lastAction.action as ActionProposal['type'],
            params: {},
            description: `${lastAction.action} completed`,
          };
        }
      }

      const assistantMessage: Message = {
        id: generateId(),
        role: 'assistant',
        content: data.response,
        timestamp: new Date(),
        action,
      };
      setMessages(prev => [...prev, assistantMessage]);

      if (action) {
        setPendingAction({ message: assistantMessage, action });
      }
    } catch (error: any) {
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

    try {
      switch (action.type) {
        case 'create_task':
          await api.post('/workspace/tasks', action.params);
          break;
        case 'create_event':
          await api.post('/workspace/events', action.params);
          break;
        case 'add_feed':
          await api.post('/workspace/feeds', action.params);
          break;
      }

      setMessages(prev => [
        ...prev,
        {
          id: generateId(),
          role: 'assistant',
          content: 'Action completed successfully!',
          timestamp: new Date(),
        },
      ]);
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

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b p-3">
        <div className="flex items-center gap-2">
          <Bot className="h-5 w-5 text-primary" />
          <span className="font-medium">AI Assistant</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-auto p-3 space-y-3">
        {messages.map(message => (
          <div
            key={message.id}
            className={`flex gap-2 ${message.role === 'user' ? 'justify-end' : ''}`}
          >
            {message.role === 'assistant' && (
              <div className="h-6 w-6 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                <Bot className="h-3 w-3 text-primary" />
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

              {/* Action confirmation UI */}
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
            <div className="h-6 w-6 rounded-full bg-primary/10 flex items-center justify-center">
              <Bot className="h-3 w-3 text-primary" />
            </div>
            <div className="bg-muted rounded-lg p-2">
              <Loader2 className="h-4 w-4 animate-spin" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

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
    </div>
  );
}
