with open("github_deploy.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace('subprocess.run([sys.executable, "build_obf.py"]', '# subprocess.run([sys.executable, "build_obf.py"]')
with open("github_deploy.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Disabled obfuscation!")
