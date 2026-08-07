import sys
import re

sys.stdout.reconfigure(encoding="utf-8")
with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

# Add error handling to fetchPCData if not present
if "const response = await fetch(" in text and "response.ok" not in text:
    target = """        const response = await fetch(config.databaseURL + "/pcs.json?auth=" + config.authKey);
        const data = await response.json();"""
    replacement = """        const response = await fetch(config.databaseURL + "/pcs.json?auth=" + config.authKey);
        if (!response.ok) {
            const errTxt = await response.text();
            console.error("fetchPCData HTTP Error:", response.status, errTxt);
            document.getElementById("pc-container").innerHTML = `<div style="color:var(--danger); padding:20px;">데이터 로드 실패 (HTTP ${response.status}): ${errTxt}</div>`;
            return;
        }
        const data = await response.json();"""
    text = text.replace(target, replacement)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(text)
print("fetchPCData error handler injected")
