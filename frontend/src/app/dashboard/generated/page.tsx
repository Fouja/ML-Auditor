'use client';

import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { GeneratedDocuments } from '@/components/dashboard/generated-documents';

export default function GeneratedPage() {
  return (
    <DashboardLayout>
      <GeneratedDocuments />
    </DashboardLayout>
  );
}
