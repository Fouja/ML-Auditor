'use client';

import React from 'react';
import { WallOfWork } from './wall-of-work';
import { CalendarWidget } from './calendar-widget';
import { NewsFeedWidget } from './news-feed-widget';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CheckCircle2, CalendarDays, Newspaper, ListTodo, Activity, StickyNote } from 'lucide-react';

interface Widget {
  id: string;
  widget_type: string;
  title: string;
  position_x: number;
  position_y: number;
  width: number;
  height: number;
  is_visible: boolean;
  config?: Record<string, any>;
}

interface BentoGridProps {
  widgets: Widget[];
  onWidgetUpdate: (widgetId: string, updates: any) => void;
}

export function BentoGrid({ widgets, onWidgetUpdate }: BentoGridProps) {
  const renderWidget = (widget: Widget) => {
    const widthClass = widget.width === 2 ? 'col-span-2' : 'col-span-1';
    const heightClass = widget.height === 2 ? 'row-span-2' : 'row-span-1';

    const content = (() => {
      switch (widget.widget_type) {
        case 'wall_of_work':
          return <WallOfWork />;
        case 'calendar':
          return <CalendarWidget />;
        case 'news_feed':
          return <NewsFeedWidget />;
        case 'quick_notes':
          return <QuickNotesWidget />;
        case 'stats':
          return <StatsWidget />;
        case 'recent_activity':
          return <RecentActivityWidget />;
        default:
          return <div className="p-4 text-muted-foreground">Unknown widget type</div>;
      }
    })();

    return (
      <Card
        key={widget.id}
        className={`${widthClass} ${heightClass} overflow-hidden`}
      >
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">{widget.title}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {content}
        </CardContent>
      </Card>
    );
  };

  const visibleWidgets = widgets.filter(w => w.is_visible);

  if (visibleWidgets.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-8 text-center">
        <div className="mb-4 rounded-full bg-muted p-4">
          <Activity className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold">Your dashboard is empty</h3>
        <p className="max-w-sm text-sm text-muted-foreground">
          Add widgets from the chatbot panel or switch to another tab to see your work.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-4 p-4">
      {visibleWidgets.map(renderWidget)}
    </div>
  );
}

function QuickNotesWidget() {
  const [notes, setNotes] = React.useState('');

  return (
    <div className="p-4">
      <div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground">
        <StickyNote className="h-3.5 w-3.5" />
        <span>Jot down anything</span>
      </div>
      <textarea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Quick notes..."
        className="w-full h-32 resize-none bg-transparent border-none focus:outline-none text-sm"
      />
    </div>
  );
}

function StatsWidget() {
  const stats = [
    { label: 'Tasks', value: 12, icon: CheckCircle2, color: 'text-blue-400 bg-blue-400/10' },
    { label: 'Events Today', value: 3, icon: CalendarDays, color: 'text-emerald-400 bg-emerald-400/10' },
    { label: 'Unread Articles', value: 8, icon: Newspaper, color: 'text-amber-400 bg-amber-400/10' },
    { label: 'Pending Items', value: 5, icon: ListTodo, color: 'text-rose-400 bg-rose-400/10' },
  ];

  return (
    <div className="p-4 grid grid-cols-2 gap-3">
      {stats.map((stat) => {
        const Icon = stat.icon;
        return (
          <div key={stat.label} className="flex items-center gap-3 rounded-lg border bg-card/50 p-3">
            <div className={`flex h-9 w-9 items-center justify-center rounded-md ${stat.color}`}>
              <Icon className="h-4 w-4" />
            </div>
            <div>
              <p className="text-lg font-bold leading-none">{stat.value}</p>
              <p className="text-xs text-muted-foreground">{stat.label}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function RecentActivityWidget() {
  const activities = [
    { icon: CheckCircle2, text: 'Task completed: "Review PR #42"', time: '2 hours ago', color: 'text-emerald-400' },
    { icon: CalendarDays, text: 'Event created: "Team standup"', time: '3 hours ago', color: 'text-blue-400' },
    { icon: Newspaper, text: 'Article bookmarked: "AI trends 2024"', time: '5 hours ago', color: 'text-amber-400' },
  ];

  return (
    <div className="p-4 space-y-3">
      {activities.map((activity, i) => {
        const Icon = activity.icon;
        return (
          <div key={i} className="flex items-start gap-3 text-sm">
            <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${activity.color}`} />
            <div className="flex-1">
              <p className="text-foreground">{activity.text}</p>
              <p className="text-xs text-muted-foreground">{activity.time}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
