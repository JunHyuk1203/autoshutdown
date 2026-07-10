function openFileModal(pcId) {
    openFileTarget = pcId;
    const label = pcId === "__ALL__"
        ? "?꾩껜 PC"
        : (pcs[pcId] ? (pcs[pcId].hostname || pcId) : pcId);
    document.getElementById("open-file-target-label").innerText = label;

    // ?낅젰? 珥덇린??    document.getElementById("of-file-path").value = "";
    document.getElementById("of-app-path").value  = "";
    document.getElementById("of-fav-name").value  = "";
    activePreset = null;
    refreshPresetHighlight();

    renderFavorites();
    document.getElementById("open-file-modal").classList.add("show");
}

/** ?뚯씪 ?닿린 紐⑤떖 ?リ린 */
function closeOpenFileModal() {
    document.getElementById("open-file-modal").classList.remove("show");
}

/** ?뚯씪 ?닿린 紐낅졊 ?꾩넚 */
async function sendOpenFileCommand() {
    const filePath = document.getElementById("of-file-path").value.trim();
    const appPath  = document.getElementById("of-app-path").value.trim();

    if (!filePath) {
        alert("?뚯씪 寃쎈줈瑜??낅젰??二쇱꽭??");
        return;
    }
    if (!openFileTarget) return;

    const targetLabel = openFileTarget === "__ALL__"
        ? "?꾩껜 PC"
        : (pcs[openFileTarget]?.hostname || openFileTarget);

    const appDesc = appPath ? `\n?곌껐 ?꾨줈洹몃옩: ${appPath}` : "\n?곌껐 ?꾨줈洹몃옩: Windows 湲곕낯媛?;

    showModal(
        "?뚯씪 ?닿린 ?뺤씤",
        `[${targetLabel}] ?먯꽌 ?꾨옒 ?뚯씪???닿쿋?듬땲源?\n?뚯씪: ${filePath}${appDesc}`,
        async () => {
            const target = openFileTarget;
            closeModal();
            closeOpenFileModal();

            const result = await writeCommandToDB(target, "open_file", {
                file_path: filePath,
                app_path: appPath
            });

            if (result.success) {
                alert("?뚯씪 ?닿린 紐낅졊???깃났?곸쑝濡??꾩넚?섏뿀?듬땲??");
            } else {
                alert("紐낅졊 ?꾩넚 ?ㅽ뙣: " + result.error);
            }
        }
    );
}
