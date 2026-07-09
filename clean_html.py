# -*- coding: utf-8 -*-
import os
import re

def clean_file(fname):
    with open(fname, 'r', encoding='utf-8') as f:
        content = f.read()

    # Fix HTML duplicates
    html_block = '''          <!-- 파일 탐색기 영역 -->
          <div style="border-top: 1px solid var(--border-light); padding-top: 16px; margin-bottom: 16px;">
              <div style="display: flex; gap: 8px; margin-bottom: 8px;">
                  <button class="action-btn" onclick="explorerGoUp()" style="padding: 0 10px; font-weight:bold;">↑ 상위</button>
                  <input class="form-input" id="explorer-path" type="text" placeholder="경로 입력 (예: C:\)" style="flex-grow: 1; margin-bottom: 0;" onkeydown="if(event.key==='Enter') loadExplorerPath()">
                  <button class="action-btn action-btn-teal" onclick="loadExplorerPath()" style="padding: 0 12px;">이동</button>
              </div>
              <div id="explorer-list" style="height: 200px; overflow-y: auto; background: var(--bg-card); border: 1px solid var(--border-light); border-radius: 6px; padding: 4px;">
                  <div style="text-align: center; color: var(--text-muted); padding-top: 80px; font-size: 12px;">PC를 선택하거나 경로를 입력하세요.</div>
              </div>
          </div>'''
    
    # Remove all occurrences of the HTML block
    while html_block in content:
        content = content.replace(html_block, '', 1)
    
    # Re-add it once before <!-- 파일 경로 -->
    content = content.replace('<!-- 파일 경로 -->', html_block + '\n<!-- 파일 경로 -->')

    # Fix JS duplicates
    # Remove all loadExplorerPath, pollExplorerData, renderExplorerList, explorerGoUp, selectExplorerItem blocks
    # It's easier to find the start and end of this block
    js_start = 'let explorerInterval = null;'
    js_end = 'function openWindowsModal(pcId) {'
    
    if js_start in content and js_end in content:
        # get all content before js_start and after js_end
        parts = content.split(js_start)
        first_part = parts[0]
        last_part = js_end + parts[-1].split(js_end, 1)[1]
        
        clean_js = '''let explorerInterval = null;
let currentExplorerPath = "";

function loadExplorerPath(path = null) {
    const targetPath = path !== null ? path : document.getElementById("explorer-path").value.trim();
    document.getElementById("explorer-list").innerHTML = '<div style="text-align: center; padding-top: 80px; font-size: 12px;">로딩 중...</div>';
    
    writeCommandToDB(openFileTarget, "list_dir", { path: targetPath || "DRIVES" }).then(() => {
        if (!explorerInterval) {
            explorerInterval = setInterval(pollExplorerData, 1000);
        }
    });
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
                <div style="color:var(--text-muted); flex-shrink:0;">${sizeStr}</div>
            </div>
        `;
    });
    
    container.innerHTML = html;
    currentExplorerPath = data.path || "";
    
    if (data.status === "done") {
        if (explorerInterval) {
            clearInterval(explorerInterval);
            explorerInterval = null;
        }
    }
}

function explorerGoUp() {
    if (!currentExplorerPath) return;
    let parts = currentExplorerPath.replace(/\\\\$/, "").split("\\\\");
    if (parts.length <= 1) {
        loadExplorerPath("DRIVES");
    } else {
        parts.pop();
        let upPath = parts.join("\\\\");
        if (upPath.length === 2 && upPath.endsWith(":")) upPath += "\\\\";
        loadExplorerPath(upPath);
    }
}

function selectExplorerItem(name, isFolder) {
    if (isFolder) {
        let newPath = "";
        if (currentExplorerPath === "DRIVES" || !currentExplorerPath) {
            newPath = name;
        } else {
            let base = currentExplorerPath.endsWith("\\\\") ? currentExplorerPath : currentExplorerPath + "\\\\";
            newPath = base + name;
        }
        loadExplorerPath(newPath);
    } else {
        let filePath = "";
        if (currentExplorerPath === "DRIVES" || !currentExplorerPath) return;
        let base = currentExplorerPath.endsWith("\\\\") ? currentExplorerPath : currentExplorerPath + "\\\\";
        filePath = base + name;
        document.getElementById("of-file-path").value = filePath;
    }
}

'''
        content = first_part + clean_js + last_part

    with open(fname, 'w', encoding='utf-8') as f:
        f.write(content)

clean_file('dashboard.html')
clean_file('index.html')
print('Cleaned up duplicates in HTML')
