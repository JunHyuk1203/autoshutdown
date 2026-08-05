#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_auth_system.py  (v2 - 이중 승인: 이메일 인증 + 마스터 승인)
dashboard.html에 Firebase Auth 로그인 시스템을 추가하는 스크립트
"""

FILE = "dashboard.html"

# ──────────────────────────────────────────────────────────────────────────────
AUTH_CSS = """
/* ══════════════════════════════════════════════════════════
   SECURITY / AUTH SYSTEM STYLES  v2
══════════════════════════════════════════════════════════ */
#auth-view, #pending-view, #setup-view, #verify-email-view {
    position: fixed; inset: 0; z-index: 9000;
    background: var(--bg-dark);
    background-image: radial-gradient(at 15% 20%, rgba(79,70,229,0.2) 0px, transparent 50%),
                      radial-gradient(at 85% 80%, rgba(168,85,247,0.15) 0px, transparent 50%);
    display: flex; align-items: center; justify-content: center; padding: 20px;
}
.auth-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.09);
    backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px);
    border-radius: 24px; padding: 44px 40px; width: 100%; max-width: 420px;
    box-shadow: 0 28px 60px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.04) inset;
    animation: fadeIn 0.5s ease;
}
.auth-tabs { display: flex; background: rgba(255,255,255,0.05); border-radius: 12px; padding: 4px; margin-bottom: 24px; gap: 4px; }
.auth-tab-btn {
    flex: 1; padding: 10px; text-align: center; border-radius: 9px; cursor: pointer;
    font-size: 14px; font-weight: 600; color: var(--text-muted);
    transition: all 0.2s; border: none; background: transparent; font-family: inherit;
}
.auth-tab-btn.active {
    background: linear-gradient(135deg, var(--primary), var(--accent-purple));
    color: white; box-shadow: 0 4px 12px rgba(79,70,229,0.4);
}
.auth-input {
    width: 100%; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
    border-radius: 12px; padding: 14px 16px; color: var(--text-main);
    font-size: 15px; font-family: inherit; margin-bottom: 10px; outline: none;
    transition: border-color 0.2s, background 0.2s; box-sizing: border-box;
}
.auth-input:focus { border-color: var(--primary); background: rgba(79,70,229,0.08); }
.auth-input::placeholder { color: var(--text-muted); }
.auth-btn {
    width: 100%; padding: 14px; border-radius: 12px; border: none; cursor: pointer;
    font-size: 15px; font-weight: 700; font-family: inherit; transition: all 0.2s;
    margin-bottom: 10px; display: flex; align-items: center; justify-content: center; gap: 8px;
}
.auth-btn-primary { background: linear-gradient(135deg, var(--primary), var(--accent-purple)); color: white; box-shadow: 0 4px 16px rgba(79,70,229,0.35); }
.auth-btn-primary:hover { transform: translateY(-1px); box-shadow: 0 8px 24px rgba(79,70,229,0.5); }
.auth-btn-primary:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
.auth-btn-google { background: rgba(255,255,255,0.06); color: var(--text-main); border: 1px solid rgba(255,255,255,0.1); }
.auth-btn-google:hover { background: rgba(255,255,255,0.1); }
.auth-btn-outline { background: transparent; color: var(--text-muted); border: 1px solid rgba(255,255,255,0.1); }
.auth-btn-outline:hover { background: rgba(255,255,255,0.05); }
.auth-error {
    background: rgba(239,68,68,0.12); border: 1px solid rgba(239,68,68,0.3);
    border-radius: 10px; padding: 12px 16px; color: #fca5a5; font-size: 13px;
    margin-bottom: 14px; display: none; text-align: left; line-height: 1.5;
}
.auth-notice {
    background: rgba(14,165,233,0.08); border: 1px solid rgba(14,165,233,0.25);
    border-radius: 10px; padding: 12px 16px; color: #7dd3fc; font-size: 13px;
    margin-bottom: 14px; text-align: left; line-height: 1.6;
}
.auth-step-badge {
    display: inline-flex; align-items: center; justify-content: center;
    width: 28px; height: 28px; border-radius: 50%;
    font-size: 13px; font-weight: 700; margin-right: 6px;
}
.step-done { background: rgba(16,185,129,0.25); color: #10b981; border: 1px solid rgba(16,185,129,0.4); }
.step-wait { background: rgba(245,158,11,0.25); color: #f59e0b; border: 1px solid rgba(245,158,11,0.4); }
.step-pending { background: rgba(156,163,175,0.15); color: var(--text-muted); border: 1px solid rgba(156,163,175,0.2); }
.auth-divider { display: flex; align-items: center; gap: 12px; margin: 6px 0; color: var(--text-muted); font-size: 12px; }
.auth-divider::before, .auth-divider::after { content: ''; flex: 1; height: 1px; background: rgba(255,255,255,0.08); }
.auth-link-btn { background: none; border: none; color: var(--accent-blue); cursor: pointer; font-size: 13px; font-family: inherit; text-decoration: underline; }
#admin-panel-overlay {
    position: fixed; inset: 0; z-index: 8000; background: rgba(0,0,0,0.7);
    display: flex; align-items: center; justify-content: center; padding: 20px;
}
.admin-panel-card {
    background: #0d0d22; border: 1px solid rgba(255,255,255,0.1);
    border-radius: 20px; padding: 32px; width: 100%; max-width: 560px;
    max-height: 80vh; overflow-y: auto; box-shadow: 0 24px 60px rgba(0,0,0,0.6);
    animation: fadeIn 0.3s ease;
}
.pending-user-row {
    display: flex; align-items: center; padding: 14px 16px;
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px; margin-bottom: 8px; gap: 12px;
}
.pending-user-avatar {
    width: 36px; height: 36px; border-radius: 50%;
    background: linear-gradient(135deg, var(--primary), var(--accent-purple));
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 14px; color: white; flex-shrink: 0;
}
.pending-user-info { flex: 1; min-width: 0; }
.pending-user-email { font-size: 13px; color: var(--text-main); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pending-user-time { font-size: 11px; color: var(--text-muted); margin-top: 2px; }
.btn-approve {
    background: rgba(16,185,129,0.15); border: 1px solid rgba(16,185,129,0.4);
    color: #10b981; padding: 7px 14px; border-radius: 9px; font-size: 12px;
    font-weight: 700; cursor: pointer; font-family: inherit; transition: all 0.2s; flex-shrink: 0;
}
.btn-approve:hover { background: rgba(16,185,129,0.3); }
.btn-reject {
    background: rgba(239,68,68,0.15); border: 1px solid rgba(239,68,68,0.4);
    color: #ef4444; padding: 7px 14px; border-radius: 9px; font-size: 12px;
    font-weight: 700; cursor: pointer; font-family: inherit; transition: all 0.2s; flex-shrink: 0;
}
.btn-reject:hover { background: rgba(239,68,68,0.3); }
.master-badge {
    display: inline-flex; align-items: center;
    background: linear-gradient(135deg, #f59e0b, #ef4444);
    color: white; font-size: 11px; font-weight: 700;
    padding: 3px 10px; border-radius: 20px; margin-left: 8px; vertical-align: middle;
}
@keyframes pulse-slow { 0%,100%{opacity:1} 50%{opacity:.6} }
"""

# ──────────────────────────────────────────────────────────────────────────────
AUTH_HTML = """<!-- ══════════════════════════════════════════════════════
   SECURITY SYSTEM: Auth Screens  (이중 승인: 이메일인증 + 마스터승인)
══════════════════════════════════════════════════════ -->

<!-- [SETUP] Firebase API 키 초기 설정 -->
<div id="setup-view" style="display:none">
  <div class="auth-card" style="max-width:460px;">
    <div style="text-align:center; margin-bottom:28px;">
      <div style="font-size:44px; margin-bottom:12px;">&#x1F527;</div>
      <h2 style="font-size:22px; font-weight:800; margin-bottom:8px;">초기 설정</h2>
      <p style="color:var(--text-muted); font-size:13px; line-height:1.7;">
        Firebase Console &rarr; 프로젝트 설정 &rarr; 일반 탭에서<br>
        <strong style="color:var(--accent-blue)">웹 API 키 (Web API Key)</strong>를 복사해 입력해주세요.
      </p>
    </div>
    <div class="auth-error" id="setup-error"></div>
    <input class="auth-input" id="setup-apikey-input" type="text" placeholder="AIzaSy... (Firebase 웹 API 키)">
    <button class="auth-btn auth-btn-primary" onclick="initAuthWithApiKey()">시작하기</button>
    <p style="font-size:11px; color:var(--text-muted); text-align:center; margin-top:4px;">이 설정은 이 브라우저에만 저장됩니다.</p>
  </div>
</div>

<!-- [AUTH] 로그인 / 회원가입 -->
<div id="auth-view" style="display:none">
  <div class="auth-card">
    <div style="text-align:center; margin-bottom:28px;">
      <h2 style="font-size:26px; font-weight:800; margin-bottom:6px;">&#x26A1; <span class="gradient-text">SmartPower</span></h2>
      <p style="color:var(--text-muted); font-size:13px;">원격 PC 관리 시스템에 로그인하세요</p>
    </div>
    <div class="auth-tabs">
      <button class="auth-tab-btn active" id="tab-login-btn" onclick="switchAuthTab('login')">로그인</button>
      <button class="auth-tab-btn" id="tab-signup-btn" onclick="switchAuthTab('signup')">회원가입</button>
    </div>
    <div class="auth-error" id="auth-error-msg"></div>
    <input class="auth-input" id="auth-email-input" type="email" placeholder="이메일" autocomplete="email">
    <input class="auth-input" id="auth-pw-input" type="password" placeholder="비밀번호 (6자리 이상)" autocomplete="current-password">
    <button class="auth-btn auth-btn-primary" id="auth-submit-btn" onclick="handleEmailAuth()">로그인</button>
    <div class="auth-divider">또는</div>
    <button class="auth-btn auth-btn-google" onclick="handleGoogleAuth()">
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
        <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908C16.658 14.013 17.64 11.706 17.64 9.2z" fill="#4285F4"/>
        <path d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.908-2.258c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z" fill="#34A853"/>
        <path d="M3.964 10.707A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.707V4.961H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.039l3.007-2.332z" fill="#FBBC05"/>
        <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.961L3.964 6.293C4.672 4.166 6.656 3.58 9 3.58z" fill="#EA4335"/>
      </svg>
      Google로 계속하기
    </button>
    <div style="text-align:center; margin-top:10px; display:flex; justify-content:center; gap:14px; flex-wrap:wrap;">
      <button class="auth-link-btn" onclick="handlePasswordReset()">비밀번호 재설정</button>
      <span style="color:rgba(255,255,255,0.2)">|</span>
      <button class="auth-link-btn" style="color:var(--text-muted)" onclick="resetApiKeySetup()">API키 재설정</button>
    </div>
  </div>
</div>

<!-- [VERIFY EMAIL] 이메일 인증 대기 (1단계) -->
<div id="verify-email-view" style="display:none">
  <div class="auth-card" style="text-align:center;">
    <div style="font-size:52px; margin-bottom:16px;">&#x1F4E7;</div>
    <h2 style="font-size:22px; font-weight:800; margin-bottom:10px;">이메일 인증 필요</h2>
    <!-- 이중 승인 단계 표시 -->
    <div style="display:flex; gap:8px; justify-content:center; margin-bottom:20px; flex-wrap:wrap;">
      <span style="display:flex; align-items:center; font-size:13px; font-weight:600; color:#f59e0b;">
        <span class="auth-step-badge step-wait">1</span>이메일 인증
      </span>
      <span style="color:rgba(255,255,255,0.2); align-self:center;">&#x2192;</span>
      <span style="display:flex; align-items:center; font-size:13px; color:var(--text-muted);">
        <span class="auth-step-badge step-pending">2</span>관리자 승인
      </span>
    </div>
    <div class="auth-notice">
      <strong id="verify-email-label" style="color:white"></strong>로<br>인증 이메일이 발송되었습니다.<br>
      메일함을 확인하고 인증 링크를 클릭한 뒤<br>아래 버튼을 눌러주세요.
    </div>
    <button class="auth-btn auth-btn-primary" onclick="checkEmailVerified()" style="margin-bottom:8px;">&#x2705; 인증 완료 확인</button>
    <button class="auth-btn" style="background:rgba(255,255,255,0.05);color:var(--text-muted);border:1px solid rgba(255,255,255,0.1);" onclick="resendVerificationEmail()">&#x1F4E8; 인증 이메일 재발송</button>
    <button class="auth-btn auth-btn-outline" onclick="signOutAndReset()">로그아웃</button>
  </div>
</div>

<!-- [PENDING] 관리자 승인 대기 (2단계) -->
<div id="pending-view" style="display:none">
  <div class="auth-card" style="text-align:center;">
    <div style="font-size:52px; margin-bottom:16px; animation:pulse-slow 2.5s infinite;">&#x23F3;</div>
    <h2 style="font-size:22px; font-weight:800; margin-bottom:10px;">관리자 승인 대기</h2>
    <!-- 이중 승인 단계 표시 -->
    <div style="display:flex; gap:8px; justify-content:center; margin-bottom:20px; flex-wrap:wrap;">
      <span style="display:flex; align-items:center; font-size:13px; font-weight:600; color:#10b981;">
        <span class="auth-step-badge step-done">&#x2713;</span>이메일 인증
      </span>
      <span style="color:rgba(255,255,255,0.2); align-self:center;">&#x2192;</span>
      <span style="display:flex; align-items:center; font-size:13px; font-weight:600; color:#f59e0b;">
        <span class="auth-step-badge step-wait">2</span>관리자 승인
      </span>
    </div>
    <p style="color:var(--text-muted); font-size:14px; line-height:1.75; margin-bottom:18px;">
      이메일 인증이 완료되었습니다.<br>관리자의 최종 승인 후 접속이 가능합니다.
    </p>
    <p id="pending-email-label" style="font-size:13px; color:var(--accent-blue); margin-bottom:22px; background:rgba(14,165,233,0.08); padding:10px 18px; border-radius:10px; border:1px solid rgba(14,165,233,0.2);">대기 중</p>
    <button class="auth-btn auth-btn-primary" onclick="checkPendingApproval()" style="margin-bottom:8px;">&#x1F504; 승인 확인</button>
    <button class="auth-btn auth-btn-outline" onclick="signOutAndReset()">로그아웃</button>
  </div>
</div>

<!-- [ADMIN] 신규 가입 검토 패널 (Master 전용) -->
<div id="admin-panel-overlay" style="display:none" onclick="if(event.target===this)closeAdminPanel()">
  <div class="admin-panel-card">
    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:24px;">
      <h2 style="font-size:20px; font-weight:800;">&#x1F6E1;&#xFE0F; 신규 가입 검토 <span class="master-badge">MASTER</span></h2>
      <button onclick="closeAdminPanel()" style="background:none;border:none;color:var(--text-muted);font-size:22px;cursor:pointer;line-height:1;padding:4px;">&#x2715;</button>
    </div>
    <p style="font-size:12px; color:var(--text-muted); margin-bottom:16px; line-height:1.6;">
      &#x26A0;&#xFE0F; 아래 목록은 이메일 인증까지 완료한 사용자입니다. (이중 승인 1단계 완료)
    </p>
    <div id="pending-user-list">
      <p style="color:var(--text-muted); text-align:center; font-size:14px; padding:20px 0;">&#x23F3; 로딩 중...</p>
    </div>
    <div style="border-top:1px solid rgba(255,255,255,0.08); margin-top:20px; padding-top:16px;">
      <p style="font-size:11px; color:var(--text-muted); text-align:center;">승인된 사용자는 모든 PC를 제어할 수 있습니다.</p>
    </div>
  </div>
</div>

"""

HEADER_BTN_OLD = '<button class="btn-icon" onclick="resetConfiguration()" title="서버 설정 변경">⚙️</button>'
HEADER_BTN_NEW = (
    '<button class="btn-icon" id="admin-panel-btn" onclick="openAdminPanel()" '
    'title="신규 가입 검토 (관리자)" style="display:none">&#x1F6E1;&#xFE0F;</button>\n'
    '            <button class="btn-icon" id="logout-header-btn" onclick="signOutAndReset()" '
    'title="로그아웃" style="display:none">&#x1F6AA;</button>\n'
    '            <button class="btn-icon" onclick="resetConfiguration()" title="서버 설정 변경">&#x2699;&#xFE0F;</button>'
)

FIREBASE_SDK_SNIPPET = (
    "<!-- Firebase Auth SDK (Compat v10) -->\n"
    '<script src="https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js"></script>\n'
    '<script src="https://www.gstatic.com/firebasejs/10.12.0/firebase-auth-compat.js"></script>\n\n'
)

OLD_ONLOAD_MARKER   = "// ── 환경 구성 로드/저장 ──\nwindow.onload = function() {"
OLD_ONLOAD_END      = (
    '    if (savedURL) {\n'
    '        config.databaseURL = savedURL;\n'
    '        config.authKey = savedSecret || "";\n'
    '        \n'
    '        document.getElementById("onboarding-view").style.display = "none";\n'
    '        document.getElementById("dashboard-view").style.display = "flex";\n'
    '        \n'
    '        initializeDashboard();\n'
    '    }\n'
    '};'
)

NEW_ONLOAD = """// ── 환경 구성 로드/저장 (이중 승인 Auth 포함) ──
let _fbAuth = null;
const MASTER_EMAIL = "tntgame1203@gmail.com";
const FB_PROJECT = {
    authDomain:    "atss-a1f9e.firebaseapp.com",
    databaseURL:   "https://atss-a1f9e-default-rtdb.firebaseio.com",
    projectId:     "atss-a1f9e",
    storageBucket: "atss-a1f9e.firebasestorage.app"
};

window.onload = function() {
    const savedApiKey = localStorage.getItem("sp_fb_apikey");
    if (savedApiKey) {
        _initFB(savedApiKey);
    } else {
        _showScreen("setup-view");
    }
};

// ─── 화면 전환 ────────────────────────────────────────────
function _showScreen(id) {
    ["setup-view","auth-view","verify-email-view","pending-view","onboarding-view","dashboard-view"]
        .forEach(v => {
            const el = document.getElementById(v);
            if (el) el.style.display = (v === id) ? "flex" : "none";
        });
}

// ─── Firebase 초기화 ──────────────────────────────────────
function _initFB(apiKey) {
    try {
        if (window.firebase && firebase.apps && firebase.apps.length > 0) {
            firebase.app().delete().then(() => _startAuth(apiKey)).catch(() => _startAuth(apiKey));
        } else {
            _startAuth(apiKey);
        }
    } catch(e) { _startAuth(apiKey); }
}

function _startAuth(apiKey) {
    try {
        firebase.initializeApp({ apiKey, ...FB_PROJECT });
        _fbAuth = firebase.auth();
        _fbAuth.onAuthStateChanged(async user => {
            if (!user) {
                _showScreen("auth-view");
                return;
            }
            // 마스터 계정은 무조건 통과
            if (user.email === MASTER_EMAIL) { _enterDashboard(user); return; }

            // ── 1단계: 이메일 인증 확인 ──
            await user.reload(); // 최신 상태로 갱신
            if (!user.emailVerified) {
                document.getElementById("verify-email-label").textContent = user.email;
                _showScreen("verify-email-view");
                return;
            }

            // ── 2단계: 마스터 승인 확인 ──
            const approved = await _isApproved(user.uid);
            if (approved) {
                _enterDashboard(user);
            } else {
                await _savePending(user);
                document.getElementById("pending-email-label").textContent = user.email;
                _showScreen("pending-view");
            }
        });
    } catch(err) {
        console.error("Firebase init error:", err);
        const el = document.getElementById("setup-error");
        if (el) { el.textContent = "Firebase 초기화 실패: " + (err.message||err); el.style.display="block"; }
        _showScreen("setup-view");
    }
}

function _enterDashboard(user) {
    const lb = document.getElementById("logout-header-btn");
    const ab = document.getElementById("admin-panel-btn");
    if (lb) lb.style.display = "flex";
    if (ab && user.email === MASTER_EMAIL) ab.style.display = "flex";

    const savedURL = localStorage.getItem("sp_db_url");
    if (savedURL) {
        config.databaseURL = savedURL;
        config.authKey = localStorage.getItem("sp_db_secret") || "";
        _showScreen("dashboard-view");
        initializeDashboard();
    } else {
        _showScreen("onboarding-view");
    }
}

async function _isApproved(uid) {
    try {
        const r = await fetch(FB_PROJECT.databaseURL + "/users/" + uid + "/approved.json");
        return (await r.json()) === true;
    } catch { return false; }
}

async function _savePending(user) {
    try {
        await fetch(FB_PROJECT.databaseURL + "/pending_users/" + user.uid + ".json", {
            method: "PUT", headers: {"Content-Type":"application/json"},
            body: JSON.stringify({ email: user.email, displayName: user.displayName || user.email.split("@")[0], requestedAt: Date.now() })
        });
    } catch(e) { console.error(e); }
}"""

AUTH_JS = r"""

/* ══════════════════════════════════════════════════════════
   SECURITY SYSTEM JS  (이중 승인 v2)
══════════════════════════════════════════════════════════ */

// ─ 초기 설정 ─────────────────────────────────────────────
function initAuthWithApiKey() {
    const key = (document.getElementById("setup-apikey-input").value || "").trim();
    const errEl = document.getElementById("setup-error");
    errEl.style.display = "none";
    if (!key || !key.startsWith("AIza")) {
        errEl.textContent = "올바른 Firebase 웹 API 키를 입력해주세요. (AIza 로 시작합니다)";
        errEl.style.display = "block"; return;
    }
    localStorage.setItem("sp_fb_apikey", key);
    _initFB(key);
}

function resetApiKeySetup() {
    if (!confirm("API 키 설정을 초기화하시겠습니까?")) return;
    localStorage.removeItem("sp_fb_apikey");
    if (_fbAuth) { _fbAuth.signOut().catch(()=>{}); _fbAuth = null; }
    try { if (firebase.apps && firebase.apps.length) firebase.app().delete(); } catch(e) {}
    _showScreen("setup-view");
}

// ─ 탭 전환 ───────────────────────────────────────────────
let _isLoginMode = true;
function switchAuthTab(mode) {
    _isLoginMode = (mode === "login");
    document.getElementById("tab-login-btn").classList.toggle("active", _isLoginMode);
    document.getElementById("tab-signup-btn").classList.toggle("active", !_isLoginMode);
    document.getElementById("auth-submit-btn").textContent = _isLoginMode ? "로그인" : "회원가입";
    document.getElementById("auth-error-msg").style.display = "none";
}

function _showErr(msg) {
    const el = document.getElementById("auth-error-msg");
    el.textContent = msg; el.style.display = "block";
}

function _fbErrKo(code) {
    const m = {
        "auth/invalid-email":"유효하지 않은 이메일 형식입니다.",
        "auth/user-not-found":"가입되지 않은 이메일이거나 삭제된 계정입니다.",
        "auth/wrong-password":"비밀번호가 틀렸습니다.",
        "auth/invalid-credential":"이메일 또는 비밀번호가 올바르지 않습니다.",
        "auth/email-already-in-use":"이미 가입된 이메일입니다.",
        "auth/weak-password":"비밀번호는 6자리 이상이어야 합니다.",
        "auth/too-many-requests":"너무 많은 시도가 있었습니다. 잠시 후 다시 시도하세요.",
        "auth/network-request-failed":"네트워크 연결에 실패했습니다.",
        "auth/popup-closed-by-user":"로그인 창이 닫혔습니다.",
        "auth/popup-blocked":"팝업이 차단되었습니다. 브라우저에서 팝업을 허용해주세요.",
    };
    return m[code] || ("오류: " + code);
}

// ─ 이메일/비밀번호 로그인/회원가입 ──────────────────────
async function handleEmailAuth() {
    if (!_fbAuth) { _showErr("Firebase가 초기화되지 않았습니다."); return; }
    const email = (document.getElementById("auth-email-input").value || "").trim();
    const pw    = (document.getElementById("auth-pw-input").value || "").trim();
    document.getElementById("auth-error-msg").style.display = "none";
    if (!email || !pw) { _showErr("이메일과 비밀번호를 입력해주세요."); return; }
    const btn = document.getElementById("auth-submit-btn");
    btn.disabled = true; btn.textContent = "처리 중...";
    try {
        if (_isLoginMode) {
            // 로그인: onAuthStateChanged가 자동으로 화면 전환
            await _fbAuth.signInWithEmailAndPassword(email, pw);
        } else {
            // 회원가입 → 이메일 인증 발송 → 자동 로그아웃
            const cred = await _fbAuth.createUserWithEmailAndPassword(email, pw);
            await cred.user.sendEmailVerification();
            // 화면 전환 (onAuthStateChanged 대신 직접)
            document.getElementById("verify-email-label").textContent = email;
            _showScreen("verify-email-view");
        }
    } catch(err) {
        _showErr(_fbErrKo(err.code) || err.message);
    } finally {
        btn.disabled = false;
        btn.textContent = _isLoginMode ? "로그인" : "회원가입";
    }
}

// ─ Google 로그인 ────────────────────────────────────────
async function handleGoogleAuth() {
    if (!_fbAuth) { _showErr("Firebase가 초기화되지 않았습니다."); return; }
    document.getElementById("auth-error-msg").style.display = "none";
    try {
        const provider = new firebase.auth.GoogleAuthProvider();
        await _fbAuth.signInWithPopup(provider);
        // onAuthStateChanged가 처리 (Google 계정은 기본 인증됨)
    } catch(err) {
        _showErr(_fbErrKo(err.code) || err.message);
    }
}

// ─ 비밀번호 재설정 ───────────────────────────────────────
async function handlePasswordReset() {
    if (!_fbAuth) return;
    const email = (document.getElementById("auth-email-input").value || "").trim();
    if (!email) { _showErr("위에 이메일을 입력한 후 눌러주세요."); return; }
    try {
        await _fbAuth.sendPasswordResetEmail(email);
        alert("비밀번호 재설정 이메일이 발송되었습니다. 메일함을 확인해주세요.");
    } catch(err) { _showErr(_fbErrKo(err.code) || err.message); }
}

// ─ 이메일 인증 확인 (1단계 완료 체크) ───────────────────
async function checkEmailVerified() {
    if (!_fbAuth || !_fbAuth.currentUser) return;
    try {
        await _fbAuth.currentUser.reload();
        if (_fbAuth.currentUser.emailVerified) {
            // 인증 완료 → 2단계(관리자 승인) 확인
            const approved = await _isApproved(_fbAuth.currentUser.uid);
            if (approved) {
                _enterDashboard(_fbAuth.currentUser);
            } else {
                await _savePending(_fbAuth.currentUser);
                document.getElementById("pending-email-label").textContent = _fbAuth.currentUser.email;
                _showScreen("pending-view");
            }
        } else {
            alert("아직 이메일 인증이 완료되지 않았습니다.\n메일함에서 인증 링크를 클릭해주세요.");
        }
    } catch(e) { alert("오류: " + e.message); }
}

async function resendVerificationEmail() {
    if (!_fbAuth || !_fbAuth.currentUser) return;
    try {
        await _fbAuth.currentUser.sendEmailVerification();
        alert("인증 이메일을 재발송했습니다. 메일함을 확인해주세요.");
    } catch(e) { alert("오류: " + e.message); }
}

// ─ 관리자 승인 확인 (2단계 완료 체크) ──────────────────
async function checkPendingApproval() {
    if (!_fbAuth || !_fbAuth.currentUser) return;
    const user = _fbAuth.currentUser;
    const approved = await _isApproved(user.uid);
    if (approved) {
        _enterDashboard(user);
    } else {
        alert("아직 관리자 승인 대기 중입니다.\n관리자에게 문의해주세요.");
    }
}

// ─ 로그아웃 ──────────────────────────────────────────────
async function signOutAndReset() {
    try {
        if (_fbAuth) await _fbAuth.signOut();
        const lb = document.getElementById("logout-header-btn");
        const ab = document.getElementById("admin-panel-btn");
        if (lb) lb.style.display = "none";
        if (ab) ab.style.display = "none";
        closeAdminPanel();
        if (pollerInterval) clearInterval(pollerInterval);
        _showScreen("auth-view");
    } catch(e) { console.error(e); }
}

// ─ 관리자 패널 ───────────────────────────────────────────
function openAdminPanel() {
    document.getElementById("admin-panel-overlay").style.display = "flex";
    loadPendingUsers();
}
function closeAdminPanel() {
    document.getElementById("admin-panel-overlay").style.display = "none";
}

async function loadPendingUsers() {
    const listEl = document.getElementById("pending-user-list");
    listEl.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:20px 0;">⏳ 불러오는 중...</p>';
    try {
        const resp = await fetch(FB_PROJECT.databaseURL + "/pending_users.json");
        const data = await resp.json();
        if (!data || Object.keys(data).length === 0) {
            listEl.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:28px 0;">✅ 대기 중인 가입 요청이 없습니다.</p>';
            return;
        }
        listEl.innerHTML = "";
        for (const [uid, info] of Object.entries(data)) {
            const time = info.requestedAt ? new Date(info.requestedAt).toLocaleString("ko-KR") : "시간 미상";
            const init = (info.email || "?")[0].toUpperCase();
            const safeEmail = (info.email || "").replace(/'/g, "\\'");
            const row = document.createElement("div");
            row.className = "pending-user-row";
            row.innerHTML = `
                <div class="pending-user-avatar">${init}</div>
                <div class="pending-user-info">
                    <div class="pending-user-email">${info.email || "알 수 없음"}</div>
                    <div class="pending-user-time">이메일인증 완료 / 관리자승인 대기 · ${time}</div>
                </div>
                <button class="btn-approve" onclick="approveUser('${uid}','${safeEmail}')">✅ 승인</button>
                <button class="btn-reject" onclick="rejectUser('${uid}','${safeEmail}')">❌ 거부</button>
            `;
            listEl.appendChild(row);
        }
    } catch(e) {
        listEl.innerHTML = `<p style="color:#fca5a5;text-align:center;padding:20px 0;">오류: ${e.message}</p>`;
    }
}

async function approveUser(uid, email) {
    if (!confirm(email + " 사용자를 최종 승인하시겠습니까?")) return;
    try {
        await fetch(FB_PROJECT.databaseURL + "/users/" + uid + ".json", {
            method: "PUT", headers: {"Content-Type":"application/json"},
            body: JSON.stringify({ email, approved: true, role: "user", approvedAt: Date.now() })
        });
        await fetch(FB_PROJECT.databaseURL + "/pending_users/" + uid + ".json", { method: "DELETE" });
        alert("✅ " + email + " 사용자가 승인되었습니다.");
        loadPendingUsers();
    } catch(e) { alert("오류: " + e.message); }
}

async function rejectUser(uid, email) {
    if (!confirm(email + " 사용자의 가입을 거부하시겠습니까?")) return;
    try {
        await fetch(FB_PROJECT.databaseURL + "/pending_users/" + uid + ".json", { method: "DELETE" });
        alert("❌ " + email + " 가입 요청이 거부되었습니다.");
        loadPendingUsers();
    } catch(e) { alert("오류: " + e.message); }
}
"""

# ──────────────────────────────────────────────────────────────────────────────
def main():
    print(f"[1] {FILE} 읽기...")
    with open(FILE, "r", encoding="utf-8") as f:
        content = f.read()
    original_size = len(content)

    # ① CSS
    print("[2] CSS 추가...")
    css_marker = "</style>\n</head>"
    if css_marker in content:
        content = content.replace(css_marker, AUTH_CSS + css_marker, 1); print("  OK")
    else:
        print("  [!] 마커 없음")

    # ② HTML 인증 화면
    print("[3] HTML 추가...")
    body_marker = "<body>\n\n<!-- ─────────────────────────────────────────────────────────────\n   1단계:"
    if body_marker in content:
        content = content.replace(body_marker,
            "<body>\n\n" + AUTH_HTML + "<!-- ─────────────────────────────────────────────────────────────\n   1단계:", 1)
        print("  OK")
    elif "<body>\n" in content:
        content = content.replace("<body>\n", "<body>\n\n" + AUTH_HTML, 1); print("  OK (대안)")
    else:
        print("  [!] 마커 없음")

    # ③ 헤더 버튼
    print("[4] 헤더 버튼 추가...")
    if HEADER_BTN_OLD in content:
        content = content.replace(HEADER_BTN_OLD, HEADER_BTN_NEW, 1); print("  OK")
    else:
        print("  [!] 마커 없음")

    # ④ Firebase SDK
    print("[5] Firebase SDK 추가...")
    sdk_marker = "<script>\nlet config = {"
    if sdk_marker in content:
        content = content.replace(sdk_marker, FIREBASE_SDK_SNIPPET + sdk_marker, 1); print("  OK")
    else:
        print("  [!] 마커 없음")

    # ⑤ window.onload 교체
    print("[6] window.onload 교체...")
    if OLD_ONLOAD_MARKER in content and OLD_ONLOAD_END in content:
        s = content.index(OLD_ONLOAD_MARKER)
        e = content.index(OLD_ONLOAD_END) + len(OLD_ONLOAD_END)
        content = content[:s] + NEW_ONLOAD + content[e:]
        print("  OK")
    else:
        print("  [!] 마커 없음")

    # ⑥ Auth JS
    print("[7] Auth JS 추가...")
    idx = content.rfind("\n</script>")
    if idx != -1:
        content = content[:idx] + AUTH_JS + content[idx:]; print("  OK")
    else:
        print("  [!] </script> 없음")

    print(f"[8] 저장... ({original_size:,} → {len(content):,} bytes)")
    with open(FILE, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[완료] {FILE} 수정 완료!")

if __name__ == "__main__":
    main()
