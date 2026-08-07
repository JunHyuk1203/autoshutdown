import sys, ast
sys.stdout.reconfigure(encoding="utf-8")
with open("temp.js", "r", encoding="utf-8") as f:
    text = f.read()

try:
    # Just a sanity check for unclosed brackets, skipping comments and regex correctly
    import re
    # We will just print the context of loadApprovedUsers to see if there is any obvious issue
    start = text.find('function loadApprovedUsers()')
    print(text[start:start+2000])
except Exception as e:
    print(f"Error: {e}")
