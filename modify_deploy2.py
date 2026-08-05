with open('github_deploy.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Find the exact line and indent
target1 = 'print("\\n[3단계] auto_shutdown.exe'
inject1 = '''print("\\n[2.5단계] 클라이언트 코드 암호화(Obfuscation) 적용...")
  try:
      subprocess.run([sys.executable, "build_obf.py"], check=True, cwd=BASE_DIR)
      import shutil
      shutil.copy(app_path, app_path + ".bak")
      shutil.copy(os.path.join(BASE_DIR, "auto_shutdown_runner.py"), app_path)
      print("암호화 적용 완료.")
  except Exception as e:
      print(f"[Error] 암호화 실패: {e}")
  
  print("\\n[3단계] auto_shutdown.exe'''

text = text.replace(target1, inject1)

target2 = 'print("\\n[4단계] GitHub Release'
inject2 = '''print("\\n[3-3단계] 원본 클라이언트 코드 복구...")
  try:
      import shutil
      shutil.move(app_path + ".bak", app_path)
  except Exception as e:
      pass
  
  print("\\n[4단계] GitHub Release'''

text = text.replace(target2, inject2)

with open('github_deploy.py', 'w', encoding='utf-8') as f:
    f.write(text)
