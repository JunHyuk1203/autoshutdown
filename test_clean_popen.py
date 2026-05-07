import os, subprocess, time, sys
import urllib.request
import shutil

current_exe = sys.executable if getattr(sys, 'frozen', False) else None
if current_exe:
    # 1. 환경변수 청소
    clean_env = os.environ.copy()
    for k in list(clean_env.keys()):
        if 'MEI' in k or 'PYI' in k or 'TCL' in k or 'TK' in k:
            clean_env.pop(k, None)
    
    # 2. 실행
    subprocess.Popen([current_exe], env=clean_env, creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
    sys.exit(0)
