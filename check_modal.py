import sys
sys.stdout.reconfigure(encoding="utf-8")
with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

start = text.find('id="account-modal"')
print(text[start-100:start+200] if start != -1 else "account-modal NOT FOUND!")
