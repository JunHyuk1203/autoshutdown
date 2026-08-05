with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Update .admin-panel-card
old_admin_card = '''\.admin-panel-card \{
    background: #0d0d22; border: 1px solid rgba\(255,255,255,0\.1\);
    border-radius: 20px; padding: 32px; width: 100%; max-width: 560px;
    max-height: 80vh; overflow-y: auto; box-shadow: 0 24px 60px rgba\(0,0,0,0\.6\);
    animation: fadeIn 0\.3s ease;
\}'''
new_admin_card = '''.admin-panel-card {
    background: #0d0d22; border: 1px solid rgba(255,255,255,0.1);
    border-radius: 20px; padding: 32px 10px; width: 100%; max-width: 600px;
    max-height: 80vh; overflow-y: auto; box-shadow: 0 24px 60px rgba(0,0,0,0.6);
    animation: fadeIn 0.3s ease;
}'''
import re
text = re.sub(old_admin_card, new_admin_card, text)

# Update .pending-user-row
old_row = '''\.pending-user-row \{
    display: flex; align-items: center; padding: 14px 16px;
    background: rgba\(255,255,255,0\.03\); border: 1px solid rgba\(255,255,255,0\.07\);
    border-radius: 12px; margin-bottom: 8px; gap: 12px;
\}'''
new_row = '''.pending-user-row {
    display: flex; align-items: center; padding: 14px 4px;
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px; margin-bottom: 8px; gap: 6px;
}'''
text = re.sub(old_row, new_row, text)

# Update .pending-user-email
old_email = '''\.pending-user-email \{ font-size: 13px; color: var\(--text-main\); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; \}'''
new_email = '''.pending-user-email { font-size: 13px; color: var(--text-main); white-space: normal; word-break: break-all; }'''
text = re.sub(old_email, new_email, text)

# Update loadPendingUsers row.innerHTML
old_html = r'<div class="pending-user-avatar">\$\{init\}</div>\s*<div class="pending-user-info">'
new_html = r'<div class="pending-user-info">'
text = re.sub(old_html, new_html, text)

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done")
