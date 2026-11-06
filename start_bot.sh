#!/usr/bin/env bash
# Khởi động BotDota2 trên Linux / Lubuntu
# Cách dùng:
#   ./start_bot.sh                 # chạy bot bình thường
#   ./start_bot.sh --test-dota     # test lệnh Dota 2 trên terminal, không cần YouTube
#   ./start_bot.sh --status        # kiểm tra trạng thái các tài khoản trong pool
#   ./start_bot.sh --auth-accounts # xác thực OAuth cho tài khoản mới
set -e
cd "$(dirname "$0")"

# 1. File cấu hình .env
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp ".env.example" ".env"
        echo "[!] Đã tạo file .env từ .env.example, hãy mở .env kiểm tra lại DOTA_ACCOUNT_ID, TARGET_CHANNEL..."
    else
        echo "[LỖI] Không tìm thấy .env và .env.example"
        exit 1
    fi
fi

# 2. File OAuth (không cần cho chế độ --test-dota)
NEED_AUTH=1
for arg in "$@"; do
    if [ "$arg" = "--test-dota" ]; then
        NEED_AUTH=0
    fi
done

if [ "$NEED_AUTH" = "1" ] && ! ls *client_secret*.json >/dev/null 2>&1; then
    echo
    echo "[LỖI] Chưa tìm thấy file 'client_secret*.json'!"
    echo "Tải file OAuth 2.0 Client Credentials từ Google Cloud Console,"
    echo "đổi tên thành 'client_secret.json' và đặt vào thư mục này."
    echo
    read -r -p "Bạn có muốn chạy thử nghiệm các lệnh Dota 2 trên Terminal trước không? (y/N): " choice
    if [ "$choice" = "y" ] || [ "$choice" = "Y" ]; then
        set -- --test-dota
        NEED_AUTH=0
    else
        exit 1
    fi
fi

# 3. Môi trường ảo Python (chỉ tạo + cài thư viện lần đầu)
if [ ! -x "venv/bin/python" ]; then
    echo "Đang tạo môi trường ảo venv (lần đầu, có thể mất 1-2 phút)..."
    python3 -m venv venv
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt
fi

# 4. Chạy bot
echo "Đang khởi động bot..."
exec ./venv/bin/python main.py "$@"
