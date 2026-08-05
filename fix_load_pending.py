import re

with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Using regex to replace the entire loadPendingUsers function
pat = re.compile(r'async function loadPendingUsers\(\) \{.*?listEl\.innerHTML = `<p style="color:#fca5a5;text-align:center;padding:20px 0;">오류: \$\{e\.message\}</p>`;\s*\}\s*\}', re.DOTALL)

new_func = '''function loadPendingUsers() {
    const listEl = document.getElementById("pending-user-list");
    listEl.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:20px 0;">⏳ 실시간 연동 중...</p>';
    
    if (adminPendingListener) return;
    
    adminPendingListener = firebase.database().ref("/pending_users").on("value", async snapshot => {
        try {
            const data = snapshot.val() || {};
            const usersResp = await fetch(FB_PROJECT.databaseURL + "/users.json?_t=" + Date.now());
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

# Also let's check if the regex matched
match = pat.search(text)
if match:
    text = text[:match.start()] + new_func + text[match.end():]
    with open('dashboard.html', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Replaced loadPendingUsers correctly")
else:
    print("Regex did not match!")

