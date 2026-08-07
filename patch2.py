import sys

with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Add banned-view to _showScreen
target_showscreen = '["auth-view","verify-email-view","pending-view","revoked-view","dashboard-view"]'
if target_showscreen in text:
    text = text.replace(target_showscreen, '["auth-view","verify-email-view","pending-view","revoked-view","dashboard-view","banned-view"]')

# 2. Modify triggerSecurityViolation to show banned-view instead of signOutAndReset
target_trigger = '    alert("🚨 보안 위반 감지\\n사유: " + reason + "\\n계정이 즉시 차단되었습니다.");\n    signOutAndReset();'
replacement_trigger = '    alert("🚨 보안 위반 감지\\n사유: " + reason + "\\n계정이 즉시 차단되었습니다.");\n    _showScreen("banned-view");'
if target_trigger in text:
    text = text.replace(target_trigger, replacement_trigger)

# 3. Inject security-list-container HTML
security_container_html = """
    <!-- 탭 3: 보안 차단 -->
    <div id="security-list-container" style="display:none;">
      <p style="font-size:12px; color:var(--text-muted); margin-bottom:16px; line-height:1.6;">
        보안 위협(비정상 접근, 개발자 도구 등)으로 영구 차단된 사용자 목록입니다. 
      </p>
      <div id="security-user-list" style="display:flex; flex-direction:column; gap:12px; max-height:400px; overflow-y:auto; padding-right:8px;">
        <!-- 리스트 동적 렌더링 -->
      </div>
    </div>
"""
if 'id="security-list-container"' not in text:
    target_approved_view = '    <div id="admin-tab-approved" style="display:none;">'
    text = text.replace(target_approved_view, security_container_html + '\n' + target_approved_view)

# 4. Inject renderSecurityLogs function
render_fn_code = """
let adminSecurityListener = null;
function renderSecurityLogs() {
    const listEl = document.getElementById("security-user-list");
    if (!listEl) return;
    if (adminSecurityListener) return;
    
    listEl.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:20px 0;">⏳ 데이터 로딩 중...</p>';
    adminSecurityListener = firebase.database().ref("/security_logs").on("value", async snapshot => {
        try {
            const data = snapshot.val() || {};
            if (Object.keys(data).length === 0) {
                listEl.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:28px 0;">✅ 보안 차단된 사용자가 없습니다.</p>';
                return;
            }
            listEl.innerHTML = "";
            for (const [uid, info] of Object.entries(data)) {
                const time = info.revoked_at ? new Date(info.revoked_at * 1000).toLocaleString("ko-KR") : "시간 미상";
                const safeEmail = escapeHtml(info.email || "알 수 없음");
                const safeReason = escapeHtml(info.reason || "알 수 없음");
                const row = document.createElement("div");
                row.className = "approved-user-row";
                row.innerHTML = `
                    <div class="pending-user-info">
                        <div class="pending-user-email">
                            ${safeEmail}
                            <span style="background:var(--danger); color:white; font-size:10px; padding:2px 6px; border-radius:4px; margin-left:4px;">영구 차단됨</span>
                        </div>
                        <div class="pending-user-time">차단 사유: <span style="color:#fca5a5;">${safeReason}</span></div>
                        <div class="pending-user-time">차단 일시: ${time}</div>
                    </div>
                    <button class="btn-approve" onclick="restoreUser('${uid}', '${safeEmail.replace(/'/g, "\\'")}')">♻️ 차단 해제 및 권한 복구</button>
                `;
                listEl.appendChild(row);
            }
        } catch (e) {
            console.error("renderSecurityLogs 에러:", e);
            if (e.code === 'PERMISSION_DENIED') {
                listEl.innerHTML = '<p style="color:#fca5a5;text-align:center;padding:20px 0;">에러: 관리자 권한이 없습니다.</p>';
            } else {
                listEl.innerHTML = `<p style="color:#fca5a5;text-align:center;padding:20px 0;">에러: ${escapeHtml(e.message)}</p>`;
            }
        }
    });
}
"""
if 'function renderSecurityLogs' not in text:
    target_load_approved = 'function loadApprovedUsers() {'
    text = text.replace(target_load_approved, render_fn_code + '\n' + target_load_approved)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(text)
print("index.html patched part 2")
