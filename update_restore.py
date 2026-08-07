import sys

sys.stdout.reconfigure(encoding="utf-8")
with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

restore_code = """async function restoreUser(uid, email) {
    if (!confirm(`${email} 계정의 접근 권한을 복구하시겠습니까?`)) return;
    try {
        await firebase.database().ref("/users/" + uid + "/approved").set(true);
        // Clear security log if exists
        await firebase.database().ref("/security_logs/" + uid).remove();
        alert("권한이 복구되었습니다.");
        // render again whatever tab is active
        if (document.getElementById('security-list-container').style.display === 'block') {
            renderSecurityLogs();
        } else {
            renderApprovedUsers();
        }
    } catch (e) {
        alert("복구 실패: " + e.message);
    }
}"""

# The original restoreUser probably looks like:
# async function restoreUser(uid, email) {
# ...
# }
# Let's use regex to replace it
import re
text = re.sub(r'async function restoreUser\(uid, email\) \{[\s\S]*?catch \(e\) \{[\s\S]*?\}[\s\S]*?\}', restore_code, text)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(text)
print("Restore logic updated.")
