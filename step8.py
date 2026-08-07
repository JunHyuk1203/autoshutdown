import re
with open('dashboard_tmp.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 5. saveFavoritesToServer
match = re.search(r'async function saveFavoritesToServer\(\)\s*\{.*?\}\n\}', text, flags=re.DOTALL)
if match:
    old_sfs = match.group(0)
    new_sfs = """async function saveFavoritesToServer() {
    if (!openFileTarget || openFileTarget === "__ALL__") return;
    const favs = _favorites[openFileTarget] || [];
    try {
        await firebase.database().ref("/explorer_favorites/" + openFileTarget).set(favs);
    } catch(e) {
        console.error("즐겨찾기 저장 실패:", e);
    }
}"""
    text = text.replace(old_sfs, new_sfs)

# 6. loadFavoritesFromServer
match = re.search(r'async function loadFavoritesFromServer\(\)\s*\{.*?\}\n\}', text, flags=re.DOTALL)
if match:
    old_lfs = match.group(0)
    new_lfs = """async function loadFavoritesFromServer() {
    if (!openFileTarget || openFileTarget === "__ALL__") return;
    try {
        const snap = await firebase.database().ref("/explorer_favorites/" + openFileTarget).once("value");
        const favs = snap.val();
        if (favs && Array.isArray(favs)) {
            localStorage.setItem(FAV_STORAGE_KEY, JSON.stringify(favs));
            renderFavorites();
        }
    } catch (e) {
        console.error("즐겨찾기 로드 실패:", e);
    }
}"""
    text = text.replace(old_lfs, new_lfs)

# 7. pollExplorerData
# Replace from `function pollExplorerData() {` until `}).catch(e => console.error("Explorer poll error:", e));\n}`
match = re.search(r'function pollExplorerData\(\)\s*\{.*?\}\)\.catch\(e => console\.error\("Explorer poll error:", e\)\);\n\}', text, flags=re.DOTALL)
if match:
    old_ped = match.group(0)
    new_ped = """function pollExplorerData() {
    if (!openFileTarget || openFileTarget === "__ALL__") return;
    
    firebase.database().ref("/explorer/" + openFileTarget).once("value").then(snap => {
        const data = snap.val();
        if (data) {
            const gotNorm = normalizePath(data.path);
            const expNorm = normalizePath(expectedExplorerPath);
            if (expectedExplorerPath && gotNorm !== expNorm) {
                const container = document.getElementById("explorer-list");
                if (container && container.innerHTML.includes("로딩 중")) {
                    container.innerHTML = `<div style="text-align: center; padding-top: 80px; font-size: 12px;">데이터 수집 중...<br><br><span style="color:var(--text-muted); font-size:10px;">[Wait] expected: '${escapeHtml(expectedExplorerPath)}', got: '${escapeHtml(data.path)}'</span></div>`;
                }
                return;
            }
            renderExplorerList(data);
        }
    }).catch(e => console.error("Explorer poll error:", e));
}"""
    text = text.replace(old_ped, new_ped)

# 8. loadExplorerPath (which also uses fetch)
match = re.search(r'async function loadExplorerPath\(path\)\s*\{.*?\}\n\}', text, flags=re.DOTALL)
if match:
    old_lep = match.group(0)
    new_lep = """async function loadExplorerPath(path) {
    if (!openFileTarget || openFileTarget === "__ALL__") return;
    
    expectedExplorerPath = path;
    const container = document.getElementById("explorer-list");
    container.innerHTML = '<div style="text-align: center; padding-top: 80px; font-size: 12px;">로딩 중...</div>';
    document.getElementById("explorer-path").value = path;
    
    // Command request
    const result = await writeCommandToDB(openFileTarget, "list_dir", path);
    if (!result.success) {
        container.innerHTML = '<div style="color:var(--danger); padding:10px; font-size:12px;">경로 요청 실패. 관리자 권한을 확인하세요.</div>';
        expectedExplorerPath = "";
        return;
    }
    
    if (typeof explorerInterval !== 'undefined' && explorerInterval) clearInterval(explorerInterval);
    explorerInterval = setInterval(pollExplorerData, 1500);
}"""
    text = text.replace(old_lep, new_lep)

with open('dashboard_tmp.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Step 8 done")
