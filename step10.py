with open('dashboard_tmp.html', 'r', encoding='utf-8') as f:
    text = f.read()

def extract_func(text, func_name):
    start_idx = text.find(f'async function {func_name}(')
    if start_idx == -1:
        start_idx = text.find(f'function {func_name}(')
    if start_idx == -1:
        return None, None
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
        return start_idx, end_idx
    return None, None

def replace_func(text, func_name, new_func):
    start_idx, end_idx = extract_func(text, func_name)
    if start_idx is not None:
        return text[:start_idx] + new_func + text[end_idx:]
    return text

new_cus = """async function checkUserStatus(uid) {
    try {
        const snapshot = await firebase.database().ref("/users/" + uid).once("value");
        return snapshot.val();
    } catch (e) { 
        if(e.code === 'PERMISSION_DENIED') return { permission_denied: true };
        return null; 
    }
}"""
text = replace_func(text, "checkUserStatus", new_cus)

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
text = replace_func(text, "requestApproval", new_ra)

new_dsp = """async function deleteSelectedPCs() {
    if (selectedPcs.size === 0) return;
    showModal("삭제 확인", `선택된 ${selectedPcs.size}대의 기기를 목록에서 삭제하시겠습니까?`, async () => {
        closeModal();
        let deletedCount = 0;
        let errs = 0;
        for (const pcId of Array.from(selectedPcs)) {
            try {
                await firebase.database().ref("/pcs/" + pcId).remove();
                deletedCount++;
            } catch(e) { errs++; }
        }
        selectedPcs.clear();
        alert(`선택된 기기 삭제 완료: ${deletedCount}개 삭제됨.` + (errs > 0 ? `\\n(${errs}개 삭제 실패)` : ""));
        fetchPCData();
    });
}"""
text = replace_func(text, "deleteSelectedPCs", new_dsp)

new_dop = """async function deleteOfflinePCs() {
    showModal("오프라인 기기 삭제", "연결이 끊긴 모든 오프라인 기기를 목록에서 삭제하시겠습니까?", async () => {
        closeModal();
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
                } catch(e) { errs++; }
            }
        }
        alert(`오프라인 기기 삭제 완료: ${deletedCount}개 삭제됨.` + (errs > 0 ? `\\n(${errs}개 삭제 실패)` : ""));
        fetchPCData();
    });
}"""
text = replace_func(text, "deleteOfflinePCs", new_dop)

with open('dashboard_tmp.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Step 10 done")
