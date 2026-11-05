@echo off
chcp 65001 >nul
title YouTube Live Chat Bot - Dota 2
cd /d "%~dp0"

echo ======================================================
echo    KHỞI ĐỘNG DOTA 2 YOUTUBE LIVE CHAT BOT
echo ======================================================

if not exist "client_secret.json" (
    echo.
    echo [LỖI] Chưa tìm thấy file 'client_secret.json'!
    echo Vui lòng tải file OAuth 2.0 Client Credentials từ Google Cloud Console,
    echo đổi tên thành 'client_secret.json' và đặt vào thư mục này.
    echo.
    echo Bạn có muốn chạy thử nghiệm các lệnh Dota 2 trên Terminal trước không? (Y/N)
    set /p choice="Lựa chọn của bạn: "
    if /i "%choice%"=="Y" (
        .\venv\Scripts\python main.py --test-dota
    )
    pause
    exit /b
)

echo Đang khởi động bot...
.\venv\Scripts\python main.py

pause
