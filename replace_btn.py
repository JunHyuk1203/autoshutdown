# -*- coding: utf-8 -*-
import os

def replace_btn(fname):
    with open(fname, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    out_lines = []
    for line in lines:
        if 'close_active_window' in line and 'card-action-btn' in line:
            indent = line[:len(line) - len(line.lstrip())]
            new_line = indent + '<button class="card-action-btn btn-dark" onclick="event.stopPropagation(); openVolumeControl(\'${pcId}\')" ${isOnline ? \'\' : \'disabled\'} title="원격 음량 제어" style="grid-column: 2 / 3;">🔊 음량조절</button>\n'
            out_lines.append(new_line)
        else:
            out_lines.append(line)

    with open(fname, 'w', encoding='utf-8') as f:
        f.write("".join(out_lines))

replace_btn('dashboard.html')
replace_btn('index.html')
print("Replaced close_active_window with openVolumeControl")
