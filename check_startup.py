with open("auto_shutdown.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "if __name__ == \"__main__\":" in line:
        print("".join(lines[i:i+30]))
        break
