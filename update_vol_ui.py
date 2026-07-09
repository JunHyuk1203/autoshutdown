# -*- coding: utf-8 -*-
import os

def update_volume_init(fname):
    with open(fname, 'r', encoding='utf-8') as f:
        content = f.read()

    old_code = '''
    // 기본값 50으로 초기화
    document.getElementById("volume-slider").value = 50;
    document.getElementById("volume-value-display").innerText = "50%";
'''

    new_code = '''
    // 기본값 설정 (현재 음량 정보가 있으면 사용, 없으면 50)
    let currentVol = 50;
    if (pcId !== "__ALL__" && pcs[pcId] && typeof pcs[pcId].volume !== "undefined") {
        currentVol = pcs[pcId].volume;
    }
    document.getElementById("volume-slider").value = currentVol;
    document.getElementById("volume-value-display").innerText = currentVol + "%";
'''

    if old_code in content:
        content = content.replace(old_code, new_code)
        with open(fname, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {fname}")
    else:
        print(f"Could not find target code in {fname}")

update_volume_init('dashboard.html')
update_volume_init('index.html')
