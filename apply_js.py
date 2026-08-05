with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Add switchAdminTab and related functions
js_code = '''
let _revokedListener = null;

function switchAdminTab(tab) {
    const btnPending = document.getElementById('tab-btn-pending');
    const btnApproved = document.getElementById('tab-btn-approved');
    const viewPending = document.getElementById('admin-tab-pending');
    const viewApproved = document.getElementById('admin-tab-approved');
    
    if (tab === 'pending') {
        btnPending.style.borderBottomColor = 'var(--primary)';
        btnPending.style.color = 'var(--text-main)';
        btnApproved.style.borderBottomColor = 'transparent';
        btnApproved.style.color = 'var(--text-muted)';
        viewPending.style.display = 'block';
        viewApproved.style.display = 'none';
        loadPendingUsers();
    } else {
        btnApproved.style.borderBottomColor = 'var(--primary)';
        btnApproved.style.color = 'var(--text-main)';
        btnPending.style.borderBottomColor = 'transparent';
        btnPending.style.color = 'var(--text-muted)';
        viewPending.style.display = 'none';
        viewApproved.style.display = 'block';
        loadApprovedUsers();
    }
}

function _revokeAccess() {
    if (pollerInterval) clearInterval(pollerInterval);
    document.querySelectorAll('button').forEach(b => b.disabled = true);
    // Except logout and re-request
    const authCard = document.querySelector('#revoked-view .auth-card');
    if (authCard) {
        authCard.querySelectorAll('button').forEach(b => b.disabled = false);
    }
    _showScreen("revoked-view");
}

async function loadApprovedUsers() {
    const listEl = document.getElementById("approved-user-list");
    listEl.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:20px 0;">⏳ 불러오는 중...</p>';
    try {
        const resp = await fetch(FB_PROJECT.databaseURL + "/users.json");
        const data = await resp.json();
        
        let hasUsers = false;
        listEl.innerHTML = "";
        
        if (data) {
            for (const [uid, info] of Object.entries(data)) {
                if (info.email === MASTER_EMAIL) continue; // 마스터는 안보이게
                
                // approved === true 이거나 (approved === false 이고 revokedAt 이 있는 경우: 박탈됨)
                if (info.approved === true || (info.approved === false && info.revokedAt)) {
                    hasUsers = true;
                    const isRevoked = info.approved === false;
                    const timeLabel = isRevoked ? 
                        `박탈일시 · ${new Date(info.revokedAt).toLocaleString("ko-KR")}` : 
                        `가입일시 · ${info.approvedAt ? new Date(info.approvedAt).toLocaleString("ko-KR") : "시간 미상"}`;
                    
                    const row = document.createElement("div");
                    row.className = "pending-user-row";
                    if (isRevoked) {
                        row.style.opacity = "0.5"; // 박탈된 유저는 반투명
                    }
                    
                    row.innerHTML = `
                        <div class="pending-user-info">
                            <div class="pending-user-email">${info.email || "알 수 없음"} 
                                ${isRevoked ? '<span style="background:#ef4444; color:white; font-size:10px; padding:2px 6px; border-radius:4px; margin-left:4px;">박탈됨</span>' : ''}
                            </div>
                            <div class="pending-user-time">${timeLabel}</div>
                        </div>
                        ${isRevoked 
                            ? `<button class="btn-approve" onclick="restoreUser('${uid}','${info.email.replace(/'/g, "\\'")}')">🟢 복구</button>`
                            : `<button class="btn-reject" onclick="revokeUser('${uid}','${info.email.replace(/'/g, "\\'")}')">🔴 박탈</button>`
                        }
                    `;
                    listEl.appendChild(row);
                }
            }
        }
        
        if (!hasUsers) {
            listEl.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:28px 0;">✅ 승인된 사용자(또는 박탈된 계정)가 없습니다.</p>';
        }
    } catch(e) {
        listEl.innerHTML = `<p style="color:#fca5a5;text-align:center;padding:20px 0;">오류: ${e.message}</p>`;
    }
}

async function revokeUser(uid, email) {
    if (!confirm(email + " 사용자의 권한을 즉시 박탈하시겠습니까?")) return;
    try {
        await fetch(FB_PROJECT.databaseURL + "/users/" + uid + ".json", {
            method: "PUT",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ email: email, approved: false, revokedAt: Date.now() })
        });
        alert("🔴 " + email + " 권한이 박탈되었습니다.");
        loadApprovedUsers(); // UI 갱신
    } catch(e) { alert("오류: " + e.message); }
}

async function restoreUser(uid, email) {
    if (!confirm(email + " 사용자의 권한을 복구하시겠습니까?")) return;
    try {
        await fetch(FB_PROJECT.databaseURL + "/users/" + uid + ".json", {
            method: "PUT",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ email: email, approved: true, approvedAt: Date.now() }) // revokedAt은 덮어쓰기됨
        });
        alert("🟢 " + email + " 권한이 복구되었습니다.");
        loadApprovedUsers(); // UI 갱신
    } catch(e) { alert("오류: " + e.message); }
}

async function reRequestReactivation() {
    if (!_fbAuth || !_fbAuth.currentUser) return;
    const user = _fbAuth.currentUser;
    try {
        await fetch(FB_PROJECT.databaseURL + "/pending_users/" + user.uid + ".json", {
            method: "PUT", headers: {"Content-Type":"application/json"},
            body: JSON.stringify({ 
                email: user.email, 
                displayName: user.displayName || user.email.split("@")[0], 
                requestedAt: Date.now(),
                requestType: "reactivation"
            })
        });
        alert("권한 복구를 다시 요청했습니다.");
        document.querySelector('#revoked-view .auth-card').querySelectorAll('button').forEach(b => b.disabled = false);
    } catch (e) {
        alert("재요청 실패: " + e.message);
    }
}
'''

if 'function switchAdminTab(' not in text:
    text = text.replace('// ─ 관리자 패널 ───────────────────────────────────────────', '// ─ 관리자 패널 ───────────────────────────────────────────\n' + js_code)

# Add real-time listener logic to _enterDashboard
old_enter_dashboard = '''function _enterDashboard(user) {
    const lb = document.getElementById("logout-header-btn");
    const ab = document.getElementById("admin-panel-btn");
    if (lb) lb.style.display = "flex";
    if (ab && user.email === MASTER_EMAIL) ab.style.display = "flex";

    // 하드코딩된 Firebase 데이터베이스 URL 사용
    config.databaseURL = FB_PROJECT.databaseURL;
    
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

new_enter_dashboard = '''function _enterDashboard(user) {
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

if 'const approvedRef = firebase.database().ref(' not in text:
    text = text.replace(old_enter_dashboard, new_enter_dashboard)

# Update signOutAndReset to remove the listener
old_signout = '''if (pollerInterval) clearInterval(pollerInterval);
        _showScreen("auth-view");'''
new_signout = '''if (pollerInterval) clearInterval(pollerInterval);
        
        if (_revokedListener && _fbAuth && _fbAuth.currentUser && window.firebase && firebase.database) {
            firebase.database().ref("/users/" + _fbAuth.currentUser.uid + "/approved").off("value", _revokedListener);
            _revokedListener = null;
        }
        
        _showScreen("auth-view");'''

text = text.replace(old_signout, new_signout)

# Update loadPendingUsers for requestType badge
old_loadpending_inner = '''<div class="pending-user-info">
                    <div class="pending-user-email">${info.email || "알 수 없음"}</div>
                    <div class="pending-user-time">이메일인증 완료 / 관리자승인 대기 · ${time}</div>
                </div>'''
new_loadpending_inner = '''<div class="pending-user-info">
                    <div class="pending-user-email">
                        ${info.email || "알 수 없음"}
                        ${info.requestType === 'reactivation' 
                            ? '<span style="background:#f59e0b; color:white; font-size:10px; padding:2px 6px; border-radius:4px; margin-left:4px;">권한 재요청</span>'
                            : '<span style="background:#3b82f6; color:white; font-size:10px; padding:2px 6px; border-radius:4px; margin-left:4px;">신규 가입</span>'}
                    </div>
                    <div class="pending-user-time">관리자승인 대기 · ${time}</div>
                </div>'''

text = text.replace(old_loadpending_inner, new_loadpending_inner)


# Also update checkPendingApproval / reRequestApproval to include reactivation
old_reRequest = '''async function reRequestApproval() {
    if (!_fbAuth || !_fbAuth.currentUser) return;
    const user = _fbAuth.currentUser;
    try {
        await fetch(FB_PROJECT.databaseURL + "/users/" + user.uid + "/approved.json", {
            method: "DELETE" // resets to null
        });
        await _savePending(user);
        alert("승인을 다시 요청했습니다.");
        
        document.getElementById("pending-title").textContent = "관리자 확인 대기중";
        document.getElementById("pending-desc").innerHTML = "이메일 인증이 완료되었습니다.<br>보안을 위해 관리자 승인이 필요합니다.";
        document.getElementById("pending-rerequest-btn").style.display = "none";
    } catch (e) {
        alert("재요청 실패: " + e.message);
    }
}'''
new_reRequest = '''async function reRequestApproval() {
    if (!_fbAuth || !_fbAuth.currentUser) return;
    const user = _fbAuth.currentUser;
    try {
        await fetch(FB_PROJECT.databaseURL + "/users/" + user.uid + "/approved.json", {
            method: "DELETE" // resets to null
        });
        await fetch(FB_PROJECT.databaseURL + "/pending_users/" + user.uid + ".json", {
            method: "PUT", headers: {"Content-Type":"application/json"},
            body: JSON.stringify({ email: user.email, displayName: user.displayName || user.email.split("@")[0], requestedAt: Date.now(), requestType: "reactivation" })
        });
        alert("승인을 다시 요청했습니다.");
        
        document.getElementById("pending-title").textContent = "관리자 확인 대기중";
        document.getElementById("pending-desc").innerHTML = "이메일 인증이 완료되었습니다.<br>보안을 위해 관리자 승인이 필요합니다.";
        document.getElementById("pending-rerequest-btn").style.display = "none";
    } catch (e) {
        alert("재요청 실패: " + e.message);
    }
}'''
text = text.replace(old_reRequest, new_reRequest)

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done")
