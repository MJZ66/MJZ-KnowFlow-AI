import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import type { APIRequestContext, Page } from '@playwright/test';
import { expect } from '@playwright/test';

export const API_BASE = process.env.VITE_API_BASE_URL || 'http://localhost:8000';

/** Align with backend scripts/e2e_acceptance.py */
export const STANDARD_DOC = `KnowFlow AI 的后端使用 FastAPI。
数据库使用 PostgreSQL。
缓存系统使用 Redis。
向量数据库使用 ChromaDB。
系统支持文档上传、文本切片、向量检索和 RAG 问答。

cd E:/AI知识平台/knowflow-ai
docker compose up -d
Get-Process | Where-Object { $_.Name -eq "node" }
`;

export const NOISE_PATTERNS = [/cd\s/i, /docker\s+compose/i, /powershell/i, /get-process/i];

/** Valid 1x1 PNG */
export const MINI_PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
  'base64',
);

/** Minimal valid xlsx fixture */
const _fixturesDir = join(dirname(fileURLToPath(import.meta.url)), 'fixtures');
export const MINI_XLSX = readFileSync(join(_fixturesDir, 'sample.xlsx'));

export interface RegisteredUser {
  email: string;
  password: string;
  username: string;
  token: string;
  suffix: string;
}

export async function registerAndLogin(page: Page, prefix = 'pw'): Promise<RegisteredUser> {
  const suffix = `${prefix}_${Date.now().toString(36)}`;
  const email = `${suffix}@example.com`;
  const password = 'TestPass123!';
  const username = suffix;

  await page.goto('/register');
  await page.getByPlaceholder(/邮箱|email/i).fill(email);
  await page.getByPlaceholder(/用户名|username/i).fill(username);
  await page.getByPlaceholder(/密码|password/i).first().fill(password);
  await page.getByRole('button', { name: /注册|sign up|register/i }).click();
  await expect(page).toHaveURL(/dashboard/, { timeout: 20000 });

  const token = await page.evaluate(() => localStorage.getItem('access_token'));
  expect(token).toBeTruthy();

  return { email, password, username, token: token!, suffix };
}

export async function createKnowledgeBase(page: Page, name: string): Promise<string> {
  await page.getByTestId('kb-create-open').click();
  await page.getByTestId('kb-create-name').fill(name);
  await page.getByTestId('kb-create-submit').click();
  await page.waitForURL(/\/kbs\/\d+/);
  const kbId = page.url().match(/\/kbs\/(\d+)/)?.[1];
  expect(kbId).toBeTruthy();
  return kbId!;
}

export async function uploadStandardDocument(
  request: APIRequestContext,
  token: string,
  kbId: string,
): Promise<{ id: number }> {
  const uploadRes = await request.post(`${API_BASE}/api/kbs/${kbId}/documents/upload`, {
    headers: { Authorization: `Bearer ${token}` },
    multipart: {
      file: {
        name: 'pw-test.txt',
        mimeType: 'text/plain',
        buffer: Buffer.from(STANDARD_DOC, 'utf-8'),
      },
    },
  });
  expect(uploadRes.ok()).toBeTruthy();
  return uploadRes.json();
}

export async function pollDocumentCompleted(
  request: APIRequestContext,
  token: string,
  docId: number,
  maxAttempts = 60,
): Promise<void> {
  for (let i = 0; i < maxAttempts; i++) {
    const st = await request.get(`${API_BASE}/api/documents/${docId}/status`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const body = await st.json();
    if (body.status === 'completed') return;
    if (body.status === 'failed') throw new Error(`Document failed: ${body.error_message}`);
    await new Promise((r) => setTimeout(r, 2000));
  }
  throw new Error('Document did not reach COMPLETED within timeout');
}
