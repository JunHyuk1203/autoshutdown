import sys
sys.stdout.reconfigure(encoding="utf-8")
with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
print("confirm-modal z-index:", re.findall(r'#confirm-modal.*?z-index:\s*(\d+)', text, re.DOTALL))
print("admin-panel-overlay z-index:", re.findall(r'#admin-panel-overlay.*?z-index:\s*(\d+)', text, re.DOTALL))
print("modal-overlay z-index:", re.findall(r'\.modal-overlay.*?z-index:\s*(\d+)', text, re.DOTALL))
