import sys

# Update auto_shutdown.py
with open("auto_shutdown.py", "r", encoding="utf-8") as f:
    text = f.read()
text = text.replace('CURRENT_VERSION = "1.1.122"', 'CURRENT_VERSION = "1.1.123"')
with open("auto_shutdown.py", "w", encoding="utf-8") as f:
    f.write(text)

# Update version.json
with open("version.json", "r", encoding="utf-8") as f:
    text = f.read()
text = text.replace('1.1.122', '1.1.123')
with open("version.json", "w", encoding="utf-8") as f:
    f.write(text)

print("Versions updated to 1.1.123")
