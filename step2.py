import re
with open('dashboard_tmp.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace writeCommandToDB
old_write = """async function writeCommandToDB(target, action, message = "") {
    if (!(await _checkAuthPermission())) return;
    let url = "";
    let method = "PUT";
    let bodyData = {};
    
    if (target === "__ALL__") {
        url = `${config.databaseURL}/commands/__ALL__.json`;
        bodyData = {
            action: action,
            message: message,
            timestamp: Date.now() / 1000.0
        };
    } else {
        url = `${config.databaseURL}/commands/${target}.json`;
        method = "POST";
        bodyData = {
            action: action,
            message: message,
            timestamp: Date.now() / 1000.0
        };
    }
    
    if (config.authKey) {
        url += `?auth=${config.authKey}`;
    }
    
    try {
        const response = await fetch(url, {
            method: method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(bodyData)
        });
        if (!response.ok) throw new Error(": " + response.status);
        return { success: true };
    } catch (e) {
        console.error("writeCommandToDB error:", e);
        alert(" : " + e.message);
        return { success: false };
    }
}"""

# Since encodings could mess up characters, let's use regex matching the body of writeCommandToDB
match = re.search(r'async function writeCommandToDB\(target,\s*action,\s*message\s*=\s*""\)\s*\{.*?\n\}', text, flags=re.DOTALL)
if match:
    new_write = """async function writeCommandToDB(target, action, message = "") {
    if (!(await _checkAuthPermission())) return;
    
    const bodyData = {
        action: action,
        message: message,
        timestamp: Date.now() / 1000.0
    };
    
    try {
        if (target === "__ALL__") {
            await firebase.database().ref("/commands/__ALL__").set(bodyData);
        } else {
            await firebase.database().ref("/commands/" + target).push(bodyData);
        }
        return { success: true };
    } catch (e) {
        console.error("writeCommandToDB error:", e);
        if (e.code === 'PERMISSION_DENIED') {
            alert("명령 전송 실패: 권한이 없습니다 (관리자 로그인 필요).");
        } else {
            alert("명령 전송 실패: " + e.message);
        }
        return { success: false };
    }
}"""
    text = text.replace(match.group(0), new_write)
else:
    print("writeCommandToDB match failed")

with open('dashboard_tmp.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Applied writeCommandToDB replacement")
