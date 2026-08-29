import React from 'react';
import { Inter, Cormorant_Garamond, Cinzel } from 'next/font/google';
import Script from 'next/script';
import { Providers } from '@/components/providers';
import '@/styles/globals.css';

const inter = Inter({ subsets: ['latin'], variable: '--font-body' });
const cormorant = Cormorant_Garamond({
  subsets: ['latin'],
  weight: ['500', '600', '700'],
  variable: '--font-display',
});
const cinzel = Cinzel({
  subsets: ['latin'],
  weight: ['500', '600', '700', '800'],
  variable: '--font-brand',
});

export const metadata = {
  title: {
    default: 'Argus',
    template: '%s | Argus',
  },
  description: 'Argus ml-auditor — your AI-powered command center for finance, operations, and intelligence.',
};

const themeInitScript = `try{var t=localStorage.getItem('ml-auditor-theme');if(t==='dark'||t==='light'){document.documentElement.classList.toggle('dark',t==='dark');document.documentElement.style.colorScheme=t;}else{document.documentElement.classList.add('dark');document.documentElement.style.colorScheme='dark';}}catch(e){document.documentElement.classList.add('dark');document.documentElement.style.colorScheme='dark';}`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <Script
          id="theme-init"
          strategy="beforeInteractive"
          dangerouslySetInnerHTML={{ __html: themeInitScript }}
        />
        <link rel="icon" href="/foujalab.png" type="image/png" />
        <link rel="apple-touch-icon" href="/foujalab.png" />
        <meta name="theme-color" content="#0a0a0a" />
      </head>
      <body
        className={`${inter.variable} ${cormorant.variable} ${cinzel.variable} font-body`}
      >
        <Script
          src="https://cdn.plaid.com/link/v2/stable/link-initialize.js"
          strategy="lazyOnload"
        />
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
