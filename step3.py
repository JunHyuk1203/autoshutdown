import re
with open('dashboard_tmp.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Add serverTimeOffset tracker near global variables
if 'let serverTimeOffset = 0;' not in text:
    text = text.replace('let _wmAllWindows = [];', 'let _wmAllWindows = [];\nlet serverTimeOffset = 0;\nfirebase.database().ref(".info/serverTimeOffset").on("value", snap => { serverTimeOffset = snap.val() || 0; });')

# Replace fetchPCData body
# The regex must capture from async function fetchPCData() to the end of the try/catch block.
# Let's match from async function fetchPCData() { until `isFetchingPC = false;`

pattern = r'async function fetchPCData\(\)\s*\{.*?isFetchingPC = false;\n\}'
match = re.search(pattern, text, flags=re.DOTALL)
if match:
    old_func = match.group(0)
    # Re-write the function to use Firebase SDK
    new_func = """async function fetchPCData() {
    if (!config.databaseURL) return;
    if (isFetchingPC) return;
    isFetchingPC = true;
    
    // Only fetch if admin
    if (!_fbAuth || !_fbAuth.currentUser || _fbAuth.currentUser.email !== MASTER_EMAIL) {
        isFetchingPC = false;
        return;
    }
    
    try {
        const snapshot = await firebase.database().ref("/pcs").once("value");
        const data = snapshot.val() || {};
        
        const serverNowMs = Date.now() + serverTimeOffset;
        let onlineCount = 0;
        let offlineCount = 0;
        
        pcs = data;
        
        const currentPcs = new Set(Object.keys(pcs));
        for (const pcId of selectedPcs) {
            if (!currentPcs.has(pcId)) selectedPcs.delete(pcId);
        }
        
        // Count online/offline based on heartbeats
        for (const id in pcs) {
            const pc = pcs[id];
            const ts = (pc.heartbeat && pc.heartbeat.timestamp) ? pc.heartbeat.timestamp * 1000 : 0;
            const diffSec = (serverNowMs - ts) / 1000;
            if (ts > 0 && diffSec <= 20) {
                onlineCount++;
            } else {
                offlineCount++;
            }
        }
        
        document.getElementById("stat-total").innerText = Object.keys(pcs).length;
        document.getElementById("stat-online").innerText = onlineCount;
        document.getElementById("stat-offline").innerText = offlineCount;
        
        renderPCList();
        
        // update windows modal if open
        if (document.getElementById('windows-modal').classList.contains('show') && _wmPcId && pcs[_wmPcId]) {
            const hw = pcs[_wmPcId].heartbeat && pcs[_wmPcId].heartbeat.windows;
            if (hw) {
                let wList = [];
                try {
                    if (typeof hw === 'string') wList = JSON.parse(hw);
                    else wList = hw;
                } catch(e) {}
                const sv = document.getElementById('wm-search-input').value.toLowerCase().trim();
                _wmAllWindows = wList;
                if (sv) {
                    wList = wList.filter(w => w.title && w.title.toLowerCase().includes(sv));
                }
                renderWindowsList(wList);
            }
        }
    } catch (e) {
        console.error("fetchPCData error:", e);
        if (e.code === 'PERMISSION_DENIED') {
            console.error("Firebase 접근 권한이 없습니다 (Admin 아님).");
        }
    }
    
    isFetchingPC = false;
}"""
    text = text.replace(old_func, new_func)
else:
    print("fetchPCData match failed")

with open('dashboard_tmp.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Applied fetchPCData replacement")
