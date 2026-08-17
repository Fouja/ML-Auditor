'use client';

import React from 'react';
import Link from 'next/link';
import { Sidebar } from './sidebar';
import { useUiStore } from '@/stores/uiStore';
import { cn } from '@/lib/utils';
import { Menu, X, Home } from 'lucide-react';

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const sidebarOpen = useUiStore((s) => s.sidebarOpen);
  const toggleSidebar = useUiStore((s) => s.toggleSidebar);

  return (
    <div className="min-h-screen bg-background bg-renaissance">
      <Sidebar />
      <div className={cn('transition-all', sidebarOpen ? 'md:ml-64' : 'md:ml-0')}>
        <header className="sticky top-0 z-30 flex h-14 items-center gap-2 border-b border-border/60 bg-background/80 px-4 backdrop-blur">
          <button
            className="rounded-md bg-background p-2 shadow-md"
            onClick={toggleSidebar}
            aria-label={sidebarOpen ? 'Close menu' : 'Open menu'}
          >
            {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
          <Link
            href="/dashboard"
            className="ml-1 flex items-center gap-2 rounded-md px-2 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
          >
            <Home className="h-4 w-4" />
            Home
          </Link>
        </header>
        <main>
          <div className="p-6">{children}</div>
        </main>
      </div>
    </div>
  );
}
