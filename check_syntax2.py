import sys, ast
sys.stdout.reconfigure(encoding="utf-8")

with open("temp_check2.js", "r", encoding="utf-8") as f:
    text = f.read()

opens = {"{": 0, "(": 0, "[": 0}
closes = {"}": "{", ")": "(", "]": "["}
in_str = None
in_ml_comment = False
lines = text.split("\n")
brace_stack = []

for line_num, line in enumerate(lines, 1):
    i = 0
    while i < len(line):
        c = line[i]
        if in_ml_comment:
            if c == "*" and i+1 < len(line) and line[i+1] == "/":
                in_ml_comment = False
                i += 1
        elif in_str:
            if c == "\\" and in_str != "`":
                i += 1  # skip escaped char
            elif c == in_str:
                in_str = None
        else:
            if c == "/" and i+1 < len(line) and line[i+1] == "*":
                in_ml_comment = True
                i += 1
            elif c == "/" and i+1 < len(line) and line[i+1] == "/":
                break  # single line comment, stop
            elif c in ('"', "'", "`"):
                in_str = c
            elif c in ("{", "(", "["):
                brace_stack.append((c, line_num))
            elif c in ("}", ")", "]"):
                if brace_stack and brace_stack[-1][0] == closes[c]:
                    brace_stack.pop()
                else:
                    print(f"MISMATCH at L{line_num}: unexpected {c!r}, stack top: {brace_stack[-1] if brace_stack else None}")
                    if len(brace_stack) == 0:
                        print("Stack is empty!")
        i += 1

if brace_stack:
    print(f"UNCLOSED: {len(brace_stack)} unclosed delimiters")
    for ch, ln in brace_stack[-10:]:
        print(f"  {ch!r} opened at L{ln}")
else:
    print("All braces/parens/brackets balanced!")
