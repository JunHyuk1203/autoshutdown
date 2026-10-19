// Application lifecycle tests with a deterministic Firebase SDK double; no real credentials or commands.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const assert = require('node:assert/strict');

function fakeFirebase() {
  const calls = window.sdkCalls = { persistence: [], signOut: 0, initialize: 0, delete: 0, goOnline: 0, tokens: 0 };
  const authListeners = new Set(), tokenListeners = new Set(), approvalListeners = new Set();
  const snapshot = value => ({ val: () => value, exists: () => value !== null });
  let approved = true, persistence = 'local';
  function makeUser(email) {
    return { uid: 'teacher-1', email, emailVerified: true, async getIdToken() {
      calls.tokens++;
      if (window.tokenError) throw Object.assign(new Error('token failed'), { code: window.tokenError });
      return 'mock-fresh-token';
    } };
  }
  const stored = localStorage.getItem('test-sdk-user') || sessionStorage.getItem('test-sdk-user');
  const auth = {
    currentUser: stored ? makeUser(stored) : null,
    async setPersistence(type) {
      calls.persistence.push(type);
      if ((window.blockLocal && type === 'local') || (window.blockSession && type === 'session')) {
        throw Object.assign(new Error('storage blocked'), { code: 'auth/web-storage-unsupported' });
      }
      persistence = type;
    },
    onAuthStateChanged(callback) { authListeners.add(callback); queueMicrotask(() => callback(auth.currentUser)); return () => authListeners.delete(callback); },
    onIdTokenChanged(callback) { tokenListeners.add(callback); queueMicrotask(() => callback(auth.currentUser)); return () => tokenListeners.delete(callback); },
    async signInWithEmailAndPassword(email) {
      auth.currentUser = makeUser(email);
      if (persistence !== 'none') (persistence === 'local' ? localStorage : sessionStorage).setItem('test-sdk-user', email);
      for (const callback of authListeners) callback(auth.currentUser);
      for (const callback of tokenListeners) callback(auth.currentUser);
    },
    async signOut() {
      calls.signOut++; auth.currentUser = null;
      localStorage.removeItem('test-sdk-user'); sessionStorage.removeItem('test-sdk-user');
      for (const callback of authListeners) callback(null);
    }
  };
  function getAuth() { return auth; }
  getAuth.Auth = { Persistence: { LOCAL: 'local', SESSION: 'session', NONE: 'none' } };
  window.emitApproval = value => {
    approved = value;
    for (const callback of approvalListeners) callback(snapshot({ approved, revokedAt: value ? null : 123 }));
  };
  const database = {
    goOnline() { calls.goOnline++; },
    ref(key) {
      const value = () => key === '.info/serverTimeOffset' ? 0 : key === '/pcs' ? {
        'PC-01': { hostname: '교실 PC 01', status: 'online', last_seen_ts: Date.now(), user: 'Student', ip: '192.168.0.21', version: '1.1.205' }
      } : key.endsWith('/approved') ? approved : key.startsWith('/users/') ? { approved, email: 'teacher@school.test' } : null;
      return {
        on(_event, callback) { if (key === '/users/teacher-1') approvalListeners.add(callback); queueMicrotask(() => callback(snapshot(value()))); return callback; },
        off(_event, callback) { approvalListeners.delete(callback); },
        async once() {
          if (window.permissionNetworkError && key.endsWith('/approved')) throw new Error('network unavailable');
          return snapshot(value());
        },
        async set() {}, async remove() {}, async push() {}
      };
    }
  };
  window.firebase = {
    apps: [], initializeApp() { calls.initialize++; this.apps.push({}); },
    app: () => ({ delete() { calls.delete++; throw new Error('Application must not delete the auth instance'); } }),
    auth: getAuth, database: () => database
  };
}

async function attachRoutes(page) {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('dialog', dialog => dialog.dismiss());
  await page.route('**/*', route => {
    const url = route.request().url();
    if (/^http:\/\/localhost\/(index|dashboard)\.html$/.test(url)) {
      return route.fulfill({ contentType: 'text/html', body: fs.readFileSync(path.join(__dirname, '..', url.split('/').pop()), 'utf8') });
    }
    if (url.includes('firebase-app-compat.js')) return route.fulfill({ contentType: 'application/javascript', body: '(' + fakeFirebase.toString() + ')()' });
    return route.abort();
  });
  return errors;
}
async function login(page, entry = 'index.html') {
  await page.goto('http://localhost/' + entry);
  await page.waitForFunction(() => window.sdkCalls && sdkCalls.persistence.length > 0);
  await page.evaluate(() => _authReady);
  if (await page.evaluate(() => _sessionPersistence === 'local')) {
    await page.screenshot({ path: path.join(__dirname, '..', 'dashboard-login.png'), animations: 'disabled' });
  }
  await page.locator('#auth-email-input').fill('teacher@school.test');
  await page.locator('#auth-pw-input').fill('test-only-password');
  await page.locator('#auth-submit-btn').click();
  await page.locator('#dashboard-view').waitFor({ state: 'visible' });
}

(async () => {
  let browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL || 'msedge' });
  try {
    let context = await browser.newContext();
    let page = await context.newPage();
    let errors = await attachRoutes(page);
    await login(page);
    assert.deepEqual(await page.evaluate(() => sdkCalls.persistence), ['local']);
    assert.equal(await page.locator('#auth-pw-input').inputValue(), '');
    assert(!JSON.stringify(await context.storageState()).includes('test-only-password'));
    await page.reload();
    await page.locator('#dashboard-view').waitFor({ state: 'visible' });
    assert.equal(await page.evaluate(() => sdkCalls.signOut + sdkCalls.delete), 0);
    await page.evaluate(() => _initFB('same-key'));
    assert.equal(await page.evaluate(() => sdkCalls.initialize), 1, 'Retries reuse the same Firebase app');
    await page.evaluate(async () => {
      window.tokenError = 'auth/network-request-failed';
      await refreshSession(true);
    });
    assert(await page.locator('#dashboard-view').isVisible(), 'Temporary network failures retain the dashboard');
    assert.equal(await page.evaluate(() => sdkCalls.signOut), 0);
    await page.evaluate(async () => {
      window.permissionNetworkError = true;
      window.testPermissionResult = await _checkAuthPermission();
    });
    assert.equal(await page.evaluate(() => testPermissionResult), false, 'Failed permission checks cannot execute commands');
    assert(await page.locator('#dashboard-view').isVisible());
    await page.evaluate(async () => {
      window.tokenError = null; window.permissionNetworkError = false;
      window.dispatchEvent(new Event('online'));
      await refreshSession();
    });
    assert.match(await page.locator('#session-status').textContent(), /로그인 유지/);
    assert.equal(await page.evaluate(() => config.authKey), 'mock-fresh-token');
    assert.deepEqual(errors, []);
    const storage = await context.storageState();
    await browser.close();
    browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL || 'msedge' });
    context = await browser.newContext({ storageState: storage });
    page = await context.newPage(); errors = await attachRoutes(page);
    await page.goto('http://localhost/dashboard.html');
    await page.locator('#dashboard-view').waitFor({ state: 'visible' });
    assert.equal(await page.evaluate(() => firebase.auth().currentUser.email), 'teacher@school.test', 'Saved SDK state is restored after browser restart and alternate entry');
    await page.evaluate(() => emitApproval(false));
    await page.locator('#revoked-view').waitFor({ state: 'visible' });
    assert.equal(await page.evaluate(() => APP_ACCESS_GRANTED), false, 'Confirmed revocation remains enforced');
    await page.evaluate(() => emitApproval(true));
    await page.locator('#dashboard-view').waitFor({ state: 'visible' });
    await page.locator('#logout-header-btn').click();
    await page.locator('#auth-view').waitFor({ state: 'visible' });
    await page.reload();
    await page.evaluate(() => _authReady);
    assert.equal(await page.evaluate(() => firebase.auth().currentUser), null, 'Explicit logout survives refresh');
    assert.deepEqual(errors, []);
    await context.close();

    for (const [blockSession, expected] of [[false, 'session'], [true, 'none']]) {
      const fallbackContext = await browser.newContext();
      const fallbackPage = await fallbackContext.newPage();
      await fallbackPage.addInitScript(value => { window.blockLocal = true; window.blockSession = value; }, blockSession);
      const fallbackErrors = await attachRoutes(fallbackPage);
      await login(fallbackPage);
      assert.equal(await fallbackPage.evaluate(() => _sessionPersistence), expected);
      assert.match(await fallbackPage.locator('#session-storage-note').textContent(), /제한|차단/);
      await fallbackPage.evaluate(async () => { window.tokenError = 'auth/user-token-expired'; await refreshSession(true); });
      assert(await fallbackPage.locator('#auth-view').isVisible(), 'Expired/revoked tokens still require a new login');
      assert.deepEqual(fallbackErrors, []);
      await fallbackContext.close();
    }
    console.log('Session tests passed: LOCAL setup, refresh/restart restoration, app reuse, offline recovery, permission failure, revocation/restore, explicit logout, SESSION/NONE fallback, terminal token expiry. SDK services mocked.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
