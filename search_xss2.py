with open('dashboard_tmp.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if 'innerHTML' in line and '$' in line:
        print(f"L{i+1}: {line.strip()}")
