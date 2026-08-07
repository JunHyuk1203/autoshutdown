import re
with open('dashboard_tmp.html', 'r', encoding='utf-8') as f:
    text = f.read()

# using regex
text = re.sub(r'async function checkUserStatus\(uid\)\s*\{.*?catch\s*\{ return null; \}\n\}', 
"""async function checkUserStatus(uid) {
    try {
        const snapshot = await firebase.database().ref("/users/" + uid).once("value");
        return snapshot.val();
    } catch (e) { 
        if(e.code === 'PERMISSION_DENIED') return { permission_denied: true };
        return null; 
    }
}""", text, flags=re.DOTALL)

text = re.sub(r'async function requestApproval\(user\)\s*\{.*?catch\(e\)\s*\{\s*console\.error\(e\);\s*\}\n\}',
"""async function requestApproval(user) {
    try {
        await firebase.database().ref("/pending_users/" + user.uid).set({
            email: user.email,
            displayName: user.displayName || user.email.split("@")[0],
            requestedAt: Date.now(),
            requestType: "new"
        });
    } catch(e) { console.error(e); }
}""", text, flags=re.DOTALL)

with open('dashboard_tmp.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Step 11 done")
