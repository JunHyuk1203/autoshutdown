import re

with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Hide dashboard-view initially
text = text.replace('<div class="dashboard-layout" id="dashboard-view">', '<div class="dashboard-layout" id="dashboard-view" style="display:none;">')

# Remove setup-view precisely
setup_start = text.find('<!-- [SETUP] Firebase API 키 초기 설정 -->')
setup_end = text.find('<!-- [AUTH] 로그인 / 회원가입 -->')
if setup_start != -1 and setup_end != -1:
    text = text[:setup_start] + text[setup_end:]

# Remove onboarding-view precisely
ob_start = text.find('<!-- \n   1단계: Firebase 연결 화면 (Onboarding)')
ob_end = text.find('<!-- ─────────────────────────────────────────────────────────────\n   2단계: 실시간 관리 대시보드 화면')
if ob_start != -1 and ob_end != -1:
    text = text[:ob_start] + text[ob_end:]

# Remove from _showScreen array
text = text.replace('"setup-view","auth-view","verify-email-view","pending-view","onboarding-view","dashboard-view"', '"auth-view","verify-email-view","pending-view","dashboard-view"')

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done")
