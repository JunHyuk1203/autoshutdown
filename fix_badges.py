with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re

# Fix reRequestApproval (which is for rejected users)
old_re_request = '''body: JSON.stringify({ email: user.email, displayName: user.displayName || user.email.split("@")[0], requestedAt: Date.now(), requestType: "reactivation" })'''
new_re_request = '''body: JSON.stringify({ email: user.email, displayName: user.displayName || user.email.split("@")[0], requestedAt: Date.now(), requestType: "re-request" })'''
text = text.replace(old_re_request, new_re_request)

# Fix loadPendingUsers badge logic
old_badge_logic = ''''''
                            
new_badge_logic = ''''''
text = text.replace(old_badge_logic, new_badge_logic)

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done")
