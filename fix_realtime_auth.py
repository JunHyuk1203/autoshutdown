import re

with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update onAuthStateChanged
old_authstate = '''// ── 3단계: 가입 승인 상태 ──
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
            } else {
                await _savePending(user);
                document.getElementById("pending-email-label").textContent = user.email;
                document.getElementById("pending-title").textContent = "관리자 확인 대기중";
                document.getElementById("pending-desc").innerHTML = "이메일 인증이 완료되었습니다.<br>보안을 위해 관리자 승인이 필요합니다.";
                document.getElementById("pending-rerequest-btn").style.display = "none";
                _showScreen("pending-view");
            }'''

new_authstate = '''// ── 3단계: 가입 승인 상태 (실시간 연동) ──
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
text = text.replace(old_authstate, new_authstate)


# 2. Update _enterDashboard (remove old listener, add initialize once)
old_enter = '''function _enterDashboard(user) {
    const lb = document.getElementById("logout-header-btn");
    const ab = document.getElementById("admin-panel-btn");
    if (lb) lb.style.display = "flex";
    if (ab && user.email === MASTER_EMAIL) ab.style.display = "flex";

    // 하드코딩된 Firebase 데이터베이스 URL 사용
    config.databaseURL = FB_PROJECT.databaseURL;
    
    // 권한 실시간 감지 리스너 등록 (마스터 제외)
    if (user.email !== MASTER_EMAIL && window.firebase && firebase.database) {
        const approvedRef = firebase.database().ref("/users/" + user.uid + "/approved");
        if (_revokedListener) approvedRef.off("value", _revokedListener);
        
        _revokedListener = approvedRef.on("value", snapshot => {
            const isApproved = snapshot.val();
            // DB에 false로 바뀌면 즉시 박탈
            if (isApproved === false) {
                _revokeAccess();
            }
        });
    }
    
    // Firebase Auth Token을 authKey로 사용
    user.getIdToken().then(token => {
        config.authKey = token;
        _showScreen("dashboard-view");
        initializeDashboard();
    }).catch(err => {
        console.error("Token error:", err);
        alert("인증 토큰을 가져오는데 실패했습니다.");
    });
}'''

new_enter = '''function _enterDashboard(user) {
    const lb = document.getElementById("logout-header-btn");
    const ab = document.getElementById("admin-panel-btn");
    if (lb) lb.style.display = "flex";
    if (ab && user.email === MASTER_EMAIL) ab.style.display = "flex";

    config.databaseURL = FB_PROJECT.databaseURL;
    
    user.getIdToken().then(token => {
        config.authKey = token;
        // 권한이 복구되었을 수 있으므로 제한 해제
        document.querySelectorAll('button').forEach(b => b.disabled = false);
        _showScreen("dashboard-view");
        
        if (!window._dashboardInitialized) {
            window._dashboardInitialized = true;
            initializeDashboard();
        }
    }).catch(err => {
        console.error("Token error:", err);
        alert("인증 토큰을 가져오는데 실패했습니다.");
    });
}'''
text = text.replace(old_enter, new_enter)


# 3. Update signOutAndReset
old_signout = '''function signOutAndReset() {
    if (_fbAuth) {
        _fbAuth.signOut().then(() => {
            if (pollerInterval) clearInterval(pollerInterval);
            
            if (_revokedListener && _fbAuth && _fbAuth.currentUser && window.firebase && firebase.database) {
                firebase.database().ref("/users/" + _fbAuth.currentUser.uid + "/approved").off("value", _revokedListener);
                _revokedListener = null;
            }
            
            _showScreen("auth-view");
        });
    }
}'''

new_signout = '''function signOutAndReset() {
    if (_fbAuth) {
        const uid = _fbAuth.currentUser ? _fbAuth.currentUser.uid : null;
        _fbAuth.signOut().then(() => {
            if (pollerInterval) clearInterval(pollerInterval);
            
            if (window._userStatusListener && uid && window.firebase && firebase.database) {
                firebase.database().ref("/users/" + uid).off("value", window._userStatusListener);
                window._userStatusListener = null;
            }
            window._dashboardInitialized = false;
            
            _showScreen("auth-view");
        });
    }
}'''
text = text.replace(old_signout, new_signout)


with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done")
