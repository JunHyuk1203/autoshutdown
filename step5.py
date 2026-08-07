with open('dashboard_tmp.html', 'r', encoding='utf-8') as f:
    text = f.read()

def replace_func(text, func_name, new_func):
    start_idx = text.find(f'function {func_name}() {{')
    if start_idx == -1:
        return text, False
    brace_count = 0
    end_idx = -1
    for i in range(start_idx, len(text)):
        if text[i] == '{':
            brace_count += 1
        elif text[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                end_idx = i + 1
                break
    if end_idx != -1:
        return text[:start_idx] + new_func + text[end_idx:], True
    return text, False

new_pending = """function loadPendingUsers() {
    const listEl = document.getElementById("pending-user-list");
    listEl.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:20px 0;">⏳ 실시간 데이터 로딩 중...</p>';
    
    if (adminPendingListener) return;
    
    adminPendingListener = firebase.database().ref("/pending_users").on("value", async snapshot => {
        try {
            const data = snapshot.val() || {};
            const usersSnap = await firebase.database().ref("/users").once("value");
            const usersData = usersSnap.val() || {};
            
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
                const safeEmail = escapeHtml(info.email || "알 수 없음");
                const row = document.createElement("div");
                row.className = "pending-user-row";
                row.innerHTML = `
                    <div class="pending-user-info">
                        <div class="pending-user-email">
                            ${safeEmail}
                            ${info.requestType === 'reactivation' 
                                ? '<span style="background:#f59e0b; color:white; font-size:10px; padding:2px 6px; border-radius:4px; margin-left:4px;">복구 요청</span>'
                                : (info.requestType === 're-request'
                                    ? '<span style="background:#10b981; color:white; font-size:10px; padding:2px 6px; border-radius:4px; margin-left:4px;">재가입 요청</span>'
                                    : '<span style="background:#3b82f6; color:white; font-size:10px; padding:2px 6px; border-radius:4px; margin-left:4px;">신규 가입</span>')}
                        </div>
                        <div class="pending-user-time">최초 요청 일시 ${escapeHtml(time)}</div>
                    </div>
                    <button class="btn-approve" onclick="approveUser('${escapeHtml(uid)}','${safeEmail.replace(/'/g, "\\'")}')">✅ 승인</button>
                    <button class="btn-reject" onclick="rejectUser('${escapeHtml(uid)}','${safeEmail.replace(/'/g, "\\'")}')">❌ 거절</button>
                `;
                listEl.appendChild(row);
            }
            
            if (!hasPending) {
                listEl.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:28px 0;">✅ 대기 중인 가입 요청이 없습니다.</p>';
            }
        } catch(e) {
            console.error("loadPendingUsers 에러:", e);
            if (e.code === 'PERMISSION_DENIED') {
                listEl.innerHTML = '<p style="color:#fca5a5;text-align:center;padding:20px 0;">에러: 관리자 권한이 없습니다.</p>';
            } else {
                listEl.innerHTML = `<p style="color:#fca5a5;text-align:center;padding:20px 0;">에러: ${escapeHtml(e.message)}</p>`;
            }
        }
    });
}"""

text, ok1 = replace_func(text, "loadPendingUsers", new_pending)

new_approved = """function loadApprovedUsers() {
    const listEl = document.getElementById("approved-user-list");
    listEl.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:20px 0;">⏳ 실시간 데이터 로딩 중...</p>';
    
    if (adminUsersListener) return;
    
    adminUsersListener = firebase.database().ref("/users").on("value", async snapshot => {
        try {
            const usersData = snapshot.val() || {};
            listEl.innerHTML = "";
            let count = 0;
            
            for (const [uid, info] of Object.entries(usersData)) {
                if (info.approved === true && info.role !== "master") {
                    count++;
                    const time = info.approvedAt ? new Date(info.approvedAt).toLocaleString("ko-KR") : "시간 미상";
                    const safeEmail = escapeHtml(info.email || "알 수 없음");
                    const row = document.createElement("div");
                    row.className = "pending-user-row";
                    row.innerHTML = `
                        <div class="pending-user-info">
                            <div class="pending-user-email">
                                ${safeEmail}
                                <span style="background:#10b981; color:white; font-size:10px; padding:2px 6px; border-radius:4px; margin-left:4px;">승인됨</span>
                            </div>
                            <div class="pending-user-time">승인 일시 ${escapeHtml(time)}</div>
                        </div>
                        <button class="btn-reject" onclick="revokeUser('${escapeHtml(uid)}','${safeEmail.replace(/'/g, "\\'")}')">🔴 박탈</button>
                    `;
                    listEl.appendChild(row);
                }
            }
            if (count === 0) {
                listEl.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:28px 0;">✅ 승인된 일반 사용자가 없습니다.</p>';
            }
        } catch(e) {
            console.error("loadApprovedUsers 에러:", e);
            if (e.code === 'PERMISSION_DENIED') {
                listEl.innerHTML = '<p style="color:#fca5a5;text-align:center;padding:20px 0;">에러: 관리자 권한이 없습니다.</p>';
            } else {
                listEl.innerHTML = `<p style="color:#fca5a5;text-align:center;padding:20px 0;">에러: ${escapeHtml(e.message)}</p>`;
            }
        }
    });
}"""

text, ok2 = replace_func(text, "loadApprovedUsers", new_approved)

with open('dashboard_tmp.html', 'w', encoding='utf-8') as f:
    f.write(text)
print(f"Replaced pending: {ok1}, Replaced approved: {ok2}")
