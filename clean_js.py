import re

with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

save_pattern = re.compile(r'function saveConfiguration\(\) \{.*?\}\n', re.DOTALL)
text = re.sub(save_pattern, '', text)

reset_pattern = re.compile(r'function resetConfiguration\(\) \{.*?\}\n', re.DOTALL)
text = re.sub(reset_pattern, '', text)

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done")
