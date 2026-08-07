import sys
sys.stdout.reconfigure(encoding="utf-8")
with open("dashboard.html", "r", encoding="utf-8") as f:
    text = f.read()

# Check if _isApproved is defined as a function
if "function _isApproved" in text:
    print("FOUND: function _isApproved")
else:
    print("MISSING: function _isApproved - not defined anywhere!")

# Check role field usage in users path
import re
matches = re.findall(r'role.*?"([^"]+)"', text)
print("Role values used:", set(matches))

# Check what fields get written to /users/
writes = re.findall(r'firebase\.database\(\)\.ref\("/users/.*?\.set\(\{([^}]+)\}', text, re.DOTALL)
for w in writes:
    print("WRITE TO /users:", w.strip()[:200])
