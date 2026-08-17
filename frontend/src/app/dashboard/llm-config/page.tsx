import LLMConfiguration from '@/components/LLMConfiguration';
import { DashboardLayout } from '@/components/layout/dashboard-layout';

export const metadata = {
  title: 'LLM Configuration | Argus',
  description: 'Configure and manage your language models (LLM)',
};

export default function LLMConfigPage() {
  return (
    <DashboardLayout>
      <LLMConfiguration />
    </DashboardLayout>
  );
}
