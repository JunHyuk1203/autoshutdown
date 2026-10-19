// Use the actual pinned Firebase app/database SDKs. Only auth and server responses
// are fixtures; the SDK's realtime transport is deliberately stalled.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const assert = require('node:assert/strict');

function authFixture() {
  const user = { uid: 'transport-test', email: 'tntgame1203@gmail.com', async getIdToken() { return 'transport-test-token'; } };
  const auth = {
    currentUser: user, async setPersistence() {},
    onAuthStateChanged(callback) { queueMicrotask(() => callback(user)); return () => {}; },
    onIdTokenChanged(callback) { queueMicrotask(() => callback(user)); return () => {}; }
  };
  function getAuth() { return auth; }
  getAuth.Auth = { Persistence: { LOCAL: 'local', SESSION: 'session', NONE: 'none' } };
  firebase.auth = getAuth;
}

(async () => {
  const root = 'https://www.gstatic.com/firebasejs/10.12.0/';
  const scripts = {};
  for (const name of ['app', 'database']) {
    const response = await fetch(root + 'firebase-' + name + '-compat.js');
    assert(response.ok, 'Official SDK download: ' + name);
    scripts[name] = await response.text();
  }
  const browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL || 'msedge' });
  try {
    for (const entry of ['index.html', 'dashboard.html']) {
      const context = await browser.newContext();
      const page = await context.newPage();
      const errors = [];
      let restRequests = 0, denyRead = false;
      page.on('pageerror', error => errors.push(error.message));
      await page.addInitScript(() => {
        class StalledSocket extends EventTarget {
          static CONNECTING = 0; static OPEN = 1; static CLOSING = 2; static CLOSED = 3;
          constructor(url) { super(); this.url = url; this.readyState = 0; }
          send() {}
          close() { this.readyState = 3; }
        }
        window.WebSocket = StalledSocket;
      });
      await page.route('**/*', route => {
        const url = new URL(route.request().url());
        if (url.origin === 'http://localhost') return route.fulfill({ contentType: 'text/html', body: fs.readFileSync(path.join(__dirname, '..', entry), 'utf8') });
        if (url.pathname.endsWith('firebase-app-compat.js')) return route.fulfill({ contentType: 'application/javascript', body: scripts.app });
        if (url.pathname.endsWith('firebase-auth-compat.js')) return route.fulfill({ contentType: 'application/javascript', body: '(' + authFixture.toString() + ')()' });
        if (url.pathname.endsWith('firebase-database-compat.js')) return route.fulfill({ contentType: 'application/javascript', body: scripts.database });
        if (url.pathname === '/pcs.json') {
          restRequests++;
          assert.equal(url.searchParams.get('auth'), 'transport-test-token', 'Fallback must authenticate');
          return route.fulfill({ status: denyRead ? 403 : 200, contentType: 'application/json', body: JSON.stringify(denyRead ? { error: 'Permission denied' } : {
            'REAL-SDK-PC': { hostname: '수신 경로 검증 PC', user: 'Student', ip: '192.168.0.31', status: 'online', last_seen_ts: Date.now(), version: '1.1.205' }
          }) });
        }
        return route.abort();
      });
      await page.clock.install();
      await page.goto('http://localhost/' + entry);
      await page.locator('#dashboard-view').waitFor({ state: 'visible' });
      assert.equal(await page.evaluate(() => firebase.SDK_VERSION), '10.12.0');
      assert.equal(await page.evaluate(() => firebase.database().app.name), '[DEFAULT]');
      await page.clock.fastForward(4500);
      await page.locator('#pc-card-REAL-SDK-PC').waitFor({ state: 'visible', timeout: 4000 });
      assert(restRequests > 0, 'Stalled SDK realtime transport falls back to an authenticated read');
      assert.equal(await page.locator('#stat-total').textContent(), '1');
      assert(await page.locator('#label-connected-db').isVisible(), 'Data status cannot be hidden');
      denyRead = true;
      await page.evaluate(() => fetchPCData());
      assert.match(await page.locator('#label-connected-db').textContent(), /권한/);
      assert(await page.locator('#pc-card-REAL-SDK-PC').isVisible(), 'A failed retry preserves already displayed devices');
      assert.deepEqual(errors, []);
      console.log(entry + ': real Firebase SDK stalled transport, authenticated fallback, visible permission error and device preservation passed');
      await context.close();
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
