import sys
import re

sys.stdout.reconfigure(encoding="utf-8")
with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

# Replace all instances of `user.email === MASTER_EMAIL` and `!== MASTER_EMAIL` with lowercase comparisons
text = re.sub(
    r'\.email\s*===\s*MASTER_EMAIL',
    r'.email && \g<0>'.replace(r'\g<0>', r'.email.toLowerCase() === MASTER_EMAIL.toLowerCase()'),
    text
)
text = re.sub(
    r'\.email\s*!==\s*MASTER_EMAIL',
    r'.email && \g<0>'.replace(r'\g<0>', r'.email.toLowerCase() !== MASTER_EMAIL.toLowerCase()'),
    text
)

# And specifically check _checkAdminPermission
check_admin_target = """async function _checkAdminPermission() {
    if (!_fbAuth || !_fbAuth.currentUser) {
        alert("로그인이 필요합니다.");
        signOutAndReset();
        return false;
    }
    if (_fbAuth.currentUser.email !== MASTER_EMAIL) {"""
    
check_admin_replacement = """async function _checkAdminPermission() {
    if (!_fbAuth || !_fbAuth.currentUser) {
        alert("로그인이 필요합니다.");
        signOutAndReset();
        return false;
    }
    if (!_fbAuth.currentUser.email || _fbAuth.currentUser.email.toLowerCase() !== MASTER_EMAIL.toLowerCase()) {"""
    
text = text.replace(check_admin_target, check_admin_replacement)

# And checkAuthPermission
check_auth_target = """    const user = _fbAuth.currentUser;
    if (user.email === MASTER_EMAIL) {"""

check_auth_replacement = """    const user = _fbAuth.currentUser;
    if (user.email && user.email.toLowerCase() === MASTER_EMAIL.toLowerCase()) {"""

text = text.replace(check_auth_target, check_auth_replacement)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(text)
print("done")
