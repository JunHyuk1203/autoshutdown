import sys
sys.stdout.reconfigure(encoding="utf-8")
with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

start = text.find('id="logout-header-btn"')
print(text[start-200:start+200])
