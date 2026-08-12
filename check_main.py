with open("auto_shutdown.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "if __name__ ==" in line:
        print("".join(lines[i:i+20]))
        break
