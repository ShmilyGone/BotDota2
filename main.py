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
    print("  !yesterday - Kết quả thi đấu phiên stream hôm trước")
    print("  !last      - Thông số chi tiết trận vừa đánh xong (KDA, PMP, Avg MMR, đồ)")
    print("  !rank      - Rank hiện tại (kèm % thế giới)")
    print("  !streak    - Chuỗi thắng/thua hiện tại")
    print("  !recent    - Kết quả 10 trận gần nhất")
    print("  !hero [tên]- Tướng hay đánh 25/100 trận (W-L) & Trending Meta (vd: !hero storm, !hero)")
    print("  !dh        - Thông tin tiểu sử streamer DH (458 / Thocac)")
    print("  !pro [tên] - Pro player gặp hôm nay / đối đầu pro player cụ thể (vd: !pro 23savage)")
    print("  !mate      - Hay duo với ai trong 100 trận gần nhất")
    print("  !live      - Trận đang diễn ra của streamer")
    print("  !career    - Tổng quan toàn bộ sự nghiệp Dota 2")
    print("  !funfact   - Góc vui: APM, số lần ping map, Thánh kiếm, gà bị giết")
    print("  !connapse  - Funfact tình đồng chí khi duo cùng connapse")
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
            elif cmd_name in ["!yesterday", "!homqua", "!prev"]:
                print(dota_client.get_yesterday_message())
            elif cmd_name in ["!last", "!chitiet", "!pmp", "!match"]:
                print(dota_client.get_last_message())
            elif cmd_name in ["!rank"]:
                print(dota_client.get_rank_message())
            elif cmd_name in ["!streak", "!chuoi", "!recent", "!5tran", "!mate", "!covy", "!vy", "!hanvy", "!leminhhanvy"]:
                print(f"⚠️ Lệnh '{cmd_name}' đang tạm thời bị khóa.")
            elif cmd_name in ["!connapse", "!collapse"]:
                print(dota_client.get_connapse_message())
            elif cmd_name in ["!duo", "!hopvia", "!synergy"]:
                print(dota_client.get_duo_message())
            elif cmd_name in ["!dh", "!458", "!thocac"]:
                print(dota_client.get_dh_message())
            elif cmd_name in ["!hero", "!heroes", "!meta", "!trending", "!besthero"]:
                print(dota_client.get_hero_message(arg))
            elif cmd_name in ["!pro", "!pros"]:
                if arg:
                    print(dota_client.get_pro_message(arg))
                else:
                    print(dota_client.get_today_pros_message())
            elif cmd_name in ["!live"]:
                print(dota_client.get_live_message())
            elif cmd_name in ["!career", "!totals"]:
                print(dota_client.get_career_message())
            elif cmd_name in ["!funfact", "!ditat"]:
                print(dota_client.get_funfact_message())
            elif cmd_name in ["!quota"]:
                from account_pool import AccountPool
                p = AccountPool()
                print(p.get_quota_chat_message())
            elif cmd_name in ["!help", "!lenh"]:
                print("📜 Lệnh: !today, !last, !rank, !hero, !dh, !live, !pro, !career, !funfact. ⏱️ Chờ 10s giữa các lệnh, 1p nếu lặp lại. Chưa kịp rep hãy gõ lại nhé! Gõ !quota để kiểm tra quota của BOT.")
            else:
                print(f"❓ Không nhận diện được lệnh '{cmd}'. Thử: !today, !rank, !career, !funfact, !connapse")
        except (KeyboardInterrupt, EOFError):
            print("\nĐã thoát chế độ test.")
            break

def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="YouTube Live Chat Bot cho Dota 2 Streamer")
    parser.add_argument("--test-dota", action="store_true", help="Chạy chế độ test lệnh Dota 2 trên Terminal (không cần YouTube)")
    parser.add_argument("--status", action="store_true", help="Kiểm tra trạng thái các tài khoản trong Account Pool")
    parser.add_argument("--quota", action="store_true", help="Hiển thị bảng ước lượng Quota YouTube API của các bot")
    parser.add_argument("--auth-accounts", action="store_true", help="Xác thực OAuth 2.0 cho các tài khoản mới trong Account Pool")
    parser.add_argument("--account-id", type=str, default=os.getenv("DOTA_ACCOUNT_ID", "196931374"), help="Dota 2 Steam Account ID (mặc định: 196931374)")
    parser.add_argument("--channel", type=str, default=os.getenv("TARGET_CHANNEL", "@DHDota2"), help="Kênh livestream mục tiêu (vd: @DHDota2 hoặc link kênh)")
    parser.add_argument("--video-id", type=str, default=os.getenv("YOUTUBE_VIDEO_ID", None), help="ID của video livestream YouTube (vd: IuM8Nhptdy4)")
    parser.add_argument("--cooldown", type=float, default=float(os.getenv("COMMAND_COOLDOWN", "20.0")), help="Thời gian hồi mỗi lệnh (giây)")
    parser.add_argument("--global-cooldown", type=float, default=float(os.getenv("GLOBAL_COOLDOWN", "10.0")), help="Thời gian hồi chung giữa mọi tin trả lời (giây)")
    parser.add_argument("--dedup-window", type=float, default=float(os.getenv("DEDUP_WINDOW_SECONDS", "60.0")), help="Trong bao nhiêu giây thì câu trả lời giống hệt lần trước sẽ bị bỏ qua (giây)")
    parser.add_argument("--queue-mode", type=str, default=os.getenv("COMMAND_QUEUE_MODE", "auto"), choices=["auto", "fixed", "off"], help="Chế độ hàng đợi lệnh (auto, fixed, off)")
    parser.add_argument("--queue-max", type=int, default=int(os.getenv("QUEUE_MAX_SIZE", "5")), help="Số lượng lệnh tối đa trong hàng đợi")
    parser.add_argument("--queue-delay-normal", type=float, default=float(os.getenv("QUEUE_DELAY_NORMAL", "10.0")), help="Giãn cách bình thường khi quota nhiều (giây)")
    parser.add_argument("--queue-delay-medium", type=float, default=float(os.getenv("QUEUE_DELAY_MEDIUM", "15.0")), help="Giãn cách khi quota trung bình (giây)")
    parser.add_argument("--queue-delay-low", type=float, default=float(os.getenv("QUEUE_DELAY_LOW", "25.0")), help="Giãn cách khi quota gần cạn (giây)")
    parser.add_argument("--queue-ttl", type=float, default=float(os.getenv("QUEUE_TTL_SECONDS", "90.0")), help="Thời gian tối đa lệnh được phép chờ trong hàng đợi (giây)")
    
    args = parser.parse_args()

    pool = AccountPool()

    if args.status:
        pool.authenticate_all(interactive=False)
        pool.print_status()
        return

    if args.quota:
        pool.authenticate_all(interactive=False)
        pool.print_quota_table()
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
        dedup_window=args.dedup_window,
        queue_mode=args.queue_mode,
        queue_max_size=args.queue_max,
        queue_delay_normal=args.queue_delay_normal,
        queue_delay_medium=args.queue_delay_medium,
        queue_delay_low=args.queue_delay_low,
        queue_ttl=args.queue_ttl
    )

    bot.start_polling()

if __name__ == "__main__":
    main()
