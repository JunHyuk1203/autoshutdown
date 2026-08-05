import re

with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Hide dashboard-view initially
text = text.replace('<div class="dashboard-layout" id="dashboard-view">', '<div class="dashboard-layout" id="dashboard-view" style="display:none;">')

# Remove setup-view
setup_view_pattern = re.compile(r'<!-- \[SETUP\].*?<div id="setup-view" style="display:none">.*?</div>\n  </div>', re.DOTALL)
text = re.sub(setup_view_pattern, '', text)

# Remove onboarding-view
onboarding_pattern = re.compile(r'<!-- \n   1단계: Firebase 연결 화면 \(Onboarding\).*?<div class="onboarding-container" id="onboarding-view">.*?</div>\n    </div>\n</div>', re.DOTALL)
text = re.sub(onboarding_pattern, '', text)

# Remove 'setup-view' and 'onboarding-view' from _showScreen array to avoid confusion
text = text.replace('"setup-view","auth-view","verify-email-view","pending-view","onboarding-view","dashboard-view"', '"auth-view","verify-email-view","pending-view","dashboard-view"')

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done")
