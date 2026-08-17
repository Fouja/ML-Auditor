'use client';

import React from 'react';
import { IntegrationsPanel } from '@/components/dashboard/integrations-panel';
import { DashboardLayout } from '@/components/layout/dashboard-layout';

export default function IntegrationsPage() {
  return (
    <DashboardLayout>
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
