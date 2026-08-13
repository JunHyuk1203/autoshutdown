import os, sys, urllib.request, ssl, json, subprocess

BASE_DIR = r"c:\Users\tntdr\.gemini\antigravity-ide\scratch\auto_shutdown"
git_exe = r"C:\Program Files\Git\cmd\git.exe"
tag = "v1.1.162"
REPO_OWNER = "JunHyuk1203"
REPO_NAME = "autoshutdown"

try:
    _ssl = ssl._create_unverified_context()
except Exception:
    _ssl = None

def _get_github_token():
    try:
        r = subprocess.run(
            [git_exe, "credential", "fill"],
            input="protocol=https\nhost=github.com\n\n",
            capture_output=True, text=True
        )
        for line in r.stdout.splitlines():
            if line.startswith("password="):
                return line.split("=", 1)[1]
    except Exception:
        pass
    return None

token = _get_github_token()
if not token:
    print("No token")
    sys.exit(1)

def _gh_api(method, path, token, data=None):
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github+json")
    if data:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(data).encode("utf-8")
    with urllib.request.urlopen(req, context=_ssl, timeout=30) as resp:
        if resp.status == 204:
            return None
        return json.loads(resp.read().decode("utf-8"))

release = _gh_api("GET", f"/repos/{REPO_OWNER}/{REPO_NAME}/releases/tags/{tag}", token)
upload_url_base = release["upload_url"].split("{")[0]

installer_exe_path = os.path.join(BASE_DIR, "dist", "스마트_전원_관리자_설치파일.exe")
if os.path.exists(installer_exe_path):
    print("Uploading installer...")
    with open(installer_exe_path, "rb") as ef:
        inst_data = ef.read()
    inst_url = f"{upload_url_base}?name=Smart_Power_Manager_Installer.exe"
    up_req2 = urllib.request.Request(
        inst_url, data=inst_data, method="POST",
        headers={"Authorization": f"token {token}", "Content-Type": "application/octet-stream", "Accept": "application/vnd.github+json"}
    )
    with urllib.request.urlopen(up_req2, context=_ssl, timeout=300) as resp:
        print("Uploaded successfully!")
else:
    print("Installer not found at:", installer_exe_path)
