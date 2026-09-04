import asyncio
import json
import urllib.request
import threading
import time
import io

try:
    from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
    from aiortc.codecs import h264
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
        self.monitor = self.sct.monitors[monitor_idx] if len(self.sct.monitors) > monitor_idx else self.sct.monitors[0]
        self.time_base = 1.0 / 15.0  # target 15 FPS

    async def recv(self):
        pts, time_base = await self.next_timestamp()
        
        # Grab screen with fallback
        img = None
        try:
            shot = self.sct.grab(self.monitor)
            from PIL import Image
            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        except Exception:
            try:
                from PIL import ImageGrab
                img = ImageGrab.grab(all_screens=True)
            except Exception:
                pass
        
        if img is None:
            from PIL import Image
            img = Image.new("RGB", (1280, 720), color=(30, 30, 30))
        
        # Resize to max 1280, ensuring EVEN width and height for H264 (libx264) compatibility
        from PIL import Image
        max_w = 1280
        if img.width > max_w:
            ratio = max_w / img.width
            new_w = max_w
            new_h = int(img.height * ratio)
            new_w -= (new_w % 2)
            new_h -= (new_h % 2)
            img = img.resize((new_w, new_h), Image.LANCZOS)
        else:
            new_w = img.width - (img.width % 2)
            new_h = img.height - (img.height % 2)
            if new_w != img.width or new_h != img.height:
                img = img.crop((0, 0, new_w, new_h))
            
        frame = VideoFrame.from_image(img)
        frame.pts = pts
        frame.time_base = time_base
        return frame


class WebRTCServer:
    def __init__(self, pc_id, central_url, db_secret, ssl_context, offer_dict=None):
        self.pc_id = pc_id
        self.central_url = central_url
        self.db_secret = db_secret
        self.ssl_context = ssl_context
        self.offer_dict = offer_dict  # SDP offer passed directly from command message
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
        from aiortc import RTCConfiguration, RTCIceServer
        config = RTCConfiguration(iceServers=[
            RTCIceServer(urls=[
                "stun:stun.l.google.com:19302",
                "stun:stun1.l.google.com:19302",
                "stun:stun2.l.google.com:19302",
                "stun:stun.cloudflare.com:3478"
            ])
        ])
        pc = RTCPeerConnection(configuration=config)
        
        @pc.on("connectionstatechange")
        def on_connectionstatechange():
            try:
                import os, sys
                from datetime import datetime
                log_path = os.path.join(os.path.dirname(sys.executable), 'error.log')
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(f"[{datetime.now()}] WebRTC state: {pc.connectionState}, ice: {pc.iceConnectionState}\n")
            except: pass

        @pc.on("iceconnectionstatechange")
        def on_iceconnectionstatechange():
            try:
                import os, sys
                from datetime import datetime
                log_path = os.path.join(os.path.dirname(sys.executable), 'error.log')
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(f"[{datetime.now()}] WebRTC ICE state: {pc.iceConnectionState}\n")
            except: pass

        @pc.on("datachannel")
        def on_datachannel(channel):
            @channel.on("message")
            def on_message(message):
                try:
                    cmd = json.loads(message)
                    self._handle_input(cmd)
                except Exception:
                    pass

        # Use offer passed directly from command, or fall back to Firebase polling
        offer_dict = self.offer_dict
        if not offer_dict:
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
        sender = pc.addTrack(track)
        
        # Codec preferences: prefer H264 for iOS/Safari/Android, with VP8 fallback
        try:
            from aiortc.codecs import get_capabilities
            caps = get_capabilities('video')
            h264_codecs = [c for c in caps.codecs if 'H264' in c.mimeType]
            other_codecs = [c for c in caps.codecs if 'H264' not in c.mimeType]
            transceiver = next(
                (t for t in pc.getTransceivers() if t.sender == sender), None
            )
            if transceiver:
                transceiver.setCodecPreferences(h264_codecs + other_codecs)
        except Exception:
            pass  # fallback to default if H264 preference fails
        
        # Create answer and set local description
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        
        # Send answer via PATCH on pcs/{pc_id} (no db_secret needed for this path)
        answer_payload = json.dumps({
            "webrtc_answer": {
                "sdp": pc.localDescription.sdp,
                "type": pc.localDescription.type
            }
        }).encode('utf-8')
        answer_url = f"{self.central_url.rstrip('/')}/pcs/{self.pc_id}.json"
        if self.db_secret: answer_url += f"?auth={self.db_secret}"
        try:
            req = urllib.request.Request(
                answer_url, data=answer_payload, method="PATCH",
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=5, context=self.ssl_context) as _:
                pass
        except Exception as e:
            pass  # answer write failure - connection will still be attempted
        
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


def start_webrtc_session(pc_id, central_url, db_secret, ssl_context, offer_dict=None):
    if not WEBRTC_AVAILABLE:
        return
        
    def _run_loop():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            server = WebRTCServer(pc_id, central_url, db_secret, ssl_context, offer_dict=offer_dict)
            loop.run_until_complete(server.run())
            loop.close()
        except Exception as err:
            try:
                import os, sys
                from datetime import datetime
                log_path = os.path.join(os.path.dirname(sys.executable), 'error.log')
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(f"[{datetime.now()}] WebRTC error: {err}\n")
            except:
                pass
        
    t = threading.Thread(target=_run_loop, daemon=True)
    t.start()
