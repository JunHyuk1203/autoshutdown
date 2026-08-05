import re

with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

helpers = '''
async function _checkAuthPermission() {
    if (!_fbAuth || !_fbAuth.currentUser) {
        alert("로그인이 필요합니다.");
        signOutAndReset();
        return false;
    }
    const user = _fbAuth.currentUser;
    if (user.email === MASTER_EMAIL) return true;
    
    try {
        const snap = await firebase.database().ref("/users/" + user.uid + "/approved").once("value");
        const isApproved = snap.val();
        if (isApproved !== true) {
            alert("보안 경고: 계정의 접근 권한이 박탈되었습니다.");
            _revokeAccess();
            return false;
        }
        return true;
    } catch(e) {
        alert("권한 확인 중 오류가 발생했습니다.");
        return false;
    }
}

async function _checkAdminPermission() {
    if (!_fbAuth || !_fbAuth.currentUser) {
        alert("로그인이 필요합니다.");
        signOutAndReset();
        return false;
    }
    if (_fbAuth.currentUser.email !== MASTER_EMAIL) {
        alert("보안 경고: 관리자 권한이 없습니다.");
        return false;
    }
    return true;
}
'''

# Insert helpers right before async function applyRemoteConfig()
text = text.replace('async function applyRemoteConfig() {', helpers + '\nasync function applyRemoteConfig() {')

# Inject into user functions
user_funcs = [
    'async function applyRemoteConfig() {',
    'async function writeCommandToDB(target, action, message = "") {',
    'async function clearSelectedDevices() {',
    'async function clearOfflineDevices() {',
    'async function syncFavoritesToFirebase(favs) {',
    'async function triggerWindowCommand(pcId, action, data, title, content) {',
    'async function sendOpenFileCommand() {',
    'async function sendOpenUrlCommand() {'
]

for func in user_funcs:
    if func in text:
        # Avoid duplicate injections
        if f'if (!(await _checkAuthPermission())) return;' not in text.split(func)[1][:200]:
            text = text.replace(func, func + '\n    if (!(await _checkAuthPermission())) return;')

# Inject into admin functions
admin_funcs = [
    'async function approveUser(uid, email) {',
    'async function rejectUser(uid, email) {',
    'async function revokeUser(uid, email) {',
    'async function restoreUser(uid, email) {'
]

for func in admin_funcs:
    if func in text:
        if f'if (!(await _checkAdminPermission())) return;' not in text.split(func)[1][:200]:
            text = text.replace(func, func + '\n    if (!(await _checkAdminPermission())) return;')

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done")
