import sys

sys.stdout.reconfigure(encoding="utf-8")
with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

# HTML Update
admin_tabs_target = '<button class="admin-tab-btn" id="tab-btn-approved"  style="flex:1; padding:10px; background:none; border:none; color:var(--text-muted); font-weight:bold; border-bottom:2px solid transparent; cursor:pointer;">👥 계정 관리</button>'
admin_tabs_replacement = admin_tabs_target + '\n      <button class="admin-tab-btn" id="tab-btn-security" style="flex:1; padding:10px; background:none; border:none; color:var(--text-muted); font-weight:bold; border-bottom:2px solid transparent; cursor:pointer;">🚨 보안 차단</button>'

text = text.replace(admin_tabs_target, admin_tabs_replacement)

admin_container_target = '    <div id="approved-list-container" style="display:none; margin-top:20px; padding:0 32px;"></div>'
admin_container_replacement = admin_container_target + '\n    <div id="security-list-container" style="display:none; margin-top:20px; padding:0 32px;"></div>'

text = text.replace(admin_container_target, admin_container_replacement)

# JS Update for switchAdminTab
switch_tab_target = """function switchAdminTab(tabName) {
    const btnPending = document.getElementById('tab-btn-pending');
    const btnApproved = document.getElementById('tab-btn-approved');
    const contPending = document.getElementById('pending-list-container');
    const contApproved = document.getElementById('approved-list-container');"""
    
switch_tab_replacement = """function switchAdminTab(tabName) {
    const btnPending = document.getElementById('tab-btn-pending');
    const btnApproved = document.getElementById('tab-btn-approved');
    const btnSecurity = document.getElementById('tab-btn-security');
    const contPending = document.getElementById('pending-list-container');
    const contApproved = document.getElementById('approved-list-container');
    const contSecurity = document.getElementById('security-list-container');"""
    
text = text.replace(switch_tab_target, switch_tab_replacement)

tab_logic_target = """    if (tabName === 'pending') {
        btnPending.style.color = 'var(--text-main)';
        btnPending.style.borderBottomColor = 'var(--primary)';
        btnApproved.style.color = 'var(--text-muted)';
        btnApproved.style.borderBottomColor = 'transparent';
        contPending.style.display = 'block';
        contApproved.style.display = 'none';
        renderPendingUsers();
    } else {
        btnApproved.style.color = 'var(--text-main)';
        btnApproved.style.borderBottomColor = 'var(--primary)';
        btnPending.style.color = 'var(--text-muted)';
        btnPending.style.borderBottomColor = 'transparent';
        contApproved.style.display = 'block';
        contPending.style.display = 'none';
        renderApprovedUsers();
    }"""
    
tab_logic_replacement = """    btnPending.style.color = 'var(--text-muted)';
    btnPending.style.borderBottomColor = 'transparent';
    btnApproved.style.color = 'var(--text-muted)';
    btnApproved.style.borderBottomColor = 'transparent';
    btnSecurity.style.color = 'var(--text-muted)';
    btnSecurity.style.borderBottomColor = 'transparent';
    
    contPending.style.display = 'none';
    contApproved.style.display = 'none';
    contSecurity.style.display = 'none';

    if (tabName === 'pending') {
        btnPending.style.color = 'var(--text-main)';
        btnPending.style.borderBottomColor = 'var(--primary)';
        contPending.style.display = 'block';
        renderPendingUsers();
    } else if (tabName === 'approved') {
        btnApproved.style.color = 'var(--text-main)';
        btnApproved.style.borderBottomColor = 'var(--primary)';
        contApproved.style.display = 'block';
        renderApprovedUsers();
    } else if (tabName === 'security') {
        btnSecurity.style.color = 'var(--danger)';
        btnSecurity.style.borderBottomColor = 'var(--danger)';
        contSecurity.style.display = 'block';
        renderSecurityLogs();
    }"""

text = text.replace(tab_logic_target, tab_logic_replacement)

# JS Update for renderSecurityLogs
render_security_logs_code = """
async function renderSecurityLogs() {
    const container = document.getElementById('security-list-container');
    container.innerHTML = `<div style="text-align:center; padding:20px; color:var(--text-muted); font-size:14px;">보안 로그 불러오는 중...</div>`;
    
    try {
        const snap = await firebase.database().ref("/security_logs").once("value");
        const logs = snap.val() || {};
        
        let html = '';
        const logKeys = Object.keys(logs);
        
        if (logKeys.length === 0) {
            container.innerHTML = `<div style="text-align:center; padding:20px; color:var(--text-muted); font-size:14px;">보안 위반으로 차단된 계정이 없습니다.</div>`;
            return;
        }
        
        // 역순 정렬 (최신 순)
        logKeys.sort((a,b) => logs[b].revoked_at - logs[a].revoked_at);
        
        for (const uid of logKeys) {
            const log = logs[uid];
            const dateStr = new Date(log.revoked_at * 1000).toLocaleString();
            html += `
                <div class="pending-user-row" style="border-color: rgba(239,68,68,0.2); background: rgba(239,68,68,0.02);">
                    <div class="pending-user-avatar" style="background: linear-gradient(135deg, #ef4444, #b91c1c);">🚨</div>
                    <div class="pending-user-info">
                        <div class="pending-user-email">${escapeHtml(log.email || uid)}</div>
                        <div class="pending-user-time" style="color:#fca5a5;">사유: ${escapeHtml(log.reason)}</div>
                        <div class="pending-user-time">${dateStr}</div>
                    </div>
                    <button class="btn-approve" data-action="restoreUser" data-uid="${escapeHtml(uid)}" data-email="${escapeHtml(log.email || '')}" title="권한 복구 및 차단 해제">🔄 복구</button>
                </div>
            `;
        }
        container.innerHTML = html;
        
    } catch(e) {
        container.innerHTML = `<div style="text-align:center; padding:20px; color:var(--danger); font-size:14px;">불러오기 실패: ${e.message}</div>`;
    }
}
"""

text = text.replace('function renderApprovedUsers() {', render_security_logs_code + '\nfunction renderApprovedUsers() {')

# Add the event listener for the security tab button
text = text.replace('switchAdminTab(\'approved\');', 'switchAdminTab(\'approved\');\n    }\n    const el_tab_btn_security = document.getElementById("tab-btn-security");\n    if (el_tab_btn_security) el_tab_btn_security.addEventListener("click", () => { switchAdminTab(\'security\'); });')

with open("index.html", "w", encoding="utf-8") as f:
    f.write(text)
print("Admin UI for security logs injected.")
