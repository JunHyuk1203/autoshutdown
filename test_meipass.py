import os
import sys
import subprocess
import time

def main():
    if "--child" in sys.argv:
        print("Child MEIPASS:", sys._MEIPASS)
        time.sleep(5)
        print("Child exiting")
    else:
        print("Parent MEIPASS:", getattr(sys, '_MEIPASS', 'Not Frozen'))
        
        env = os.environ.copy()
        for k in [k for k in env if k.upper() in ["TCL_LIBRARY", "TK_LIBRARY", "_MEIPASS2", "_MEIPASS"]]:
            env.pop(k, None)
            
        print("Starting child...")
        p = subprocess.Popen([sys.executable, "--child"], env=env, creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
        print("Child PID:", p.pid)
        time.sleep(1)
        print("Parent exiting")

if __name__ == "__main__":
    main()
