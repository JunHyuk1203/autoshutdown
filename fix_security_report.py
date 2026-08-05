import re

with open('dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Add name attributes to auth inputs
text = text.replace('id="auth-email-input" type="email"', 'id="auth-email-input" type="email" name="email"')
text = text.replace('id="auth-pw-input" type="password"', 'id="auth-pw-input" type="password" name="password"')

# 2. Add inert toggle in _showScreen
old_show = '''function _showScreen(id) {
    const screens = ["auth-view", "verify-email-view", "pending-view", "revoked-view", "dashboard-view"];
    screens.forEach(s => {
        document.getElementById(s).style.display = (s === id) ? "flex" : "none";
    });
}'''
new_show = '''function _showScreen(id) {
    const screens = ["auth-view", "verify-email-view", "pending-view", "revoked-view", "dashboard-view"];
    screens.forEach(s => {
        const el = document.getElementById(s);
        if (s === id) {
            el.style.display = "flex";
            el.removeAttribute("inert");
        } else {
            el.style.display = "none";
            el.setAttribute("inert", "");
        }
    });
}'''
text = text.replace(old_show, new_show)

# 3. Clear sensitive data and close overlays in signOutAndReset
old_signout = '''window._dashboardInitialized = false;
            
            _showScreen("auth-view");
        });
    }
}'''
new_signout = '''window._dashboardInitialized = false;
            
            // Clear sensitive DOM data
            const els = ["pc-grid", "of-list", "pending-user-list", "approved-user-list", "fav-list"];
            els.forEach(id => {
                const el = document.getElementById(id);
                if (el) el.innerHTML = "";
            });
            
            // Close all overlays/modals
            const modals = ["admin-panel-overlay", "config-modal", "windows-modal", "open-file-modal", "volume-modal"];
            modals.forEach(id => {
                const el = document.getElementById(id);
                if (el) {
                    el.style.display = "none";
                    el.classList.remove("show");
                }
            });
            
            _showScreen("auth-view");
        });
    }
}'''
text = text.replace(old_signout, new_signout)

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Done")
