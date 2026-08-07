import re

with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Inject Account Modal HTML before Config Modal
account_modal_html = """
<!-- [MODAL] 계정 관리 -->
<div class="modal-overlay" id="account-modal">
  <div class="modal-card">
    <div class="modal-header">
      <h3 style="margin:0; font-size:18px; color:var(--text-main); font-weight:700;">&#x1F510; 계정 관리</h3>
      <button class="modal-close" onclick="closeAccountModal()">&times;</button>
    </div>
    <div class="modal-body" style="padding:20px;">
      <div class="config-group" style="margin-bottom:20px;">
        <label style="display:block; margin-bottom:6px; color:var(--text-muted); font-size:13px; font-weight:600;">현재 로그인된 계정</label>
        <div style="font-weight:600; margin-bottom:20px; color:var(--primary);" id="account-email-display">-</div>
        
        <label style="display:block; margin-bottom:6px; color:var(--text-muted); font-size:13px; font-weight:600;">이메일 로그인용 비밀번호 추가</label>
        <p style="font-size:12px; color:var(--text-muted); margin-bottom:12px; line-height:1.4;">구글 로그인 대신 이메일/비밀번호로도 로그인하려면 아래에 비밀번호를 설정하세요.</p>
        <input type="password" id="account-new-pw" class="auth-input" placeholder="새 비밀번호 (6자리 이상)">
        <input type="password" id="account-new-pw-confirm" class="auth-input" placeholder="새 비밀번호 확인" style="margin-top:10px;">
      </div>
      <div class="auth-error" id="account-error-msg" style="display:none; color:var(--error); font-size:13px; padding:10px; background:rgba(239,68,68,0.1); border-radius:8px;"></div>
    </div>
    <div class="modal-footer" style="padding:16px 20px; border-top:1px solid rgba(255,255,255,0.1); display:flex; justify-content:flex-end; gap:10px;">
      <button class="btn btn-secondary" onclick="closeAccountModal()" style="padding:10px 16px; border-radius:8px; border:none; cursor:pointer; background:rgba(255,255,255,0.1); color:var(--text-main);">닫기</button>
      <button class="btn btn-primary" onclick="addPasswordToAccount()" style="padding:10px 16px; border-radius:8px; border:none; cursor:pointer; background:var(--primary); color:white; font-weight:600;">설정 저장</button>
    </div>
  </div>
</div>
"""
if 'id="account-modal"' not in text:
    text = text.replace('<!-- [MODAL] 공통 알림 (Confirm) -->', account_modal_html + '\n\n  <!-- [MODAL] 공통 알림 (Confirm) -->')

# 2. Inject Account JS logic before PC CONTROL LOGIC
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
        modal.style.display = "flex";
        setTimeout(() => modal.classList.add("show"), 10);
    }
}

function closeAccountModal() {
    const modal = document.getElementById("account-modal");
    if(modal) {
        modal.classList.remove("show");
        setTimeout(() => modal.style.display = "none", 300);
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
            msg.textContent = _translateAuthError(err.code) || "비밀번호 설정 중 오류가 발생했습니다.";
        }
        msg.style.display = "block";
    }
}
'''
if 'function openAccountModal()' not in text:
    text = text.replace('// --- 모달 헬퍼 ---', account_js + '\n\n  // --- 모달 헬퍼 ---')

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Injected successfully 2.")
