@echo off
chcp 65001 > nul
echo ==================================================
echo [AutoShutdown] 버전 배포 및 자동 업로드 시작
echo ==================================================
python github_deploy.py
pause
