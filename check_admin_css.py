import sys
sys.stdout.reconfigure(encoding="utf-8")
with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
print(re.findall(r'#admin-panel-overlay\s*\{[^}]*\}', text, re.DOTALL))
