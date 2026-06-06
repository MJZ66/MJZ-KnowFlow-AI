import { test, expect } from '@playwright/test';
import {
  API_BASE,
  createKnowledgeBase,
  pollDocumentCompleted,
  registerAndLogin,
  MINI_PNG,
  MINI_XLSX,
  STANDARD_DOC,
} from './helpers';

test.describe('Multi-format document preview', () => {
  test('text, image, and spreadsheet previews open in panel', async ({ page }) => {
    const user = await registerAndLogin(page, 'prev');
    const kbId = await createKnowledgeBase(page, `Preview KB ${user.suffix}`);

    const txtRes = await page.request.post(`${API_BASE}/api/kbs/${kbId}/documents/upload`, {
      headers: { Authorization: `Bearer ${user.token}` },
      multipart: {
        file: { name: 'preview.txt', mimeType: 'text/plain', buffer: Buffer.from(STANDARD_DOC, 'utf-8') },
      },
    });
    const pngRes = await page.request.post(`${API_BASE}/api/kbs/${kbId}/documents/upload`, {
      headers: { Authorization: `Bearer ${user.token}` },
      multipart: {
        file: { name: 'preview.png', mimeType: 'image/png', buffer: MINI_PNG },
      },
    });
    const xlsxRes = await page.request.post(`${API_BASE}/api/kbs/${kbId}/documents/upload`, {
      headers: { Authorization: `Bearer ${user.token}` },
      multipart: {
        file: {
          name: 'preview.xlsx',
          mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
          buffer: MINI_XLSX,
        },
      },
    });

    const txtDoc = await txtRes.json();
    const pngDoc = await pngRes.json();
    const xlsxDoc = await xlsxRes.json();

    await pollDocumentCompleted(page.request, user.token, txtDoc.id);
    await pollDocumentCompleted(page.request, user.token, pngDoc.id);
    await pollDocumentCompleted(page.request, user.token, xlsxDoc.id);

    await page.reload();

    await page.getByTestId(`doc-preview-${pngDoc.id}`).click();
    await expect(page.getByTestId('document-preview-panel')).toBeVisible();
    await expect(page.getByTestId('preview-image')).toBeVisible({ timeout: 15000 });
    await page.getByTestId('preview-close').click();
    await expect(page.getByTestId('document-preview-panel')).not.toBeVisible();

    await page.getByTestId(`doc-preview-${txtDoc.id}`).click();
    await expect(page.getByTestId('document-preview-panel')).toBeVisible();
    await expect(page.locator('[data-testid^="preview-chunk-"]').first()).toBeVisible();
    await page.getByTestId('preview-close').click();

    await page.getByTestId(`doc-preview-${xlsxDoc.id}`).click();
    await expect(page.getByTestId('document-preview-panel')).toBeVisible();
    await expect(page.locator('[data-testid^="preview-chunk-"]').first()).toBeVisible();
    await page.getByTestId('preview-close').click();
  });
});

test.describe('Setup guide', () => {
  test('setup page shows system status', async ({ page }) => {
    await registerAndLogin(page, 'setup');
    await page.getByTestId('nav-setup').click();
    await expect(page).toHaveURL(/\/setup/);
    await expect(page.getByTestId('setup-overall-status')).toBeVisible({ timeout: 15000 });
    await page.getByTestId('setup-go-dashboard').click();
    await expect(page).toHaveURL(/\/dashboard/);
  });
});
