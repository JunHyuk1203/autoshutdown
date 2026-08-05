with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re

# Fix restoreUser to delete from pending_users
old_restore = '''async function restoreUser(uid, email) {
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
}'''
new_restore = '''async function restoreUser(uid, email) {
    if (!confirm(email + " 사용자의 권한을 복구하시겠습니까?")) return;
    try {
        await fetch(FB_PROJECT.databaseURL + "/users/" + uid + ".json", {
            method: "PUT",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ email: email, approved: true, approvedAt: Date.now() }) // revokedAt은 덮어쓰기됨
        });
        await fetch(FB_PROJECT.databaseURL + "/pending_users/" + uid + ".json", { method: "DELETE" }); // 대기열에서 삭제
        alert("🟢 " + email + " 권한이 복구되었습니다.");
        loadApprovedUsers(); // UI 갱신
    } catch(e) { alert("오류: " + e.message); }
}'''
text = text.replace(old_restore, new_restore)

# Fix loadPendingUsers to ensure no approved users are ever shown
old_loadpending = '''async function loadPendingUsers() {
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
            row.innerHTML = 
                <div class="pending-user-info">
                    <div class="pending-user-email">
                        
                        
                    </div>
                    <div class="pending-user-time">관리자승인 대기 · </div>
                </div>
                <button class="btn-approve" onclick="approveUser('','')">✅ 승인</button>
                <button class="btn-reject" onclick="rejectUser('','')">❌ 거부</button>
            ;
            listEl.appendChild(row);
        }
    } catch(e) {
        listEl.innerHTML = <p style="color:#fca5a5;text-align:center;padding:20px 0;">오류: </p>;
    }
}'''

new_loadpending = '''async function loadPendingUsers() {
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
            row.innerHTML = 
                <div class="pending-user-info">
                    <div class="pending-user-email">
                        
                        
                    </div>
                    <div class="pending-user-time">관리자승인 대기 · </div>
                </div>
                <button class="btn-approve" onclick="approveUser('','')">✅ 승인</button>
                <button class="btn-reject" onclick="rejectUser('','')">❌ 거부</button>
            ;
            listEl.appendChild(row);
        }
        
        if (!hasPending) {
            listEl.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:28px 0;">✅ 대기 중인 가입 요청이 없습니다.</p>';
        }
    } catch(e) {
        listEl.innerHTML = <p style="color:#fca5a5;text-align:center;padding:20px 0;">오류: </p>;
    }
}'''
text = text.replace(old_loadpending, new_loadpending)

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done")
