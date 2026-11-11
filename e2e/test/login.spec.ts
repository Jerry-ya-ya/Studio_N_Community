import { test, expect } from '@playwright/test';

test('test', async ({ page }) => {
  await page.goto('/login');
  await expect(page.getByRole('img')).toBeVisible();
  await expect(page.getByRole('heading', { name: '登入' })).toBeVisible();
  await expect(page.getByRole('textbox', { name: '帳號' })).toBeVisible();
  await expect(page.getByRole('textbox', { name: '密碼' })).toBeVisible();
  await expect(page.getByRole('checkbox')).toBeVisible();
  await expect(page.getByText('記住密碼')).toBeVisible();
  await expect(page.getByText('忘記密碼?')).toBeVisible();
  await expect(page.getByRole('link', { name: '找回密碼' })).toBeVisible();
  await expect(page.getByRole('button', { name: '登入' })).toBeVisible();
  await expect(page.getByText('沒有帳號?')).toBeVisible();
  await expect(page.getByRole('link', { name: '註冊帳號' })).toBeVisible();

  await page.getByRole('link', { name: '找回密碼' }).click();
  await expect(page).toHaveURL(/\/forgotpassword$/);
  await page.getByRole('link', { name: 'Login' }).click();
  
  await page.getByRole('link', { name: '註冊帳號' }).click();
  await expect(page).toHaveURL(/\/register$/);
  await page.getByRole('link', { name: 'Login' }).click();
  await page.getByRole('checkbox').check();
  await page.getByRole('checkbox').uncheck();
});