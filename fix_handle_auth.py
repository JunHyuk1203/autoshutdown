import re

with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

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

text = re.sub(r'async function handleEmailAuth\(\).*?^\}', new_auth, text, flags=re.DOTALL|re.MULTILINE)

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("handleEmailAuth updated.")
