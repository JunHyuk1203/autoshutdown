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
        const auth = {
          currentUser: null, setPersistence: async () => {},
          onAuthStateChanged(callback) { queueMicrotask(() => callback(null)); return () => {}; },
          onIdTokenChanged() { return () => {}; }
        };
        function getAuth() { return auth; }
        getAuth.Auth = { Persistence: { LOCAL: 'local', SESSION: 'session', NONE: 'none' } };
        window.firebase = {
          apps: [], initializeApp() { this.apps.push({}); }, auth: getAuth,
          database: () => ({ goOnline() {}, ref: () => ({ off() {} }) })
        };
      });
      await page.locator('#boot-retry').click();
      await page.waitForFunction(() => firebase.apps.length === 1);
      await page.evaluate(() => _authReady);
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
      await page.locator('#pc-card-PC-01 [data-action="openConfigModal"]').click();
      assert(await page.locator('#config-modal').isVisible());
      await page.locator('#config-cancel-btn').click();
      await page.locator('[data-device-filter="online"]').click();
      assert.equal(await page.locator('.pc-card:visible').count(), 1);
      await page.locator('[data-device-filter="all"]').click();
      await page.getByRole('searchbox', { name: '기기 검색' }).fill('192.168.0.21');
      assert.equal(await page.locator('.pc-card:visible').count(), 1);
      await page.getByRole('searchbox', { name: '기기 검색' }).fill('no-such-device');
      assert(await page.locator('#device-filter-empty').isVisible());
      await page.getByRole('searchbox', { name: '기기 검색' }).fill('');
      await page.locator('#pc-card-PC-01 .pc-checkbox').check();
      await page.evaluate(() => renderPCGrid(Date.now()));
      assert(await page.locator('#pc-card-PC-01 .pc-checkbox').isChecked());
      assert.equal(await page.locator('#selected-count').textContent(), '1대 선택');
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
        pcs = {};
        for (let i = 1; i <= 30; i++) {
          const id = 'CLASS-' + String(i).padStart(2, '0');
          pcs[id] = { hostname: '컴퓨터실 ' + String(i).padStart(2, '0'), user: 'Student-' + i, ip: '192.168.0.' + (20 + i), version: '1.1.205', status: i % 7 === 0 ? 'offline' : 'online', last_seen_ts: Date.now() - (i % 7 === 0 ? 3600000 : 0), next_event: i % 3 === 0 ? '오늘 16:30 [시스템 종료]' : '없음' };
        }
        selectedPcs.clear(); renderPCGrid(Date.now()); updateStatistics(Date.now());
        document.getElementById('label-connected-db').textContent = '로컬 미리보기 · 모의 데이터';
        document.getElementById('session-status').textContent = '로그인 유지 중';
      });
      const density = await page.evaluate(() => {
        const cards = [...document.querySelectorAll('.pc-card')];
        return { columns: getComputedStyle(document.querySelector('.pc-grid')).gridTemplateColumns.split(' ').length,
          visible: cards.filter(card => card.getBoundingClientRect().bottom <= innerHeight).length };
      });
      assert(density.columns >= 6 && density.visible >= 18, 'Dense default layout: ' + JSON.stringify(density));
      await page.screenshot({ path: path.join(__dirname, '..', 'dashboard-desktop.png'), fullPage: true });
      for (const width of [360, 390, 768]) {
        await page.setViewportSize({ width, height: 844 });
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'No horizontal overflow at ' + width);
      }
      await page.setViewportSize({ width: 390, height: 844 });
      await page.evaluate(() => { for (const id of Object.keys(pcs).slice(3)) delete pcs[id]; renderPCGrid(Date.now()); updateStatistics(Date.now()); });
      await page.screenshot({ path: path.join(__dirname, '..', 'dashboard-mobile.png'), fullPage: true });
      assert.deepEqual(errors, [], 'No uncaught browser errors');
      console.log(entry + ': SDK failure/retry, metadata safety, selection, controls, status expiry, responsive layout passed');
      await context.close();
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
