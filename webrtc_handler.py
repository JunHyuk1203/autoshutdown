import asyncio
import json
import urllib.request
import threading
import time
import io

try:
    from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
    from av import VideoFrame
    import mss
    import pynput.mouse
    import pynput.keyboard
    WEBRTC_AVAILABLE = True
except ImportError:
    WEBRTC_AVAILABLE = False


class ScreenTrack(VideoStreamTrack):
    kind = "video"

    def __init__(self, monitor_idx=1):
        super().__init__()
        self.monitor_idx = monitor_idx
        self.sct = mss.mss()
        self.monitor = self.sct.monitors[monitor_idx]
        self.time_base = 1.0 / 15.0  # target 15 FPS

    async def recv(self):
        pts, time_base = await self.next_timestamp()
        
        # Grab screen
        shot = self.sct.grab(self.monitor)
        
        from PIL import Image
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        
        # Optionally resize to reduce bandwidth
        max_w = 1280
        if img.width > max_w:
            ratio = max_w / img.width
            img = img.resize((max_w, int(img.height * ratio)), Image.LANCZOS)
            
        frame = VideoFrame.from_image(img)
        frame.pts = pts
        frame.time_base = time_base
        return frame


class WebRTCServer:
    def __init__(self, pc_id, central_url, db_secret, ssl_context):
        self.pc_id = pc_id
        self.central_url = central_url
        self.db_secret = db_secret
        self.ssl_context = ssl_context
        self.mouse = pynput.mouse.Controller()
        self.keyboard = pynput.keyboard.Controller()
        
    def _firebase_read(self, path):
        url = f"{self.central_url.rstrip('/')}/{path}.json"
        if self.db_secret: url += f"?auth={self.db_secret}"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=5, context=self.ssl_context) as res:
                return json.loads(res.read().decode('utf-8'))
        except Exception:
            return None
            
    def _firebase_write(self, path, data):
        url = f"{self.central_url.rstrip('/')}/{path}.json"
        if self.db_secret: url += f"?auth={self.db_secret}"
        try:
            req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), method="PUT", headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=5, context=self.ssl_context) as _:
                pass
        except Exception:
            pass
            
    def _firebase_delete(self, path):
        url = f"{self.central_url.rstrip('/')}/{path}.json"
        if self.db_secret: url += f"?auth={self.db_secret}"
        try:
            req = urllib.request.Request(url, method="DELETE")
            with urllib.request.urlopen(req, timeout=5, context=self.ssl_context) as _:
                pass
        except Exception:
            pass

    async def run(self):
        pc = RTCPeerConnection()
        
        @pc.on("datachannel")
        def on_datachannel(channel):
            @channel.on("message")
            def on_message(message):
                try:
                    cmd = json.loads(message)
                    self._handle_input(cmd)
                except Exception:
                    pass

        # Wait for offer
        offer_dict = None
        for _ in range(15): # 15 seconds wait
            offer_dict = self._firebase_read(f"webrtc/{self.pc_id}/offer")
            if offer_dict:
                break
            await asyncio.sleep(1)
            
        if not offer_dict:
            await pc.close()
            return
            
        offer = RTCSessionDescription(sdp=offer_dict["sdp"], type=offer_dict["type"])
        await pc.setRemoteDescription(offer)
        
        # Add video track
        track = ScreenTrack()
        pc.addTrack(track)
        
        # Create answer
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        
        # Send answer
        self._firebase_write(f"webrtc/{self.pc_id}/answer", {
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type
        })
        
        # Delete offer to prevent re-processing
        self._firebase_delete(f"webrtc/{self.pc_id}/offer")
        
        # Wait until connection is closed or failed
        while pc.connectionState not in ["failed", "closed"]:
            await asyncio.sleep(1)
            
        await pc.close()
        
    def _handle_input(self, cmd):
        try:
            action = cmd.get("t")
            if action == "mousemove":
                monitors = mss.mss().monitors
                mon = monitors[1] if len(monitors) > 1 else monitors[0]
                abs_x = int(mon["left"] + cmd["x"] * mon["width"])
                abs_y = int(mon["top"] + cmd["y"] * mon["height"])
                self.mouse.position = (abs_x, abs_y)
            elif action == "mousedown":
                btn = cmd.get("b", 0)
                m_btn = pynput.mouse.Button.left if btn == 0 else pynput.mouse.Button.right
                self.mouse.press(m_btn)
            elif action == "mouseup":
                btn = cmd.get("b", 0)
                m_btn = pynput.mouse.Button.left if btn == 0 else pynput.mouse.Button.right
                self.mouse.release(m_btn)
            elif action == "keydown":
                self._press_key(cmd.get("k"), press=True)
            elif action == "keyup":
                self._press_key(cmd.get("k"), press=False)
        except Exception:
            pass
            
    def _press_key(self, key_str, press=True):
        key_map = {
            "Enter": pynput.keyboard.Key.enter,
            "Backspace": pynput.keyboard.Key.backspace,
            "Shift": pynput.keyboard.Key.shift,
            "Control": pynput.keyboard.Key.ctrl,
            "Alt": pynput.keyboard.Key.alt,
            "Escape": pynput.keyboard.Key.esc,
            "Tab": pynput.keyboard.Key.tab,
            "ArrowUp": pynput.keyboard.Key.up,
            "ArrowDown": pynput.keyboard.Key.down,
            "ArrowLeft": pynput.keyboard.Key.left,
            "ArrowRight": pynput.keyboard.Key.right,
            "Meta": pynput.keyboard.Key.cmd,
            "Delete": pynput.keyboard.Key.delete,
        }
        k = key_map.get(key_str)
        if not k:
            if len(key_str) == 1:
                k = pynput.keyboard.KeyCode.from_char(key_str)
            else:
                return
        try:
            if press:
                self.keyboard.press(k)
            else:
                self.keyboard.release(k)
        except Exception:
            pass


def start_webrtc_session(pc_id, central_url, db_secret, ssl_context):
    if not WEBRTC_AVAILABLE:
        return
        
    def _run_loop():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        server = WebRTCServer(pc_id, central_url, db_secret, ssl_context)
        loop.run_until_complete(server.run())
        loop.close()
        
    t = threading.Thread(target=_run_loop, daemon=True)
    t.start()
