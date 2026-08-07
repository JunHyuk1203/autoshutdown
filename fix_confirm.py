import re
with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

def replace_confirm(text, func_name, title, action_msg, success_msg, set_data, db_path2=None):
    # This regex is meant to find the exact function
    # It might be simpler to just match and replace the inner text.
    # Since we know the structure, let's just do exact string replacement for the `confirm` line.
    pass

# We will just use regex to replace the function entirely
new_revoke = """async function revokeUser(uid, email) {
    if (!(await _checkAdminPermission())) return;
    showModal("권한 박탈", `<b>${escapeHtml(email)}</b>의 권한을 박탈하시겠습니까?`, async () => {
        closeModal();
        try {
            await firebase.database().ref("/users/" + uid).set({ email: email, approved: false, revokedAt: Date.now() });
        } catch(e) { alert("에러: " + e.message); }
    });
}"""
text = re.sub(r'async function revokeUser\(uid, email\)\s*\{.*?\n\}', new_revoke, text, flags=re.DOTALL)

new_restore = """async function restoreUser(uid, email) {
    if (!(await _checkAdminPermission())) return;
    showModal("권한 복구", `<b>${escapeHtml(email)}</b> 사용자를 다시 승인하시겠습니까?`, async () => {
        closeModal();
        try {
            await firebase.database().ref("/users/" + uid).set({ email: email, approved: true, approvedAt: Date.now() });
            await firebase.database().ref("/pending_users/" + uid).remove();
            alert("✅ " + email + " 승인되었습니다.");
        } catch(e) { alert("에러: " + e.message); }
    });
}"""
text = re.sub(r'async function restoreUser\(uid, email\)\s*\{.*?\n\}', new_restore, text, flags=re.DOTALL)

new_approve = """async function approveUser(uid, email) {
    if (!(await _checkAdminPermission())) return;
    showModal("가입 승인", `<b>${escapeHtml(email)}</b> 가입을 승인하시겠습니까?`, async () => {
        closeModal();
        try {
            await firebase.database().ref("/users/" + uid).set({ email, approved: true, role: "user", approvedAt: Date.now() });
            await firebase.database().ref("/pending_users/" + uid).remove();
            alert("✅ " + email + " 승인되었습니다.");
        } catch(e) { alert("에러: " + e.message); }
    });
}"""
text = re.sub(r'async function approveUser\(uid, email\)\s*\{.*?\n\}', new_approve, text, flags=re.DOTALL)

new_reject = """async function rejectUser(uid, email) {
    if (!(await _checkAdminPermission())) return;
    showModal("가입 거절", `<b>${escapeHtml(email)}</b> 가입 요청을 거절하시겠습니까?`, async () => {
        closeModal();
        try {
            await firebase.database().ref("/users/" + uid).set({ email: email, approved: false, rejectedAt: Date.now() });
            await firebase.database().ref("/pending_users/" + uid).remove();
            alert("❌ " + email + " 요청이 거절되었습니다.");
        } catch(e) { alert("에러: " + e.message); }
    });
}"""
text = re.sub(r'async function rejectUser\(uid, email\)\s*\{.*?\n\}', new_reject, text, flags=re.DOTALL)


# Let's also check for resetApiKeySetup confirm
new_reset = """function resetApiKeySetup() {
    showModal("API 키 초기화", "저장된 API 키와 설정 정보를 초기화하시겠습니까?", () => {
        closeModal();
        localStorage.removeItem("sp_fb_apikey");
        if (_fbAuth) { _fbAuth.signOut().catch(()=>{}); _fbAuth = null; }
        try { if (firebase.apps && firebase.apps.length) firebase.app().delete(); } catch(e) {}
        _showScreen("setup-view");
    });
}"""
text = re.sub(r'function resetApiKeySetup\(\)\s*\{.*?\n\}', new_reset, text, flags=re.DOTALL)

with open('dashboard_tmp2.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Finished replacing confirm")
