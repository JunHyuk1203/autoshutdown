with open('dashboard_tmp.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re

# 1. checkUserStatus
old_cus = """async function checkUserStatus(uid) {
    try {
        const r = await fetch(FB_PROJECT.databaseURL + "/users/" + uid + ".json");
        const val = await r.json();
        return val; // Returns object { approved, revokedAt, rejectedAt } or null
    } catch { return null; }
}"""
new_cus = """async function checkUserStatus(uid) {
    try {
        const snapshot = await firebase.database().ref("/users/" + uid).once("value");
        return snapshot.val();
    } catch (e) { 
        if(e.code === 'PERMISSION_DENIED') return { permission_denied: true };
        return null; 
    }
}"""
text = text.replace(old_cus, new_cus)

# 2. requestApproval (pending_users PUT)
old_ra = """async function requestApproval(user) {
    try {
        await fetch(FB_PROJECT.databaseURL + "/pending_users/" + user.uid + ".json", {
            method: "PUT", headers: {"Content-Type":"application/json"},
            body: JSON.stringify({ email: user.email, displayName: user.displayName || user.email.split("@")[0], requestedAt: Date.now() })
        });
    } catch(e) { console.error(e); }
}"""
new_ra = """async function requestApproval(user) {
    try {
        await firebase.database().ref("/pending_users/" + user.uid).set({
            email: user.email,
            displayName: user.displayName || user.email.split("@")[0],
            requestedAt: Date.now(),
            requestType: "new"
        });
    } catch(e) { console.error(e); }
}"""
text = text.replace(old_ra, new_ra)

# 3. deleteOfflinePCs
match = re.search(r'async function deleteOfflinePCs\(\)\s*\{.*?\}\n\s*\}', text, flags=re.DOTALL)
if match:
    old_dof = match.group(0)
    new_dof = """async function deleteOfflinePCs() {
    if (!(await _checkAdminPermission())) return;
    
    let deletedCount = 0;
    let errs = 0;
    const serverNowMs = Date.now() + serverTimeOffset;
    
    for (const pcId in pcs) {
        const pc = pcs[pcId];
        const ts = (pc.heartbeat && pc.heartbeat.timestamp) ? pc.heartbeat.timestamp * 1000 : 0;
        const diffSec = (serverNowMs - ts) / 1000;
        if (ts === 0 || diffSec > 20) {
            try {
                await firebase.database().ref("/pcs/" + pcId).remove();
                deletedCount++;
            } catch(e) {
                errs++;
            }
        }
    }
    
    alert(`오프라인 기기 삭제 완료: ${deletedCount}개 삭제됨.` + (errs > 0 ? `\\n(${errs}개 삭제 실패)` : ""));
    fetchPCData();
}"""
    text = text.replace(old_dof, new_dof)

# 4. deleteSelectedPCs
match = re.search(r'async function deleteSelectedPCs\(\)\s*\{.*?\}\n\s*\}', text, flags=re.DOTALL)
if match:
    old_dsp = match.group(0)
    new_dsp = """async function deleteSelectedPCs() {
    if (!(await _checkAdminPermission())) return;
    
    if (selectedPcs.size === 0) return;
    let deletedCount = 0;
    let errs = 0;
    
    for (const pcId of selectedPcs) {
        try {
            await firebase.database().ref("/pcs/" + pcId).remove();
            deletedCount++;
        } catch(e) {
            errs++;
        }
    }
    
    selectedPcs.clear();
    alert(`선택된 기기 삭제 완료: ${deletedCount}개 삭제됨.` + (errs > 0 ? `\\n(${errs}개 삭제 실패)` : ""));
    fetchPCData();
}"""
    text = text.replace(old_dsp, new_dsp)

with open('dashboard_tmp.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Step 7 done")
