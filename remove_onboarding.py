import re

with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Try a more robust regex to remove onboarding-view
onboarding_pattern = re.compile(r'<div class="onboarding-container" id="onboarding-view">.*?</div>\n    </div>\n</div>', re.DOTALL)
text = re.sub(onboarding_pattern, '', text)

# Remove the exact comment before it
comment_pattern = re.compile(r'<!-- ─+\n   1단계: Firebase 연결 화면 \(Onboarding\)\n   ─+ -->\n', re.DOTALL)
text = re.sub(comment_pattern, '', text)

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done")
