import { test, expect } from '@playwright/test';

test('test', async ({ page }) => {
  await page.goto('/register');
  await expect(page.getByRole('heading', { name: '註冊帳號' })).toBeVisible();

  await expect(page.getByText('帳號：')).toBeVisible();
  await expect(page.getByText('密碼：')).toBeVisible();
  await expect(page.getByText('郵箱：')).toBeVisible();
  await expect(page.locator('div').filter({ hasText: /^帳號：$/ }).getByRole('textbox')).toBeVisible();
  await expect(page.locator('input[type="password"]')).toBeVisible();
  await expect(page.locator('div').filter({ hasText: /^郵箱：$/ }).getByRole('textbox')).toBeVisible();
  await expect(page.getByRole('button', { name: '註冊' })).toBeVisible();

  await expect(page.getByText('沒收到驗證信？')).toBeVisible();
  await expect(page.getByRole('link', { name: '重新寄送' })).toBeVisible();
  await page.getByRole('link', { name: '重新寄送' }).click();
  
  await expect(page.getByRole('heading', { name: '重新寄送驗證信' })).toBeVisible();
  await expect(page.getByRole('textbox', { name: '請輸入註冊時的 Email' })).toBeVisible();
  await expect(page.getByRole('button', { name: '重新寄送' })).toBeVisible();
});