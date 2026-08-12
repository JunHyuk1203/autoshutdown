with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Add general unlock button
target1 = """<button class="action-btn action-btn-blue" >🔄 전체 재부팅</button>"""
code1 = """<button class="action-btn action-btn-blue" >🔄 전체 재부팅</button>
                    <button class="action-btn action-btn-warning" onclick="sendGlobalCommand('unlock_screen', '')">🔓 전체 화면 깨우기</button>"""
text = text.replace(target1, code1)

# 2. Add individual unlock button
target2 = """<button class="action-btn action-btn-blue" onclick="executeRemoteCommand('${pcId}', 'restart')">🔄 재부팅</button>"""
code2 = """<button class="action-btn action-btn-blue" onclick="executeRemoteCommand('${pcId}', 'restart')">🔄 재부팅</button>
                    <button class="action-btn action-btn-warning" onclick="executeRemoteCommand('${pcId}', 'unlock_screen')">🔓 깨우기</button>"""
text = text.replace(target2, code2)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(text)

print("Patched index.html")
