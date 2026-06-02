import { test, expect } from '@playwright/test';

const API_BASE = process.env.VITE_API_BASE_URL || 'http://localhost:8000';

/** Align with backend scripts/e2e_acceptance.py — includes CLI noise lines for reference filter. */
const STANDARD_DOC = `KnowFlow AI 的后端使用 FastAPI。
数据库使用 PostgreSQL。
缓存系统使用 Redis。
向量数据库使用 ChromaDB。
系统支持文档上传、文本切片、向量检索和 RAG 问答。

cd E:/AI知识平台/knowflow-ai
docker compose up -d
Get-Process | Where-Object { $_.Name -eq "node" }
`;

const NOISE_PATTERNS = [/cd\s/i, /docker\s+compose/i, /powershell/i, /get-process/i];

test.describe('KnowFlow E2E', () => {
  test('register → KB → upload → RAG → reference preview → i18n persistence', async ({ page }) => {
    const suffix = Date.now().toString(36);
    const email = `pw_${suffix}@example.com`;
    const password = 'TestPass123!';
    const username = `pw_${suffix}`;

    await page.goto('/register');

    await page.getByPlaceholder(/邮箱|email/i).fill(email);
    await page.getByPlaceholder(/用户名|username/i).fill(username);
    await page.getByPlaceholder(/密码|password/i).first().fill(password);
    await page.getByRole('button', { name: /注册|sign up|register/i }).click();

    await expect(page).toHaveURL(/dashboard/, { timeout: 20000 });

    await page.getByTestId('kb-create-open').click();
    await page.getByTestId('kb-create-name').fill(`PW KB ${suffix}`);
    await page.getByTestId('kb-create-submit').click();

    await page.waitForURL(/\/kbs\/\d+/);
    const kbUrl = page.url();
    const kbId = kbUrl.match(/\/kbs\/(\d+)/)?.[1];
    expect(kbId).toBeTruthy();

    const token = await page.evaluate(() => localStorage.getItem('access_token'));
    expect(token).toBeTruthy();

    const uploadRes = await page.request.post(`${API_BASE}/api/kbs/${kbId}/documents/upload`, {
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
    const doc = await uploadRes.json();

    let completed = false;
    for (let i = 0; i < 60; i++) {
      const st = await page.request.get(`${API_BASE}/api/documents/${doc.id}/status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const body = await st.json();
      if (body.status === 'completed') {
        completed = true;
        break;
      }
      if (body.status === 'failed') throw new Error(`Document failed: ${body.error_message}`);
      await page.waitForTimeout(2000);
    }
    if (!completed) throw new Error('Document did not reach COMPLETED within timeout');

    await page.getByTestId('chat-new-session').first().click();

    const input = page.getByPlaceholder(/问题|question/i);
    await input.fill('KnowFlow AI 的后端使用了哪些组件？');
    await page.getByRole('button', { name: /发送|send/i }).click();

    await expect(page.locator('.prose-sm', { hasText: /FastAPI/i })).toBeVisible({ timeout: 120000 });
    await expect(page.getByText(/PostgreSQL/i).first()).toBeVisible();
    await expect(page.getByText(/Redis/i).first()).toBeVisible();
    await expect(page.getByText(/ChromaDB/i).first()).toBeVisible();

    const refCard = page.getByTestId('reference-card-0');
    await expect(refCard).toBeVisible({ timeout: 30000 });
    const refText = await refCard.innerText();
    for (const pattern of NOISE_PATTERNS) {
      expect(refText).not.toMatch(pattern);
    }
    expect(refText).toMatch(/FastAPI|PostgreSQL|Redis|ChromaDB|知识库|文档/);

    await refCard.click();
    await expect(page.getByTestId('document-preview-panel')).toBeVisible();
    await expect(page.locator('[data-testid^="preview-chunk-"]').first()).toBeVisible();

    await page.getByTestId('preview-close').click();

    await page.getByTestId('kb-detail-lang-switcher').click();
    await expect
      .poll(async () => page.evaluate(() => localStorage.getItem('knowflow_lang')))
      .toBe('en-US');

    await page.reload();
    await expect(page.getByTestId('kb-detail-lang-switcher')).toContainText('中文');
    await expect(page.getByRole('heading', { name: /^Upload Document$/i })).toBeVisible();
  });

  test('dashboard KB pagination controls', async ({ page }) => {
    const suffix = `pg_${Date.now().toString(36)}`;
    const email = `${suffix}@example.com`;
    await page.goto('/register');
    await page.getByPlaceholder(/邮箱|email/i).fill(email);
    await page.getByPlaceholder(/用户名|username/i).fill(suffix);
    await page.getByPlaceholder(/密码|password/i).first().fill('TestPass123!');
    await page.getByRole('button', { name: /注册|sign up/i }).click();
    await expect(page).toHaveURL(/dashboard/, { timeout: 20000 });

    const token = await page.evaluate(() => localStorage.getItem('access_token'));
    for (let i = 0; i < 3; i++) {
      await page.request.post(`${API_BASE}/api/kbs`, {
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        data: { name: `Pag KB ${i}`, description: '', visibility: 'private' },
      });
    }
    await page.goto('/dashboard');
    await expect(page.getByTestId('kb-pagination')).toBeVisible();
    await expect(page.getByTestId('kb-page-size')).toBeVisible();
    await expect(page.getByTestId('kb-page-prev')).toBeDisabled();
  });
});
