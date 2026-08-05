import re

with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Extract listener attachment to a separate function
old_authstate = '''// ── 3단계: 가입 승인 상태 (실시간 연동) ──
            if (window._userStatusListener) {
                firebase.database().ref("/users/" + user.uid).off("value", window._userStatusListener);
            }
            
            window._userStatusListener = firebase.database().ref("/users/" + user.uid).on("value", snapshot => {
                const statusObj = snapshot.val();
                const status = statusObj ? statusObj.approved : null;
                
                if (status === true) {
                    _enterDashboard(user);
                } else if (status === false) {
                    if (statusObj.revokedAt) {
                        _revokeAccess();
                    } else {
                        document.getElementById("pending-email-label").textContent = user.email;
                        document.getElementById("pending-title").textContent = "가입 거부됨";
                        document.getElementById("pending-desc").innerHTML = "관리자가 가입을 거부했습니다.";
                        document.getElementById("pending-rerequest-btn").style.display = "block";
                        _showScreen("pending-view");
                    }
                } else {
                    _savePending(user);
                    document.getElementById("pending-email-label").textContent = user.email;
                    document.getElementById("pending-title").textContent = "관리자 확인 대기중";
                    document.getElementById("pending-desc").innerHTML = "이메일 인증이 완료되었습니다.<br>보안을 위해 관리자 승인이 필요합니다.";
                    document.getElementById("pending-rerequest-btn").style.display = "none";
                    _showScreen("pending-view");
                }
            });'''

new_authstate = '''// ── 3단계: 가입 승인 상태 (실시간 연동) ──
            _attachUserStatusListener(user);'''

new_listener_func = '''
function _attachUserStatusListener(user) {
    if (window._userStatusListener) {
        firebase.database().ref("/users/" + user.uid).off("value", window._userStatusListener);
    }
    window._userStatusListener = firebase.database().ref("/users/" + user.uid).on("value", snapshot => {
        const statusObj = snapshot.val();
        const status = statusObj ? statusObj.approved : null;
        
        if (status === true) {
            _enterDashboard(user);
        } else if (status === false) {
            if (statusObj.revokedAt) {
                _revokeAccess();
            } else {
                document.getElementById("pending-email-label").textContent = user.email;
                document.getElementById("pending-title").textContent = "가입 거부됨";
                document.getElementById("pending-desc").innerHTML = "관리자가 가입을 거부했습니다.";
                document.getElementById("pending-rerequest-btn").style.display = "block";
                _showScreen("pending-view");
            }
        } else {
            _savePending(user);
            document.getElementById("pending-email-label").textContent = user.email;
            document.getElementById("pending-title").textContent = "관리자 확인 대기중";
            document.getElementById("pending-desc").innerHTML = "이메일 인증이 완료되었습니다.<br>보안을 위해 관리자 승인이 필요합니다.";
            document.getElementById("pending-rerequest-btn").style.display = "none";
            _showScreen("pending-view");
        }
    });
}
'''
text = text.replace(old_authstate, new_authstate + new_listener_func)

# 2. Update checkEmailVerified to attach listener instead of manual pending save
old_check = '''// 2단계(관리자 승인) 확인
            const approved = await _isApproved(_fbAuth.currentUser.uid);
            if (approved) {
                _enterDashboard(_fbAuth.currentUser);
            } else {
                await _savePending(_fbAuth.currentUser);
                document.getElementById("pending-email-label").textContent = _fbAuth.currentUser.email;
                _showScreen("pending-view");
            }'''
new_check = '''// 2단계(관리자 승인) 확인 - 실시간 리스너 부착
            _attachUserStatusListener(_fbAuth.currentUser);'''
text = text.replace(old_check, new_check)


# 3. Update admin actions to use firebase.database() SDK for latency compensation
old_revoke_func = '''async function revokeUser(uid, email) {
    if (!confirm(email + " 사용자의 권한을 즉시 박탈하시겠습니까?")) return;
    try {
        await fetch(FB_PROJECT.databaseURL + "/users/" + uid + ".json", {
            method: "PUT",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ email: email, approved: false, revokedAt: Date.now() })
        });
        alert("🔴 " + email + " 권한이 박탈되었습니다.");
        // UI 갱신은 실시간 리스너가 자동 처리합니다.
    } catch(e) { alert("오류: " + e.message); }
}'''
new_revoke_func = '''async function revokeUser(uid, email) {
    if (!confirm(email + " 사용자의 권한을 즉시 박탈하시겠습니까?")) return;
    try {
        await firebase.database().ref("/users/" + uid).set({ email: email, approved: false, revokedAt: Date.now() });
        // UI 갱신은 실시간 리스너가 자동 처리합니다.
    } catch(e) { alert("오류: " + e.message); }
}'''
text = text.replace(old_revoke_func, new_revoke_func)

old_restore_func = '''async function restoreUser(uid, email) {
    if (!confirm(email + " 사용자를 복구하시겠습니까?")) return;
    try {
        await fetch(FB_PROJECT.databaseURL + "/users/" + uid + ".json", {
            method: "PUT",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ email: email, approved: true, approvedAt: Date.now() }) // revokedAt은 덮어씌움
        });
        await fetch(FB_PROJECT.databaseURL + "/pending_users/" + uid + ".json", { method: "DELETE" }); // 대기열 삭제
        alert("🟢 " + email + " 복구되었습니다.");
        // UI 갱신은 실시간 리스너가 자동 처리합니다.
    } catch(e) { alert("오류: " + e.message); }
}'''
new_restore_func = '''async function restoreUser(uid, email) {
    if (!confirm(email + " 사용자를 복구하시겠습니까?")) return;
    try {
        await firebase.database().ref("/users/" + uid).set({ email: email, approved: true, approvedAt: Date.now() });
        await firebase.database().ref("/pending_users/" + uid).remove();
        // UI 갱신은 실시간 리스너가 자동 처리합니다.
    } catch(e) { alert("오류: " + e.message); }
}'''
text = text.replace(old_restore_func, new_restore_func)

old_approve_func = '''async function approveUser(uid, email) {
    if (!confirm(email + " 사용자를 승인하시겠습니까?")) return;
    try {
        await fetch(FB_PROJECT.databaseURL + "/users/" + uid + ".json", {
            method: "PUT", headers: {"Content-Type":"application/json"},
            body: JSON.stringify({ email, approved: true, role: "user", approvedAt: Date.now() })
        });
        await fetch(FB_PROJECT.databaseURL + "/pending_users/" + uid + ".json", { method: "DELETE" });
        alert("✅ " + email + " 사용자가 승인되었습니다.");
        // UI 갱신은 실시간 리스너가 자동 처리합니다.
    } catch(e) { alert("오류: " + e.message); }
}'''
new_approve_func = '''async function approveUser(uid, email) {
    if (!confirm(email + " 사용자를 승인하시겠습니까?")) return;
    try {
        await firebase.database().ref("/users/" + uid).set({ email, approved: true, role: "user", approvedAt: Date.now() });
        await firebase.database().ref("/pending_users/" + uid).remove();
        // UI 갱신은 실시간 리스너가 자동 처리합니다.
    } catch(e) { alert("오류: " + e.message); }
}'''
text = text.replace(old_approve_func, new_approve_func)

old_reject_func = '''async function rejectUser(uid, email) {
    if (!confirm(email + " 가입 요청을 거부하시겠습니까?")) return;
    try {
        // 거부 상태를 DB에 기록 (가입 거부됨 표시)
        await fetch(FB_PROJECT.databaseURL + "/users/" + uid + ".json", {
            method: "PUT",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ email: email, approved: false, rejectedAt: Date.now() })
        });
        await fetch(FB_PROJECT.databaseURL + "/pending_users/" + uid + ".json", { method: "DELETE" });
        alert("❌ " + email + " 가입 요청이 거부되었습니다.");
        // UI 갱신은 실시간 리스너가 자동 처리합니다.
    } catch(e) { alert("오류: " + e.message); }
}'''
new_reject_func = '''async function rejectUser(uid, email) {
    if (!confirm(email + " 가입 요청을 거부하시겠습니까?")) return;
    try {
        await firebase.database().ref("/users/" + uid).set({ email: email, approved: false, rejectedAt: Date.now() });
        await firebase.database().ref("/pending_users/" + uid).remove();
        // UI 갱신은 실시간 리스너가 자동 처리합니다.
    } catch(e) { alert("오류: " + e.message); }
}'''
text = text.replace(old_reject_func, new_reject_func)

# Also update reRequestApproval and reRequestReactivation to use SDK
old_rereq1 = '''await fetch(FB_PROJECT.databaseURL + "/users/" + user.uid + "/approved.json", {
            method: "DELETE" // resets to null
        });
        await fetch(FB_PROJECT.databaseURL + "/pending_users/" + user.uid + ".json", {
            method: "PUT", headers: {"Content-Type":"application/json"},
            body: JSON.stringify({ email: user.email, displayName: user.displayName || user.email.split("@")[0], requestedAt: Date.now(), requestType: "re-request" })
        });'''
new_rereq1 = '''await firebase.database().ref("/users/" + user.uid + "/approved").remove();
        await firebase.database().ref("/pending_users/" + user.uid).set({ email: user.email, displayName: user.displayName || user.email.split("@")[0], requestedAt: Date.now(), requestType: "re-request" });'''
text = text.replace(old_rereq1, new_rereq1)

old_rereq2 = '''await fetch(FB_PROJECT.databaseURL + "/pending_users/" + user.uid + ".json", {
            method: "PUT", headers: {"Content-Type":"application/json"},
            body: JSON.stringify({ 
                email: user.email, 
                displayName: user.displayName || user.email.split("@")[0], 
                requestedAt: Date.now(),
                requestType: "reactivation"
            })
        });'''
new_rereq2 = '''await firebase.database().ref("/pending_users/" + user.uid).set({ 
            email: user.email, 
            displayName: user.displayName || user.email.split("@")[0], 
            requestedAt: Date.now(),
            requestType: "reactivation"
        });'''
text = text.replace(old_rereq2, new_rereq2)

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done")
