"""배치 vs VBScript vs 직접실행 비교 테스트"""
import os, subprocess, time

TEST_DIR = os.path.join(os.getcwd(), "_update_test")
exe_path = os.path.join(TEST_DIR, "auto_shutdown.exe")

# 이전 프로세스 정리
subprocess.run(['taskkill', '/IM', 'auto_shutdown.exe', '/F'], 
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2)

print("=== 테스트 1: VBScript로 실행 ===")
vbs_path = os.path.join(TEST_DIR, "_launcher.vbs")
with open(vbs_path, 'w') as f:
    f.write('WScript.Sleep 3000\n')
    f.write(f'Set WshShell = CreateObject("WScript.Shell")\n')
    f.write(f'WshShell.Run Chr(34) & "{exe_path}" & Chr(34), 0\n')
    f.write('Set WshShell = Nothing\n')

# WScript는 별도 프로세스로 실행
subprocess.Popen(
    ['wscript.exe', vbs_path],
    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
)
print("  VBScript 실행됨, 8초 대기...")
time.sleep(8)

# 실행 확인
result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq auto_shutdown.exe'], 
                       capture_output=True, text=True)
if 'auto_shutdown.exe' in result.stdout:
    print("  [PASS] VBScript 경유 실행 성공!")
else:
    print("  [FAIL] 실행 안됨")

# 정리
subprocess.run(['taskkill', '/IM', 'auto_shutdown.exe', '/F'], 
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2)

print("\n=== 테스트 2: PowerShell Start-Process로 실행 ===")
ps_path = os.path.join(TEST_DIR, "_launcher.ps1")
with open(ps_path, 'w') as f:
    f.write('Start-Sleep -Seconds 3\n')
    f.write(f'$env:TCL_LIBRARY = $null\n')
    f.write(f'$env:TK_LIBRARY = $null\n')
    f.write(f'$env:_MEIPASS = $null\n')
    f.write(f'$env:_MEIPASS2 = $null\n')
    f.write(f'Start-Process -FilePath "{exe_path}"\n')

subprocess.Popen(
    ['powershell.exe', '-ExecutionPolicy', 'Bypass', '-WindowStyle', 'Hidden', '-File', ps_path],
    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
)
print("  PowerShell 실행됨, 8초 대기...")
time.sleep(8)

result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq auto_shutdown.exe'], 
                       capture_output=True, text=True)
if 'auto_shutdown.exe' in result.stdout:
    print("  [PASS] PowerShell 경유 실행 성공!")
else:
    print("  [FAIL] 실행 안됨")

# 정리
subprocess.run(['taskkill', '/IM', 'auto_shutdown.exe', '/F'], 
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)

# 임시 파일 정리
for f in [vbs_path, ps_path]:
    if os.path.exists(f): os.remove(f)

print("\n[완료]")
