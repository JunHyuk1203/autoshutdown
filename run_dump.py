import os
import subprocess

test_py = 'dump_env.py'
with open(test_py, 'w') as f:
    f.write('import os\nfor k, v in os.environ.items():\n    if "MEI" in k or "PYINSTALLER" in k or "TCL" in k:\n        print(f"{k}={v}")\n')

subprocess.run(['pyinstaller', '--onefile', '--clean', '--noconfirm', test_py], capture_output=True)
result = subprocess.run(['dist/dump_env.exe'], capture_output=True, text=True)
print("VARS:")
print(result.stdout)
if os.path.exists(test_py): os.remove(test_py)
