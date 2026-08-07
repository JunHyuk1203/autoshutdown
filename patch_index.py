import re

with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

# Remove setPollerInterval
target_init = """function initializeDashboard() {
    document.getElementById("label-connected-db").innerText = `연결 주소: ${config.databaseURL}`;
    
    // 첫 조회 실행
    fetchPCData();
    
    // 기본적으로 5초마다 REST API 호출 (트래픽 절약), 창 관리 시 1초로 가속
    setPollerInterval(5000);
}"""

replacement_init = """function initializeDashboard() {
    document.getElementById("label-connected-db").innerText = `연결 주소: ${config.databaseURL}`;
    
    // Real-time synchronization
    startRealtimeSync();
}"""

if target_init in text:
    text = text.replace(target_init, replacement_init)

# Replace fetchPCData with startRealtimeSync
target_fetch = """// REST API로 Firebase DB의 pcs 노드 동기화
async function fetchPCData() {
    if (!config.databaseURL) return;
    
    // 이중 가드: 인증 실패 상태면 즉시 차단
    if (APP_ACCESS_GRANTED !== true) return;
    
    // Firebase Auth 체크
    if (!_fbAuth || !_fbAuth.currentUser) {
        setAccessGranted(false);
        return;
    }
    
    try {
        const snapshot = await firebase.database().ref("/pcs").once("value");
        const data = snapshot.val() || {};
        
        const serverNowMs = Date.now() + serverTimeOffset;
        pcs = data;
        
        renderPCGrid(serverNowMs);
        updateStatistics(serverNowMs);
        
        if (_wmPcId && document.getElementById('windows-modal').classList.contains('show')) {
            const pc = pcs[_wmPcId];
            if (pc) {
                const raw = pc.windows;
                let newWindows = [];
                if (Array.isArray(raw)) {
                    newWindows = raw;
                } else if (raw && typeof raw === 'object') {
                    newWindows = Object.values(raw);
                }
                
                if (JSON.stringify(_wmAllWindows) !== JSON.stringify(newWindows)) {
                    _wmAllWindows = newWindows;
                    const q = document.getElementById('wm-search-input').value.trim().toLowerCase();
                    if (q) { filterWindowsList(); } else { renderWindowsList(_wmAllWindows); }
                }
            }
        }
    } catch (e) {
        console.error("fetchPCData error:", e);
    }
}"""

replacement_fetch = """// Realtime Firebase DB sync
function startRealtimeSync() {
    if (!config.databaseURL) return;
    
    // 이중 가드: 인증 실패 상태면 즉시 차단
    if (APP_ACCESS_GRANTED !== true) return;
    
    // Firebase Auth 체크
    if (!_fbAuth || !_fbAuth.currentUser) {
        setAccessGranted(false);
        return;
    }
    
    if (window._pcsListener) {
        firebase.database().ref("/pcs").off("value", window._pcsListener);
    }
    
    window._pcsListener = firebase.database().ref("/pcs").on("value", snapshot => {
        const data = snapshot.val() || {};
        
        const serverNowMs = Date.now() + serverTimeOffset;
        pcs = data;
        
        renderPCGrid(serverNowMs);
        updateStatistics(serverNowMs);
        
        if (_wmPcId && document.getElementById('windows-modal').classList.contains('show')) {
            const pc = pcs[_wmPcId];
            if (pc) {
                const raw = pc.windows;
                let newWindows = [];
                if (Array.isArray(raw)) {
                    newWindows = raw;
                } else if (raw && typeof raw === 'object') {
                    newWindows = Object.values(raw);
                }
                
                if (JSON.stringify(_wmAllWindows) !== JSON.stringify(newWindows)) {
                    _wmAllWindows = newWindows;
                    const q = document.getElementById('wm-search-input').value.trim().toLowerCase();
                    if (q) { filterWindowsList(); } else { renderWindowsList(_wmAllWindows); }
                }
            }
        }
    }, error => {
        console.error("Firebase sync error:", error);
    });
    
    // Also set an interval just to re-render the time tags "X seconds ago" without fetching new data
    if (window._renderInterval) clearInterval(window._renderInterval);
    window._renderInterval = setInterval(() => {
        if (APP_ACCESS_GRANTED === true) {
            renderPCGrid(Date.now() + serverTimeOffset);
        }
    }, 1000);
}

async function fetchPCData() {
    // Deprecated. Handled by startRealtimeSync.
}"""

if target_fetch in text:
    text = text.replace(target_fetch, replacement_fetch)

# Remove setPollerInterval calls
text = text.replace("setPollerInterval(1000);", "")
text = text.replace("setPollerInterval(currentPollerMs);", "")
text = text.replace("setPollerInterval(5000);", "")
text = text.replace("let pollerInterval = null;", "")
text = text.replace("let currentPollerMs = 5000;", "")
text = text.replace("function setPollerInterval(ms) {", "function setPollerInterval(ms) { return; // Deprecated")

# Wait, there's another place where fetchPCData is called:
text = text.replace("fetchPCData();\n                setPollerInterval(currentPollerMs);", "startRealtimeSync();")

with open("index.html", "w", encoding="utf-8") as f:
    f.write(text)

print("index.html patched with Real-Time sync")
