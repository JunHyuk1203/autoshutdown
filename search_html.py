import sys, re
sys.stdout.reconfigure(encoding="utf-8")
with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

# Look at the html around admin-panel-overlay
start = text.find('id="admin-panel-overlay"')
end = text.find('admin-tab-pending')
print(text[start:start+1000])
