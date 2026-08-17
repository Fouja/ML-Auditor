'use client';

import { X, AlertCircle, CheckCircle, Info, AlertTriangle } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';

const iconMap = {
  default: Info,
  success: CheckCircle,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
};

const colorMap = {
  default: 'border-border bg-background text-foreground',
  success: 'border-green-500/50 bg-green-500/10 text-green-600 dark:text-green-400',
  error: 'border-red-500/50 bg-red-500/10 text-red-600 dark:text-red-400',
  warning: 'border-yellow-500/50 bg-yellow-500/10 text-yellow-600 dark:text-yellow-400',
  info: 'border-blue-500/50 bg-blue-500/10 text-blue-600 dark:text-blue-400',
};

export function Toaster() {
  const { toasts, dismiss } = useToast();

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none">
      {toasts.map(t => {
        const Icon = iconMap[t.variant || 'default'];
        return (
          <div
            key={t.id}
            className={cn(
              'pointer-events-auto flex items-start gap-3 rounded-lg border p-4 shadow-lg transition-all duration-200',
              colorMap[t.variant || 'default']
            )}
          >
            <Icon className="h-5 w-5 flex-shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              {t.title && <p className="text-sm font-medium">{t.title}</p>}
              {t.description && <p className="text-sm opacity-90">{t.description}</p>}
            </div>
            <button
              onClick={() => dismiss(t.id)}
              className="flex-shrink-0 opacity-50 hover:opacity-100 transition-opacity"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
