# -*- coding: utf-8 -*-
"""Fix index.html which has duplicate JS blocks from sync_index.py runs"""

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# There are two copies of: handleOpenSubmit ... sendOpenUrlCommand ... }
# The first copy is at pos ~93705 (old version without confirmation popup)
# The second copy is at pos ~96692 (new version with confirmation popup)
# We need to remove the first (old) copy.

# Find the two handleOpenSubmit positions
positions = []
idx = 0
while True:
    pos = content.find('async function handleOpenSubmit', idx)
    if pos == -1:
        break
    positions.append(pos)
    idx = pos + 1

if len(positions) < 2:
    print('Only one handleOpenSubmit found, nothing to remove')
else:
    first_pos = positions[0]
    second_pos = positions[1]
    # Remove everything from first_pos up to (not including) second_pos
    to_remove = content[first_pos:second_pos]
    content = content.replace(to_remove, '', 1)
    print(f'Removed {len(to_remove)} chars between pos {first_pos} and {second_pos}')

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(content)

# Verify
c1 = content.count('let _ofCurrentTab')
c2 = content.count('async function sendOpenUrlCommand')
c3 = content.count('async function handleOpenSubmit')
print(f'index.html after fix: _ofCurrentTab={c1}, sendOpenUrlCommand={c2}, handleOpenSubmit={c3}')

# Also fix dashboard.html which has sendOpenUrlCommand=2 (call + definition is fine, but check)
with open('dashboard.html', 'r', encoding='utf-8') as f:
    d = f.read()
d1 = d.count('async function sendOpenUrlCommand')
d2 = d.count('async function handleOpenSubmit')
print(f'dashboard.html: sendOpenUrlCommand(def)={d1}, handleOpenSubmit={d2}')
