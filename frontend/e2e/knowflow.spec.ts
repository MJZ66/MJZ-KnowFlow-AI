import { test, expect } from '@playwright/test';
import {
  NOISE_PATTERNS,
  createKnowledgeBase,
  pollDocumentCompleted,
  registerAndLogin,
  uploadStandardDocument,
} from './helpers';

test.describe('KnowFlow E2E', () => {
  test('register → KB → upload → RAG → reference preview → i18n persistence', async ({ page }) => {
    const user = await registerAndLogin(page, 'pw');
    const kbId = await createKnowledgeBase(page, `PW KB ${user.suffix}`);

    const doc = await uploadStandardDocument(page.request, user.token, kbId);
    await pollDocumentCompleted(page.request, user.token, doc.id);

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
    await expect(page.getByText(/^Upload Document$/i).first()).toBeVisible();
  });

  test('dashboard KB pagination controls', async ({ page }) => {
    const user = await registerAndLogin(page, 'pg');
    for (let i = 0; i < 3; i++) {
      await page.request.post(`${process.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/kbs`, {
        headers: { Authorization: `Bearer ${user.token}`, 'Content-Type': 'application/json' },
        data: { name: `Pag KB ${i}`, description: '', visibility: 'private' },
      });
    }
    await page.goto('/dashboard');
    await expect(page.getByTestId('kb-pagination')).toBeVisible();
    await expect(page.getByTestId('kb-page-size')).toBeVisible();
    await expect(page.getByTestId('kb-page-prev')).toBeDisabled();
  });
});
