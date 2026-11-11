// test/home.spec.ts
import { test, expect } from '@playwright/test';

test('test', async ({ page }) => {
  await page.goto('/home');
  await expect(page.getByRole('heading', { name: '蘇建華資訊數學人才培育團' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Let us make the Department of Mathematics great again.' })).toBeVisible();
  
  await expect(page.getByRole('heading', { name: '團隊願景' })).toBeVisible();
  await expect(page.getByText('團隊的目標是培養數學結合資訊的專業人才')).toBeVisible();
  await expect(page.getByText('結合數學理論與程式設計')).toBeVisible();
  await expect(page.getByText('提升成員的技術能力')).toBeVisible();
  await expect(page.getByText('並為未來的學術研究與產業應用鋪路')).toBeVisible();

  await expect(page.getByRole('heading', { name: '招募要求' })).toBeVisible();
  await expect(page.getByText('希望有點程式設計基礎')).toBeVisible();
  await expect(page.getByText('並且要能溝通')).toBeVisible();
  await expect(page.getByText('有上進心')).toBeVisible();
  await expect(page.getByText('性別不拘(學妹為佳)')).toBeVisible();

  await expect(page.getByRole('heading', { name: '團隊目標' })).toBeVisible();
  await expect(page.getByText('充實計算機與數學基礎')).toBeVisible();
  await expect(page.getByText('掌握人工智慧與系統開發相關技術')).toBeVisible();
  await expect(page.getByText('透過實戰與專題提升應用能力')).toBeVisible();

  await expect(page.getByRole('heading', { name: '學習路線', exact: true })).toBeVisible();
  await expect(page.getByText('網頁基礎（前端與後端）')).toBeVisible();
  await expect(page.getByText('組合語言(Assembly)')).toBeVisible();
  await expect(page.getByText('C 語言', { exact: true })).toBeVisible();
  await expect(page.getByText('C 語言與組合語言的連結')).toBeVisible();
  await expect(page.getByText('腳本語言 (Bash)')).toBeVisible();
  
  await expect(page.getByRole('heading', { name: '進階學習路線' })).toBeVisible();
  await expect(page.getByText('Angular(前端)')).toBeVisible();
  await expect(page.getByText('資料結構與演算法')).toBeVisible();
  await expect(page.getByText('機器學習與人工智慧')).toBeVisible();
  await expect(page.getByText('系統開發與安全')).toBeVisible();
  await expect(page.getByText('數據分析與應用')).toBeVisible();
});