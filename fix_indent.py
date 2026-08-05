import re

with open('github_deploy.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix indentation error by ensuring proper space alignment
def fix_indent(match):
    return match.group(1).replace('\n', '\n' + ' ' * 4)

text = text.replace('print("\n[2.5단계] 클라이언트 코드 암호화(Obfuscation) 적용...")', 'print("\\n[2.5단계] 클라이언트 코드 암호화(Obfuscation) 적용...")')

# Re-do cleanly
text = re.sub(r'\n(\s*print\("\[2\.5단계\](.*?)except Exception as e:\s*print\(f"\[Error\] 암호화 실패: \{e\}"\))', lambda m: '\n' + m.group(1).replace('\n', '\n' + ' ' * 4), text, flags=re.DOTALL)

with open('github_deploy.py', 'w', encoding='utf-8') as f:
    f.write(text)
