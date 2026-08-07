import re
with open('dashboard_tmp.html', 'r', encoding='utf-8') as f:
    text = f.read()

pattern = r'async function fetchPCData\(\) \{.*?\n\}'
# Find the exact function by counting braces
start_idx = text.find('async function fetchPCData() {')
if start_idx != -1:
    brace_count = 0
    end_idx = -1
    for i in range(start_idx, len(text)):
        if text[i] == '{':
            brace_count += 1
        elif text[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                end_idx = i + 1
                break
    if end_idx != -1:
        old_func = text[start_idx:end_idx]
        new_func = """async function fetchPCData() {
    if (!config.databaseURL) return;
    
    // Only fetch if admin
    if (!_fbAuth || !_fbAuth.currentUser || _fbAuth.currentUser.email !== MASTER_EMAIL) {
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
        text = text[:start_idx] + new_func + text[end_idx:]
        print("fetchPCData replaced successfully")

with open('dashboard_tmp.html', 'w', encoding='utf-8') as f:
    f.write(text)
