# -*- coding: utf-8 -*-
import re

def fix_polling(fname):
    with open(fname, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Add `let expectedExplorerPath = "";` near `let openFileTarget = null;`
    if 'let expectedExplorerPath' not in content:
        content = content.replace('let openFileTarget = null;', 'let openFileTarget = null;\nlet expectedExplorerPath = "";')

    # 2. Update `loadExplorerPath`
    load_pattern = r'function loadExplorerPath\(path = null\) \{.*?\n\}'
    
    new_load = '''function loadExplorerPath(path = null) {
    const targetPath = path !== null ? path : document.getElementById("explorer-path").value.trim();
    const finalPath = targetPath || "DRIVES";
    expectedExplorerPath = finalPath; // Set the expected path
    
    document.getElementById("explorer-list").innerHTML = '<div style="text-align: center; padding-top: 80px; font-size: 12px;">로딩 중...</div>';

    writeCommandToDB(openFileTarget, "list_dir", { path: finalPath }).then(() => {
        if (!explorerInterval) {
            explorerInterval = setInterval(pollExplorerData, 1000);
        }
    });
}'''

    # Because `.*?` might not match up to `\n}` if we have inner blocks?
    # Actually `loadExplorerPath` doesn't have nested braces in the original:
    # function loadExplorerPath(path = null) {
    #     const targetPath = path !== null ? path : document.getElementById("explorer-path").value.trim();
    #     document.getElementById("explorer-list").innerHTML = '<div style="text-align: center; padding-top: 80px; font-size: 12px;">로딩 중...</div>';
    #
    #     writeCommandToDB(openFileTarget, "list_dir", { path: targetPath || "DRIVES" }).then(() => {
    #         if (!explorerInterval) {
    #             explorerInterval = setInterval(pollExplorerData, 1000);
    #         }
    #     });
    # }
    # So `.*?\n}` will match the first `}` which is at the end of `.then(() => { ... })`!
    # Wait, the `.then(() => { ... })` ends with `});\n}`.
    # So `\n}` matches the end of the function!
    # Let's use a simpler replace.

    old_load_str = '''function loadExplorerPath(path = null) {
    const targetPath = path !== null ? path : document.getElementById("explorer-path").value.trim();
    document.getElementById("explorer-list").innerHTML = '<div style="text-align: center; padding-top: 80px; font-size: 12px;">로딩 중...</div>';

    writeCommandToDB(openFileTarget, "list_dir", { path: targetPath || "DRIVES" }).then(() => {
        if (!explorerInterval) {
            explorerInterval = setInterval(pollExplorerData, 1000);
        }
    });
}'''

    if old_load_str in content:
        content = content.replace(old_load_str, new_load)
    else:
        # Fallback to regex if exact match fails
        content = re.sub(r'function loadExplorerPath\(path = null\) \{.*?\n\}', new_load, content, flags=re.DOTALL)

    # 3. Update `pollExplorerData`
    old_poll_str = '''function pollExplorerData() {
    if (!openFileTarget || openFileTarget === "__ALL__") return;
    const url = `${config.databaseURL}/explorer/${openFileTarget}.json` + (config.authKey ? `?auth=${config.authKey}` : "");
    fetch(url).then(r => r.json()).then(data => {
        if (data) renderExplorerList(data);
    }).catch(e => console.error("Explorer poll error:", e));
}'''

    new_poll = '''function pollExplorerData() {
    if (!openFileTarget || openFileTarget === "__ALL__") return;
    const url = `${config.databaseURL}/explorer/${openFileTarget}.json` + (config.authKey ? `?auth=${config.authKey}` : "");
    fetch(url).then(r => r.json()).then(data => {
        if (data) {
            // Ignore stale data from previous path
            if (expectedExplorerPath && data.path !== expectedExplorerPath) {
                return;
            }
            renderExplorerList(data);
        }
    }).catch(e => console.error("Explorer poll error:", e));
}'''

    if old_poll_str in content:
        content = content.replace(old_poll_str, new_poll)
    else:
        # Fallback
        content = re.sub(r'function pollExplorerData\(\) \{.*?\n\}', new_poll, content, flags=re.DOTALL)

    with open(fname, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'Fixed {fname}')

fix_polling('dashboard.html')
fix_polling('index.html')
