with open("auto_shutdown.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1
for i, line in enumerate(lines):
    if "def _open_autologin_settings_gui(self):" in line:
        start_idx = i
    if start_idx != -1 and i > start_idx and line.startswith("    def "):
        end_idx = i
        break

print(f"start: {start_idx+1}, end: {end_idx+1}")
print("--- start ---")
print("".join(lines[start_idx:start_idx+5]))
print("--- end ---")
print("".join(lines[end_idx-3:end_idx+2]))
