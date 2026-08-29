/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Static export is required so Tauri can bundle the built frontend.
  // In dev mode Tauri proxies the Next.js dev server, so this does not affect development.
  output: process.env.TAURI_BUILD === '1' ? 'export' : undefined,
  distDir: process.env.TAURI_BUILD === '1' ? 'dist' : '.next',
  images: {
    unoptimized: process.env.TAURI_BUILD === '1',
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
      },
    ],
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000',
    NEXT_PUBLIC_DESKTOP_MODE: process.env.NEXT_PUBLIC_DESKTOP_MODE || 'false',
  },
};

module.exports = nextConfig;
