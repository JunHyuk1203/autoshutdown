import sys
import re

sys.stdout.reconfigure(encoding="utf-8")
with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

# Fix the syntax error: `user.email && .email.toLowerCase() === MASTER_EMAIL.toLowerCase()`
# Wait, it looks like `obj.email && .email.toLowerCase()`
# I can just use regex to capture the object before `.email` and fix it.
# Actually, the string is literally `.email && .email.toLowerCase()`
# I need to find `([a-zA-Z0-9_\.\?]+)\.email && \.email\.toLowerCase\(\)`
text = re.sub(r'([a-zA-Z0-9_\.\?]+)\.email && \.email\.toLowerCase\(\)', r'\1.email && \1.email.toLowerCase()', text)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(text)
print("done")
