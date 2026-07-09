# -*- coding: utf-8 -*-
import os

def add_slider_modal(fname):
    with open(fname, 'r', encoding='utf-8') as f:
        content = f.read()

    # The HTML for the modal
    modal_html = '''
<!-- ─────────────────────────────────────────────────────────────
   음량 제어 모달 (Slider)
   ───────────────────────────────────────────────────────────── -->
<div class="modal-overlay" id="volume-modal">
    <div class="modal-card" style="max-width: 400px; width: 95%;">
        <h3 class="modal-title" style="margin-bottom: 4px; display: flex; align-items: center; justify-content: space-between;">
            <span>🔊 원격 음량 제어</span>
            <span style="font-size: 12px; color: var(--accent-blue);" id="volume-target-label">-</span>
        </h3>
        <p style="font-size: 12px; color: var(--text-muted); margin-bottom: 24px;">슬라이더를 조절하여 대상 PC의 시스템 마스터 볼륨을 설정합니다.</p>
        
        <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 30px;">
            <span style="font-size: 16px;">🔈</span>
            <input type="range" id="volume-slider" min="0" max="100" value="50" style="flex-grow: 1; accent-color: var(--primary); cursor: pointer;" oninput="document.getElementById('volume-value-display').innerText = this.value + '%'">
            <span style="font-size: 16px;">🔊</span>
        </div>
        <div style="text-align: center; font-size: 24px; font-weight: 800; color: var(--accent-blue); margin-bottom: 20px;" id="volume-value-display">50%</div>
        
        <div class="modal-actions">
            <button class="modal-btn modal-btn-cancel" onclick="closeVolumeModal()">취소</button>
            <button class="modal-btn" style="background: var(--primary);" onclick="applyVolumeControl()">적용</button>
        </div>
    </div>
</div>
'''
    # Insert modal HTML before <!-- ─────────────────────────────────────────────────────────────
    #    JAVASCRIPT LOGIC
    if 'id="volume-modal"' not in content:
        content = content.replace('<!-- ─────────────────────────────────────────────────────────────\n   JAVASCRIPT LOGIC', modal_html + '\n<!-- ─────────────────────────────────────────────────────────────\n   JAVASCRIPT LOGIC')

    # The new JS for openVolumeControl
    new_js = '''
let _volumePcId = null;

function openVolumeControl(pcId) {
    _volumePcId = pcId;
    const label = pcId === "__ALL__" ? "전체 PC" : (pcs[pcId]?.hostname || pcId);
    document.getElementById("volume-target-label").innerText = label;
    
    // 기본값 50으로 초기화
    document.getElementById("volume-slider").value = 50;
    document.getElementById("volume-value-display").innerText = "50%";
    
    document.getElementById("volume-modal").classList.add("show");
}

function closeVolumeModal() {
    document.getElementById("volume-modal").classList.remove("show");
    _volumePcId = null;
}

function applyVolumeControl() {
    if (!_volumePcId) return;
    const vol = parseInt(document.getElementById("volume-slider").value);
    const scalar = vol / 100.0;
    
    if (_volumePcId === "__ALL__") {
        writeCommandToDB("__ALL__", "volume_control", { level: scalar });
        alert("전체 PC에 음량 " + vol + "% 설정 명령을 보냈습니다.");
    } else {
        writeCommandToDB(_volumePcId, "volume_control", { level: scalar });
        alert("해당 PC에 음량 " + vol + "% 설정 명령을 보냈습니다.");
    }
    
    closeVolumeModal();
}
'''
    # Replace the old JS `function openVolumeControl(pcId) { ... }` with the new one
    old_js_start = 'function openVolumeControl(pcId) {'
    old_js_end = '}\n' # Wait, let's use regex or split to accurately remove the old function
    
    import re
    # Match the old function
    pattern = r'function openVolumeControl\(pcId\) \{.*?\n\}'
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, new_js.strip(), content, flags=re.DOTALL)
    
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(content)

add_slider_modal('dashboard.html')
add_slider_modal('index.html')
print("Volume slider modal added.")
