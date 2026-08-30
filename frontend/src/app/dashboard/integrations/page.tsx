'use client';

import React, { Suspense } from 'react';
import { IntegrationsPanel } from '@/components/dashboard/integrations-panel';
import { OAuthCallbackHandler } from '@/components/dashboard/oauth-callback-handler';
import { DashboardLayout } from '@/components/layout/dashboard-layout';

export default function IntegrationsPage() {
  return (
    <DashboardLayout>
      <Suspense fallback={null}>
        <OAuthCallbackHandler />
      </Suspense>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Integrations</h1>
          <p className="text-muted-foreground">Connect your external services and manage sync settings.</p>
        </div>
        <IntegrationsPanel />
      </div>
    </DashboardLayout>
  );
}
