# -*- coding: utf-8 -*-

funcs = '''
function openFileModal(pcId) {
    openFileTarget = pcId;
    const label = pcId === "__ALL__"
        ? "전체 PC"
        : (pcs[pcId] ? (pcs[pcId].hostname || pcId) : pcId);
    document.getElementById("open-file-target-label").innerText = label;

    // 입력값 초기화
    document.getElementById("of-file-path").value = "";
    document.getElementById("of-app-path").value  = "";
    document.getElementById("of-fav-name").value  = "";
    activePreset = null;
    refreshPresetHighlight();

    renderFavorites();
    loadFavoritesFromServer(); // 모달 오픈 시 다시 Firebase 원격 데이터 내려받기 동기화
    document.getElementById("open-file-modal").classList.add("show");
    if (pcId !== "__ALL__") loadExplorerPath("DRIVES");
    else { document.getElementById("explorer-list").innerHTML = "<div style='text-align: center; padding-top: 80px; font-size: 12px;'>전체 PC에서는 탐색기를 사용할 수 없습니다.</div>"; document.getElementById("explorer-path").value = ""; }
}

/** 파일 열기 모달 닫기 */
function closeOpenFileModal() {
    document.getElementById("open-file-modal").classList.remove("show");
    if (typeof explorerInterval !== 'undefined' && explorerInterval) { clearInterval(explorerInterval); explorerInterval = null; }
}

/** 파일 열기 명령 전송 */
async function sendOpenFileCommand() {
    const filePath = document.getElementById("of-file-path").value.trim();
    const appPath  = document.getElementById("of-app-path").value.trim();

    if (!filePath) {
        alert("파일 경로를 입력해 주세요.");
        return;
    }
    if (!openFileTarget) return;

    const targetLabel = openFileTarget === "__ALL__"
        ? "전체 PC"
        : (pcs[openFileTarget]?.hostname || openFileTarget);

    const appDesc = appPath ? `\\n연결 프로그램: ${appPath}` : "\\n연결 프로그램: Windows 기본값";

    showModal(
        "파일 열기 확인",
        `[${targetLabel}] 에서 아래 파일을 여시겠습니까?\\n파일: ${filePath}${appDesc}`,
        async () => {
            const target = openFileTarget;
            closeModal();
            closeOpenFileModal();

            const result = await writeCommandToDB(target, "open_file", {
                file_path: filePath,
                app_path: appPath
            });

            if (result.success) {
                alert("파일 열기 명령이 성공적으로 전송되었습니다.");
            } else {
                alert("명령 전송 실패: " + result.error);
            }
        }
    );
}
'''

def restore(fname):
    with open(fname, 'r', encoding='utf-8') as f:
        content = f.read()
    if 'function openFileModal' not in content:
        content = content.replace('</script>', funcs + '\n</script>')
        with open(fname, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Restored to {fname}')

restore('dashboard.html')
restore('index.html')
