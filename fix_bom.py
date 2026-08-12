with open("auto_shutdown.py", "r", encoding="utf-8-sig") as f:
    text = f.read()

# Remove BOM characters anywhere in the middle of the file
text = text.replace("\ufeff", "")

with open("auto_shutdown.py", "w", encoding="utf-8") as f:
    f.write(text)

import py_compile
try:
    py_compile.compile("auto_shutdown.py", doraise=True)
    print("Syntax OK")
except py_compile.PyCompileError as e:
    print(f"Syntax ERROR: {e}")
