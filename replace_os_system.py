# -*- coding: utf-8 -*-
import os

def fix_os_system(fname):
    with open(fname, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1
    content = content.replace(
        "os.system('shutdown /s /t 0')", 
        "subprocess.run(['shutdown', '/s', '/t', '0'], creationflags=subprocess.CREATE_NO_WINDOW)"
    )
    # 2
    content = content.replace(
        "os.system('rundll32.exe powrprof.dll,SetSuspendState 0,1,0')", 
        "subprocess.run(['rundll32.exe', 'powrprof.dll,SetSuspendState', '0,1,0'], creationflags=subprocess.CREATE_NO_WINDOW)"
    )
    # 3
    content = content.replace(
        "os.system('shutdown /r /t 0')", 
        "subprocess.run(['shutdown', '/r', '/t', '0'], creationflags=subprocess.CREATE_NO_WINDOW)"
    )

    with open(fname, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed os.system calls")

fix_os_system('auto_shutdown.py')
