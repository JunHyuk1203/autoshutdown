import subprocess, os

html = """<!DOCTYPE html>
<html>
<body>
<div id="res">EMPTY</div>
<script>
async function go() {
    try {
        const pc = new RTCPeerConnection({
            iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
        });
        pc.createDataChannel('test');
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);
        
        await new Promise(resolve => {
            if (pc.iceGatheringState === 'complete') resolve();
            else {
                pc.onicegatheringstatechange = () => {
                    if (pc.iceGatheringState === 'complete') resolve();
                };
                setTimeout(resolve, 2000);
            }
        });
        
        document.getElementById('res').innerText = pc.localDescription.sdp;
    } catch(e) {
        document.getElementById('res').innerText = 'ERROR: ' + e;
    }
}
go();
</script>
</body>
</html>
"""

with open("test_webrtc.html", "w", encoding="utf-8") as f:
    f.write(html)

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(chrome_path):
    chrome_path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

file_url = os.path.abspath("test_webrtc.html")
cmd = [chrome_path, "--headless=new", "--disable-gpu", "--dump-dom", file_url]
res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
lines = [l for l in res.stdout.splitlines() if "candidate" in l or "a=ice" in l]
print("Found lines:", len(lines))
for l in lines:
    print(" ", l)
