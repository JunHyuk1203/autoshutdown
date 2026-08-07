import sys
import re
with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

handlers = re.findall(r'\s+on[a-z]+="[^"]+"', text)
print("Remaining handlers:", len(handlers))
for h in set(handlers):
    print(h)
