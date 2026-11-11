// npx playwright test
// npx playwright test --ui
// npx playwright codegen http://localhost:4200/home
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './test',
  outputDir: './test/test-results/results',
  timeout: 30 * 1000,
  expect: {
    timeout: 5000
  },
  fullyParallel: true,
  retries: 0, // 若想自動重跑失敗測試可設 >0
  workers: 1, // 本地測試設1，CI/CD 可用多核心
  reporter: [['list'], ['html', { outputFolder: './test/test-results/playwright-report' }]],
  globalSetup: './test/global-setup.ts',
  use: {
    baseURL: process.env['E2E_BASE_URL'] || 'http://localhost:4200/',
    trace: 'on-first-retry',
    video: 'retain-on-failure',
    screenshot: 'on',
    viewport: { width: 1920, height: 1080 },
    storageState: './test/storageState.json'
  },
  projects: [
    {
      name: 'Chromium',
      use: { ...devices['Desktop Chrome'] }
    },
    {
      name: 'Firefox',
      use: { ...devices['Desktop Firefox'] }
    },
    {
      name: 'WebKit',
      use: { ...devices['Desktop Safari'] }
    }
  ]
});