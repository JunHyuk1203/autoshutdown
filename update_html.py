with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Add revoked-view
revoked_html = '''
<!-- [REVOKED] 권한 박탈 화면 -->
<div id="revoked-view" style="display:none">
  <div class="auth-card" style="text-align:center;">
    <div style="font-size:52px; margin-bottom:16px; animation:pulse-slow 2.5s infinite;">🚫</div>
    <h2 style="font-size:22px; font-weight:800; margin-bottom:10px; color:#ef4444;">접근 권한 박탈됨</h2>
    <p style="color:var(--text-muted); font-size:14px; line-height:1.75; margin-bottom:18px;">
      관리자에 의해 기기 제어 권한이 박탈되었습니다.<br>더 이상 대시보드에 접근할 수 없습니다.
    </p>
    <button class="auth-btn auth-btn-primary" onclick="reRequestReactivation()" style="margin-bottom:8px;">🔄 권한 재요청</button>
    <button class="auth-btn auth-btn-outline" onclick="signOutAndReset()">로그아웃</button>
  </div>
</div>
'''

if 'id="revoked-view"' not in text:
    text = text.replace('<!-- [ADMIN] 신규 가입 검토 패널 (Master 전용) -->', revoked_html + '\n<!-- [ADMIN] 신규 가입 검토 패널 (Master 전용) -->')

# Update admin panel
old_admin = '''<div id="admin-panel-overlay" style="display:none" onclick="if(event.target===this)closeAdminPanel()">
  <div class="admin-panel-card">
    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:24px;">
      <h2 style="font-size:20px; font-weight:800;">🛡️ 신규 가입 검토 <span class="master-badge">MASTER</span></h2>
      <button onclick="closeAdminPanel()" style="background:none;border:none;color:var(--text-muted);font-size:22px;cursor:pointer;line-height:1;padding:4px;">✕</button>
    </div>
    <p style="font-size:12px; color:var(--text-muted); margin-bottom:16px; line-height:1.6;">
      ⚠️ 아래 목록은 이메일 인증까지 완료한 사용자입니다. (이중 승인 1단계 완료)
    </p>
    <div id="pending-user-list">
      <p style="color:var(--text-muted); text-align:center; font-size:14px; padding:20px 0;">⏳ 불러오는 중...</p>
    </div>
    <div style="border-top:1px solid rgba(255,255,255,0.08); margin-top:20px; padding-top:16px;">
      <p style="font-size:11px; color:var(--text-muted); text-align:center;">승인된 사용자는 모든 PC를 제어할 수 있습니다.</p>
    </div>
  </div>
</div>'''

new_admin = '''<div id="admin-panel-overlay" style="display:none" onclick="if(event.target===this)closeAdminPanel()">
  <div class="admin-panel-card" onclick="event.stopPropagation()">
    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:16px;">
      <h2 style="font-size:20px; font-weight:800;">🛡️ 마스터 제어판 <span class="master-badge">MASTER</span></h2>
      <button onclick="closeAdminPanel()" style="background:none;border:none;color:var(--text-muted);font-size:22px;cursor:pointer;line-height:1;padding:4px;">✕</button>
    </div>
    
    <div class="admin-tabs" style="display:flex; border-bottom:1px solid rgba(255,255,255,0.1); margin-bottom:16px;">
      <button class="admin-tab-btn active" id="tab-btn-pending" onclick="switchAdminTab('pending')" style="flex:1; padding:10px; background:none; border:none; color:var(--text-main); font-weight:bold; border-bottom:2px solid var(--primary); cursor:pointer;">📋 가입 요청</button>
      <button class="admin-tab-btn" id="tab-btn-approved" onclick="switchAdminTab('approved')" style="flex:1; padding:10px; background:none; border:none; color:var(--text-muted); font-weight:bold; border-bottom:2px solid transparent; cursor:pointer;">👥 계정 관리</button>
    </div>

    <!-- 탭 1: 가입 요청 -->
    <div id="admin-tab-pending" style="display:block;">
      <p style="font-size:12px; color:var(--text-muted); margin-bottom:16px; line-height:1.6;">
        ⚠️ 아래 목록은 이메일 인증까지 완료한 가입 요청 대기열입니다.
      </p>
      <div id="pending-user-list">
        <p style="color:var(--text-muted); text-align:center; font-size:14px; padding:20px 0;">⏳ 불러오는 중...</p>
      </div>
      <div style="border-top:1px solid rgba(255,255,255,0.08); margin-top:20px; padding-top:16px;">
        <p style="font-size:11px; color:var(--text-muted); text-align:center;">승인된 사용자는 모든 PC를 제어할 수 있습니다.</p>
      </div>
    </div>

    <!-- 탭 2: 계정 관리 -->
    <div id="admin-tab-approved" style="display:none;">
      <p style="font-size:12px; color:var(--text-muted); margin-bottom:16px; line-height:1.6;">
        ⚠️ 이미 승인된 사용자 목록입니다. 즉시 권한을 박탈할 수 있습니다.
      </p>
      <div id="approved-user-list">
        <p style="color:var(--text-muted); text-align:center; font-size:14px; padding:20px 0;">⏳ 불러오는 중...</p>
      </div>
    </div>

  </div>
</div>'''

if 'id="admin-tab-pending"' not in text:
    text = text.replace(old_admin, new_admin)
    if 'id="admin-tab-pending"' not in text:
        # try regex if exact string mismatch
        import re
        pat = re.compile(r'<div id="admin-panel-overlay" style="display:none".*?</div>\n  </div>\n</div>', re.DOTALL)
        text = re.sub(pat, new_admin, text)

# Add _showScreen update for revoked-view
text = text.replace('"pending-view","dashboard-view"', '"pending-view","revoked-view","dashboard-view"')

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done")
