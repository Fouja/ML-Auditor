import LLMConfiguration from '@/components/LLMConfiguration';

export const metadata = {
  title: 'Configuration des LLMs | ML-Auditor',
  description: 'Configurer et gérer vos modèles de langage (LLM)',
};

export default function LLMConfigPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      <LLMConfiguration />
    </div>
  );
}
