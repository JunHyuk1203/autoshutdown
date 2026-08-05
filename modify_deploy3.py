with open('github_deploy.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if '[3단계] auto_shutdown.exe' in line:
        indent = line[:line.find('print')]
        new_lines.append(indent + 'print("\\n[2.5단계] 클라이언트 코드 암호화(Obfuscation) 적용...")\n')
        new_lines.append(indent + 'try:\n')
        new_lines.append(indent + '    subprocess.run([sys.executable, "build_obf.py"], check=True, cwd=BASE_DIR)\n')
        new_lines.append(indent + '    import shutil\n')
        new_lines.append(indent + '    shutil.copy(app_path, app_path + ".bak")\n')
        new_lines.append(indent + '    shutil.copy(os.path.join(BASE_DIR, "auto_shutdown_runner.py"), app_path)\n')
        new_lines.append(indent + '    print("암호화 적용 완료.")\n')
        new_lines.append(indent + 'except Exception as e:\n')
        new_lines.append(indent + '    print(f"[Error] 암호화 실패: {e}")\n')
        new_lines.append(line)
    elif '[4단계] GitHub Release' in line:
        indent = line[:line.find('print')]
        new_lines.append(indent + 'print("\\n[3-3단계] 원본 클라이언트 코드 복구...")\n')
        new_lines.append(indent + 'try:\n')
        new_lines.append(indent + '    import shutil\n')
        new_lines.append(indent + '    shutil.move(app_path + ".bak", app_path)\n')
        new_lines.append(indent + 'except Exception as e:\n')
        new_lines.append(indent + '    pass\n')
        new_lines.append(line)
    else:
        new_lines.append(line)

with open('github_deploy.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
