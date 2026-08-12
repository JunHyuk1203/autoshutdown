with open("github_deploy.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace('shutil.copy(os.path.join(BASE_DIR, "auto_shutdown_runner.py"), app_path)', '# shutil.copy(os.path.join(BASE_DIR, "auto_shutdown_runner.py"), app_path)')
with open("github_deploy.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Disabled obfuscation completely!")
