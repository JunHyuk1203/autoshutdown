// Run with Node and Playwright available through NODE_PATH. All services are mocked.
const { chromium } = require('playwright');
const fs = require('fs');
const assert = require('node:assert/strict');
const path = require('path');

(async () => {
  const browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL || 'msedge' });
  try {
    for (const entry of ['index.html', 'dashboard.html']) {
      const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
      const page = await context.newPage();
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.route('**/*', route => {
        if (route.request().url() === 'http://localhost/' + entry) {
          return route.fulfill({ contentType: 'text/html', body: fs.readFileSync(path.join(__dirname, '..', entry), 'utf8') });
        }
        return route.abort();
      });
      await page.goto('http://localhost/' + entry);
      await page.locator('#boot-retry').waitFor({ state: 'visible' });
      assert(await page.locator('#auth-view').isVisible(), 'Blocked SDK still shows login');
      await page.locator('#auth-submit-btn').click();
      assert.match(await page.locator('#auth-error-msg').textContent(), /연결/);
      await page.evaluate(() => {
        window.firebase = {
          apps: [], initializeApp() {},
          auth: () => ({ currentUser: null, onAuthStateChanged: callback => callback(null) }),
          database: () => ({ ref: () => ({ off() {} }) })
        };
      });
      await page.locator('#boot-retry').click();
      await page.evaluate(() => {
        pcs = {
          'PC-01': { hostname: '교실 PC 01', user: '학생', ip: '192.168.0.21', version: '2.0', status: 'online', last_seen_ts: Date.now(), next_event: '오늘 16:30 [시스템 종료]' },
          'PC-02': { hostname: '<img src=x onerror=alert(1)>', status: 'offline', last_seen_ts: Date.now() - 3600000 }
        };
        setAccessGranted(true);
        _showScreen('dashboard-view');
        renderPCGrid(Date.now()); updateStatistics(Date.now());
      });
      assert.equal(await page.locator('#stat-online').textContent(), '1');
      assert.equal(await page.locator('.pc-name img').count(), 0, 'Device names are escaped');
      assert.equal(await page.locator('#pc-card-PC-02 button:disabled').count(), 6);
      await page.locator('#pc-card-PC-01 .pc-checkbox').check();
      await page.evaluate(() => renderPCGrid(Date.now()));
      assert(await page.locator('#pc-card-PC-01 .pc-checkbox').isChecked());
      await page.getByRole('button', { name: '전체 종료', exact: true }).click();
      assert(await page.locator('#confirm-modal').isVisible(), 'Global control is bound');
      await page.locator('#windows-cancel-btn').click();
      await page.evaluate(() => {
        pcs['PC-01'].last_seen_ts = Date.now() - 31000;
        renderPCGrid(Date.now()); updateStatistics(Date.now());
      });
      assert.equal(await page.locator('#stat-online').textContent(), '0', 'Stale heartbeat expires');
      await page.evaluate(() => { pcs['PC-01'].last_seen_ts = Date.now(); renderPCGrid(Date.now()); updateStatistics(Date.now()); });
      await page.evaluate(() => {
        window.testCommands = [];
        window.savedCommandWriter = writeCommandToDB;
        writeCommandToDB = async (pc, action) => { window.testCommands.push(action); return { success: true }; };
        window.savedDatabase = firebase.database;
        firebase.database = () => ({ ref: () => ({ on: (_event, callback) => callback, off() {} }) });
      });
      await page.locator('#pc-card-PC-01 [data-action="startWebRTC"]').click();
      await page.locator('#live-screen-modal.show').waitFor();
      await page.locator('#live-screen-modal [data-action="closeLiveScreen"]').click();
      assert.deepEqual(await page.evaluate(() => testCommands), ['stream_start', 'stream_stop']);
      await page.evaluate(() => { writeCommandToDB = savedCommandWriter; firebase.database = savedDatabase; });
      await page.evaluate(() => {
        pcs['PC-02'].hostname = '교실 PC 02'; renderPCGrid(Date.now());
        document.getElementById('label-connected-db').textContent = '로컬 미리보기 · 모의 데이터';
      });
      await page.screenshot({ path: path.join(__dirname, '..', 'dashboard-desktop.png'), fullPage: true });
      for (const width of [360, 390, 768]) {
        await page.setViewportSize({ width, height: 844 });
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'No horizontal overflow at ' + width);
      }
      await page.setViewportSize({ width: 390, height: 844 });
      await page.screenshot({ path: path.join(__dirname, '..', 'dashboard-mobile.png'), fullPage: true });
      assert.deepEqual(errors, [], 'No uncaught browser errors');
      console.log(entry + ': SDK failure/retry, metadata safety, selection, controls, status expiry, responsive layout passed');
      await context.close();
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
