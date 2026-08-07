import sys, re
sys.stdout.reconfigure(encoding="utf-8")

with open("dashboard.html", "r", encoding="utf-8") as f:
    text = f.read()

# The loadApprovedUsers function - replace the entire row creation 
# to use data-uid and data-email attributes instead of inline params

old_row = """                    row.innerHTML = `
                        <div class="pending-user-info">
                            <div class="pending-user-email">
                                ${safeEmail}
                                <span style="background:#10b981; color:white; font-size:10px; padding:2px 6px; border-radius:4px; margin-left:4px;">승인됨</span>
                            </div>
                            <div class="pending-user-time">승인 일시 ${escapeHtml(time)}</div>
                        </div>
                        <button class="btn-reject" onclick="revokeUser('${safeUid}','${safeEmail.replace(/'/g, &quot;&#x27;&quot;)}')">🔴 박탈</button>
                    `;"""

new_row = """                    const revokeBtn = document.createElement("button");
                    revokeBtn.className = "btn-reject";
                    revokeBtn.textContent = "🔴 박탈";
                    revokeBtn.dataset.uid = uid;
                    revokeBtn.dataset.email = info.email || "";
                    revokeBtn.addEventListener("click", function() {
                        revokeUser(this.dataset.uid, this.dataset.email);
                    });
                    
                    const infoDiv = document.createElement("div");
                    infoDiv.className = "pending-user-info";
                    infoDiv.innerHTML = `
                        <div class="pending-user-email">
                            ${safeEmail}
                            <span style="background:#10b981; color:white; font-size:10px; padding:2px 6px; border-radius:4px; margin-left:4px;">승인됨</span>
                        </div>
                        <div class="pending-user-time">승인 일시 ${escapeHtml(time)}</div>
                    `;
                    row.appendChild(infoDiv);
                    row.appendChild(revokeBtn);"""

if old_row in text:
    text = text.replace(old_row, new_row)
    print("Replaced loadApprovedUsers row!")
else:
    print("NOT FOUND - trying to locate...")
    idx = text.find("safeEmail.replace(/'/g, &quot;&#x27;&quot;)")
    if idx != -1:
        print(f"Found at position {idx}")
        print(repr(text[max(0,idx-200):idx+50]))

with open("dashboard.html", "w", encoding="utf-8") as f:
    f.write(text)
