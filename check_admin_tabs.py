import sys
sys.stdout.reconfigure(encoding="utf-8")
with open("dashboard.html", "r", encoding="utf-8") as f:
    text = f.read()

start = text.find('class="admin-tabs"')
print(text[start:start+500])
