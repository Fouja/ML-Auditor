'use client';

import React from 'react';
import { WallOfWork } from './wall-of-work';
import { CalendarWidget } from './calendar-widget';
import { NewsFeedWidget } from './news-feed-widget';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

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
  return (
    <div className="p-4 space-y-2">
      <div className="flex justify-between text-sm">
        <span className="text-muted-foreground">Tasks</span>
        <span className="font-medium">12</span>
      </div>
      <div className="flex justify-between text-sm">
        <span className="text-muted-foreground">Events Today</span>
        <span className="font-medium">3</span>
      </div>
      <div className="flex justify-between text-sm">
        <span className="text-muted-foreground">Unread Articles</span>
        <span className="font-medium">8</span>
      </div>
    </div>
  );
}

function RecentActivityWidget() {
  return (
    <div className="p-4 space-y-2">
      <div className="text-sm">
        <p className="text-muted-foreground">Task completed: &quot;Review PR #42&quot;</p>
        <p className="text-xs text-muted-foreground">2 hours ago</p>
      </div>
      <div className="text-sm">
        <p className="text-muted-foreground">Event created: &quot;Team standup&quot;</p>
        <p className="text-xs text-muted-foreground">3 hours ago</p>
      </div>
      <div className="text-sm">
        <p className="text-muted-foreground">Article bookmarked: &quot;AI trends 2024&quot;</p>
        <p className="text-xs text-muted-foreground">5 hours ago</p>
      </div>
    </div>
  );
}
