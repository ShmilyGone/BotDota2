import os
import sys
import argparse
import logging
from dotenv import load_dotenv

# Ensure UTF-8 output in Windows terminal
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

from opendota_client import OpenDotaClient
from youtube_bot import YouTubeLiveChatBot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("Main")

def run_terminal_test(dota_client: OpenDotaClient):
    """Interactive mode to test Dota 2 commands directly in terminal without YouTube."""
    print("=" * 60)
    print("🎮 CHẾ ĐỘ TEST LỆNH DOTA 2 TRÊN TERMINAL")
    print(f"Player ID: {dota_client.account_id}")
    print("Gõ một lệnh bất kỳ để thử nghiệm (hoặc 'exit' để thoát):")
    print("  !today     - Kết quả thi đấu hôm nay")
    print("  !rank      - Rank hiện tại")
    print("  !mmr       - Thông tin MMR / Bảng xếp hạng")
    print("  !lastmatch - Chi tiết trận đấu vừa xong")
    print("  !profile   - Link Dotabuff / OpenDota")
    print("  !help      - Trợ giúp")
    print("=" * 60)

    while True:
        try:
            cmd = input("\nNhập lệnh (vd: !today) > ").strip()
            if not cmd:
                continue
            if cmd.lower() in ["exit", "quit", "q"]:
                print("Tạm biệt!")
                break
            
            cmd_lower = cmd.lower()
            if cmd_lower in ["!today", "!homnay"]:
                print(dota_client.get_today_message())
            elif cmd_lower in ["!rank"]:
                print(dota_client.get_rank_message())
            elif cmd_lower in ["!mmr"]:
                print(dota_client.get_mmr_message())
            elif cmd_lower in ["!lastmatch", "!last"]:
                print(dota_client.get_last_match_message())
            elif cmd_lower in ["!dotabuff", "!profile", "!opendota"]:
                print(dota_client.get_profile_message())
            elif cmd_lower in ["!help", "!lenh"]:
                print("📜 Lệnh có sẵn: !today, !rank, !mmr, !lastmatch, !profile")
            else:
                print(f"❓ Không nhận diện được lệnh '{cmd}'. Thử: !today, !rank, !mmr")
        except (KeyboardInterrupt, EOFError):
            print("\nĐã thoát chế độ test.")
            break

def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="YouTube Live Chat Bot cho Dota 2 Streamer")
    parser.add_argument("--test-dota", action="store_true", help="Chạy chế độ test lệnh Dota 2 trên Terminal (không cần YouTube)")
    parser.add_argument("--account-id", type=str, default=os.getenv("DOTA_ACCOUNT_ID", "196931374"), help="Dota 2 Steam Account ID (mặc định: 196931374)")
    parser.add_argument("--channel", type=str, default=os.getenv("TARGET_CHANNEL", "@DHDota2"), help="Kênh livestream mục tiêu (vd: @DHDota2 hoặc link kênh)")
    parser.add_argument("--video-id", type=str, default=os.getenv("YOUTUBE_VIDEO_ID", None), help="ID của video livestream YouTube (vd: IuM8Nhptdy4)")
    parser.add_argument("--manual-mmr", type=str, default=os.getenv("MANUAL_MMR", None), help="MMR thực tế của streamer nếu muốn hiển thị cụ thể (vd: 10500)")
    parser.add_argument("--cooldown", type=float, default=float(os.getenv("COMMAND_COOLDOWN", "8.0")), help="Thời gian hồi lệnh (giây)")
    
    args = parser.parse_args()

    api_key = os.getenv("OPENDOTA_API_KEY")
    tz_offset = int(os.getenv("TIMEZONE_OFFSET", "7"))

    dota_client = OpenDotaClient(
        account_id=args.account_id,
        api_key=api_key,
        tz_offset_hours=tz_offset,
        manual_mmr=args.manual_mmr
    )

    if args.test_dota:
        run_terminal_test(dota_client)
        return

    # Check for credentials before running YouTube bot
    client_secret_file = os.getenv("CLIENT_SECRET_FILE", "client_secret.json")
    if not os.path.exists(client_secret_file):
        logger.error("=" * 65)
        logger.error(f"❌ KHÔNG TÌM THẤY FILE: '{client_secret_file}'")
        logger.error("Để bot có thể đọc và gửi tin nhắn lên YouTube Live Chat, bạn cần:")
        logger.error("1. Vào Google Cloud Console: https://console.cloud.google.com/")
        logger.error("2. Bật 'YouTube Data API v3'.")
        logger.error("3. Tạo OAuth 2.0 Client ID (chọn Application type: Desktop App).")
        logger.error("4. Tải file credentials về, đổi tên thành 'client_secret.json' và đặt vào thư mục này.")
        logger.error("")
        logger.error("💡 Bạn có thể thử nghiệm các lệnh Dota 2 ngay bây giờ bằng lệnh:")
        logger.error("   python main.py --test-dota")
        logger.error("=" * 65)
        sys.exit(1)

    bot = YouTubeLiveChatBot(
        dota_client=dota_client,
        client_secrets_file=client_secret_file,
        target_channel=args.channel,
        video_id=args.video_id,
        command_cooldown=args.cooldown
    )

    bot.start_polling()

if __name__ == "__main__":
    main()
