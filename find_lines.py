with open('dashboard.html', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'function loadPendingUsers' in line:
            print(f'Found at line {i}')
