import sys
sys.stdout.reconfigure(encoding="utf-8")
import glob
for file in ["auto_shutdown.py", "auto_shutdown_runner.py"]:
    try:
        with open(file, "r", encoding="utf-8") as f:
            text = f.read()
            if "requests." in text:
                print(f"--- {file} ---")
                import re
                print(re.findall(r'requests\.[a-z]+\([^)]+\)', text))
    except Exception as e:
        print(f"Error {file}: {e}")
