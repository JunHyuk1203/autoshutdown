with open('dashboard_tmp.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re

# deleteSelectedPCs regex
match1 = re.search(r'function deleteSelectedPCs\(\)\s*\{.*?\}\n\s*\}', text, flags=re.DOTALL)
if match1:
    old1 = match1.group(0)
    new1 = """function deleteSelectedPCs() {
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
    text = text.replace(old1, new1)

# deleteOfflinePCs regex
match2 = re.search(r'function deleteOfflinePCs\(\)\s*\{.*?\}\n\s*\}', text, flags=re.DOTALL)
if match2:
    old2 = match2.group(0)
    new2 = """function deleteOfflinePCs() {
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
    text = text.replace(old2, new2)

# syncFavoritesToFirebase
match3 = re.search(r'async function syncFavoritesToFirebase\(favs\)\s*\{.*?\}\n\}', text, flags=re.DOTALL)
if match3:
    old3 = match3.group(0)
    new3 = """async function syncFavoritesToFirebase(favs) {
    if (!(await _checkAuthPermission())) return;
    try {
        await firebase.database().ref("/file_favorites").set(favs);
    } catch(e) {
        console.error("즐겨찾기 저장 실패:", e);
    }
}"""
    text = text.replace(old3, new3)

# ensure loadFavoritesFromFirebase is also covered if it exists
match4 = re.search(r'async function loadFavoritesFromFirebase\(\)\s*\{.*?\}\n\}', text, flags=re.DOTALL)
if match4:
    old4 = match4.group(0)
    new4 = """async function loadFavoritesFromFirebase() {
    if (!(await _checkAuthPermission())) return;
    try {
        const snap = await firebase.database().ref("/file_favorites").once("value");
        const favs = snap.val();
        if (favs && Array.isArray(favs)) {
            localStorage.setItem(FAV_STORAGE_KEY, JSON.stringify(favs));
            renderFavorites();
        }
    } catch (e) {
        console.error("즐겨찾기 로드 실패:", e);
    }
}"""
    text = text.replace(old4, new4)

with open('dashboard_tmp.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Step 9 done")
