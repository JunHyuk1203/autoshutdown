import sys

sys.stdout.reconfigure(encoding="utf-8")
with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

mappings = {
    # Buttons
    r'<button class="admin-tab-btn active" id="tab-btn-pending" onclick="switchAdminTab(\'pending\')" style="flex:1; padding:10px; background:none; border:none; color:var(--text-main); font-weight:bold; border-bottom:2px solid var(--primary); cursor:pointer;">':
        ('<button class="admin-tab-btn active" id="tab-btn-pending" style="flex:1; padding:10px; background:none; border:none; color:var(--text-main); font-weight:bold; border-bottom:2px solid var(--primary); cursor:pointer;">', "switchAdminTab('pending');"),
    r'<button class="admin-tab-btn" id="tab-btn-approved" onclick="switchAdminTab(\'approved\')" style="flex:1; padding:10px; background:none; border:none; color:var(--text-muted); font-weight:bold; border-bottom:2px solid transparent; cursor:pointer;">':
        ('<button class="admin-tab-btn" id="tab-btn-approved" style="flex:1; padding:10px; background:none; border:none; color:var(--text-muted); font-weight:bold; border-bottom:2px solid transparent; cursor:pointer;">', "switchAdminTab('approved');"),
    r'<button id="of-tab-file" onclick="switchOpenTab(\'file\')" style="flex:1; padding: 7px 0; font-size: 12px; font-weight: 700; background: none; border: none; border-bottom: 2px solid var(--primary); color: var(--text-main); cursor: pointer;">':
        ('<button id="of-tab-file" style="flex:1; padding: 7px 0; font-size: 12px; font-weight: 700; background: none; border: none; border-bottom: 2px solid var(--primary); color: var(--text-main); cursor: pointer;">', "switchOpenTab('file');"),
    r'<button id="of-tab-url" onclick="switchOpenTab(\'url\')" style="flex:1; padding: 7px 0; font-size: 12px; font-weight: 700; background: none; border: none; border-bottom: 2px solid transparent; color: var(--text-muted); cursor: pointer;">':
        ('<button id="of-tab-url" style="flex:1; padding: 7px 0; font-size: 12px; font-weight: 700; background: none; border: none; border-bottom: 2px solid transparent; color: var(--text-muted); cursor: pointer;">', "switchOpenTab('url');"),
    r'<button onclick="addFavoriteFromInputs()" style="padding:0; width:36px; height:36px; border-radius:8px; border:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.05); color:var(--text-muted); font-size:16px; cursor:pointer;">➕</button>':
        ('<button id="add-favorite-btn" style="padding:0; width:36px; height:36px; border-radius:8px; border:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.05); color:var(--text-muted); font-size:16px; cursor:pointer;">➕</button>', "addFavoriteFromInputs();"),
    
    # Action buttons
    r'<button class="action-btn action-btn-danger" onclick="triggerCommandAll(\'shutdown\')">':
        ('<button class="action-btn action-btn-danger" id="all-shutdown-btn">', "triggerCommandAll('shutdown');"),
    r'<button class="action-btn action-btn-blue" onclick="triggerCommandAll(\'restart\')">🔄 전체 재부팅</button>':
        ('<button class="action-btn action-btn-blue" id="all-restart-btn">🔄 전체 재부팅</button>', "triggerCommandAll('restart');"),
    r'<button class="action-btn action-btn-secondary" onclick="triggerCommandAll(\'setup_mode\')">🚀 전체 초기설정</button>':
        ('<button class="action-btn action-btn-secondary" id="all-setup-btn">🚀 전체 초기설정</button>', "triggerCommandAll('setup_mode');"),
    r'<button class="action-btn action-btn-warning" onclick="openFileModal(\'__ALL__\')">📂 전체 파일 열기</button>':
        ('<button class="action-btn action-btn-warning" id="all-file-btn">📂 전체 파일 열기</button>', "openFileModal('__ALL__');"),
    r'<button class="action-btn action-btn-dark" onclick="triggerCommandAll(\'close_active_window\')">❌ 전체 창 닫기</button>':
        ('<button class="action-btn action-btn-dark" id="all-close-btn">❌ 전체 창 닫기</button>', "triggerCommandAll('close_active_window');"),
    r'<button class="action-btn action-btn-secondary" onclick="openVolumeControl(\'__ALL__\')">🔊 전체 음량제어</button>':
        ('<button class="action-btn action-btn-secondary" id="all-volume-btn">🔊 전체 음량제어</button>', "openVolumeControl('__ALL__');"),
    r'<button class="action-btn action-btn-teal" onclick="triggerWindowCommand(_wmPcId, \'show_desktop\', {}, \'바탕화면 표시\', \'모든 창을 최소화하고 바탕화면을 표시하시겠습니까?\')" style="padding: 0 12px; font-size: 13px; white-space: nowrap; height: auto;">🖥️ 바탕화면</button>':
        ('<button class="action-btn action-btn-teal" id="wm-desktop-btn" style="padding: 0 12px; font-size: 13px; white-space: nowrap; height: auto;">🖥️ 바탕화면</button>', "triggerWindowCommand(_wmPcId, 'show_desktop', {}, '바탕화면 표시', '모든 창을 최소화하고 바탕화면을 표시하시겠습니까?');"),

    # Presets
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

    r'<button type="button" onclick="setUrlBrowserPreset(\'chrome\')" class="app-preset-btn" id="url-preset-chrome">Chrome</button>':
        ('<button type="button" class="app-preset-btn" id="url-preset-chrome">Chrome</button>', "setUrlBrowserPreset('chrome');"),
    r'<button type="button" onclick="setUrlBrowserPreset(\'edge\')" class="app-preset-btn" id="url-preset-edge">Edge</button>':
        ('<button type="button" class="app-preset-btn" id="url-preset-edge">Edge</button>', "setUrlBrowserPreset('edge');"),
    r'<button type="button" onclick="setUrlBrowserPreset(\'whale\')" class="app-preset-btn" id="url-preset-whale">Whale</button>':
        ('<button type="button" class="app-preset-btn" id="url-preset-whale">Whale</button>', "setUrlBrowserPreset('whale');"),
    r'<button type="button" onclick="setUrlBrowserPreset(\'\')" class="app-preset-btn" id="url-preset-default" style="border-color:rgba(255,255,255,0.12); color:var(--text-muted);">🔄 기본값</button>':
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

text = text.replace('''<input type="range" id="volume-slider" min="0" max="100" value="50" style="flex-grow: 1; accent-color: var(--primary); cursor: pointer;" oninput="document.getElementById('volume-value-display').innerText = this.value + '%'">''', '''<input type="range" id="volume-slider" min="0" max="100" value="50" style="flex-grow: 1; accent-color: var(--primary); cursor: pointer;">''')
js_bindings += f'    const el_volume_slider = document.getElementById("volume-slider");\n'
js_bindings += f'    if (el_volume_slider) el_volume_slider.addEventListener("input", (e) => {{ document.getElementById("volume-value-display").innerText = e.target.value + "%"; }});\n'

# Update the js_bindings inside the existing DOMContentLoaded listener.
# The listener was added as "window.addEventListener('DOMContentLoaded', () => {" 
# We can just append this to the script block.

text = text.replace('</script>\n</body>', """
window.addEventListener('DOMContentLoaded', () => {
""" + js_bindings + """
});
</script>
</body>""")

text = text.replace('''                 onmouseover="this.style.background='var(--hover-bg)'" onmouseout="this.style.background='transparent'"''', '')
text = text.replace('''<style>''', '''<style>
.explorer-item { transition: background 0.2s; }
.explorer-item:hover { background: var(--hover-bg) !important; }
''')
text = text.replace('style="display:flex; justify-content:space-between; padding:6px 8px; border-bottom:1px solid var(--border-light); cursor:pointer; font-size:12px;"', 'class="explorer-item" style="display:flex; justify-content:space-between; padding:6px 8px; border-bottom:1px solid var(--border-light); cursor:pointer; font-size:12px;"')

# Ensure we remove any broken string like "onclick="approveUser('${escapeHtml(uid)}','${safeEmail.replace(/'/g, "
text = re.sub(r'onclick="[^"]+"', '', text)
text = re.sub(r'onchange="[^"]+"', '', text)
text = re.sub(r'oninput="[^"]+"', '', text)
text = re.sub(r'onkeydown="[^"]+"', '', text)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(text)
print("All handlers replaced.")
