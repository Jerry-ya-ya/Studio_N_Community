import { test, expect } from '@playwright/test';

test('test', async ({ page }) => {
  await page.goto('/member');
  await expect(page.getByText('教授').first()).toBeVisible();
  await expect(page.getByText('團長').first()).toBeVisible();
  await expect(page.getByText('副團長').first()).toBeVisible();
  await expect(page.getByText('資安組').first()).toBeVisible();
  await expect(page.getByText('計算機結構組').first()).toBeVisible();
  await expect(page.getByText('教學組').first()).toBeVisible();
  await expect(page.getByText('UI,UX設計').first()).toBeVisible();
  await expect(page.getByText('外援組').first()).toBeVisible();

  await expect(page.getByRole('heading', { name: '第一屆' })).toBeVisible();
  await expect(page.getByText('俞贊城')).toBeVisible();
  await expect(page.getByText('潘俊杰')).toBeVisible();
  await expect(page.getByText('簡偉恆')).toBeVisible();
  await expect(page.getByText('盧詠涵', { exact: true })).toBeVisible();
  await expect(page.getByText('蕭士壕')).toBeVisible();
  await expect(page.getByText('盧詠涵.')).toBeVisible();
  await expect(page.getByText('趙仲德')).toBeVisible();
  await expect(page.getByText('李欣翰')).toBeVisible();
  await expect(page.getByText('許順傑(程式)')).toBeVisible();
  await expect(page.getByText('盧詠涵(數學)')).toBeVisible();
  await expect(page.getByText('鄭兆崴')).toBeVisible();
  await expect(page.getByText('簡語辰')).toBeVisible();
  
  await expect(page.getByRole('heading', { name: '第二屆' })).toBeVisible();
});