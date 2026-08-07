import re

with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Remove the incorrectly added JS
text = re.sub(r'// --- 계정 관리 로직 ---.*?\}\s*</script>', '</script>', text, flags=re.DOTALL)

# Add it back ONLY ONCE at the very end of the file, right before the LAST </script> tag
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
    if(modal) {
        modal.classList.add("show");
    }
}

function closeAccountModal() {
    const modal = document.getElementById("account-modal");
    if(modal) {
        modal.classList.remove("show");
    }
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
            msg.textContent = err.message || "비밀번호 설정 중 오류가 발생했습니다.";
        }
        msg.style.display = "block";
    }
}
'''

# Find the LAST </script>
idx = text.rfind('</script>')
if idx != -1:
    text = text[:idx] + account_js + '\n' + text[idx:]

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Cleaned and injected JS")
