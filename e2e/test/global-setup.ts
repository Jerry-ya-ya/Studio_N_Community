import { request } from '@playwright/test';
import dotenv from 'dotenv';

dotenv.config({ path: ['.env', '../.env'] });

async function globalSetup() {
  const username = process.env['TEST_USERNAME'];
  const password = process.env['TEST_PASSWORD'];
  const email = process.env['TEST_EMAIL'];
  const token = process.env['E2E_TEST_TOKEN'];

  if (!username || !email || !password) {
    throw new Error('請設定 TEST_USERNAME、TEST_EMAIL 與 TEST_PASSWORD');
  }
  if (!token || token.length < 32) {
    throw new Error('請設定至少 32 字元的 E2E_TEST_TOKEN');
  }

  const apiContext = await request.newContext({
    baseURL: process.env['E2E_BASE_URL'] || 'http://localhost:5000',
  });
  const testApiOptions = {
    headers: { 'X-E2E-Test-Token': token },
    maxRedirects: 0,
  };

  try {
    const reset = await apiContext.post('/api/test/clear-db', testApiOptions);
    if (!reset.ok()) {
      throw new Error(`清除測試資料失敗（HTTP ${reset.status()}）`);
    }

    const response = await apiContext.post('/api/register', {
      data: { username, password, email },
    });
    if (!response.ok()) {
      throw new Error(`❌ 註冊失敗：${await response.text()}`);
    }

    const verified = await apiContext.post('/api/test/verify-user', {
      ...testApiOptions,
      data: { email },
    });
    if (!verified.ok()) {
      throw new Error(`驗證測試帳號失敗（HTTP ${verified.status()}）`);
    }

    const login = await apiContext.post('/api/login', {
      data: { username, password },
    });
    if (!login.ok()) {
      throw new Error(`❌ 登入失敗：${await login.text()}`);
    }

    // Persist only the HttpOnly refresh and CSRF cookies. The application obtains
    // an access token into memory on its first authenticated API request.
    await apiContext.storageState({ path: './test/storageState.json' });
  } finally {
    await apiContext.dispose();
  }

  console.log('✅ 已寫入 storageState.json');
}

export default globalSetup;
