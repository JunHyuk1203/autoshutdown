import re

with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Remove emailVerified block
text = re.sub(r'// \S+ 1단계: 이메일 인증 확인.*?// \S+ 3단계: 권한 상태 \(실시간 감시\) 등록', '// [권한 실시간 감시] 등록', text, flags=re.DOTALL)
# Actually, the user's code had `// 제 1단계: 이메일 인증 확인`
# Let's just use string replacement for the email verified check.
lines = text.split('\n')
new_lines = []
skip = False
for line in lines:
    if 'await user.reload();' in line or '// 제 1단계: 이메일 인증' in line:
        skip = True
    if skip and ('return;' in line) and ('_showScreen("verify-email-view")' in new_lines[-1] or '_showScreen("verify-email-view")' in line or 'verify-email-view' in text):
        pass # keep skipping
    if skip and ('_attachUserStatusListener' in line or '// 제 3단계' in line):
        skip = False
    
    if not skip:
        new_lines.append(line)

# To be safer, let's just use regex on the whole text
text = '\n'.join(lines)
text = re.sub(r'\s*// [^\n]*1단계[^\n]*\n\s*await user\.reload\(\);[^\n]*\n\s*if \(!user\.emailVerified\) \{.*?\n\s*\}', '', text, flags=re.DOTALL)

# 2. Update handleEmailAuth to ONLY sign in (Remove createUserWithEmailAndPassword)
old_auth = '''async function handleEmailAuth() {
    const email = document.getElementById("auth-email-input").value.trim();
    const pw = document.getElementById("auth-pw-input").value;
    const msg = document.getElementById("auth-error-msg");
    if (!email || !pw) {
        msg.textContent = "이메일과 비밀번호를 입력해주세요.";
        msg.style.display = "block";
        return;
    }
    msg.style.display = "none";
    try {
        await firebase.auth().signInWithEmailAndPassword(email, pw);
    } catch(err) {
        if (err.code === "auth/user-not-found") {
            try {
                const cred = await firebase.auth().createUserWithEmailAndPassword(email, pw);
                await cred.user.sendEmailVerification();
            } catch(e2) {
                msg.textContent = _translateAuthError(e2.code);
                msg.style.display = "block";
            }
        } else {
            msg.textContent = _translateAuthError(err.code);
            msg.style.display = "block";
        }
    }
}'''

new_auth = '''async function handleEmailAuth() {
    const email = document.getElementById("auth-email-input").value.trim();
    const pw = document.getElementById("auth-pw-input").value;
    const msg = document.getElementById("auth-error-msg");
    if (!email || !pw) {
        msg.textContent = "이메일과 비밀번호를 입력해주세요.";
        msg.style.display = "block";
        return;
    }
    msg.style.display = "none";
    try {
        await firebase.auth().signInWithEmailAndPassword(email, pw);
    } catch(err) {
        if (err.code === "auth/user-not-found" || err.code === "auth/invalid-credential") {
            msg.textContent = "회원가입은 Google 로그인으로만 가능합니다. 이미 계정이 있다면 비밀번호를 확인해주세요.";
        } else {
            msg.textContent = _translateAuthError(err.code);
        }
        msg.style.display = "block";
    }
}'''
if old_auth in text:
    text = text.replace(old_auth, new_auth)
else:
    print("WARNING: handleEmailAuth not found in exact format!")

# 3. Add JS for Account Modal
account_js = '''
// --- 계정 관리 로직 ---
function openAccountModal() {
    const user = _fbAuth ? _fbAuth.currentUser : null;
    if (user) {
        document.getElementById("account-email-display").textContent = user.email || "이메일 정보 없음";
    }
    document.getElementById("account-error-msg").style.display = "none";
    document.getElementById("account-new-pw").value = "";
    document.getElementById("account-new-pw-confirm").value = "";
    
    const modal = document.getElementById("account-modal");
    modal.style.display = "flex";
    setTimeout(() => modal.classList.add("show"), 10);
}

function closeAccountModal() {
    const modal = document.getElementById("account-modal");
    modal.classList.remove("show");
    setTimeout(() => modal.style.display = "none", 300);
}

async function addPasswordToAccount() {
    const user = _fbAuth ? _fbAuth.currentUser : null;
    if (!user) return;
    
    const pw1 = document.getElementById("account-new-pw").value;
    const pw2 = document.getElementById("account-new-pw-confirm").value;
    const msg = document.getElementById("account-error-msg");
    
    if (!pw1 || pw1.length < 6) {
        msg.textContent = "비밀번호는 6자리 이상이어야 합니다.";
        msg.style.display = "block";
        return;
    }
    if (pw1 !== pw2) {
        msg.textContent = "비밀번호 확인이 일치하지 않습니다.";
        msg.style.display = "block";
        return;
    }
    
    msg.style.display = "none";
    try {
        await user.updatePassword(pw1);
        closeAccountModal();
        alert("이메일 로그인용 비밀번호가 성공적으로 설정되었습니다!\\n이제 구글 버튼을 누르지 않아도 이메일과 비밀번호로 로그인할 수 있습니다.");
    } catch(err) {
        console.error(err);
        if (err.code === 'auth/requires-recent-login') {
            msg.textContent = "보안을 위해 다시 로그인한 후 비밀번호를 설정해주세요.";
        } else {
            msg.textContent = _translateAuthError(err.code) || "비밀번호 설정 중 오류가 발생했습니다.";
        }
        msg.style.display = "block";
    }
}
'''
text = text.replace('// ==========================================\n//    PC CONTROL LOGIC', account_js + '\n// ==========================================\n//    PC CONTROL LOGIC')

# 4. Make account-header-btn visible in _enterDashboard
text = text.replace('if (lb) lb.style.display = "flex";', 'if (lb) lb.style.display = "flex";\n    const actb = document.getElementById("account-header-btn");\n    if (actb) actb.style.display = "flex";')

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Logic updated.")
