with open("new_func.txt", "r", encoding="utf-8") as f:
    new_func = f.read()

with open("auto_shutdown.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1
for i, line in enumerate(lines):
    if "    def _open_autologin_settings_gui(self):" in line:
        start_idx = i
    if start_idx != -1 and i > start_idx and line.startswith("    def "):
        end_idx = i
        break

new_lines = lines[:start_idx] + [new_func] + lines[end_idx:]
with open("auto_shutdown.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)
print(f"Done, replaced lines {start_idx+1} to {end_idx}")
