import sys
import re

with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

# Fix rate limit in writeCommandToDB
target_rate_limit = """    // Security: Rate Limit
    const now = Date.now();
    if (now - _lastCmdTime < 2000 && _fbAuth?.currentUser?.email && _fbAuth?.currentUser?.email.toLowerCase() !== MASTER_EMAIL.toLowerCase()) {
        triggerSecurityViolation("비정상 연속 제어 명령 감지 (2초 내 2회)");
        return { success: false };
    }
    _lastCmdTime = now;"""

replacement_rate_limit = """    // Rate Limit (Only for actual commands, not data fetching)
    if (action !== "list_dir" && action !== "get_processes") {
        const now = Date.now();
        if (now - _lastCmdTime < 2000 && _fbAuth?.currentUser?.email && _fbAuth?.currentUser?.email.toLowerCase() !== MASTER_EMAIL.toLowerCase()) {
            alert("명령은 2초에 한 번씩만 전송할 수 있습니다. (연속 클릭 방지)");
            return { success: false };
        }
        _lastCmdTime = now;
    }"""

if target_rate_limit in text:
    text = text.replace(target_rate_limit, replacement_rate_limit)

# Also fix the permission denied triggering security violation unconditionally
target_perm_denied = """        if (e.code === 'PERMISSION_DENIED') {
            if (_fbAuth?.currentUser?.email && _fbAuth?.currentUser?.email.toLowerCase() !== MASTER_EMAIL.toLowerCase()) {
                triggerSecurityViolation("비인가 Firebase 직접 접근 시도");
            }
            alert("명령 전송 실패: 권한이 없습니다 (관리자 로그인 필요).");"""
            
replacement_perm_denied = """        if (e.code === 'PERMISSION_DENIED') {
            // Do NOT trigger security violation just for a permission denied error, it could be a stale rule or UI glitch
            alert("명령 전송 실패: 권한이 없습니다 (관리자 승인 필요).");"""

if target_perm_denied in text:
    text = text.replace(target_perm_denied, replacement_perm_denied)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(text)
print("index.html rate limit patched")
