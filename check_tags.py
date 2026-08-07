import sys
import re
sys.stdout.reconfigure(encoding="utf-8")
with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

print("youtube match:", text.find("youtube"))
print("fontawesome match:", text.find("fontawesome"))
print("iframe match:", text.find("iframe"))
