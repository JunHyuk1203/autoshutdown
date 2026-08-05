import urllib.request
import hashlib
import base64
import re

scripts = [
    "https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js",
    "https://www.gstatic.com/firebasejs/10.12.0/firebase-auth-compat.js",
    "https://www.gstatic.com/firebasejs/10.12.0/firebase-database-compat.js"
]

hashes = {}
for url in scripts:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    data = urllib.request.urlopen(req).read()
    digest = hashlib.sha384(data).digest()
    b64 = base64.b64encode(digest).decode('utf-8')
    hashes[url] = f"sha384-{b64}"

with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace script tags with SRI
for url in scripts:
    old_tag = f'<script src="{url}"></script>'
    new_tag = f'<script src="{url}" integrity="{hashes[url]}" crossorigin="anonymous"></script>'
    text = text.replace(old_tag, new_tag)

# Update _enterDashboard to remove admin DOM for non-admins
old_enter = '''if (ab && user.email === MASTER_EMAIL) ab.style.display = "flex";'''
new_enter = '''if (ab && user.email === MASTER_EMAIL) {
        ab.style.display = "flex";
    } else {
        if (ab) ab.remove();
        const overlay = document.getElementById("admin-panel-overlay");
        if (overlay) overlay.remove();
    }'''
text = text.replace(old_enter, new_enter)

# Update signOutAndReset to reload page
old_signout = '''function signOutAndReset() {
    if (_fbAuth) {
        const uid = _fbAuth.currentUser ? _fbAuth.currentUser.uid : null;
        _fbAuth.signOut().then(() => {
            if (pollerInterval) clearInterval(pollerInterval);
            
            if (window._userStatusListener && uid && window.firebase && firebase.database) {
                firebase.database().ref("/users/" + uid).off("value", window._userStatusListener);
                window._userStatusListener = null;
            }
            window._dashboardInitialized = false;
            
            // Clear sensitive DOM data
            const els = ["pc-grid", "of-list", "pending-user-list", "approved-user-list", "fav-list"];
            els.forEach(id => {
                const el = document.getElementById(id);
                if (el) el.innerHTML = "";
            });
            
            // Close all overlays/modals
            const modals = ["admin-panel-overlay", "config-modal", "windows-modal", "open-file-modal", "volume-modal"];
            modals.forEach(id => {
                const el = document.getElementById(id);
                if (el) {
                    el.style.display = "none";
                    el.classList.remove("show");
                }
            });
            
            _showScreen("auth-view");
        });
    }
}'''

new_signout = '''function signOutAndReset() {
    if (_fbAuth) {
        _fbAuth.signOut().then(() => {
            // 완전히 세션을 삭제하고 모든 메모리 변수를 초기화하기 위해 페이지 새로고침
            window.location.reload();
        });
    } else {
        window.location.reload();
    }
}'''
text = text.replace(old_signout, new_signout)

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done")
