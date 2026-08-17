'use client';

import React, { useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useUiStore } from '@/stores/uiStore';
import { useThemeStore } from '@/stores/themeStore';
import {
  Bell,
  BarChart3,
  Settings,
  LogOut,
  Link as LinkIcon,
  Bot,
  FileDown,
  Home,
  Moon,
  Sun,
} from 'lucide-react';

export function Sidebar() {
  const { user, logout } = useAuth();
  const isOpen = useUiStore((s) => s.sidebarOpen);
  const setSidebarOpen = useUiStore((s) => s.setSidebarOpen);
  const toggleSidebar = useUiStore((s) => s.toggleSidebar);
  const theme = useThemeStore((s) => s.theme);
  const hydrated = useThemeStore((s) => s.hydrated);
  const toggleTheme = useThemeStore((s) => s.toggleTheme);
  const hydrateTheme = useThemeStore((s) => s.hydrate);
  const pathname = usePathname();

  useEffect(() => {
    hydrateTheme();
  }, [hydrateTheme]);

  useEffect(() => {
    const open = window.innerWidth >= 768;
    setSidebarOpen(open);
    const onResize = () => setSidebarOpen(window.innerWidth >= 768);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [setSidebarOpen]);

  const navigation = [
    { name: 'Analytics', href: '/dashboard/analytics', icon: BarChart3 },
    { name: 'LLM Config', href: '/dashboard/llm-config', icon: Bot },
    { name: 'Integrations', href: '/dashboard/integrations', icon: LinkIcon },
    { name: 'Generated', href: '/dashboard/generated', icon: FileDown },
    { name: 'Alerts & Notifications', href: '/dashboard/notifications', icon: Bell },
    { name: 'Settings', href: '/dashboard/settings', icon: Settings },
  ];

  const isActive = (href: string) =>
    href === '/dashboard' ? pathname === '/dashboard' : pathname.startsWith(href);

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 z-40 h-screen w-64 border-r border-border/60 bg-background/95 backdrop-blur transition-transform',
        isOpen ? 'translate-x-0' : '-translate-x-full'
      )}
    >
      <div className="flex h-full flex-col">
        <div className="flex h-16 flex-col justify-center border-b border-border/60 px-4">
          <Link href="/dashboard" className="flex items-center gap-2.5">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/foujalab.png"
              alt="FoujaLab logo"
              className="h-9 w-9 rounded-full object-cover border border-accent/40"
            />
            <span className="font-brand text-lg font-bold tracking-[0.15em] accent-text">
              Argus <span className="text-xs font-normal tracking-normal opacity-80">ml-auditor</span>
            </span>
          </Link>
          <div className="accent-rule mt-3" />
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto p-4">
          <Link
            href="/dashboard"
            className={cn(
              'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-semibold transition-colors',
              pathname === '/dashboard'
                ? 'bg-primary text-primary-foreground accent-glow'
                : 'text-foreground hover:bg-accent hover:text-accent-foreground'
            )}
          >
            <Home className="h-4 w-4" />
            Home
          </Link>
          {navigation.map((item) => (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                isActive(item.href)
                  ? 'bg-primary text-primary-foreground accent-glow'
                  : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.name}
            </Link>
          ))}
        </nav>

        <div className="border-t border-border/60 p-4">
          <div className="mb-3">
            <Button variant="outline" size="sm" className="w-full" onClick={toggleTheme}>
              {!hydrated || theme === 'dark' ? (
                <Sun className="mr-2 h-4 w-4" />
              ) : (
                <Moon className="mr-2 h-4 w-4" />
              )}
              {!hydrated || theme === 'dark' ? 'Light mode' : 'Dark mode'}
            </Button>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground ring-1 ring-accent/50">
              {user?.email?.charAt(0).toUpperCase() || 'U'}
            </div>
            <div className="flex-1 truncate text-sm">
              <p className="font-medium">{user?.username}</p>
              <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
            </div>
            <Button variant="ghost" size="icon" onClick={logout}>
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </aside>
  );
}
