import re

with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. replace restoreUser
pat_restore = re.compile(r'async function restoreUser\(uid,\s*email\)\s*\{.*?\s*\}\s*catch\(e\)\s*\{\s*alert\("오류: "\s*\+\s*e\.message\);\s*\}\s*\}', re.DOTALL)
new_restore = '''async function restoreUser(uid, email) {
    if (!confirm(email + " 사용자를 복구하시겠습니까?")) return;
    try {
        await firebase.database().ref("/users/" + uid).set({ email: email, approved: true, approvedAt: Date.now() });
        await firebase.database().ref("/pending_users/" + uid).remove();
        alert("🟢 " + email + " 복구되었습니다.");
    } catch(e) { alert("오류: " + e.message); }
}'''

# 2. replace approveUser
pat_approve = re.compile(r'async function approveUser\(uid,\s*email\)\s*\{.*?\s*\}\s*catch\(e\)\s*\{\s*alert\("오류: "\s*\+\s*e\.message\);\s*\}\s*\}', re.DOTALL)
new_approve = '''async function approveUser(uid, email) {
    if (!confirm(email + " 사용자를 승인하시겠습니까?")) return;
    try {
        await firebase.database().ref("/users/" + uid).set({ email, approved: true, role: "user", approvedAt: Date.now() });
        await firebase.database().ref("/pending_users/" + uid).remove();
        alert("✅ " + email + " 사용자가 승인되었습니다.");
    } catch(e) { alert("오류: " + e.message); }
}'''

# 3. replace rejectUser
pat_reject = re.compile(r'async function rejectUser\(uid,\s*email\)\s*\{.*?\s*\}\s*catch\(e\)\s*\{\s*alert\("오류: "\s*\+\s*e\.message\);\s*\}\s*\}', re.DOTALL)
new_reject = '''async function rejectUser(uid, email) {
    if (!confirm(email + " 가입 요청을 거부하시겠습니까?")) return;
    try {
        await firebase.database().ref("/users/" + uid).set({ email: email, approved: false, rejectedAt: Date.now() });
        await firebase.database().ref("/pending_users/" + uid).remove();
        alert("❌ " + email + " 가입 요청이 거부되었습니다.");
    } catch(e) { alert("오류: " + e.message); }
}'''


if pat_restore.search(text):
    text = pat_restore.sub(new_restore, text)
    print("Replaced restoreUser")
if pat_approve.search(text):
    text = pat_approve.sub(new_approve, text)
    print("Replaced approveUser")
if pat_reject.search(text):
    text = pat_reject.sub(new_reject, text)
    print("Replaced rejectUser")

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
