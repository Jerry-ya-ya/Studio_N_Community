import { FullConfig, request } from '@playwright/test';
import dotenv from 'dotenv';

dotenv.config();

async function globalSetup(config: FullConfig) {
  const apiContext = await request.newContext();

  await apiContext.post('http://localhost:5000/api/test/clear-db');

  const username = process.env['TEST_USERNAME'];
  const password = process.env['TEST_PASSWORD'];
  const email = process.env['TEST_EMAIL'];

  if (!username || !email || !password) {
    throw new Error('❌ TEST_USERNAME、TEST_EMAIL 或 TEST_PASSWORD 未設定於 .env');
  }

  console.log('🚀 註冊...');
  const response = await apiContext.post('http://localhost:5000/api/register', {
    data: { username, password, email },
  });

  if (!response.ok()) {
    const body = await response.text();
    throw new Error(`❌ 註冊失敗：${body}`);
  }

  await apiContext.post('http://localhost:5000/api/test/verify-user', { data: { email } });

  console.log('✅ 已驗證 Email');

  console.log('🚀 登入...');
  const loginResponse = await apiContext.post('http://localhost:5000/api/login', {
    data: { username, password },
  });

  if (!loginResponse.ok()) {
    const body = await loginResponse.text();
    throw new Error(`❌ 登入失敗：${body}`);
  }

  // Persist only the HttpOnly refresh and CSRF cookies. The application obtains
  // an access token into memory on its first authenticated API request.
  await apiContext.storageState({ path: './test/storageState.json' });
  await apiContext.dispose();

  console.log('✅ 已寫入 storageState.json');
}

export default globalSetup;
