import sys
sys.stdout.reconfigure(encoding="utf-8")
with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()
print("confirm-modal exists: ", text.find('id="confirm-modal"') != -1)
