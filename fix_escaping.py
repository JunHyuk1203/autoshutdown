import os

for fname in ['dashboard.html', 'index.html', 'patch_html.py']:
    with open(fname, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # In dashboard.html and index.html:
    old_html = 'const safeName = item.name.replace(/\'/g, "\\\\\'").replace(/"/g, "&quot;");'
    new_html = 'const safeName = item.name.replace(/\\\\\\\\/g, "\\\\\\\\\\\\\\\\").replace(/\'/g, "\\\\\'").replace(/"/g, "&quot;");'
    content = content.replace(old_html, new_html)

    # In patch_html.py:
    old_py = r'''const safeName = item.name.replace(/'/g, "\\\\\\'").replace(/"/g, "&quot;");'''
    new_py = r'''const safeName = item.name.replace(/\\\\/g, "\\\\\\\\\\\\\\\\").replace(/'/g, "\\\\\\'").replace(/"/g, "&quot;");'''
    content = content.replace(old_py, new_py)

    with open(fname, 'w', encoding='utf-8') as f:
        f.write(content)
print("Done!")
