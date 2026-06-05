import urllib.request
import urllib.error
import ssl
import json
import sys
import socket

sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

ctx = ssl._create_unverified_context()
socket.setdefaulttimeout(8)

TESTS = [
    ("Firebase (버전확인용)",
     "https://atss-a1f9e-default-rtdb.firebaseio.com/update_info.json",
     "version"),

    ("GitHub Releases (exe 다운로드용)",
     "https://github.com/JunHyuk1203/autoshutdown/releases/download/v1.1.81/auto_shutdown.exe",
     "size"),

    ("jsDelivr CDN (구 방식 - 403 예상)",
     "https://cdn.jsdelivr.net/gh/JunHyuk1203/autoshutdown@main/dist/auto_shutdown.exe",
     "size"),

    ("raw.githubusercontent.com (구 방식 - 막힘 예상)",
     "https://raw.githubusercontent.com/JunHyuk1203/autoshutdown/main/version.json",
     "version"),

    ("GitHub.com 메인",
     "https://github.com",
     "html"),
]

print("=" * 55)
print("   AutoShutdown 네트워크 접속 진단 테스트")
print("=" * 55)

for name, url, check in TESTS:
    print(f"\n[{name}]")
    print(f"  URL: {url[:70]}{'...' if len(url)>70 else ''}")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ctx, timeout=8) as r:
            data = r.read(512)  # 처음 512바이트만 읽어서 연결 확인
            status = r.status
            content_len = r.headers.get('Content-Length', '?')

            if check == "version":
                try:
                    obj = json.loads(data)
                    print(f"  결과: OK ({status}) — 버전: {obj.get('version','?')}")
                except Exception:
                    print(f"  결과: OK ({status}) — {len(data)} bytes 수신")
            elif check == "size":
                print(f"  결과: OK ({status}) — Content-Length: {content_len} bytes")
            else:
                print(f"  결과: OK ({status})")

    except urllib.error.HTTPError as e:
        print(f"  결과: HTTP {e.code} {e.reason}  ← {'차단됨' if e.code == 403 else '오류'}")
    except urllib.error.URLError as e:
        reason = str(e.reason)
        if 'timed out' in reason.lower() or 'timeout' in reason.lower():
            print(f"  결과: TIMEOUT (방화벽 차단으로 응답 없음)")
        else:
            print(f"  결과: 연결 실패 — {reason}")
    except Exception as e:
        print(f"  결과: 오류 — {e}")

print("\n" + "=" * 55)
input("\n엔터를 누르면 창이 닫힙니다...")
