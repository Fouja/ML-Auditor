'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { BentoGrid } from '@/components/dashboard/bento-grid';
import { ChatbotPanel } from '@/components/dashboard/chatbot-panel';
import { WallOfWork } from '@/components/dashboard/wall-of-work';
import { Notes } from '@/components/dashboard/notes';
import { NewsPanel } from '@/components/dashboard/news-panel';
import { ClusterBoard } from '@/components/dashboard/cluster-board';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Toaster } from '@/components/ui/toaster';
import { LayoutDashboard, ListTodo, StickyNote, Newspaper, Layers } from 'lucide-react';
import api from '@/lib/api';

export default function DashboardPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();
  const [widgets, setWidgets] = useState<any[]>([]);
  const [loadingWidgets, setLoadingWidgets] = useState(true);
  const [activeTab, setActiveTab] = useState<'board' | 'bento' | 'notes' | 'news' | 'clusters'>('bento');

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
        { id: '1', widget_type: 'stats', title: 'Overview', position_x: 0, position_y: 0, width: 2, height: 1, is_visible: true },
        { id: '2', widget_type: 'wall_of_work', title: 'Wall of Work', position_x: 0, position_y: 1, width: 2, height: 1, is_visible: true },
        { id: '3', widget_type: 'calendar', title: 'Calendar', position_x: 0, position_y: 2, width: 1, height: 1, is_visible: true },
        { id: '4', widget_type: 'news_feed', title: 'News Feed', position_x: 1, position_y: 2, width: 1, height: 1, is_visible: true },
        { id: '5', widget_type: 'recent_activity', title: 'Recent Activity', position_x: 0, position_y: 3, width: 1, height: 1, is_visible: true },
        { id: '6', widget_type: 'quick_notes', title: 'Quick Notes', position_x: 1, position_y: 3, width: 1, height: 1, is_visible: true },
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
      <Toaster />
      <div className="flex h-[calc(100vh-4rem)] gap-4">
        {/* Main Dashboard Area */}
        <div className="flex-1 overflow-hidden flex flex-col">
          {/* Tab Switcher */}
          <div className="px-4 pt-3">
            <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as typeof activeTab)}>
              <TabsList className="h-9 bg-transparent">
                <TabsTrigger value="board" className="font-display tracking-wide">
                  <ListTodo className="h-3.5 w-3.5" />
                  Wall of Work
                </TabsTrigger>
                <TabsTrigger value="bento" className="font-display tracking-wide">
                  <LayoutDashboard className="h-3.5 w-3.5" />
                  Dashboard
                </TabsTrigger>
                <TabsTrigger value="notes" className="font-display tracking-wide">
                  <StickyNote className="h-3.5 w-3.5" />
                  Notes
                </TabsTrigger>
                <TabsTrigger value="news" className="font-display tracking-wide">
                  <Newspaper className="h-3.5 w-3.5" />
                  Actualités
                </TabsTrigger>
                <TabsTrigger value="clusters" className="font-display tracking-wide">
                  <Layers className="h-3.5 w-3.5" />
                  Clusters
                </TabsTrigger>
              </TabsList>
            </Tabs>
            <div className="accent-rule mt-2" />
          </div>

          {/* Content */}
          <div className="flex-1 overflow-auto">
            {activeTab === 'board' ? (
              <WallOfWork />
            ) : activeTab === 'notes' ? (
              <Notes />
            ) : activeTab === 'news' ? (
              <NewsPanel />
            ) : activeTab === 'clusters' ? (
              <ClusterBoard />
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
