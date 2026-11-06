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
from account_pool import AccountPool
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
    print("  !today     - Kết quả thi đấu hôm nay (ca stream)")
    print("  !rank      - Rank hiện tại (kèm % thế giới)")
    print("  !streak    - Chuỗi thắng/thua hiện tại")
    print("  !recent    - Kết quả 10 trận gần nhất")
    print("  !heroes    - Tướng tủ trong 100 trận gần nhất")
    print("  !mate      - Hay duo với ai trong 100 trận gần nhất")
    print("  !live      - Trận đang diễn ra của streamer")
    print("  !pro <tên> - Thống kê đối đầu với pro player (vd: !pro 23savage, !pro skem)")
    print("  !career    - Tổng quan toàn bộ sự nghiệp Dota 2")
    print("  !funfact   - Góc vui: APM, số lần ping map, Thánh kiếm, gà bị giết")
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
            
            parts = cmd.split(maxsplit=1)
            cmd_name = parts[0].lower()
            arg = parts[1].strip() if len(parts) > 1 else ""

            if cmd_name in ["!today", "!homnay"]:
                print(dota_client.get_today_message())
            elif cmd_name in ["!rank"]:
                print(dota_client.get_rank_message())
            elif cmd_name in ["!streak", "!chuoi"]:
                print(dota_client.get_streak_message())
            elif cmd_name in ["!recent", "!5tran"]:
                print(dota_client.get_recent_message())
            elif cmd_name in ["!heroes", "!besthero"]:
                print(dota_client.get_heroes_message())
            elif cmd_name in ["!mate"]:
                print(dota_client.get_mate_message())
            elif cmd_name in ["!live"]:
                print(dota_client.get_live_message())
            elif cmd_name in ["!pro", "!pros"]:
                print(dota_client.get_pro_message(arg))
            elif cmd_name in ["!career", "!totals"]:
                print(dota_client.get_career_message())
            elif cmd_name in ["!funfact", "!ditat"]:
                print(dota_client.get_funfact_message())
            elif cmd_name in ["!help", "!lenh"]:
                print("📜 Lệnh có sẵn: !today, !rank, !streak, !recent, !heroes, !mate, !live, !pro <tên>, !career, !funfact")
            else:
                print(f"❓ Không nhận diện được lệnh '{cmd}'. Thử: !today, !rank, !pro 23savage, !career, !funfact")
        except (KeyboardInterrupt, EOFError):
            print("\nĐã thoát chế độ test.")
            break

def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="YouTube Live Chat Bot cho Dota 2 Streamer")
    parser.add_argument("--test-dota", action="store_true", help="Chạy chế độ test lệnh Dota 2 trên Terminal (không cần YouTube)")
    parser.add_argument("--status", action="store_true", help="Kiểm tra trạng thái các tài khoản trong Account Pool")
    parser.add_argument("--auth-accounts", action="store_true", help="Xác thực OAuth 2.0 cho các tài khoản mới trong Account Pool")
    parser.add_argument("--account-id", type=str, default=os.getenv("DOTA_ACCOUNT_ID", "196931374"), help="Dota 2 Steam Account ID (mặc định: 196931374)")
    parser.add_argument("--channel", type=str, default=os.getenv("TARGET_CHANNEL", "@DHDota2"), help="Kênh livestream mục tiêu (vd: @DHDota2 hoặc link kênh)")
    parser.add_argument("--video-id", type=str, default=os.getenv("YOUTUBE_VIDEO_ID", None), help="ID của video livestream YouTube (vd: IuM8Nhptdy4)")
    parser.add_argument("--cooldown", type=float, default=float(os.getenv("COMMAND_COOLDOWN", "20.0")), help="Thời gian hồi mỗi lệnh (giây)")
    parser.add_argument("--global-cooldown", type=float, default=float(os.getenv("GLOBAL_COOLDOWN", "10.0")), help="Thời gian hồi chung giữa mọi tin trả lời (giây)")
    parser.add_argument("--dedup-window", type=float, default=float(os.getenv("DEDUP_WINDOW_SECONDS", "180.0")), help="Trong bao nhiêu giây thì câu trả lời giống hệt lần trước sẽ bị bỏ qua (giây)")
    
    args = parser.parse_args()

    pool = AccountPool()

    if args.status:
        pool.authenticate_all(interactive=False)
        pool.print_status()
        return

    if args.auth_accounts:
        import auth_pool
        auth_pool.main()
        return

    api_key = os.getenv("OPENDOTA_API_KEY")
    steam_api_key = os.getenv("STEAM_API_KEY")
    stratz_api_token = os.getenv("STRATZ_API_TOKEN")
    tz_offset = int(os.getenv("TIMEZONE_OFFSET", "7"))
    session_gap = float(os.getenv("SESSION_GAP_HOURS", "5.0"))

    dota_client = OpenDotaClient(
        account_id=args.account_id,
        api_key=api_key,
        steam_api_key=steam_api_key,
        stratz_api_token=stratz_api_token,
        tz_offset_hours=tz_offset,
        session_gap_hours=session_gap
    )

    if args.test_dota:
        run_terminal_test(dota_client)
        return

    if not pool.accounts:
        logger.error("=" * 65)
        logger.error("❌ KHÔNG TÌM THẤY BẤT KỲ FILE CLIENT_SECRET NÀO!")
        logger.error("Vui lòng tải file OAuth 2.0 Credentials từ Google Cloud Console về thư mục này.")
        logger.error("=" * 65)
        sys.exit(1)

    # Check unauthenticated accounts
    unauth = [a for a in pool.accounts if not a.is_authenticated()]
    if unauth:
        logger.info(f"💡 Phát hiện {len(unauth)} tài khoản chưa tạo token: {[a.project_id for a in unauth]}")
        logger.info("Bạn có thể chạy lệnh sau bất kỳ lúc nào để đăng nhập bổ sung:")
        logger.info("   python auth_pool.py")

    bot = YouTubeLiveChatBot(
        dota_client=dota_client,
        account_pool=pool,
        target_channel=args.channel,
        video_id=args.video_id,
        command_cooldown=args.cooldown,
        global_cooldown=args.global_cooldown,
        dedup_window=args.dedup_window
    )

    bot.start_polling()

if __name__ == "__main__":
    main()
