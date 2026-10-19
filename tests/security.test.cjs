const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const assert = require('node:assert/strict');

(async () => {
  const browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL || 'msedge' });
  try {
    for (const entry of ['index.html', 'dashboard.html']) {
      const page = await browser.newPage();
      await page.route('**/*', route => route.request().url() === 'http://localhost/' + entry
        ? route.fulfill({ contentType: 'text/html', body: fs.readFileSync(path.join(__dirname, '..', entry), 'utf8') })
        : route.abort());
      await page.goto('http://localhost/' + entry);
      const result = await page.evaluate(async () => {
        window.__xss = 0;
        const attack = '<img src=x onerror="window.__xss=1">&quot;';
        renderExplorerList({ path: 'C:/', items: [{ name: attack, type: 'file', size: 1 }] });
        const row = document.querySelector('#explorer-list [data-name]');
        const filename = row.dataset.name;
        const explorerImages = document.querySelectorAll('#explorer-list img').length;
        renderWindowsList([{ exe: attack, title: attack, pid: '1" onmouseover="window.__xss=1', hwnd: attack }]);
        const windowImages = document.querySelectorAll('#windows-list img').length;
        showModal('test', attack, () => {});
        const modalImages = document.querySelectorAll('#modal-msg img').length;
        window.dispatchEvent(new ErrorEvent('error', { message: attack, filename: attack, lineno: 1 }));
        window.dispatchEvent(new PromiseRejectionEvent('unhandledrejection', { promise: Promise.resolve(), reason: attack }));
        await new Promise(resolve => setTimeout(resolve, 100));
        return { filename, explorerImages, windowImages, modalImages, xss: window.__xss,
          errorImages: document.querySelectorAll('#global-error-display img').length };
      });
      assert.equal(result.filename, '<img src=x onerror="window.__xss=1">&quot;');
      assert.equal(result.explorerImages, 0);
      assert.equal(result.windowImages, 0);
      assert.equal(result.modalImages, 0);
      assert.equal(result.errorImages, 0);
      assert.equal(result.xss, 0);
      await page.close();
    }
    console.log('Security browser tests passed for both entry points: filenames, window metadata, attributes, error events.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
