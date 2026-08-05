import re

with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update switchAdminTab & closeAdminPanel to include listeners
old_switch = '''function switchAdminTab(tab) {
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
}'''

new_switch = '''let adminPendingListener = null;
let adminUsersListener = null;

function detachAdminListeners() {
    if (adminPendingListener && window.firebase && firebase.database) {
        firebase.database().ref("/pending_users").off("value", adminPendingListener);
        adminPendingListener = null;
    }
    if (adminUsersListener && window.firebase && firebase.database) {
        firebase.database().ref("/users").off("value", adminUsersListener);
        adminUsersListener = null;
    }
}

function switchAdminTab(tab) {
    detachAdminListeners();
    
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
}'''

text = text.replace(old_switch, new_switch)

old_close = '''function closeAdminPanel() {
    document.getElementById('admin-panel-overlay').style.display = 'none';
}'''
new_close = '''function closeAdminPanel() {
    detachAdminListeners();
    document.getElementById('admin-panel-overlay').style.display = 'none';
}'''
text = text.replace(old_close, new_close)

# 2. Update loadApprovedUsers
old_approved = '''async function loadApprovedUsers() {
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
}'''

new_approved = '''function loadApprovedUsers() {
    const listEl = document.getElementById("approved-user-list");
    listEl.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:20px 0;">⏳ 실시간 연동 중...</p>';
    
    if (adminUsersListener) return;
    adminUsersListener = firebase.database().ref("/users").on("value", snapshot => {
        try {
            const data = snapshot.val() || {};
            let hasUsers = false;
            listEl.innerHTML = "";
            
            for (const [uid, info] of Object.entries(data)) {
                if (info.email === MASTER_EMAIL) continue;
                
                if (info.approved === true || (info.approved === false && info.revokedAt)) {
                    hasUsers = true;
                    const isRevoked = info.approved === false;
                    const timeLabel = isRevoked ? 
                        `박탈일시 · ${new Date(info.revokedAt).toLocaleString("ko-KR")}` : 
                        `가입일시 · ${info.approvedAt ? new Date(info.approvedAt).toLocaleString("ko-KR") : "시간 미상"}`;
                    
                    const row = document.createElement("div");
                    row.className = "pending-user-row";
                    if (isRevoked) {
                        row.style.opacity = "0.5";
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
            
            if (!hasUsers) {
                listEl.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:28px 0;">✅ 승인된 사용자(또는 박탈된 계정)가 없습니다.</p>';
            }
        } catch(e) {
            listEl.innerHTML = `<p style="color:#fca5a5;text-align:center;padding:20px 0;">오류: ${e.message}</p>`;
        }
    });
}'''
text = text.replace(old_approved, new_approved)


# 3. Update loadPendingUsers
old_pending = '''async function loadPendingUsers() {
    const listEl = document.getElementById("pending-user-list");
    listEl.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:20px 0;">⏳ 불러오는 중...</p>';
    try {
        const [pendingResp, usersResp] = await Promise.all([
            fetch(FB_PROJECT.databaseURL + "/pending_users.json"),
            fetch(FB_PROJECT.databaseURL + "/users.json")
        ]);
        const data = await pendingResp.json();
        const usersData = await usersResp.json() || {};
        
        if (!data || Object.keys(data).length === 0) {
            listEl.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:28px 0;">✅ 대기 중인 가입 요청이 없습니다.</p>';
            return;
        }
        listEl.innerHTML = "";
        let hasPending = false;
        
        for (const [uid, info] of Object.entries(data)) {
            // 무조건 권한이 있으면 요청 페이지에 뜨지 않도록 (자동 정리)
            if (usersData[uid] && usersData[uid].approved === true) {
                fetch(FB_PROJECT.databaseURL + "/pending_users/" + uid + ".json", { method: "DELETE" }).catch(()=>{});
                continue;
            }
            
            hasPending = true;
            const time = info.requestedAt ? new Date(info.requestedAt).toLocaleString("ko-KR") : "시간 미상";
            const safeEmail = (info.email || "").replace(/'/g, "\\'");
            const row = document.createElement("div");
            row.className = "pending-user-row";
            row.innerHTML = `
                <div class="pending-user-info">
                    <div class="pending-user-email">
                        ${info.email || "알 수 없음"}
                        ${info.requestType === 'reactivation' 
                            ? '<span style="background:#f59e0b; color:white; font-size:10px; padding:2px 6px; border-radius:4px; margin-left:4px;">권한 복구 요청</span>'
                            : (info.requestType === 're-request'
                                ? '<span style="background:#10b981; color:white; font-size:10px; padding:2px 6px; border-radius:4px; margin-left:4px;">가입 재요청</span>'
                                : '<span style="background:#3b82f6; color:white; font-size:10px; padding:2px 6px; border-radius:4px; margin-left:4px;">신규 가입</span>')}
                    </div>
                    <div class="pending-user-time">관리자승인 대기 · ${time}</div>
                </div>
                <button class="btn-approve" onclick="approveUser('${uid}','${safeEmail}')">✅ 승인</button>
                <button class="btn-reject" onclick="rejectUser('${uid}','${safeEmail}')">❌ 거부</button>
            `;
            listEl.appendChild(row);
        }
        
        if (!hasPending) {
            listEl.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:28px 0;">✅ 대기 중인 가입 요청이 없습니다.</p>';
        }
    } catch(e) {
        listEl.innerHTML = `<p style="color:#fca5a5;text-align:center;padding:20px 0;">오류: ${e.message}</p>`;
    }
}'''

new_pending = '''function loadPendingUsers() {
    const listEl = document.getElementById("pending-user-list");
    listEl.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:20px 0;">⏳ 실시간 연동 중...</p>';
    
    if (adminPendingListener) return;
    
    adminPendingListener = firebase.database().ref("/pending_users").on("value", async snapshot => {
        try {
            const data = snapshot.val() || {};
            const usersResp = await fetch(FB_PROJECT.databaseURL + "/users.json");
            const usersData = await usersResp.json() || {};
            
            if (Object.keys(data).length === 0) {
                listEl.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:28px 0;">✅ 대기 중인 가입 요청이 없습니다.</p>';
                return;
            }
            listEl.innerHTML = "";
            let hasPending = false;
            
            for (const [uid, info] of Object.entries(data)) {
                if (usersData[uid] && usersData[uid].approved === true) {
                    firebase.database().ref("/pending_users/" + uid).remove().catch(()=>{});
                    continue;
                }
                
                hasPending = true;
                const time = info.requestedAt ? new Date(info.requestedAt).toLocaleString("ko-KR") : "시간 미상";
                const safeEmail = (info.email || "").replace(/'/g, "\\'");
                const row = document.createElement("div");
                row.className = "pending-user-row";
                row.innerHTML = `
                    <div class="pending-user-info">
                        <div class="pending-user-email">
                            ${info.email || "알 수 없음"}
                            ${info.requestType === 'reactivation' 
                                ? '<span style="background:#f59e0b; color:white; font-size:10px; padding:2px 6px; border-radius:4px; margin-left:4px;">권한 복구 요청</span>'
                                : (info.requestType === 're-request'
                                    ? '<span style="background:#10b981; color:white; font-size:10px; padding:2px 6px; border-radius:4px; margin-left:4px;">가입 재요청</span>'
                                    : '<span style="background:#3b82f6; color:white; font-size:10px; padding:2px 6px; border-radius:4px; margin-left:4px;">신규 가입</span>')}
                        </div>
                        <div class="pending-user-time">관리자승인 대기 · ${time}</div>
                    </div>
                    <button class="btn-approve" onclick="approveUser('${uid}','${safeEmail}')">✅ 승인</button>
                    <button class="btn-reject" onclick="rejectUser('${uid}','${safeEmail}')">❌ 거부</button>
                `;
                listEl.appendChild(row);
            }
            
            if (!hasPending) {
                listEl.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:28px 0;">✅ 대기 중인 가입 요청이 없습니다.</p>';
            }
        } catch(e) {
            listEl.innerHTML = `<p style="color:#fca5a5;text-align:center;padding:20px 0;">오류: ${e.message}</p>`;
        }
    });
}'''
text = text.replace(old_pending, new_pending)

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done")
