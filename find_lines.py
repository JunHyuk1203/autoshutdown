import sys
sys.stdout.reconfigure(encoding="utf-8")
with open("index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find key line numbers
for i, line in enumerate(lines, 1):
    if any(kw in line for kw in ["let pollerInterval", "APP_ACCESS_GRANTED", "let _fbAuth", "let adminPendingListener", "function _enterDashboard", "function _attachUserStatusListener", "function fetchPCData", "function setPollerInterval"]):
        print(f"{i}: {line.rstrip()}")
