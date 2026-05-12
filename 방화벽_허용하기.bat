@echo off
chcp 65001 >nul
:: 관리자 권한 확인
net session >nul 2>&1
if %errorLevel% == 0 (
    echo 관리자 권한이 확인되었습니다. 방화벽 규칙을 추가합니다...
    netsh advfirewall firewall add rule name="스마트 전원 관리자 (웹 제어 TCP 5000)" dir=in action=allow protocol=TCP localport=5000
    netsh advfirewall firewall add rule name="스마트 전원 관리자 (P2P 통신 UDP 5555)" dir=in action=allow protocol=UDP localport=5555
    echo.
    echo 방화벽 설정이 성공적으로 완료되었습니다! 이제 다른 기기에서 접속이 가능합니다.
    echo 아무 키나 누르면 창이 닫힙니다.
    pause >nul
) else (
    echo [오류] 관리자 권한이 필요합니다.
    echo 창을 닫고, 이 파일(방화벽_허용하기.bat)을 우클릭한 후 "관리자 권한으로 실행"을 선택해주세요.
    pause
)
