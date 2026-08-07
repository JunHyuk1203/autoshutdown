import sys
import re

sys.stdout.reconfigure(encoding="utf-8")
with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Add security variables and function near the top of the JS block
security_vars_code = """
// ── SECURITY AUTO-REVOKE ──
let _devToolsDetectedAt = null;
const DEVTOOLS_WINDOW_MS = 30 * 60 * 1000;
let _lastCmdTime = 0;

async function triggerSecurityViolation(reason, isDevToolsCompound = false) {
    const user = _fbAuth?.currentUser;
    if (!user || user.email === MASTER_EMAIL) return;

    if (!isDevToolsCompound) {
        if (_devToolsDetectedAt && (Date.now() - _devToolsDetectedAt) < DEVTOOLS_WINDOW_MS) {
            reason = "DevTools 중첩 감지 + " + reason;
        }
    }

    try {
        await firebase.database().ref(`/security_logs/${user.uid}`).set({
            revoked_at: Date.now() / 1000,
            reason: reason,
            user_agent: navigator.userAgent,
            email: user.email
        });
        await firebase.database().ref(`/users/${user.uid}/approved`).set(false);
    } catch(e) {
        console.warn("[SYSTEM] Error writing security log:", e);
    }

    _devToolsDetectedAt = null;
    setAccessGranted(false);
    alert(`🚨 보안 위반 감지\n사유: ${reason}\n계정이 즉시 차단되었습니다.`);
    signOutAndReset();
}
"""

text = text.replace('let db = null;', 'let db = null;\n' + security_vars_code)

# 2. Add signature verification and devtools scanner
security_scanners = """
// --- Security Scanners ---
const _fnSig_checkAuth = _checkAuthPermission.toString();
const _fnSig_writeCmd = writeCommandToDB.toString();

setInterval(() => {
    if (!APP_ACCESS_GRANTED) return;
    if (_fbAuth?.currentUser?.email === MASTER_EMAIL) return;

    // 1. Signature Check
    if (_checkAuthPermission.toString() !== _fnSig_checkAuth ||
        writeCommandToDB.toString() !== _fnSig_writeCmd) {
        triggerSecurityViolation("보안 함수 무단 변조");
    }

    // 2. DevTools Check (Window size difference)
    const devOpen = window.outerWidth - window.innerWidth > 160 ||
                    window.outerHeight - window.innerHeight > 160;
    if (devOpen && !_devToolsDetectedAt) {
        _devToolsDetectedAt = Date.now();
        console.warn("[SYSTEM] DevTools 감지됨 - 30분 대기");
    }
}, 3000);

// 3. Console Override
const _origLog = console.log.bind(console);
const _origWarn = console.warn.bind(console);
const _origError = console.error.bind(console);
['log', 'warn', 'error', 'debug'].forEach(method => {
    if(!console[method]) return;
    const orig = console[method].bind(console);
    console[method] = function(...args) {
        if (args[0]?.toString?.().startsWith('[SYSTEM]')) {
            return orig(...args);
        }
        if (APP_ACCESS_GRANTED && _fbAuth?.currentUser?.email !== MASTER_EMAIL) {
            triggerSecurityViolation("콘솔 직접 사용 감지");
        }
        orig(...args);
    };
});
"""

text = text.replace('// ── DOM ELEMENTS ──', security_scanners + '\n// ── DOM ELEMENTS ──')

# 3. Add rate limit and XSS check inside writeCommandToDB
xss_and_rate_code = """
    // Security: Rate Limit
    const now = Date.now();
    if (now - _lastCmdTime < 2000 && _fbAuth?.currentUser?.email !== MASTER_EMAIL) {
        triggerSecurityViolation("비정상 연속 제어 명령 감지 (2초 내 2회)");
        return { success: false };
    }
    _lastCmdTime = now;

    // Security: XSS Pattern Check
    const xssPattern = /<script|javascript:|on[a-z]+=|eval\\(|document\\.|window\\./i;
    if (xssPattern.test(message) || xssPattern.test(action) || xssPattern.test(target)) {
        triggerSecurityViolation("XSS 패턴 입력 감지");
        return { success: false };
    }
"""

text = text.replace('    if (!(await _checkAuthPermission())) return;\n    \n    const bodyData = {', 
                    '    if (!(await _checkAuthPermission())) return;\n    ' + xss_and_rate_code + '\n    const bodyData = {')

# 4. Add Permission Denied check in writeCommandToDB catch block
pd_check = """
        if (e.code === 'PERMISSION_DENIED') {
            if (_fbAuth?.currentUser?.email !== MASTER_EMAIL) {
                triggerSecurityViolation("비인가 Firebase 직접 접근 시도");
            }
            alert("명령 전송 실패: 권한이 없습니다 (관리자 로그인 필요).");
        } else {
"""
text = text.replace("""        if (e.code === 'PERMISSION_DENIED') {
            alert("명령 전송 실패: 권한이 없습니다 (관리자 로그인 필요).");
        } else {""", pd_check)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(text)
print("Security rules injected")
