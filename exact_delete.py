with open('dashboard.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Convert to 0-indexed lists of indices to delete
to_delete = list(range(1016, 1038)) + list(range(1573, 1614))

# Keep only the lines not in the to_delete list
new_lines = [line for i, line in enumerate(lines) if i not in to_delete]

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print("Done")
