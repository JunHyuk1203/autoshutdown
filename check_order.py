with open("auto_shutdown.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if line.startswith("def encrypt_password"):
        print("encrypt_password at line", i)
    elif line.startswith("def set_auto_logon"):
        print("set_auto_logon at line", i)
    elif line.startswith("def run_standalone_autologin_gui"):
        print("run_standalone_autologin_gui at line", i)
