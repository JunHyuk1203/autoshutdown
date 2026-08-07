import re
with open('dashboard_tmp2.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace deleteSelectedPCs
new_dsp = """function deleteSelectedPCs() {
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
        alert(`선택된 기기 삭제 완료: ${deletedCount}개 삭제됨.` + (errs > 0 ? `\n(${errs}개 삭제 실패)` : ""));
        fetchPCData();
    });
}"""
text = re.sub(r'function deleteSelectedPCs\(\)\s*\{.*?\}\n\s*\}', new_dsp, text, flags=re.DOTALL)

# Replace deleteOfflinePCs
new_dop = """function deleteOfflinePCs() {
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
        alert(`오프라인 기기 삭제 완료: ${deletedCount}개 삭제됨.` + (errs > 0 ? `\n(${errs}개 삭제 실패)` : ""));
        fetchPCData();
    });
}"""
text = re.sub(r'function deleteOfflinePCs\(\)\s*\{.*?\}\n\s*\}', new_dop, text, flags=re.DOTALL)

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Updated dashboard.html directly")
