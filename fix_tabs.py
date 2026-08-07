import sys
import re
import os

with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

# Add event listeners for the tabs at the end of bindStaticEvents
target = 'if (el_admin_close_btn) el_admin_close_btn.addEventListener("click", function(e) { closeAdminPanel(); });'
replacement = target + """
    const el_tab_btn_pending = document.getElementById("tab-btn-pending");
    const el_tab_btn_approved = document.getElementById("tab-btn-approved");
    const el_tab_btn_security = document.getElementById("tab-btn-security");
    
    if (el_tab_btn_pending) el_tab_btn_pending.addEventListener("click", () => { switchAdminTab('pending'); });
    if (el_tab_btn_approved) el_tab_btn_approved.addEventListener("click", () => { switchAdminTab('approved'); });
    if (el_tab_btn_security) el_tab_btn_security.addEventListener("click", () => { switchAdminTab('security'); });
"""

if target in text and "el_tab_btn_pending.addEventListener" not in text:
    text = text.replace(target, replacement)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(text)
    print("Event listeners added.")
else:
    print("Already added or target not found.")
