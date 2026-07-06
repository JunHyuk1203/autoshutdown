import sys

def clean_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Remove SmartThings settings block in modal
    start_str = "<!-- SmartThings 연동 설정 -->"
    end_str = "<!-- 학교 정보 설정 (NEIS 연동) -->"
    if start_str in content and end_str in content:
        start_idx = content.find(start_str)
        end_idx = content.find(end_str)
        content = content[:start_idx] + end_str + content[end_idx + len(end_str):]

    # 2. Remove WOL/SmartThings button from card
    # Find the button condition:
    target_btn = """                    : `<button class="card-action-btn btn-success" onclick="event.stopPropagation(); triggerWOL('${pcId}', '${pc.mac || ''}')" title="원격 전원 켜기" style="grid-column: 1 / -1;">⚡ 전원 켜기 (WOL)</button>`"""
    if target_btn in content:
        content = content.replace(target_btn, "                    : ''")

    # 3. Remove st config reading
    content = content.replace("const st = cfg.smartthings || {};", "")
    content = content.replace('document.getElementById("cfg-st-token").value = st.token || "";', "")
    content = content.replace('document.getElementById("cfg-st-device-id").value = st.deviceId || "";', "")

    # 4. Remove st config saving
    content = content.replace('const stToken = document.getElementById("cfg-st-token").value.trim();', "")
    content = content.replace('const stDeviceId = document.getElementById("cfg-st-device-id").value.trim();', "")
    
    st_payload = """        smartthings: {
            token: stToken,
            deviceId: stDeviceId
        },"""
    content = content.replace(st_payload, "")

    # 5. Remove triggerWOL function completely
    start_wol = "/** 원격 PC 전원 켜기 (WOL) 명령 전송 */\nasync function triggerWOL(pcId, mac) {"
    end_wol = "}\n\n/** 파일 열기 모달 열기 (개별 PC 또는 '__ALL__') */"
    if start_wol in content and end_wol in content:
        start_idx = content.find(start_wol)
        end_idx = content.find(end_wol)
        content = content[:start_idx] + end_wol + content[end_idx + len(end_wol):]

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

clean_file('index.html')
clean_file('dashboard.html')
print("Cleanup complete.")
