'use client';

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { HelpCircle, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';

interface Guide {
  key: string;
  title: string;
  steps: React.ReactNode[];
  links?: { label: string; url: string }[];
}

const GUIDES: Guide[] = [
  {
    key: 'plaid',
    title: 'Plaid (Banking)',
    steps: [
      <>Go to the <a href="https://dashboard.plaid.com/" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline inline-flex items-center gap-1">Plaid Dashboard <ExternalLink className="h-3 w-3" /></a>.</>,
      'Create a team if you have not already, then open Settings → Keys.',
      'Copy the Client ID and Sandbox (or Development/Production) Secret.',
      'In ML-Auditor, click Add Key → Plaid, paste both values, pick the matching environment, and save.',
      'Click the test icon to verify. To link a real bank you must use Development or Production keys; Sandbox only accepts test credentials.',
    ],
    links: [
      { label: 'Plaid Dashboard', url: 'https://dashboard.plaid.com/' },
      { label: 'Plaid Docs', url: 'https://plaid.com/docs/' },
    ],
  },
  {
    key: 'gmail',
    title: 'Gmail / Google Calendar',
    steps: [
      <>Open <a href="https://console.cloud.google.com/" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline inline-flex items-center gap-1">Google Cloud Console <ExternalLink className="h-3 w-3" /></a> and select a project.</>,
      'Enable the Gmail API and/or Google Calendar API under APIs & Services → Library.',
      'Go to APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID (Web application).',
      'Add this Authorized redirect URI: http://localhost:8000/api/integrations/oauth/google/callback',
      'On the OAuth consent screen, add your Google account as a Test user.',
      'Back in ML-Auditor, use the Gmail/Google Calendar card to connect with OAuth, or paste an API access token under Add Key.',
    ],
    links: [
      { label: 'Google Cloud Console', url: 'https://console.cloud.google.com/' },
      { label: 'Gmail API Docs', url: 'https://developers.google.com/gmail/api/guides' },
    ],
  },
  {
    key: 'canva',
    title: 'Canva',
    steps: [
      <>Visit <a href="https://www.canva.com/developers/" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline inline-flex items-center gap-1">Canva Developers <ExternalLink className="h-3 w-3" /></a> and create an app.</>,
      'Copy the Client ID and Secret from your app settings.',
      'Use the Canva card in ML-Auditor to start OAuth, or save a personal access token via Add Key → Canva.',
      'Approve the requested scopes (design read, folder read, etc.).',
    ],
    links: [
      { label: 'Canva Developers', url: 'https://www.canva.com/developers/' },
    ],
  },
  {
    key: 'jira',
    title: 'Jira',
    steps: [
      'Find your Jira site URL, e.g. https://your-domain.atlassian.net.',
      <>Go to <a href="https://id.atlassian.com/manage/api-tokens" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline inline-flex items-center gap-1">Atlassian API Tokens <ExternalLink className="h-3 w-3" /></a> and create a token.</>,
      'In ML-Auditor, click Add Key → Jira, enter the site URL, your Atlassian email, and the API token.',
      'Click test to confirm the connection, then select a project to sync issues into RAG.',
    ],
    links: [
      { label: 'Atlassian API Tokens', url: 'https://id.atlassian.com/manage/api-tokens' },
      { label: 'Jira REST API Docs', url: 'https://developer.atlassian.com/cloud/jira/platform/rest/v3/' },
    ],
  },
  {
    key: 'email',
    title: 'Email (Any Provider via IMAP/SMTP)',
    steps: [
      'Open the Email card and choose your provider (Gmail, Outlook, Yahoo, or Custom).',
      'For Gmail: generate an App Password at myaccount.google.com/apppasswords (not your normal password).',
      'For Outlook: use your password or an app password if 2FA is enabled.',
      'Enter the password and click Connect. ML-Auditor will log in live to verify the credentials.',
      'Once connected, click Sync Inbox to index emails into clusters.',
    ],
    links: [
      { label: 'Google App Passwords', url: 'https://myaccount.google.com/apppasswords' },
    ],
  },
  {
    key: 'openai',
    title: 'OpenAI / Anthropic / NVIDIA NIM',
    steps: [
      'Get an API key from your provider dashboard.',
      'In ML-Auditor, click Add Key, pick the provider, paste the key, and save.',
      'Use the Test button to verify the key is active and has quota.',
      'These keys are also used by the LLM configuration panel for chat responses.',
    ],
    links: [
      { label: 'OpenAI Platform', url: 'https://platform.openai.com/' },
      { label: 'Anthropic Console', url: 'https://console.anthropic.com/' },
      { label: 'NVIDIA NIM', url: 'https://build.nvidia.com/' },
    ],
  },
];

export function HowItWorks() {
  const [open, setOpen] = useState<string[]>(['plaid']);

  const toggle = (key: string) => {
    setOpen((prev) => (prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]));
  };

  return (
    <Card className="panel-gilded">
      <CardHeader className="flex flex-row items-center gap-3 pb-2">
        <div className="text-2xl"><HelpCircle className="h-6 w-6" /></div>
        <div>
          <CardTitle className="text-base font-display tracking-wide">How It Works</CardTitle>
          <p className="text-xs text-muted-foreground">Step-by-step guides for connecting every API integration.</p>
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        {GUIDES.map((guide) => {
          const isOpen = open.includes(guide.key);
          return (
            <div key={guide.key} className="border rounded">
              <Button
                variant="ghost"
                className="w-full justify-between h-auto py-3 px-4 font-medium"
                onClick={() => toggle(guide.key)}
              >
                <span className="text-sm">{guide.title}</span>
                {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </Button>
              {isOpen && (
                <div className="px-4 pb-4 space-y-3">
                  <ol className="list-decimal list-inside space-y-1.5 text-sm text-muted-foreground">
                    {guide.steps.map((step, idx) => (
                      <li key={idx}>{step}</li>
                    ))}
                  </ol>
                  {guide.links && (
                    <div className="flex flex-wrap gap-2 pt-1">
                      {guide.links.map((link) => (
                        <a
                          key={link.url}
                          href={link.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs inline-flex items-center gap-1 text-blue-500 hover:underline"
                        >
                          {link.label} <ExternalLink className="h-3 w-3" />
                        </a>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
