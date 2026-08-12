import re

with open("auto_shutdown.py", "r", encoding="utf-8") as f:
    text = f.read()
text = text.replace('CURRENT_VERSION = "1.1.148"', 'CURRENT_VERSION = "1.1.149"')
with open("auto_shutdown.py", "w", encoding="utf-8") as f:
    f.write(text)

with open("version.json", "r", encoding="utf-8") as f:
    vtext = f.read()
vtext = re.sub(r'1\.1\.148', '1.1.149', vtext)
with open("version.json", "w", encoding="utf-8") as f:
    f.write(vtext)

print("Version bumped to 1.1.149")
