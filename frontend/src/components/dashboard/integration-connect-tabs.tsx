'use client';

import React from 'react';

interface IntegrationConnectTabsProps {
  active: 'oauth' | 'apikey';
  onChange: (tab: 'oauth' | 'apikey') => void;
  oauthLabel?: string;
  apiKeyLabel?: string;
}

export function IntegrationConnectTabs({
  active,
  onChange,
  oauthLabel = 'OAuth2',
  apiKeyLabel = 'API Key',
}: IntegrationConnectTabsProps) {
  return (
    <div className="flex border-b mb-3">
      <button
        type="button"
        onClick={() => onChange('oauth')}
        className={`flex-1 pb-2 text-xs font-medium transition-colors ${
          active === 'oauth'
            ? 'border-b-2 border-primary text-primary'
            : 'text-muted-foreground hover:text-foreground'
        }`}
      >
        {oauthLabel}
      </button>
      <button
        type="button"
        onClick={() => onChange('apikey')}
        className={`flex-1 pb-2 text-xs font-medium transition-colors ${
          active === 'apikey'
            ? 'border-b-2 border-primary text-primary'
            : 'text-muted-foreground hover:text-foreground'
        }`}
      >
        {apiKeyLabel}
      </button>
    </div>
  );
}
