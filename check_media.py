import sys
sys.stdout.reconfigure(encoding="utf-8")
with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
matches = re.findall(r'@media.*\{[^}]*\}', text, re.DOTALL)
for m in matches:
    if "header-btn" in m or "account" in m:
        print(m)
