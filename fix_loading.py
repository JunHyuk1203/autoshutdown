with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re

# Remove loadApprovedUsers() from revokeUser
old_revoke = '''alert("🔴 " + email + " 권한이 박탈되었습니다.");
        loadApprovedUsers(); // UI 갱신'''
new_revoke = '''alert("🔴 " + email + " 권한이 박탈되었습니다.");
        // UI 갱신은 실시간 리스너가 자동 처리합니다.'''
text = text.replace(old_revoke, new_revoke)

# Remove loadApprovedUsers() from restoreUser
old_restore = '''alert("🟢 " + email + " 복구되었습니다.");
        loadApprovedUsers(); // UI 갱신'''
new_restore = '''alert("🟢 " + email + " 복구되었습니다.");
        // UI 갱신은 실시간 리스너가 자동 처리합니다.'''
text = text.replace(old_restore, new_restore)

# Remove loadPendingUsers() from approveUser
old_approve = '''alert("✅ " + email + " 사용자가 승인되었습니다.");
        loadPendingUsers();'''
new_approve = '''alert("✅ " + email + " 사용자가 승인되었습니다.");
        // UI 갱신은 실시간 리스너가 자동 처리합니다.'''
text = text.replace(old_approve, new_approve)

# Remove loadPendingUsers() from rejectUser
old_reject = '''alert("❌ " + email + " 가입 요청이 거부되었습니다.");
        loadPendingUsers();'''
new_reject = '''alert("❌ " + email + " 가입 요청이 거부되었습니다.");
        // UI 갱신은 실시간 리스너가 자동 처리합니다.'''
text = text.replace(old_reject, new_reject)

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done")
