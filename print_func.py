import sys
sys.stdout.reconfigure(encoding="utf-8")
with open("dashboard.html", "r", encoding="utf-8") as f:
    text = f.read()

# Print the loadApprovedUsers function
import re
match = re.search(r'function loadApprovedUsers\(\) \{.*?\n\}', text, re.DOTALL)
if match:
    print(match.group(0))
else:
    print("Function not found with regex.")
