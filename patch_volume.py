# -*- coding: utf-8 -*-
import os

def patch_file(fname):
    with open(fname, 'r', encoding='utf-8') as f:
        content = f.read()

    script = '''
function openVolumeControl(pcId) {
    let volStr = prompt("설정할 음량을 0 ~ 100 사이의 숫자로 입력하세요:\\n(예: 50)", "50");
    if (volStr === null) return;
    let vol = parseInt(volStr);
    if (isNaN(vol) || vol < 0 || vol > 100) {
        alert("올바른 0~100 사이의 숫자를 입력해주세요.");
        return;
    }
    let scalar = vol / 100.0;
    if (pcId === "__ALL__") {
        writeCommandToDB("__ALL__", "volume_control", { level: scalar });
        alert("전체 PC에 음량 설정 명령을 보냈습니다.");
    } else {
        writeCommandToDB(pcId, "volume_control", { level: scalar });
        alert("음량 설정 명령을 보냈습니다.");
    }
}
'''
    if 'openVolumeControl' not in content:
        content = content.replace('// ── 환경 구성 로드/저장 ──', script + '\n// ── 환경 구성 로드/저장 ──')
    
    global_btn = '''<button class="action-btn action-btn-secondary" onclick="openVolumeControl('__ALL__')">🔊 전체 음량제어</button>'''
    if '전체 음량제어' not in content:
        content = content.replace('''<button class="action-btn action-btn-dark" onclick="triggerCommandAll('close_active_window')">❌ 전체 창 닫기</button>''', '''<button class="action-btn action-btn-dark" onclick="triggerCommandAll('close_active_window')">❌ 전체 창 닫기</button>\n                    ''' + global_btn)
    
    single_btn = '''<button class="card-action-btn btn-secondary" onclick="event.stopPropagation(); openVolumeControl('${pcId}')" ${isOnline ? '' : 'disabled'} title="원격 음량 제어" style="grid-column: 1 / 4; padding: 4px; font-size: 9px;">🔊 음량 제어</button>'''
    if '🔊 음량 제어' not in content:
        content = content.replace('''<button class="card-action-btn btn-teal" onclick="event.stopPropagation(); openWindowsModal('${pcId}')" title="실행 중인 창 목록 보기" style="grid-column: 3 / 4;">🖥️실행 창</button>''', '''<button class="card-action-btn btn-teal" onclick="event.stopPropagation(); openWindowsModal('${pcId}')" title="실행 중인 창 목록 보기" style="grid-column: 3 / 4;">🖥️실행 창</button>\n                ''' + single_btn)

    with open(fname, 'w', encoding='utf-8') as f:
        f.write(content)

patch_file('dashboard.html')
patch_file('index.html')
print('HTML Patched')
