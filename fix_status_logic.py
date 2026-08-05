with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re

# Update _getApprovalStatus
old_getstatus = '''async function _getApprovalStatus(uid) {
    try {
        const r = await fetch(FB_PROJECT.databaseURL + "/users/" + uid + "/approved.json");
        const val = await r.json();
        return val; // Returns true, false, or null
    } catch { return null; }
}'''
new_getstatus = '''async function _getApprovalStatus(uid) {
    try {
        const r = await fetch(FB_PROJECT.databaseURL + "/users/" + uid + ".json");
        const val = await r.json();
        return val; // Returns object { approved, revokedAt, rejectedAt } or null
    } catch { return null; }
}'''
text = text.replace(old_getstatus, new_getstatus)

# Update onAuthStateChanged
old_authstate = '''// ── 3단계: 가입 승인 상태 ──
            const status = await _getApprovalStatus(user.uid);
            if (status === true) {
                _enterDashboard(user);
            } else if (status === false) {
                document.getElementById("pending-email-label").textContent = user.email;
                document.getElementById("pending-title").textContent = "가입 거부됨";
                document.getElementById("pending-desc").innerHTML = "관리자가 가입을 거부했습니다.";
                document.getElementById("pending-rerequest-btn").style.display = "block";
                _showScreen("pending-view");
            } else {'''
new_authstate = '''// ── 3단계: 가입 승인 상태 ──
            const statusObj = await _getApprovalStatus(user.uid);
            const status = statusObj ? statusObj.approved : null;
            if (status === true) {
                _enterDashboard(user);
            } else if (status === false) {
                if (statusObj.revokedAt) {
                    _showScreen("revoked-view");
                } else {
                    document.getElementById("pending-email-label").textContent = user.email;
                    document.getElementById("pending-title").textContent = "가입 거부됨";
                    document.getElementById("pending-desc").innerHTML = "관리자가 가입을 거부했습니다.";
                    document.getElementById("pending-rerequest-btn").style.display = "block";
                    _showScreen("pending-view");
                }
            } else {'''
text = text.replace(old_authstate, new_authstate)

# Update checkPendingApproval
old_checkpending = '''async function checkPendingApproval() {
    if (!_fbAuth || !_fbAuth.currentUser) return;
    const user = _fbAuth.currentUser;
    const status = await _getApprovalStatus(user.uid);
    if (status === true) {
        alert("승인되었습니다!");
        _enterDashboard(user);
    } else if (status === false) {
        alert("관리자가 가입을 거부했습니다.");
        document.getElementById("pending-title").textContent = "가입 거부됨";
        document.getElementById("pending-desc").innerHTML = "관리자가 가입을 거부했습니다.";
        document.getElementById("pending-rerequest-btn").style.display = "inline-block";
    } else {
        alert("아직 승인 대기 중입니다.");
    }
}'''
new_checkpending = '''async function checkPendingApproval() {
    if (!_fbAuth || !_fbAuth.currentUser) return;
    const user = _fbAuth.currentUser;
    const statusObj = await _getApprovalStatus(user.uid);
    const status = statusObj ? statusObj.approved : null;
    if (status === true) {
        alert("승인되었습니다!");
        _enterDashboard(user);
    } else if (status === false) {
        if (statusObj.revokedAt) {
            alert("관리자에 의해 접근 권한이 박탈되었습니다.");
            _showScreen("revoked-view");
        } else {
            alert("관리자가 가입을 거부했습니다.");
            document.getElementById("pending-title").textContent = "가입 거부됨";
            document.getElementById("pending-desc").innerHTML = "관리자가 가입을 거부했습니다.";
            document.getElementById("pending-rerequest-btn").style.display = "inline-block";
        }
    } else {
        alert("아직 승인 대기 중입니다.");
    }
}'''
text = text.replace(old_checkpending, new_checkpending)

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done")
