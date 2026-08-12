import re

with open("auto_shutdown.py", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace('CURRENT_VERSION = "1.1.140"', 'CURRENT_VERSION = "1.1.143"')
text = text.replace('CURRENT_VERSION = "1.1.142"', 'CURRENT_VERSION = "1.1.143"')

with open("auto_shutdown.py", "w", encoding="utf-8") as f:
    f.write(text)

with open("version.json", "r", encoding="utf-8") as f:
    vtext = f.read()
vtext = re.sub(r'1\.1\.14[02]', '1.1.143', vtext)
with open("version.json", "w", encoding="utf-8") as f:
    f.write(vtext)

print("Updated versions to 1.1.143")
