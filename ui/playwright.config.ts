import { defineConfig, devices } from '@playwright/test';

// Playwright pins each release to one Chromium build and refuses to launch
// any other, so a machine with a different build installed (a cloud
// container, a CI image with a system Chromium) cannot run the suite at
// all. Setting PLAYWRIGHT_CHROMIUM_EXECUTABLE to a Chromium binary makes
// every project launch that binary instead; leave it unset to use the
// build `npx playwright install chromium` fetched.
const executablePath = process.env['PLAYWRIGHT_CHROMIUM_EXECUTABLE'];

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [['html', { open: 'never' }], ['list']],
  use: {
    baseURL: 'http://127.0.0.1:4200',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    ...(executablePath ? { launchOptions: { executablePath } } : {}),
  },
  webServer: {
    command: 'npm start -- --host 127.0.0.1 --port 4200',
    url: 'http://127.0.0.1:4200',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
  projects: [
    {
      name: 'mobile-chrome-360',
      use: {
        ...devices['Pixel 5'],
        viewport: { width: 360, height: 800 },
      },
    },
    {
      name: 'mobile-safari-390',
      use: {
        ...devices['iPhone 12'],
        viewport: { width: 390, height: 844 },
      },
    },
    {
      name: 'tablet-portrait',
      use: {
        ...devices['iPad (gen 7)'],
        viewport: { width: 768, height: 1024 },
      },
    },
    {
      name: 'desktop-chrome',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1280, height: 900 },
      },
    },
  ],
});
