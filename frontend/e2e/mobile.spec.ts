import { test, expect } from '@playwright/test';
import {
  NOISE_PATTERNS,
  createKnowledgeBase,
  pollDocumentCompleted,
  registerAndLogin,
  uploadStandardDocument,
} from './helpers';

test.describe('KnowFlow Mobile E2E', () => {
  test('mobile tabs → session sheet → RAG → references sheet', async ({ page }) => {
    const user = await registerAndLogin(page, 'mob');
    await createKnowledgeBase(page, `Mobile KB ${user.suffix}`);

    const kbId = page.url().match(/\/kbs\/(\d+)/)?.[1]!;
    const doc = await uploadStandardDocument(page.request, user.token, kbId);
    await pollDocumentCompleted(page.request, user.token, doc.id);

    await page.goto(page.url());
    await expect(page.getByTestId('mobile-pane-docs')).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId('mobile-pane-chat')).toBeVisible();

    await page.getByTestId('mobile-pane-docs').click();
    await expect(page.getByTestId('doc-search')).toBeVisible();
    await expect(page.getByTestId('file-uploader')).toBeVisible();

    await page.getByTestId('mobile-pane-chat').click();
    await expect(page.getByTestId('mobile-sessions-open')).toBeVisible();
    await expect(page.getByTestId('mobile-refs-open')).toBeVisible();

    await page.getByTestId('mobile-sessions-open').click();
    await expect(page.getByTestId('mobile-session-sheet')).toBeVisible();
    await page.getByTestId('mobile-session-sheet').getByTestId('chat-new-session').click();
    await expect(page.getByTestId('mobile-session-sheet')).not.toBeVisible({ timeout: 10000 });

    const input = page.getByPlaceholder(/问题|question/i);
    await input.fill('KnowFlow AI 的后端使用了哪些组件？');
    await page.getByRole('button', { name: /发送|send/i }).click();

    await expect(page.locator('.prose-sm', { hasText: /FastAPI/i })).toBeVisible({ timeout: 120000 });

    await page.getByTestId('mobile-refs-open').click();
    await expect(page.getByTestId('mobile-refs-sheet')).toBeVisible();

    const refCard = page.getByTestId('mobile-refs-sheet').getByTestId('reference-card-0');
    await expect(refCard).toBeVisible({ timeout: 30000 });
    const refText = await refCard.innerText();
    for (const pattern of NOISE_PATTERNS) {
      expect(refText).not.toMatch(pattern);
    }
    expect(refText).toMatch(/FastAPI|PostgreSQL|Redis|ChromaDB|知识库|文档/);

    await refCard.click();
    await expect(page.getByTestId('document-preview-panel')).toBeVisible();
    await page.getByTestId('preview-close').click();
    await expect(page.getByTestId('document-preview-panel')).not.toBeVisible();
    await expect(page.getByTestId('mobile-refs-open')).toBeVisible();
  });

  test('chat route redirects to KB detail on mobile', async ({ page }) => {
    const user = await registerAndLogin(page, 'mob_redir');
    const kbId = await createKnowledgeBase(page, `Redirect KB ${user.suffix}`);

    await page.goto(`/kbs/${kbId}/chat`);
    await expect(page).toHaveURL(new RegExp(`/kbs/${kbId}$`));
    await expect(page.getByTestId('mobile-pane-chat')).toBeVisible();
  });
});
