import re
import os

def patch_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    html_inject = '''
          <!-- 파일 탐색기 영역 -->
          <div style="border-top: 1px solid var(--border-light); padding-top: 16px; margin-bottom: 16px;">
              <div style="display: flex; gap: 8px; margin-bottom: 8px;">
                  <button class="action-btn" onclick="explorerGoUp()" style="padding: 0 10px; font-weight:bold;">↑ 상위</button>
                  <input class="form-input" id="explorer-path" type="text" placeholder="경로 입력 (예: C:\)" style="flex-grow: 1; margin-bottom: 0;" onkeydown="if(event.key==='Enter') loadExplorerPath()">
                  <button class="action-btn action-btn-teal" onclick="loadExplorerPath()" style="padding: 0 12px;">이동</button>
              </div>
              <div id="explorer-list" style="height: 200px; overflow-y: auto; background: var(--bg-card); border: 1px solid var(--border-light); border-radius: 6px; padding: 4px;">
                  <div style="text-align: center; color: var(--text-muted); padding-top: 80px; font-size: 12px;">PC를 선택하거나 경로를 입력하세요.</div>
              </div>
          </div>
'''
    
    content = content.replace('<!-- 파일 경로 -->', html_inject + '<!-- 파일 경로 -->')
    
    js_inject = '''
let explorerInterval = null;

function loadExplorerPath(path = null) {
    if (!openFileTarget || openFileTarget === "__ALL__") {
        document.getElementById("explorer-list").innerHTML = '<div style="text-align: center; padding-top: 80px; font-size: 12px;">전체 PC에서는 탐색기를 사용할 수 없습니다.</div>';
        return;
    }
    const targetPath = path !== null ? path : document.getElementById("explorer-path").value.trim();
    document.getElementById("explorer-list").innerHTML = '<div style="text-align: center; padding-top: 80px; font-size: 12px;">로딩 중...</div>';
    
    writeCommandToDB(openFileTarget, "list_dir", { path: targetPath || "DRIVES" }).then(() => {
        if (!explorerInterval) {
            explorerInterval = setInterval(pollExplorerData, 1000);
        }
    });
}

function explorerGoUp() {
    const currentPath = document.getElementById("explorer-path").value.trim();
    if (!currentPath || currentPath === "DRIVES") return;
    
    let parts = currentPath.split('\\\\').filter(p => p);
    if (parts.length <= 1) {
        loadExplorerPath("DRIVES");
    } else {
        parts.pop();
        loadExplorerPath(parts.join('\\\\') + '\\\\');
    }
}

function pollExplorerData() {
    if (!openFileTarget || openFileTarget === "__ALL__") return;
    const url = `${config.databaseURL}/explorer/${openFileTarget}.json` + (config.authKey ? `?auth=${config.authKey}` : "");
    fetch(url).then(r => r.json()).then(data => {
        if (data) renderExplorerList(data);
    }).catch(e => console.error("Explorer poll error:", e));
}

function renderExplorerList(data) {
    const container = document.getElementById("explorer-list");
    const pathInput = document.getElementById("explorer-path");
    if (data.path && document.activeElement !== pathInput) {
        pathInput.value = data.path;
    }
    
    if (data.error) {
        container.innerHTML = `<div style="color:var(--danger); padding:10px; font-size:12px;">오류: ${data.error}</div>`;
        return;
    }
    
    if (!data.items || data.items.length === 0) {
        container.innerHTML = '<div style="text-align:center; color:var(--text-muted); padding-top:80px; font-size:12px;">빈 폴더입니다.</div>';
        return;
    }
    
    let html = '';
    data.items.forEach(item => {
        const isFolder = item.type === "folder";
        const icon = isFolder ? "📁" : "📄";
        const sizeStr = isFolder ? "" : (item.size > 1024*1024 ? (item.size/(1024*1024)).toFixed(1)+'MB' : Math.ceil(item.size/1024)+'KB');
        
        const safeName = item.name.replace(/\\\\/g, "\\\\\\\\").replace(/'/g, "\\\\\\'").replace(/"/g, "&quot;");
        
        html += `
            <div style="display:flex; justify-content:space-between; padding:6px 8px; border-bottom:1px solid var(--border-light); cursor:pointer; font-size:12px;"
                 onmouseover="this.style.background='var(--hover-bg)'" onmouseout="this.style.background='transparent'"
                 onclick="selectExplorerItem('${safeName}', ${isFolder})">
                <div style="display:flex; gap:6px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                    <span>${icon}</span>
                    <span>${item.name}</span>
                </div>
                <div style="color:var(--text-muted); font-size:11px;">${sizeStr}</div>
            </div>
        `;
    });
    
    if (container.getAttribute('data-hash') !== String(html.length)) {
        container.innerHTML = html;
        container.setAttribute('data-hash', String(html.length));
    }
}

function selectExplorerItem(name, isFolder) {
    const currentPath = document.getElementById("explorer-path").value.trim();
    let newPath = "";
    if (currentPath === "DRIVES" || !currentPath) {
        newPath = name;
    } else {
        newPath = currentPath.endsWith('\\\\') ? currentPath + name : currentPath + '\\\\' + name;
    }
    
    document.getElementById("of-file-path").value = newPath;
    
    if (isFolder) {
        loadExplorerPath(newPath);
    }
}
'''
    
    content = content.replace('function openFileModal(pcId) {', js_inject + '\nfunction openFileModal(pcId) {')
    
    content = content.replace(
        'document.getElementById("open-file-modal").classList.remove("show");',
        'document.getElementById("open-file-modal").classList.remove("show");\n    if (explorerInterval) { clearInterval(explorerInterval); explorerInterval = null; }'
    )
    
    content = content.replace(
        'document.getElementById("open-file-modal").classList.add("show");',
        'document.getElementById("open-file-modal").classList.add("show");\n    if (pcId !== "__ALL__") loadExplorerPath("DRIVES");\n    else { document.getElementById("explorer-list").innerHTML = "<div style=\'text-align: center; padding-top: 80px; font-size: 12px;\'>전체 PC에서는 탐색기를 사용할 수 없습니다.</div>"; document.getElementById("explorer-path").value = ""; }'
    )
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

patch_file('index.html')
patch_file('dashboard.html')
print("Successfully patched HTML files.")
