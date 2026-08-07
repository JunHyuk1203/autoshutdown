import sys
sys.stdout.reconfigure(encoding="utf-8")
with open("dashboard.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
match = re.search(r'function loadPendingUsers\(\) \{.*?\n\}', text, re.DOTALL)
if match:
    print(match.group(0))
else:
    print("Function not found.")
