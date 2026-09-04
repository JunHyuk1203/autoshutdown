import subprocess, os

html = """<!DOCTYPE html>
<html><body><div id="res"></div>
<script>
async function test() {
    const t0 = performance.now();
    const pc = new RTCPeerConnection({
        iceServers: [
            { urls: 'stun:stun.l.google.com:19302' },
            { urls: 'stun:stun.cloudflare.com:3478' }
        ]
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
            setTimeout(resolve, 5000);
        }
    });
    const t1 = performance.now();
    const cands = pc.localDescription.sdp.split('\\r\\n').filter(l => l.includes('candidate'));
    document.getElementById('res').innerText = 'TIME:' + Math.round(t1-t0) + ' GATHER:' + pc.iceGatheringState + ' CANDS:' + cands.join(' || ');
}
test();
</script></body></html>"""

with open('test_gather.html', 'w', encoding='utf-8') as f:
    f.write(html)

chrome = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
cmd = [chrome, '--headless=new', '--disable-gpu', '--dump-dom', os.path.abspath('test_gather.html')]
res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
for line in res.stdout.splitlines():
    if 'TIME:' in line or 'candidate' in line:
        print(line)
