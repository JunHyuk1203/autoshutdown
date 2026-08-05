with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re

# Remove outer padding for auth views
pat1 = re.compile(r'#auth-view, #pending-view, #setup-view, #verify-email-view, #revoked-view \{\n    position: fixed; inset: 0; z-index: 9000;\n    background: var\(--bg-dark\);\n    display: flex; align-items: center; justify-content: center; padding: 20px;\n\}', re.DOTALL)
rep1 = '''#auth-view, #pending-view, #setup-view, #verify-email-view, #revoked-view {
    position: fixed; inset: 0; z-index: 9000;
    background: var(--bg-dark);
    display: flex; align-items: center; justify-content: center; padding: 0;
}'''
text = re.sub(pat1, rep1, text)

# auth-card padding
pat2 = re.compile(r'\.auth-card \{\n    background: rgba\(255,255,255,0\.03\);\n    border: 1px solid rgba\(255,255,255,0\.09\);\n    backdrop-filter: blur\(24px\); -webkit-backdrop-filter: blur\(24px\);\n    border-radius: 24px; padding: 44px 40px; width: 100%; max-width: 420px;\n    box-shadow: 0 28px 60px rgba\(0,0,0,0\.5\), 0 0 0 1px rgba\(255,255,255,0\.04\) inset;\n\}', re.DOTALL)
rep2 = '''.auth-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.09);
    backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px);
    border-radius: 24px; padding: 44px 10px; width: 100%; max-width: 420px;
    box-shadow: 0 28px 60px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.04) inset;
    box-sizing: border-box;
}'''
text = re.sub(pat2, rep2, text)

# admin-panel-card padding
pat3 = re.compile(r'\.admin-panel-card \{\n    background: #0d0d22; border: 1px solid rgba\(255,255,255,0\.1\);\n    border-radius: 20px; padding: 32px 10px; width: 100%; max-width: 600px;\n    max-height: 80vh; overflow-y: auto; box-shadow: 0 24px 60px rgba\(0,0,0,0\.6\);\n    animation: fadeIn 0\.3s ease;\n\}', re.DOTALL)
rep3 = '''.admin-panel-card {
    background: #0d0d22; border: 1px solid rgba(255,255,255,0.1);
    border-radius: 20px; padding: 32px 0; width: 100%; max-width: 600px;
    max-height: 80vh; overflow-y: auto; box-shadow: 0 24px 60px rgba(0,0,0,0.6);
    animation: fadeIn 0.3s ease;
    box-sizing: border-box;
}'''
text = re.sub(pat3, rep3, text)

# modal-card padding
pat4 = re.compile(r'\.modal-card \{\n    background: #0f0f23;\n    border: 1px solid var\(--border-light\);\n    border-radius: 20px;\n    padding: 28px;\n    width: 90%;\n    max-width: 360px;', re.DOTALL)
rep4 = '''.modal-card {
    background: #0f0f23;
    border: 1px solid var(--border-light);
    border-radius: 20px;
    padding: 28px 0;
    width: 90%;
    max-width: 360px;
    box-sizing: border-box;'''
text = re.sub(pat4, rep4, text)

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done")
