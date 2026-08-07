with open('dashboard_tmp.html', 'r', encoding='utf-8') as f:
    text = f.read()

# checkUserStatus
old_cus = """async function checkUserStatus(uid) {
    try {
        const r = await fetch(FB_PROJECT.databaseURL + "/users/" + uid + ".json");
        const val = await r.json();
        return val; // Returns object { approved, revokedAt, rejectedAt } or null
    } catch { return null; }
}"""
new_cus = """async function checkUserStatus(uid) {
    try {
        const snapshot = await firebase.database().ref("/users/" + uid).once("value");
        return snapshot.val();
    } catch (e) { 
        if(e.code === 'PERMISSION_DENIED') return { permission_denied: true };
        return null; 
    }
}"""
text = text.replace(old_cus, new_cus)

# requestApproval
old_ra = """async function requestApproval(user) {
    try {
        await fetch(FB_PROJECT.databaseURL + "/pending_users/" + user.uid + ".json", {
            method: "PUT", headers: {"Content-Type":"application/json"},
            body: JSON.stringify({ email: user.email, displayName: user.displayName || user.email.split("@")[0], requestedAt: Date.now() })
        });
    } catch(e) { console.error(e); }
}"""
new_ra = """async function requestApproval(user) {
    try {
        await firebase.database().ref("/pending_users/" + user.uid).set({
            email: user.email,
            displayName: user.displayName || user.email.split("@")[0],
            requestedAt: Date.now(),
            requestType: "new"
        });
    } catch(e) { console.error(e); }
}"""
text = text.replace(old_ra, new_ra)

with open('dashboard_tmp.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Step 13 done")
