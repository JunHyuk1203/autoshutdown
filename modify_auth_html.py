import re

with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Modify auth-submit-btn text to "이메일 로그인"
text = text.replace('<button class="auth-btn auth-btn-primary" id="auth-submit-btn" onclick="handleEmailAuth()">로그인 / 회원가입</button>', 
                    '<button class="auth-btn auth-btn-primary" id="auth-submit-btn" onclick="handleEmailAuth()">이메일로 로그인</button>')

# 2. Remove verify-email-view HTML
verify_email_regex = re.compile(r'<!-- \[AUTH\] 이메일 인증 대기 -->\s*<div id="verify-email-view".*?</div>\s*</div>\s*</div>', re.DOTALL)
text = verify_email_regex.sub('', text)

# 3. Add Account Management Modal HTML (after config-modal)
account_modal_html = """
<!-- [MODAL] 계정 관리 -->
<div class="modal-overlay" id="account-modal">
  <div class="modal-content">
    <div class="modal-header">
      <h3>🔐 계정 관리</h3>
      <button class="close-btn" onclick="closeAccountModal()">&times;</button>
    </div>
    <div class="modal-body">
      <div class="config-group">
        <label>현재 로그인된 계정</label>
        <div style="font-weight:600; margin-bottom:15px; color:var(--text-main);" id="account-email-display">-</div>
        
        <label>이메일 로그인용 비밀번호 추가</label>
        <p style="font-size:12px; color:var(--text-muted); margin-bottom:10px;">구글 로그인 대신 이메일/비밀번호로도 로그인하려면 아래에 비밀번호를 추가하세요.</p>
        <input type="password" id="account-new-pw" class="auth-input" placeholder="새 비밀번호 (6자리 이상)">
        <input type="password" id="account-new-pw-confirm" class="auth-input" placeholder="새 비밀번호 확인">
      </div>
      <div class="auth-error" id="account-error-msg" style="display:none; margin-top:10px;"></div>
    </div>
    <div class="modal-footer">
      <button class="btn btn-secondary" onclick="closeAccountModal()">닫기</button>
      <button class="btn btn-primary" onclick="addPasswordToAccount()">저장</button>
    </div>
  </div>
</div>
"""
text = text.replace('<!-- [MODAL] 설정 변경 (Config) -->', account_modal_html + '\n  <!-- [MODAL] 설정 변경 (Config) -->')

# 4. Add Account Management button to header (next to logout)
account_btn_html = '<button class="header-btn" id="account-header-btn" style="display:none" onclick="openAccountModal()">계정 관리</button>'
text = text.replace('<button class="header-btn" id="logout-header-btn" style="display:none" onclick="signOutAndReset()">로그아웃</button>', 
                    account_btn_html + '\n      <button class="header-btn" id="logout-header-btn" style="display:none" onclick="signOutAndReset()">로그아웃</button>')

# 5. Modify JS logic
# Remove user.emailVerified check
on_auth_regex = re.compile(r'// \[2단계\]: 이메일 인증 확인.*?// \[3단계\]', re.DOTALL)
text = on_auth_regex.sub('// [3단계]', text)
# (Actually the comment says: "// 2단계: 이메일 인증 확인 로직" or similar in Korean, let's just find "user.emailVerified" and remove the block)

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
