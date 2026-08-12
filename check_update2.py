with open("auto_shutdown.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i in range(1525, 1550):
    if i < len(lines):
        print(lines[i], end="")
