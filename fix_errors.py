import sys

sys.stdout.reconfigure(encoding="utf-8")
with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

# Add error handler for loadPendingUsers
text = text.replace(
    'adminPendingListener = firebase.database().ref("/pending_users").on("value", async snapshot => {',
    'adminPendingListener = firebase.database().ref("/pending_users").on("value", async snapshot => {'
)
# Ah I need to replace the end of the block.
# Let's just do it with python regex
import re
text = re.sub(
    r'(adminPendingListener = firebase\.database\(\)\.ref\("/pending_users"\)\.on\("value", async snapshot => \{[\s\S]*?\n    \}\);)',
    r'\1'.replace('});', '}, err => { document.getElementById("pending-user-list").innerHTML = `<p style="color:#fca5a5;text-align:center;padding:20px 0;">에러: ${err.message}</p>`; });'),
    text,
    count=1
)

text = re.sub(
    r'(adminUsersListener = firebase\.database\(\)\.ref\("/users"\)\.on\("value", async snapshot => \{[\s\S]*?\n    \}\);)',
    r'\1'.replace('});', '}, err => { document.getElementById("approved-user-list").innerHTML = `<p style="color:#fca5a5;text-align:center;padding:20px 0;">에러: ${err.message}</p>`; });'),
    text,
    count=1
)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(text)
print("done")
