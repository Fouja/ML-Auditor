'use client';

import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useRouter, useSearchParams } from 'next/navigation';
import api from '@/lib/api';
import { toast } from '@/hooks/use-toast';
import { isDesktopMode } from '@/lib/desktop';

export function OAuthCallbackHandler() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const searchParams = useSearchParams();

  // Handle web/browser OAuth callbacks via URL params.
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const oauth = searchParams?.get('oauth');
    const service = searchParams?.get('service') || 'google';
    if (!oauth) return;

    if (oauth === 'success') {
      queryClient.invalidateQueries({ queryKey: ['integrationStatus'] });
      queryClient.invalidateQueries({ queryKey: ['emailClusters'] });
      toast({ title: 'Connected', description: `${service} connected successfully.`, variant: 'success' });
    } else if (oauth === 'error') {
      toast({ title: 'Connection failed', description: `Could not connect ${service}. Check your OAuth app settings.`, variant: 'error' });
    } else if (oauth === 'nouser') {
      toast({ title: 'Connection failed', description: 'User session not found. Please log in again.', variant: 'error' });
    }

    // Remove query params without reloading.
    router.replace(window.location.pathname);
  }, [searchParams, queryClient, router]);

  // Handle desktop deep-link callbacks (ml-auditor://oauth/callback?...).
  useEffect(() => {
    let unlisten: (() => void) | undefined;

    async function setupDeepLink() {
      const desktop = await isDesktopMode();
      if (!desktop) return;

      try {
        const { onOpenUrl } = await import('@tauri-apps/plugin-deep-link');
        unlisten = await onOpenUrl((urls) => {
          for (const url of urls) {
            if (!url.startsWith('ml-auditor://oauth/callback')) continue;
            const params = new URLSearchParams(url.split('?')[1] || '');
            const oauth = params.get('oauth');
            const service = params.get('service') || 'google';

            if (oauth === 'success') {
              queryClient.invalidateQueries({ queryKey: ['integrationStatus'] });
              queryClient.invalidateQueries({ queryKey: ['emailClusters'] });
              toast({ title: 'Connected', description: `${service} connected successfully.`, variant: 'success' });
            } else if (oauth === 'error') {
              toast({ title: 'Connection failed', description: `Could not connect ${service}.`, variant: 'error' });
            } else if (oauth === 'nouser') {
              toast({ title: 'Connection failed', description: 'User session not found.', variant: 'error' });
            }
          }
        });
      } catch {
        // Deep-link plugin unavailable in this environment; ignore.
      }
    }

    setupDeepLink();
    return () => {
      if (unlisten) unlisten();
    };
  }, [queryClient]);

  return null;
}
