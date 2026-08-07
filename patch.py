import sys

with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Add banned-view HTML right after revoked-view
banned_view_html = """
<!-- [BANNED] 보안 위협 영구 차단 화면 -->
<div id="banned-view" style="display:none">
  <div class="auth-card" style="text-align:center;">
    <div style="font-size:52px; margin-bottom:16px; animation:pulse-slow 2.5s infinite;">☠️</div>
    <h2 style="font-size:22px; font-weight:800; margin-bottom:10px; color:#ef4444;">보안 위협 감지됨</h2>
    <p style="color:var(--text-muted); font-size:14px; line-height:1.75; margin-bottom:18px;">
      비정상적인 접근이 감지되어 시스템에 의해 영구 차단되었습니다.<br>이 계정으로는 더 이상 제어판을 이용할 수 없습니다.
    </p>
    <button class="auth-btn auth-btn-outline" id="signout-btn-banned">로그아웃</button>
  </div>
</div>
"""
if 'id="banned-view"' not in text:
    text = text.replace('<!-- [REVOKED] 권한 박탈 화면 -->', banned_view_html + '\n<!-- [REVOKED] 권한 박탈 화면 -->')

# 2. Update bindStaticEvents for banned-view signout
if 'id="signout-btn-banned"' in text and 'signout-btn-banned"' not in text[text.find('bindStaticEvents'):]:
    target = 'if (el_signout_btn_1) el_signout_btn_1.addEventListener("click", function(e) { signOutAndReset(); });'
    replacement = target + '\n    const el_signout_btn_banned = document.getElementById("signout-btn-banned");\n    if (el_signout_btn_banned) el_signout_btn_banned.addEventListener("click", function(e) { signOutAndReset(); });'
    text = text.replace(target, replacement)

# 3. Update _attachUserStatusListener to check security_logs
listener_target = """        if (status === true) {
            setAccessGranted(true);
            _enterDashboard(user);
        } else if (status === false) {
            setAccessGranted(false);
            if (statusObj.revokedAt) {
                _revokeAccess();
            } else {
                document.getElementById("pending-email-label").textContent = user.email;
                document.getElementById("pending-title").textContent = "가입 거부됨";
                document.getElementById("pending-desc").innerHTML = "관리자가 가입을 거부했습니다.";
                document.getElementById("pending-rerequest-btn").style.display = "block";
                _showScreen("pending-view");
            }
        } else {
            setAccessGranted(false);"""
            
listener_replacement = """        if (status === true) {
            setAccessGranted(true);
            _enterDashboard(user);
        } else if (status === false) {
            setAccessGranted(false);
            firebase.database().ref("/security_logs/" + user.uid).once("value").then(secSnap => {
                if (secSnap.exists()) {
                    _showScreen("banned-view");
                } else if (statusObj.revokedAt) {
                    _revokeAccess();
                } else {
                    document.getElementById("pending-email-label").textContent = user.email;
                    document.getElementById("pending-title").textContent = "가입 거부됨";
                    document.getElementById("pending-desc").innerHTML = "관리자가 가입을 거부했습니다.";
                    document.getElementById("pending-rerequest-btn").style.display = "block";
                    _showScreen("pending-view");
                }
            });
        } else {
            setAccessGranted(false);"""
if listener_target in text:
    text = text.replace(listener_target, listener_replacement)

# 4. _checkAuthPermission shouldn't just alert and sign out if it's a security ban. Actually, just let it reload the page to trigger the proper screen.
check_auth_target = """        if (isApproved !== true) {
            alert("보안 경고: 계정의 접근 권한이 박탈되었습니다.");
            setAccessGranted(false);
            signOutAndReset();
            return false;
        }"""
        
check_auth_replacement = """        if (isApproved !== true) {
            alert("보안 경고: 계정의 접근 권한이 박탈되었습니다.");
            setAccessGranted(false);
            location.reload();
            return false;
        }"""
if check_auth_target in text:
    text = text.replace(check_auth_target, check_auth_replacement)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(text)
print("index.html patched")
