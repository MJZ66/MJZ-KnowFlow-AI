import { defineConfig } from '@playwright/test';

/** Matches vite.config.ts server.port when PLAYWRIGHT_BASE_URL is unset. */
const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000';

export default defineConfig({
  testDir: './e2e',
  timeout: 180000,
  use: {
    baseURL,
    trace: 'on-first-retry',
    viewport: { width: 1280, height: 720 },
  },
  webServer: {
    command: 'npm run dev -- --host 0.0.0.0',
    url: baseURL,
    reuseExistingServer: true,
    timeout: 120000,
  },
});
