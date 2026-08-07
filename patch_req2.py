import re

with open("auto_shutdown.py", "r", encoding="utf-8") as f:
    text = f.read()

# Make sure requests is imported
if "import requests" not in text:
    text = text.replace("import urllib.request\n", "import urllib.request\nimport requests\nimport urllib3\nurllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)\n")

def patch_poller(class_name, text):
    # Regex to find the http_poller_thread method
    pattern = r'(def http_poller_thread\(self\):.*?while getattr\(self, \'is_running\', True\):)(.*?)(\n        except Exception as ge:)'
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        print(f"Could not find http_poller_thread in {class_name}")
        return text

    prefix = match.group(1)
    body = match.group(2)
    suffix = match.group(3)

    # Insert session initialization before the loop
    session_init = """
        if not hasattr(self, 'http_session'):
            self.http_session = requests.Session()
            self.http_session.verify = False
"""
    prefix = prefix.replace("def http_poller_thread(self):", "def http_poller_thread(self):" + session_init)

    # 1. Replace PATCH block
    # We will just rewrite the whole body up to "cmd = None"
    # Wait, the body has a lot of things. It's safer to just regex replace specific urllib calls.
    
    # PATCH
    body = re.sub(
        r'patch_req = urllib\.request\.Request\([\s\S]*?with urllib\.request\.urlopen\(patch_req, timeout=10, context=ssl_context\) as res:\s*pass',
        r'''try:
                        self.http_session.patch(patch_url, data=status_payload, headers={'Content-Type': 'application/json'}, timeout=10)
                    except Exception as _pe:
                        pass''',
        body
    )
    
    # GET cmd
    body = re.sub(
        r'cmd_req = urllib\.request\.Request\(cmd_url, method=\'GET\'.*?with urllib\.request\.urlopen\(cmd_req, timeout=[0-9]+, context=ssl_context\) as res:\s*cmd = json\.loads\(res\.read\(\)\.decode\(\'utf-8\'\)\)',
        r'''try:
                    res = self.http_session.get(cmd_url, timeout=6)
                    if res.status_code == 200:
                        cmd = res.json()''',
        body, flags=re.DOTALL
    )

    # GET all_cmd
    body = re.sub(
        r'all_cmd_req = urllib\.request\.Request\(all_cmd_url, method=\'GET\'.*?with urllib\.request\.urlopen\(all_cmd_req, timeout=[0-9]+, context=ssl_context\) as res:\s*cmd = json\.loads\(res\.read\(\)\.decode\(\'utf-8\'\)\)',
        r'''try:
                        res = self.http_session.get(all_cmd_url, timeout=6)
                        if res.status_code == 200:
                            cmd = res.json()''',
        body, flags=re.DOTALL
    )

    # DELETE cmd
    body = re.sub(
        r'del_req = urllib\.request\.Request\(del_url, method=\'DELETE\'.*?with urllib\.request\.urlopen\(del_req, timeout=[0-9]+, context=ssl_context\) as res:\s*pass',
        r'''try:
                                self.http_session.delete(del_url, timeout=6)
                            except Exception as _de:
                                pass''',
        body, flags=re.DOTALL
    )
    
    # PATCH set_config
    body = re.sub(
        r'cfg_patch_req = urllib\.request\.Request\([\s\S]*?with urllib\.request\.urlopen\(cfg_patch_req, timeout=[0-9]+, context=ssl_context\) as _:\s*pass',
        r'''try:
                                        self.http_session.patch(cfg_patch_url, data=cfg_patch_payload, headers={'Content-Type': 'application/json'}, timeout=5)
                                    except Exception as _ce:
                                        pass''',
        body
    )

    return text[:match.start()] + prefix + body + suffix + text[match.end():]

# We must do this for both GUI (AutoShutdownApp) and Headless (HeadlessClient)
# Since the regex uses re.DOTALL and finds the FIRST match, we can just run it twice.
# But wait, AutoShutdownApp has the first one. HeadlessClient has the second.
# Let's just split by class.
parts = text.split("class HeadlessShutdownApp:")
if len(parts) == 2:
    parts[0] = patch_poller("GUI", parts[0])
    parts[1] = patch_poller("Headless", parts[1])
    text = parts[0] + "class HeadlessShutdownApp:" + parts[1]
else:
    print("Could not split by class HeadlessShutdownApp")

text = text.replace('CURRENT_VERSION = "1.1.131"', 'CURRENT_VERSION = "1.1.133"')
text = text.replace('CURRENT_VERSION = "1.1.132"', 'CURRENT_VERSION = "1.1.133"')

with open("auto_shutdown.py", "w", encoding="utf-8") as f:
    f.write(text)

with open("version.json", "r", encoding="utf-8") as f:
    vtext = f.read()
vtext = re.sub(r'1\.1\.13[12]', '1.1.133', vtext)
with open("version.json", "w", encoding="utf-8") as f:
    f.write(vtext)

print("auto_shutdown.py fully patched with requests.Session() !!")
