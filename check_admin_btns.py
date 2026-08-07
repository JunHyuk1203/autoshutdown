with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()
import re
# check all onclick inside admin panel
admin_panel = text[text.find('id="admin-panel-overlay"'):text.find('<!-- [ADMIN] ')] # wait, it ends before next section
lines = text.split('\n')
for i, line in enumerate(lines):
    if 'approveUser(' in line or 'revokeUser(' in line or 'restoreUser(' in line or 'deleteUser(' in line or 'rejectUser(' in line:
        print(f"L{i+1}: {line.strip()}")
