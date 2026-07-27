'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { BentoGrid } from '@/components/dashboard/bento-grid';
import { ChatbotPanel } from '@/components/dashboard/chatbot-panel';
import { WallOfWork } from '@/components/dashboard/wall-of-work';
import api from '@/lib/api';

export default function DashboardPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();
  const [widgets, setWidgets] = useState<any[]>([]);
  const [loadingWidgets, setLoadingWidgets] = useState(true);
  const [activeTab, setActiveTab] = useState<'board' | 'bento'>('board');

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, isLoading, router]);

  useEffect(() => {
    if (isAuthenticated) {
      fetchWidgets();
    }
  }, [isAuthenticated]);

  const fetchWidgets = async () => {
    try {
      const response = await api.get('/workspace/widgets');
      setWidgets(response.data);
    } catch (error) {
      console.error('Failed to fetch widgets:', error);
      setWidgets([
        { id: '1', widget_type: 'wall_of_work', title: 'Wall of Work', position_x: 0, position_y: 0, width: 2, height: 1, is_visible: true },
        { id: '2', widget_type: 'calendar', title: 'Calendar', position_x: 0, position_y: 1, width: 1, height: 1, is_visible: true },
        { id: '3', widget_type: 'news_feed', title: 'News Feed', position_x: 1, position_y: 1, width: 1, height: 1, is_visible: true },
      ]);
    } finally {
      setLoadingWidgets(false);
    }
  };

  const handleWidgetUpdate = async (widgetId: string, updates: any) => {
    try {
      await api.put(`/workspace/widgets/${widgetId}`, updates);
      setWidgets(prev => prev.map(w => w.id === widgetId ? { ...w, ...updates } : w));
    } catch (error) {
      console.error('Failed to update widget:', error);
    }
  };

  if (isLoading || loadingWidgets) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-12 w-12 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <DashboardLayout>
      <div className="flex h-[calc(100vh-4rem)] gap-4">
        {/* Main Dashboard Area */}
        <div className="flex-1 overflow-hidden flex flex-col">
          {/* Tab Switcher */}
          <div className="flex items-center gap-1 px-4 pt-3 border-b">
            <button
              className={`px-3 py-1.5 text-sm font-medium rounded-t-md transition-colors ${
                activeTab === 'board'
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-muted'
              }`}
              onClick={() => setActiveTab('board')}
            >
              Wall of Work
            </button>
            <button
              className={`px-3 py-1.5 text-sm font-medium rounded-t-md transition-colors ${
                activeTab === 'bento'
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-muted'
              }`}
              onClick={() => setActiveTab('bento')}
            >
              Dashboard
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-auto">
            {activeTab === 'board' ? (
              <WallOfWork />
            ) : (
              <BentoGrid
                widgets={widgets}
                onWidgetUpdate={handleWidgetUpdate}
              />
            )}
          </div>
        </div>

        {/* Chatbot Panel */}
        <div className="w-96 border-l bg-card">
          <ChatbotPanel
            onWidgetUpdate={handleWidgetUpdate}
          />
        </div>
      </div>
    </DashboardLayout>
  );
}
