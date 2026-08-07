import sys

sys.stdout.reconfigure(encoding="utf-8")
with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

mappings = {
    # Buttons
    r'<button class="admin-tab-btn active" id="tab-btn-pending" onclick="switchAdminTab(''pending'')" style="flex:1; padding:10px; background:none; border:none; color:var(--text-main); font-weight:bold; border-bottom:2px solid var(--primary); cursor:pointer;">':
        ('<button class="admin-tab-btn active" id="tab-btn-pending" style="flex:1; padding:10px; background:none; border:none; color:var(--text-main); font-weight:bold; border-bottom:2px solid var(--primary); cursor:pointer;">', "switchAdminTab('pending');"),
    r'<button class="admin-tab-btn" id="tab-btn-approved" onclick="switchAdminTab(''approved'')" style="flex:1; padding:10px; background:none; border:none; color:var(--text-muted); font-weight:bold; border-bottom:2px solid transparent; cursor:pointer;">':
        ('<button class="admin-tab-btn" id="tab-btn-approved" style="flex:1; padding:10px; background:none; border:none; color:var(--text-muted); font-weight:bold; border-bottom:2px solid transparent; cursor:pointer;">', "switchAdminTab('approved');"),
    r'<button id="of-tab-file" onclick="switchOpenTab(''file'')" style="flex:1; padding: 7px 0; font-size: 12px; font-weight: 700; background: none; border: none; border-bottom: 2px solid var(--primary); color: var(--text-main); cursor: pointer;">':
        ('<button id="of-tab-file" style="flex:1; padding: 7px 0; font-size: 12px; font-weight: 700; background: none; border: none; border-bottom: 2px solid var(--primary); color: var(--text-main); cursor: pointer;">', "switchOpenTab('file');"),
    r'<button id="of-tab-url" onclick="switchOpenTab(''url'')" style="flex:1; padding: 7px 0; font-size: 12px; font-weight: 700; background: none; border: none; border-bottom: 2px solid transparent; color: var(--text-muted); cursor: pointer;">':
        ('<button id="of-tab-url" style="flex:1; padding: 7px 0; font-size: 12px; font-weight: 700; background: none; border: none; border-bottom: 2px solid transparent; color: var(--text-muted); cursor: pointer;">', "switchOpenTab('url');"),
    r'<button onclick="addFavoriteFromInputs()" style="padding:0; width:36px; height:36px; border-radius:8px; border:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.05); color:var(--text-muted); font-size:16px; cursor:pointer;">➕</button>':
        ('<button id="add-favorite-btn" style="padding:0; width:36px; height:36px; border-radius:8px; border:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.05); color:var(--text-muted); font-size:16px; cursor:pointer;">➕</button>', "addFavoriteFromInputs();"),
    
    # Action buttons
    r'<button class="action-btn action-btn-danger" onclick="triggerCommandAll(''shutdown'')">':
        ('<button class="action-btn action-btn-danger" id="all-shutdown-btn">', "triggerCommandAll('shutdown');"),
    r'<button class="action-btn action-btn-blue" onclick="triggerCommandAll(''restart'')">🔄 전체 재부팅</button>':
        ('<button class="action-btn action-btn-blue" id="all-restart-btn">🔄 전체 재부팅</button>', "triggerCommandAll('restart');"),
    r'<button class="action-btn action-btn-secondary" onclick="triggerCommandAll(''setup_mode'')">🚀 전체 초기설정</button>':
        ('<button class="action-btn action-btn-secondary" id="all-setup-btn">🚀 전체 초기설정</button>', "triggerCommandAll('setup_mode');"),
    r'<button class="action-btn action-btn-warning" onclick="openFileModal(''__ALL__'')">📂 전체 파일 열기</button>':
        ('<button class="action-btn action-btn-warning" id="all-file-btn">📂 전체 파일 열기</button>', "openFileModal('__ALL__');"),
    r'<button class="action-btn action-btn-dark" onclick="triggerCommandAll(''close_active_window'')">❌ 전체 창 닫기</button>':
        ('<button class="action-btn action-btn-dark" id="all-close-btn">❌ 전체 창 닫기</button>', "triggerCommandAll('close_active_window');"),
    r'<button class="action-btn action-btn-secondary" onclick="openVolumeControl(''__ALL__'')">🔊 전체 음량제어</button>':
        ('<button class="action-btn action-btn-secondary" id="all-volume-btn">🔊 전체 음량제어</button>', "openVolumeControl('__ALL__');"),
    r'<button class="modal-btn modal-btn-cancel" onclick="closeOpenFileModal()">취소</button>':
        ('<button class="modal-btn modal-btn-cancel" id="of-cancel-btn">취소</button>', "closeOpenFileModal();"),
    r'<button class="modal-btn" id="of-submit-btn" style="background: var(--primary);" onclick="handleOpenSubmit()">📂 파일 열기</button>':
        ('<button class="modal-btn" id="of-submit-btn" style="background: var(--primary);">📂 파일 열기</button>', "handleOpenSubmit();"),
    r'<button class="action-btn action-btn-teal" onclick="triggerWindowCommand(_wmPcId, ''show_desktop'', {}, ''바탕화면 표시'', ''모든 창을 최소화하고 바탕화면을 표시하시겠습니까?'')" style="padding: 0 12px; font-size: 13px; white-space: nowrap; height: auto;">🖥️ 바탕화면</button>':
        ('<button class="action-btn action-btn-teal" id="wm-desktop-btn" style="padding: 0 12px; font-size: 13px; white-space: nowrap; height: auto;">🖥️ 바탕화면</button>', "triggerWindowCommand(_wmPcId, 'show_desktop', {}, '바탕화면 표시', '모든 창을 최소화하고 바탕화면을 표시하시겠습니까?');"),
    r'<button class="modal-btn modal-btn-cancel" onclick="closeWindowsModal()">닫기</button>':
        ('<button class="modal-btn modal-btn-cancel" id="wm-close-btn">닫기</button>', "closeWindowsModal();"),
    r'<button class="modal-btn modal-btn-cancel" onclick="closeVolumeModal()">취소</button>':
        ('<button class="modal-btn modal-btn-cancel" id="vol-cancel-btn">취소</button>', "closeVolumeModal();"),
    r'<button class="modal-btn" style="background: var(--primary);" onclick="applyVolumeControl()">적용</button>':
        ('<button class="modal-btn" id="vol-apply-btn" style="background: var(--primary);">적용</button>', "applyVolumeControl();"),

    # Presets
    r'<button type="button" onclick="setAppPreset(''chrome'')" class="app-preset-btn" id="preset-chrome">':
        ('<button type="button" class="app-preset-btn" id="preset-chrome">', "setAppPreset('chrome');"),
    r'<button type="button" onclick="setAppPreset(''edge'')" class="app-preset-btn" id="preset-edge">':
        ('<button type="button" class="app-preset-btn" id="preset-edge">', "setAppPreset('edge');"),
    r'<button type="button" onclick="setAppPreset(''powerpoint'')" class="app-preset-btn" id="preset-powerpoint">':
        ('<button type="button" class="app-preset-btn" id="preset-powerpoint">', "setAppPreset('powerpoint');"),
    r'<button type="button" onclick="setAppPreset(''excel'')" class="app-preset-btn" id="preset-excel">':
        ('<button type="button" class="app-preset-btn" id="preset-excel">', "setAppPreset('excel');"),
    r'<button type="button" onclick="setAppPreset(''word'')" class="app-preset-btn" id="preset-word">':
        ('<button type="button" class="app-preset-btn" id="preset-word">', "setAppPreset('word');"),
    r'<button type="button" onclick="setAppPreset(''notepad'')" class="app-preset-btn" id="preset-notepad">':
        ('<button type="button" class="app-preset-btn" id="preset-notepad">', "setAppPreset('notepad');"),
    r'<button type="button" onclick="setAppPreset('''')" class="app-preset-btn" id="preset-default" style="border-color: rgba(255,255,255,0.12); color: var(--text-muted);">':
        ('<button type="button" class="app-preset-btn" id="preset-default" style="border-color: rgba(255,255,255,0.12); color: var(--text-muted);">', "setAppPreset('');"),

    r'<button type="button" onclick="setUrlBrowserPreset(''chrome'')" class="app-preset-btn" id="url-preset-chrome">Chrome</button>':
        ('<button type="button" class="app-preset-btn" id="url-preset-chrome">Chrome</button>', "setUrlBrowserPreset('chrome');"),
    r'<button type="button" onclick="setUrlBrowserPreset(''edge'')" class="app-preset-btn" id="url-preset-edge">Edge</button>':
        ('<button type="button" class="app-preset-btn" id="url-preset-edge">Edge</button>', "setUrlBrowserPreset('edge');"),
    r'<button type="button" onclick="setUrlBrowserPreset(''whale'')" class="app-preset-btn" id="url-preset-whale">Whale</button>':
        ('<button type="button" class="app-preset-btn" id="url-preset-whale">Whale</button>', "setUrlBrowserPreset('whale');"),
    r'<button type="button" onclick="setUrlBrowserPreset('''')" class="app-preset-btn" id="url-preset-default" style="border-color:rgba(255,255,255,0.12); color:var(--text-muted);">🔄 기본값</button>':
        ('<button type="button" class="app-preset-btn" id="url-preset-default" style="border-color:rgba(255,255,255,0.12); color:var(--text-muted);">🔄 기본값</button>', "setUrlBrowserPreset('');"),
}

js_bindings = ""
for k, (v_html, v_js) in mappings.items():
    if k in text:
        text = text.replace(k, v_html)
        import re
        m = re.search(r'id="([^"]+)"', v_html)
        if m:
            el_id = m.group(1)
            var_name = "el_" + el_id.replace('-', '_')
            js_bindings += f'    const {var_name} = document.getElementById("{el_id}");\n'
            js_bindings += f'    if ({var_name}) {var_name}.addEventListener("click", () => {{ {v_js} }});\n'

# Delegations for templates
text = text.replace('onclick="renderScheduleTabs(''${day}'')"', 'data-action="renderScheduleTabs" data-day="${day}"')
text = text.replace('onclick="loadFavorite(${idx})"', 'data-action="loadFavorite" data-idx="${idx}"')
text = text.replace('onclick="deleteFavorite(${idx})"', 'data-action="deleteFavorite" data-idx="${idx}"')
text = text.replace('onclick="selectExplorerItem(''${safeName}'', ${isFolder})"', 'data-action="selectExplorerItem" data-name="${safeName}" data-isfolder="${isFolder}"')

text = text.replace('''onclick="triggerWindowCommand('${_wmPcId}', 'bring_to_front', {hwnd: ${hwnd}}, '창 앞으로 가져오기', '${escapedTitle} 창을 가장 앞으로 가져오시겠습니까?')"''', '''data-action="triggerWindowCommand" data-cmd="bring_to_front" data-hwnd="${hwnd}" data-title="창 앞으로 가져오기" data-msg="${escapedTitle} 창을 가장 앞으로 가져오시겠습니까?"''')
text = text.replace('''onclick="triggerWindowCommand('${_wmPcId}', 'minimize_window', {hwnd: ${hwnd}}, '창 최소화', '${escapedTitle} 창을 최소화하시겠습니까?')"''', '''data-action="triggerWindowCommand" data-cmd="minimize_window" data-hwnd="${hwnd}" data-title="창 최소화" data-msg="${escapedTitle} 창을 최소화하시겠습니까?"''')
text = text.replace('''onclick="triggerWindowCommand('${_wmPcId}', 'maximize_window', {hwnd: ${hwnd}}, '창 최대화', '${escapedTitle} 창을 최대화하시겠습니까?')"''', '''data-action="triggerWindowCommand" data-cmd="maximize_window" data-hwnd="${hwnd}" data-title="창 최대화" data-msg="${escapedTitle} 창을 최대화하시겠습니까?"''')
text = text.replace('''onclick="triggerWindowCommand('${_wmPcId}', 'restore_window', {hwnd: ${hwnd}}, '창 복구', '${escapedTitle} 창을 원래 크기로 복구하시겠습니까?')"''', '''data-action="triggerWindowCommand" data-cmd="restore_window" data-hwnd="${hwnd}" data-title="창 복구" data-msg="${escapedTitle} 창을 원래 크기로 복구하시겠습니까?"''')
text = text.replace('''onclick="triggerWindowCommand('${_wmPcId}', 'close_window', {hwnd: ${hwnd}}, '창 닫기', '${escapedTitle} 창을 닫으시겠습니까?')"''', '''data-action="triggerWindowCommand" data-cmd="close_window" data-hwnd="${hwnd}" data-title="창 닫기" data-msg="${escapedTitle} 창을 닫으시겠습니까?"''')

text = text.replace('onclick="approveUser(''${escapeHtml(uid)}'',''${safeEmail.replace(/\'/g, \\"\\\\\'\\")}'')"', 'data-action="approveUser" data-uid="${escapeHtml(uid)}" data-email="${safeEmail.replace(/\'/g, \\"\\\\\'\\")}"')
text = text.replace('onclick="rejectUser(''${escapeHtml(uid)}'',''${safeEmail.replace(/\'/g, \\"\\\\\'\\")}'')"', 'data-action="rejectUser" data-uid="${escapeHtml(uid)}" data-email="${safeEmail.replace(/\'/g, \\"\\\\\'\\")}"')

text = text.replace('''onclick="event.stopPropagation(); triggerSingleCommand('${pcId}', 'shutdown')"''', '''data-action="triggerSingleCommand" data-cmd="shutdown" data-pcid="${pcId}"''')
text = text.replace('''onclick="event.stopPropagation(); triggerSingleCommand('${pcId}', 'restart')"''', '''data-action="triggerSingleCommand" data-cmd="restart" data-pcid="${pcId}"''')
text = text.replace('''onclick="event.stopPropagation(); triggerSingleCommand('${pcId}', 'setup_mode')"''', '''data-action="triggerSingleCommand" data-cmd="setup_mode" data-pcid="${pcId}"''')
text = text.replace('''onclick="event.stopPropagation(); triggerSingleCommand('${pcId}', 'update')"''', '''data-action="triggerSingleCommand" data-cmd="update" data-pcid="${pcId}"''')
text = text.replace('''onclick="event.stopPropagation(); triggerSingleMessage('${pcId}')"''', '''data-action="triggerSingleMessage" data-pcid="${pcId}"''')

text = text.replace('''onclick="event.stopPropagation(); openConfigModal('${pcId}')"''', '''data-action="openConfigModal" data-pcid="${pcId}"''')
text = text.replace('''onclick="event.stopPropagation(); openFileModal('${pcId}')"''', '''data-action="openFileModal" data-pcid="${pcId}"''')
text = text.replace('''onclick="event.stopPropagation(); openVolumeControl('${pcId}')"''', '''data-action="openVolumeControl" data-pcid="${pcId}"''')
text = text.replace('''onclick="event.stopPropagation(); openWindowsModal('${pcId}')"''', '''data-action="openWindowsModal" data-pcid="${pcId}"''')

delegation = """
window.addEventListener('DOMContentLoaded', () => {
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;
        const action = btn.getAttribute('data-action');
        
        if (action === 'renderScheduleTabs') renderScheduleTabs(btn.getAttribute('data-day'));
        if (action === 'loadFavorite') loadFavorite(parseInt(btn.getAttribute('data-idx')));
        if (action === 'deleteFavorite') deleteFavorite(parseInt(btn.getAttribute('data-idx')));
        if (action === 'selectExplorerItem') selectExplorerItem(btn.getAttribute('data-name'), btn.getAttribute('data-isfolder') === 'true');
        
        if (action === 'triggerWindowCommand') {
            triggerWindowCommand(_wmPcId, btn.getAttribute('data-cmd'), {hwnd: parseInt(btn.getAttribute('data-hwnd'))}, btn.getAttribute('data-title'), btn.getAttribute('data-msg'));
        }
        
        if (action === 'approveUser') approveUser(btn.getAttribute('data-uid'), btn.getAttribute('data-email'));
        if (action === 'rejectUser') rejectUser(btn.getAttribute('data-uid'), btn.getAttribute('data-email'));
        
        if (action === 'triggerSingleCommand') {
            e.stopPropagation();
            triggerSingleCommand(btn.getAttribute('data-pcid'), btn.getAttribute('data-cmd'));
        }
        if (action === 'triggerSingleMessage') {
            e.stopPropagation();
            triggerSingleMessage(btn.getAttribute('data-pcid'));
        }
        if (action === 'openConfigModal') {
            e.stopPropagation();
            openConfigModal(btn.getAttribute('data-pcid'));
        }
        if (action === 'openFileModal') {
            e.stopPropagation();
            openFileModal(btn.getAttribute('data-pcid'));
        }
        if (action === 'openVolumeControl') {
            e.stopPropagation();
            openVolumeControl(btn.getAttribute('data-pcid'));
        }
        if (action === 'openWindowsModal') {
            e.stopPropagation();
            openWindowsModal(btn.getAttribute('data-pcid'));
        }
    });
"""

js_bindings = f"{delegation}\n{js_bindings}\n}});"
text = text.replace('</script>\n</body>', js_bindings + '\n</script>\n</body>')

with open("index.html", "w", encoding="utf-8") as f:
    f.write(text)
print("Finished!")
