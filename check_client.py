import sys
sys.stdout.reconfigure(encoding="utf-8")
with open("아트시크_셧다운.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
print("Requests used:", text.find("requests.put") != -1 or text.find("requests.patch") != -1 or text.find("requests.post") != -1)
print("Auth used:", text.find("auth") != -1)
print("Secret used:", text.find("authKey") != -1 or text.find("auth=") != -1)

match = re.search(r'requests\.[a-z]+\([^)]+\)', text)
if match:
    print(match.group(0))
