import { test, expect, request, chromium } from '@playwright/test';

test('page', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('link', { name: 'Profile' }).click();
  await page.getByRole('link', { name: 'Login' }).click();
  await page.getByRole('textbox', { name: '帳號' }).click();
  await page.getByRole('textbox', { name: '帳號' }).fill('Test');
  await page.getByRole('textbox', { name: '帳號' }).press('Tab');
  await page.getByRole('textbox', { name: '密碼' }).fill('123');
  await page.getByRole('button', { name: '登入' }).click();
  await page.getByRole('link', { name: 'Profile' }).click();
});