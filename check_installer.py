import sys
sys.stdout.reconfigure(encoding="utf-8")
with open("installer.py", "r", encoding="utf-8") as f:
    text = f.read()
print(text.find("tntgame1203@gmail.com"))
