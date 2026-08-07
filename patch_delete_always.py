import re

with open("auto_shutdown.py", "r", encoding="utf-8") as f:
    text = f.read()

target = "if cmd_success and cmd_type == 'individual':"
replacement = "if cmd_type == 'individual':"

if target in text:
    text = text.replace(target, replacement)
    print("Patched GUI & Headless to always delete commands!")
else:
    print("Could not find target!")

text = text.replace('CURRENT_VERSION = "1.1.138"', 'CURRENT_VERSION = "1.1.139"')
text = text.replace('CURRENT_VERSION = "1.1.137"', 'CURRENT_VERSION = "1.1.139"')

with open("auto_shutdown.py", "w", encoding="utf-8") as f:
    f.write(text)

with open("version.json", "r", encoding="utf-8") as f:
    vtext = f.read()
vtext = re.sub(r'1\.1\.13[78]', '1.1.139', vtext)
with open("version.json", "w", encoding="utf-8") as f:
    f.write(vtext)

