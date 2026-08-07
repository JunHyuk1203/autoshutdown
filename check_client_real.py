import sys
import glob
sys.stdout.reconfigure(encoding="utf-8")

# find the client script
files = glob.glob("**.py") + glob.glob("*_*.py")
for file in files:
    if file.endswith("installer.py"): continue
    try:
        with open(file, "r", encoding="utf-8") as f:
            text = f.read()
            if "requests." in text and "firebaseio.com" in text:
                print("FOUND:", file)
                import re
                match = re.search(r'requests\.[a-z]+\([^)]+\)', text)
                if match:
                    print(match.group(0))
    except:
        pass
