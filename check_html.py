import sys, re
sys.stdout.reconfigure(encoding="utf-8")
with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

# check for any unclosed divs or broken HTML near the tabs
start = text.find('<div id="admin-tab-approved"')
print(text[start:start+500])
