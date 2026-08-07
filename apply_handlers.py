import re
import sys
sys.stdout.reconfigure(encoding="utf-8")

with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

# Static mappings: ID -> JS code
# For elements that already have IDs, we just strip the inline handler.
# For elements without IDs, we'll assign one.
mappings = {
    # Auth
    r'<button class="auth-btn auth-btn-primary" id="auth-submit-btn" onclick="handleEmailAuth()">': 
        ('<button class="auth-btn auth-btn-primary" id="auth-submit-btn">', 'handleEmailAuth();'),
    r'<button class="auth-btn auth-btn-google" onclick="handleGoogleAuth()">': 
        ('<button class="auth-btn auth-btn-google" id="auth-google-btn">', 'handleGoogleAuth();'),
    r'<button class="auth-link-btn" onclick="handlePasswordReset()">': 
        ('<button class="auth-link-btn" id="auth-reset-pw-btn">', 'handlePasswordReset();'),
    r'<button class="auth-link-btn" style="color:var(--text-muted)" onclick="resetApiKeySetup()">': 
        ('<button class="auth-link-btn" style="color:var(--text-muted)" id="auth-reset-api-btn">', 'resetApiKeySetup();'),
        
    # Verify Email
    r'<button class="auth-btn auth-btn-primary" onclick="checkEmailVerified()" style="margin-bottom:8px;">': 
        ('<button class="auth-btn auth-btn-primary" id="verify-check-btn" style="margin-bottom:8px;">', 'checkEmailVerified();'),
    r'<button class="auth-btn" style="background:rgba(255,255,255,0.05);color:var(--text-muted);border:1px solid rgba(255,255,255,0.1);" onclick="resendVerificationEmail()">': 
        ('<button class="auth-btn" id="verify-resend-btn" style="background:rgba(255,255,255,0.05);color:var(--text-muted);border:1px solid rgba(255,255,255,0.1);">', 'resendVerificationEmail();'),
    r'<button class="auth-btn auth-btn-outline" onclick="signOutAndReset()">': 
        ('<button class="auth-btn auth-btn-outline" id="signout-btn-1">', 'signOutAndReset();'),
        
    # Pending View
    r'<button class="auth-btn auth-btn-primary" onclick="checkPendingApproval()" style="margin-bottom:8px;">': 
        ('<button class="auth-btn auth-btn-primary" id="pending-check-btn" style="margin-bottom:8px;">', 'checkPendingApproval();'),
    r'<button id="pending-rerequest-btn" class="auth-btn auth-btn-google" onclick="reRequestApproval()" style="margin-bottom:8px; display:none;">': 
        ('<button id="pending-rerequest-btn" class="auth-btn auth-btn-google" style="margin-bottom:8px; display:none;">', 'reRequestApproval();'),
    
    # Revoked View
    r'<button class="auth-btn auth-btn-primary" onclick="reRequestReactivation()" style="margin-bottom:8px;">': 
        ('<button class="auth-btn auth-btn-primary" id="revoked-rerequest-btn" style="margin-bottom:8px;">', 'reRequestReactivation();'),
        
    # Header Buttons (already have IDs)
    r'<button class="btn-icon" id="admin-panel-btn" onclick="openAdminPanel()" title="신규 가입 검토 (관리자)" style="display:none">': 
        ('<button class="btn-icon" id="admin-panel-btn" title="신규 가입 검토 (관리자)" style="display:none">', 'openAdminPanel();'),
    r'<button class="btn-icon" id="account-header-btn" onclick="openAccountModal()" title="계정 관리" style="display:none">': 
        ('<button class="btn-icon" id="account-header-btn" title="계정 관리" style="display:none">', 'openAccountModal();'),
    r'<button class="btn-icon" id="logout-header-btn" onclick="signOutAndReset()" title="로그아웃" style="display:none">': 
        ('<button class="btn-icon" id="logout-header-btn" title="로그아웃" style="display:none">', 'signOutAndReset();'),

    # Admin Panel
    r'<div id="admin-panel-overlay" style="display:none" onclick="if(event.target===this)closeAdminPanel()">': 
        ('<div id="admin-panel-overlay" style="display:none">', 'if(e.target===this) closeAdminPanel();'),
    r'<div class="admin-panel-card" onclick="event.stopPropagation()">': 
        ('<div class="admin-panel-card">', 'e.stopPropagation();'),
    r'<button onclick="closeAdminPanel()" style="background:none;border:none;color:var(--text-muted);font-size:22px;cursor:pointer;line-height:1;padding:4px;">': 
        ('<button id="admin-close-btn" style="background:none;border:none;color:var(--text-muted);font-size:22px;cursor:pointer;line-height:1;padding:4px;">', 'closeAdminPanel();'),
    r'<button class="admin-tab-btn active" id="tab-btn-pending" onclick="switchAdminTab(\'pending\')" style="flex:1; padding:10px; background:none; border:none; color:var(--text-main); font-weight:bold; border-bottom:2px solid var(--primary); cursor:pointer;">': 
        ('<button class="admin-tab-btn active" id="tab-btn-pending" style="flex:1; padding:10px; background:none; border:none; color:var(--text-main); font-weight:bold; border-bottom:2px solid var(--primary); cursor:pointer;">', "switchAdminTab('pending');"),
    r'<button class="admin-tab-btn" id="tab-btn-approved" onclick="switchAdminTab(\'approved\')" style="flex:1; padding:10px; background:none; border:none; color:var(--text-muted); font-weight:bold; border-bottom:2px solid transparent; cursor:pointer;">': 
        ('<button class="admin-tab-btn" id="tab-btn-approved" style="flex:1; padding:10px; background:none; border:none; color:var(--text-muted); font-weight:bold; border-bottom:2px solid transparent; cursor:pointer;">', "switchAdminTab('approved');"),
        
    # Account Modal
    r'<button class="modal-close" onclick="closeAccountModal()" style="background:transparent; border:none; color:var(--text-muted); font-size:24px; cursor:pointer;">': 
        ('<button class="modal-close" id="account-close-btn" style="background:transparent; border:none; color:var(--text-muted); font-size:24px; cursor:pointer;">', 'closeAccountModal();'),
    r'<button class="btn btn-secondary" onclick="closeAccountModal()" style="padding:10px 16px; border-radius:8px; border:none; cursor:pointer; background:rgba(255,255,255,0.1); color:var(--text-main);">': 
        ('<button class="btn btn-secondary" id="account-cancel-btn" style="padding:10px 16px; border-radius:8px; border:none; cursor:pointer; background:rgba(255,255,255,0.1); color:var(--text-main);">', 'closeAccountModal();'),
    r'<button class="btn btn-primary" onclick="addPasswordToAccount()" style="padding:10px 16px; border-radius:8px; border:none; cursor:pointer; background:var(--primary); color:white; font-weight:600;">': 
        ('<button class="btn btn-primary" id="account-save-btn" style="padding:10px 16px; border-radius:8px; border:none; cursor:pointer; background:var(--primary); color:white; font-weight:600;">', 'addPasswordToAccount();'),

    # Config Modal
    r'<button class="modal-btn modal-btn-cancel" onclick="closeConfigModal()">': 
        ('<button class="modal-btn modal-btn-cancel" id="config-cancel-btn">', 'closeConfigModal();'),
    r'<button class="modal-btn modal-btn-confirm" style="background: var(--primary);" onclick="applyRemoteConfig()">': 
        ('<button class="modal-btn modal-btn-confirm" id="config-save-btn" style="background: var(--primary);">', 'applyRemoteConfig();'),
        
    # Windows Modal
    r'<button class="modal-btn modal-btn-cancel" onclick="closeModal()">': 
        ('<button class="modal-btn modal-btn-cancel" id="windows-cancel-btn">', 'closeModal();'),
        
    # Open File/URL Modal
    r'<button id="of-tab-file" onclick="switchOpenTab(\'file\')" style="flex:1; padding: 7px 0; font-size: 12px; font-weight: 700; background: none; border: none; border-bottom: 2px solid var(--primary); color: var(--text-main); cursor: pointer;">': 
        ('<button id="of-tab-file" style="flex:1; padding: 7px 0; font-size: 12px; font-weight: 700; background: none; border: none; border-bottom: 2px solid var(--primary); color: var(--text-main); cursor: pointer;">', "switchOpenTab('file');"),
    r'<button id="of-tab-url" onclick="switchOpenTab(\'url\')" style="flex:1; padding: 7px 0; font-size: 12px; font-weight: 700; background: none; border: none; border-bottom: 2px solid transparent; color: var(--text-muted); cursor: pointer;">': 
        ('<button id="of-tab-url" style="flex:1; padding: 7px 0; font-size: 12px; font-weight: 700; background: none; border: none; border-bottom: 2px solid transparent; color: var(--text-muted); cursor: pointer;">', "switchOpenTab('url');"),
    r'<button onclick="addFavoriteFromInputs()" style="padding:0; width:36px; height:36px; border-radius:8px; border:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.05); color:var(--text-muted); font-size:16px; cursor:pointer;">➕</button>': 
        ('<button id="add-favorite-btn" style="padding:0; width:36px; height:36px; border-radius:8px; border:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.05); color:var(--text-muted); font-size:16px; cursor:pointer;">➕</button>', 'addFavoriteFromInputs();'),
    r'<button class="action-btn" onclick="explorerGoUp()" style="padding: 0 10px; font-weight:bold;">': 
        ('<button class="action-btn" id="explorer-up-btn" style="padding: 0 10px; font-weight:bold;">', 'explorerGoUp();'),
    r'<button class="action-btn action-btn-teal" onclick="loadExplorerPath()" style="padding: 0 12px;">': 
        ('<button class="action-btn action-btn-teal" id="explorer-go-btn" style="padding: 0 12px;">', 'loadExplorerPath();'),

    # Control Grid Toolbar
    r'<button class="btn-clear-offline" onclick="clearSelectedDevices()">': 
        ('<button class="btn-clear-offline" id="clear-selected-btn">', 'clearSelectedDevices();'),
    r'<button class="btn-clear-offline" onclick="clearOfflineDevices()">': 
        ('<button class="btn-clear-offline" id="clear-offline-btn">', 'clearOfflineDevices();'),
        
    r'<button class="action-btn action-btn-danger" onclick="triggerCommandAll(\'shutdown\')">': 
        ('<button class="action-btn action-btn-danger" id="all-shutdown-btn">', "triggerCommandAll('shutdown');"),
    r'<button class="action-btn action-btn-blue" onclick="triggerCommandAll(\'restart\')">': 
        ('<button class="action-btn action-btn-blue" id="all-restart-btn">', "triggerCommandAll('restart');"),
    r'<button class="action-btn action-btn-secondary" onclick="triggerCommandAll(\'setup_mode\')">': 
        ('<button class="action-btn action-btn-secondary" id="all-setup-btn">', "triggerCommandAll('setup_mode');"),
    r'<button class="action-btn action-btn-warning" onclick="openFileModal(\'__ALL__\')">': 
        ('<button class="action-btn action-btn-warning" id="all-file-btn">', "openFileModal('__ALL__');"),
    r'<button class="action-btn action-btn-dark" onclick="triggerCommandAll(\'close_active_window\')">': 
        ('<button class="action-btn action-btn-dark" id="all-close-win-btn">', "triggerCommandAll('close_active_window');"),
    r'<button class="action-btn action-btn-secondary" onclick="openVolumeControl(\'__ALL__\')">': 
        ('<button class="action-btn action-btn-secondary" id="all-volume-btn">', "openVolumeControl('__ALL__');"),

    # App Presets
    r'<button type="button" onclick="setAppPreset(\'chrome\')" class="app-preset-btn" id="preset-chrome">': 
        ('<button type="button" class="app-preset-btn" id="preset-chrome">', "setAppPreset('chrome');"),
    r'<button type="button" onclick="setAppPreset(\'edge\')" class="app-preset-btn" id="preset-edge">': 
        ('<button type="button" class="app-preset-btn" id="preset-edge">', "setAppPreset('edge');"),
    r'<button type="button" onclick="setAppPreset(\'powerpoint\')" class="app-preset-btn" id="preset-powerpoint">': 
        ('<button type="button" class="app-preset-btn" id="preset-powerpoint">', "setAppPreset('powerpoint');"),
    r'<button type="button" onclick="setAppPreset(\'excel\')" class="app-preset-btn" id="preset-excel">': 
        ('<button type="button" class="app-preset-btn" id="preset-excel">', "setAppPreset('excel');"),
    r'<button type="button" onclick="setAppPreset(\'word\')" class="app-preset-btn" id="preset-word">': 
        ('<button type="button" class="app-preset-btn" id="preset-word">', "setAppPreset('word');"),
    r'<button type="button" onclick="setAppPreset(\'notepad\')" class="app-preset-btn" id="preset-notepad">': 
        ('<button type="button" class="app-preset-btn" id="preset-notepad">', "setAppPreset('notepad');"),
    r'<button type="button" onclick="setAppPreset(\'\')" class="app-preset-btn" id="preset-default" style="border-color: rgba(255,255,255,0.12); color: var(--text-muted);">': 
        ('<button type="button" class="app-preset-btn" id="preset-default" style="border-color: rgba(255,255,255,0.12); color: var(--text-muted);">', "setAppPreset('');"),

    # URL App Presets
    r'<button type="button" onclick="setUrlBrowserPreset(\'chrome\')" class="app-preset-btn" id="url-preset-chrome">': 
        ('<button type="button" class="app-preset-btn" id="url-preset-chrome">', "setUrlBrowserPreset('chrome');"),
    r'<button type="button" onclick="setUrlBrowserPreset(\'edge\')" class="app-preset-btn" id="url-preset-edge">': 
        ('<button type="button" class="app-preset-btn" id="url-preset-edge">', "setUrlBrowserPreset('edge');"),
    r'<button type="button" onclick="setUrlBrowserPreset(\'whale\')" class="app-preset-btn" id="url-preset-whale">': 
        ('<button type="button" class="app-preset-btn" id="url-preset-whale">', "setUrlBrowserPreset('whale');"),
    r'<button type="button" onclick="setUrlBrowserPreset(\'\')" class="app-preset-btn" id="url-preset-default" style="border-color:rgba(255,255,255,0.12); color:var(--text-muted);">': 
        ('<button type="button" class="app-preset-btn" id="url-preset-default" style="border-color:rgba(255,255,255,0.12); color:var(--text-muted);">', "setUrlBrowserPreset('');"),
}

js_bindings = "\n// --- Auto-generated Event Bindings ---\nfunction bindStaticEvents() {\n"

for k, (new_html, js_code) in mappings.items():
    if k in text:
        text = text.replace(k, new_html)
        # Extract ID
        m = re.search(r'id="([^"]+)"', new_html)
        if m:
            el_id = m.group(1)
            js_bindings += f'    const el_{el_id.replace("-", "_")} = document.getElementById("{el_id}");\n'
            js_bindings += f'    if (el_{el_id.replace("-", "_")}) el_{el_id.replace("-", "_")}.addEventListener("click", function(e) {{ {js_code} }});\n'
    else:
        print("Not found:", k)

# Handle multiple occurrences of signout-btn
signout_btn_counter = 1
while '<button class="auth-btn auth-btn-outline" onclick="signOutAndReset()">' in text:
    signout_btn_counter += 1
    new_html = f'<button class="auth-btn auth-btn-outline" id="signout-btn-{signout_btn_counter}">'
    text = text.replace('<button class="auth-btn auth-btn-outline" onclick="signOutAndReset()">', new_html, 1)
    js_bindings += f'    const el_signout_btn_{signout_btn_counter} = document.getElementById("signout-btn-{signout_btn_counter}");\n'
    js_bindings += f'    if (el_signout_btn_{signout_btn_counter}) el_signout_btn_{signout_btn_counter}.addEventListener("click", function(e) {{ signOutAndReset(); }});\n'

# Inputs bindings
input_mappings = {
    r'oninput="document.getElementById(\'volume-value-display\').innerText = this.value + \'%\'"':
        ('', 'volume-slider', 'input', "document.getElementById('volume-value-display').innerText = this.value + '%';"),
}

for k, (new_str, el_id, event, js_code) in input_mappings.items():
    if k in text:
        text = text.replace(k, new_str)
        js_bindings += f'    const el_{el_id.replace("-", "_")} = document.getElementById("{el_id}");\n'
        js_bindings += f'    if (el_{el_id.replace("-", "_")}) el_{el_id.replace("-", "_")}.addEventListener("{event}", function(e) {{ {js_code} }});\n'

js_bindings += "}\nwindow.addEventListener('DOMContentLoaded', bindStaticEvents);\n"

# Replace inline input handlers which were left over
text = re.sub(r'onkeydown="if\(event\.key===\'Enter\'\) loadExplorerPath\(\)"', 'id="explorer-path"', text)
text = text.replace('id="explorer-path" type="text" placeholder="경로 입력 (예: C:\\)" style="flex-grow: 1; margin-bottom: 0;" id="explorer-path"', 'id="explorer-path" type="text" placeholder="경로 입력 (예: C:\\)" style="flex-grow: 1; margin-bottom: 0;"')
text = text.replace('id="explorer-path" type="text" placeholder="경로 입력 (예: C:\\)" style="flex-grow: 1; margin-bottom: 0;" maxlength="500" id="explorer-path"', 'id="explorer-path" type="text" placeholder="경로 입력 (예: C:\\)" style="flex-grow: 1; margin-bottom: 0;" maxlength="500"')

js_bindings += """
window.addEventListener('DOMContentLoaded', () => {
    const el_explorer = document.getElementById('explorer-path');
    if (el_explorer) el_explorer.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') loadExplorerPath();
    });
    
    const el_wm_search = document.getElementById('wm-search-input');
    if (el_wm_search) el_wm_search.addEventListener('input', (e) => {
        filterWindowsList();
    });
});
"""
text = re.sub(r'oninput="filterWindowsList\(\)"', '', text)


# Event Delegation for templates (renderPCGrid)
# We will remove onclick, onchange from the template string.
# We need to add classes or data-attributes so we can catch them.

# pc card elements:
# <div class="pc-action-btn pc-btn-power" onclick="triggerCommand('${pcId}', 'shutdown')" title="종료">
# <div class="pc-action-btn pc-btn-restart" onclick="triggerCommand('${pcId}', 'restart')" title="재부팅">
# <div class="pc-action-btn pc-btn-msg" onclick="openFileModal('${pcId}')" title="파일 열기">
# <div class="pc-action-btn pc-btn-volume" onclick="openVolumeControl('${pcId}')" title="음량 조절">
# <div class="pc-action-btn pc-btn-win" onclick="openWindowsControl('${pcId}')" title="창 관리">
# <input type="checkbox" onchange="togglePCSelection('${pcId}', this.checked)"

text = text.replace('onclick="triggerCommand(\'${pcId}\', \'shutdown\')"', 'data-action="shutdown" data-pcid="${pcId}"')
text = text.replace('onclick="triggerCommand(\'${pcId}\', \'restart\')"', 'data-action="restart" data-pcid="${pcId}"')
text = text.replace('onclick="openFileModal(\'${pcId}\')"', 'data-action="openFileModal" data-pcid="${pcId}"')
text = text.replace('onclick="openVolumeControl(\'${pcId}\')"', 'data-action="openVolumeControl" data-pcid="${pcId}"')
text = text.replace('onclick="openWindowsControl(\'${pcId}\')"', 'data-action="openWindowsControl" data-pcid="${pcId}"')
text = text.replace('onchange="togglePCSelection(\'${pcId}\', this.checked)"', 'class="pc-checkbox" data-pcid="${pcId}"')

# Windows modal list items
# <button class="win-btn win-btn-restore" onclick="triggerCommand('${_wmPcId}', 'restore_window', {hwnd: ${win.hwnd}})">복원</button>
# <button class="win-btn win-btn-close" onclick="triggerCommand('${_wmPcId}', 'close_window', {hwnd: ${win.hwnd}})">종료</button>

text = text.replace('onclick="triggerCommand(\'${_wmPcId}\', \'restore_window\', {hwnd: ${win.hwnd}})"', 'data-action="restore_window" data-hwnd="${win.hwnd}"')
text = text.replace('onclick="triggerCommand(\'${_wmPcId}\', \'close_window\', {hwnd: ${win.hwnd}})"', 'data-action="close_window" data-hwnd="${win.hwnd}"')

# Config Schedule table
# <input type="checkbox" onchange="updateScheduleEnabled('${activeDay}', '${period}', this.checked)" ${isChecked ? 'checked' : ''} style="accent-color: var(--accent-blue);">
# <select class="cfg-select" onchange="updateScheduleAction('${activeDay}', '${period}', this.value)">

text = text.replace('onchange="updateScheduleEnabled(\'${activeDay}\', \'${period}\', this.checked)"', 'class="sched-checkbox" data-day="${activeDay}" data-period="${period}"')
text = text.replace('onchange="updateScheduleAction(\'${activeDay}\', \'${period}\', this.value)"', 'class="cfg-select sched-select" data-day="${activeDay}" data-period="${period}"')


delegation_script = """
window.addEventListener('DOMContentLoaded', () => {
    // Delegation for PC Grid
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;
        const action = btn.getAttribute('data-action');
        const pcId = btn.getAttribute('data-pcid');
        const hwnd = btn.getAttribute('data-hwnd');
        
        if (action === 'shutdown' && pcId) triggerCommand(pcId, 'shutdown');
        if (action === 'restart' && pcId) triggerCommand(pcId, 'restart');
        if (action === 'openFileModal' && pcId) openFileModal(pcId);
        if (action === 'openVolumeControl' && pcId) openVolumeControl(pcId);
        if (action === 'openWindowsControl' && pcId) openWindowsControl(pcId);
        
        if (action === 'restore_window' && hwnd) {
            triggerCommand(_wmPcId, 'restore_window', {hwnd: parseInt(hwnd)});
        }
        if (action === 'close_window' && hwnd) {
            triggerCommand(_wmPcId, 'close_window', {hwnd: parseInt(hwnd)});
        }
    });

    document.addEventListener('change', (e) => {
        if (e.target.classList.contains('pc-checkbox')) {
            const pcId = e.target.getAttribute('data-pcid');
            togglePCSelection(pcId, e.target.checked);
        }
        if (e.target.classList.contains('sched-checkbox')) {
            const day = e.target.getAttribute('data-day');
            const period = e.target.getAttribute('data-period');
            updateScheduleEnabled(day, period, e.target.checked);
        }
        if (e.target.classList.contains('sched-select')) {
            const day = e.target.getAttribute('data-day');
            const period = e.target.getAttribute('data-period');
            updateScheduleAction(day, period, e.target.value);
        }
    });
});
"""

js_bindings += delegation_script

# admin buttons delegation (approve/reject/revoke/restore)
text = text.replace('onclick="approveUser(\'${uid}\', \'${email}\')"', 'data-admin="approve" data-uid="${uid}" data-email="${email}"')
text = text.replace('onclick="rejectUser(\'${uid}\', \'${email}\')"', 'data-admin="reject" data-uid="${uid}" data-email="${email}"')
text = text.replace('onclick="revokeUser(\'${uid}\', \'${email}\')"', 'data-admin="revoke" data-uid="${uid}" data-email="${email}"')
text = text.replace('onclick="restoreUser(\'${uid}\', \'${email}\')"', 'data-admin="restore" data-uid="${uid}" data-email="${email}"')

admin_delegation = """
window.addEventListener('DOMContentLoaded', () => {
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-admin]');
        if (!btn) return;
        const action = btn.getAttribute('data-admin');
        const uid = btn.getAttribute('data-uid');
        const email = btn.getAttribute('data-email');
        
        if (action === 'approve') approveUser(uid, email);
        if (action === 'reject') rejectUser(uid, email);
        if (action === 'revoke') revokeUser(uid, email);
        if (action === 'restore') restoreUser(uid, email);
    });
});
"""
js_bindings += admin_delegation

text = text.replace('</script>\n</body>', js_bindings + '\n</script>\n</body>')

with open("index.html", "w", encoding="utf-8") as f:
    f.write(text)
print("Event Handlers replaced!")
