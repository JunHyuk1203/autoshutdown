import sys, re
sys.stdout.reconfigure(encoding="utf-8")

with open("dashboard.html", "r", encoding="utf-8") as f:
    text = f.read()

# Simply build the button HTML cleanly - no complex escaping needed
# revokeUser is called with uid and email. If email has apostrophe we escape it.
# The simplest safe approach: use data attributes instead of inline onclick parameters

# Find the problematic line and replace with simpler version
old = """                        <button class="btn-reject" onclick="revokeUser('${safeUid}','${safeEmail.replace(/&apos;/g, &apos;\\\\&apos;&apos;)}')">🔴 박탈</button>"""
new = """                        <button class="btn-reject" onclick="revokeUser('${safeUid}','${safeEmail.replace(/'/g, &quot;&#x27;&quot;)}')">🔴 박탈</button>"""

if old in text:
    text = text.replace(old, new)
    print("Replaced!")
else:
    print("Not found, trying different approach...")
    # Just find and replace the entire row.innerHTML block
    idx = text.find("safeEmail.replace(/&apos;")
    if idx != -1:
        print(f"Found &apos; at position {idx}")
        print(repr(text[idx-50:idx+100]))

with open("dashboard.html", "w", encoding="utf-8") as f:
    f.write(text)
