import re

with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Remove duplicate checkPendingApproval and reRequestApproval block
block_to_remove = re.search(r'// ── 가입 승인 확인 \(수동 새로고침\) ──.*?alert\("재요청 실패: " \+ e\.message\);\n}', text, re.DOTALL)
if block_to_remove:
    text = text.replace(block_to_remove.group(0), "")

# Replace the original checkPendingApproval
old_check = r'''// ── 가입 승인 확인 \(2단계 완료 체크\) ──
async function checkPendingApproval\(\) \{
    if \(!_fbAuth \|\| !_fbAuth\.currentUser\) return;
    const user = _fbAuth\.currentUser;
    const approved = await _isApproved\(user\.uid\);
    if \(approved\) \{
        _enterDashboard\(user\);
    \} else \{
        alert\("아직 관리자 승인 대기중입니다\.\\n잠시 후 다시 시도해주세요\."\);
    \}
\}'''

new_check = '''// ── 가입 승인 확인 (수동 새로고침) ──
async function checkPendingApproval() {
    if (!_fbAuth || !_fbAuth.currentUser) return;
    const user = _fbAuth.currentUser;
    const status = await _getApprovalStatus(user.uid);
    if (status === true) {
        alert("승인되었습니다!");
        _enterDashboard(user);
    } else if (status === false) {
        alert("관리자가 가입을 거부했습니다.");
        document.getElementById("pending-title").textContent = "가입 거부됨";
        document.getElementById("pending-desc").innerHTML = "관리자가 가입을 거부했습니다.";
        document.getElementById("pending-rerequest-btn").style.display = "inline-block";
    } else {
        alert("아직 관리자 승인 대기중입니다.");
    }
}

async function reRequestApproval() {
    if (!_fbAuth || !_fbAuth.currentUser) return;
    const user = _fbAuth.currentUser;
    try {
        await fetch(FB_PROJECT.databaseURL + "/users/" + user.uid + "/approved.json", {
            method: "DELETE" // resets to null
        });
        await _savePending(user);
        alert("승인을 다시 요청했습니다.");
        
        document.getElementById("pending-title").textContent = "관리자 확인 대기중";
        document.getElementById("pending-desc").innerHTML = "이메일 인증이 완료되었습니다.<br>보안을 위해 관리자 승인이 필요합니다.";
        document.getElementById("pending-rerequest-btn").style.display = "none";
    } catch (e) {
        alert("재요청 실패: " + e.message);
    }
}'''

text = re.sub(old_check, new_check, text, flags=re.DOTALL)

# Replace rejectUser
old_reject = r'''async function rejectUser\(uid, email\) \{
    if \(!confirm\(email \+ " 님의 요청을 거부하시겠습니까\?"\)\) return;
    try \{
        await fetch\(FB_PROJECT\.databaseURL \+ "/pending_users/" \+ uid \+ "\.json", \{ method: "DELETE" \}\);
        alert\("🚫 " \+ email \+ " 님의 요청이 거부되었습니다\."\);
        loadPendingUsers\(\);
    \} catch\(e\) \{ alert\("오류: " \+ e\.message\); \}
\}'''

new_reject = '''async function rejectUser(uid, email) {
    if (!confirm(email + " 님의 요청을 거부하시겠습니까?")) return;
    try {
        await fetch(FB_PROJECT.databaseURL + "/users/" + uid + ".json", {
            method: "PUT", headers: {"Content-Type":"application/json"},
            body: JSON.stringify({ email, approved: false, rejectedAt: Date.now() })
        });
        await fetch(FB_PROJECT.databaseURL + "/pending_users/" + uid + ".json", { method: "DELETE" });
        alert("🚫 " + email + " 님의 요청을 거부했습니다.");
        loadPendingUsers();
    } catch(e) { alert("오류: " + e.message); }
}'''

text = re.sub(old_reject, new_reject, text, flags=re.DOTALL)

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done")
