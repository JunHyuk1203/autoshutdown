with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

account_modal_html = """
<!-- 계정 관리 모달 -->
<div class="modal-overlay" id="account-modal">
  <div class="modal-card" style="max-width: 400px; width: 95%;">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
      <h3 style="margin:0; font-size:18px; color:var(--text-main); font-weight:700;">&#x1F510; 계정 관리</h3>
      <button class="modal-close" onclick="closeAccountModal()" style="background:transparent; border:none; color:var(--text-muted); font-size:24px; cursor:pointer;">&times;</button>
    </div>
    <div style="padding-bottom:10px;">
      <label style="display:block; margin-bottom:6px; color:var(--text-muted); font-size:13px; font-weight:600;">현재 로그인된 계정</label>
      <div style="font-weight:600; margin-bottom:20px; color:var(--primary);" id="account-email-display">-</div>
      
      <label style="display:block; margin-bottom:6px; color:var(--text-muted); font-size:13px; font-weight:600;">이메일 로그인용 비밀번호 추가</label>
      <p style="font-size:12px; color:var(--text-muted); margin-bottom:12px; line-height:1.4;">구글 로그인 대신 이메일/비밀번호로도 로그인하려면 아래에 비밀번호를 설정하세요.</p>
      <input type="password" id="account-new-pw" class="auth-input" placeholder="새 비밀번호 (6자리 이상)" style="width:100%; box-sizing:border-box;">
      <input type="password" id="account-new-pw-confirm" class="auth-input" placeholder="새 비밀번호 확인" style="width:100%; box-sizing:border-box; margin-top:10px;">
    </div>
    <div id="account-error-msg" style="display:none; color:var(--error); font-size:13px; padding:10px; background:rgba(239,68,68,0.1); border-radius:8px; margin-bottom:15px;"></div>
    <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:10px;">
      <button class="btn btn-secondary" onclick="closeAccountModal()" style="padding:10px 16px; border-radius:8px; border:none; cursor:pointer; background:rgba(255,255,255,0.1); color:var(--text-main);">닫기</button>
      <button class="btn btn-primary" onclick="addPasswordToAccount()" style="padding:10px 16px; border-radius:8px; border:none; cursor:pointer; background:var(--primary); color:white; font-weight:600;">설정 저장</button>
    </div>
  </div>
</div>
"""
if 'id="account-modal"' not in text:
    text = text.replace('<div class="modal-overlay" id="config-modal">', account_modal_html + '\n<div class="modal-overlay" id="config-modal">')

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Injected HTML")
