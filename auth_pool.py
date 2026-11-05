import os
import sys
import argparse
import logging

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("AuthPool")

from account_pool import AccountPool

def main():
    parser = argparse.ArgumentParser(description="Xác thực OAuth 2.0 cho các tài khoản trong Account Pool")
    parser.add_argument("--force", action="store_true", help="Xác thực lại toàn bộ, kể cả tài khoản đã có token")
    args = parser.parse_args()

    print("=" * 65)
    print("🔑 TRÌNH XÁC THỰC ACCOUNT POOL CHO BOT DOTA 2")
    print("=" * 65)

    pool = AccountPool()
    if not pool.accounts:
        print("❌ Không tìm thấy bất kỳ file client_secret*.json nào trong thư mục!")
        print("Vui lòng tải file OAuth 2.0 credentials từ Google Cloud Console về thư mục này.")
        return

    print(f"🔍 Tìm thấy {len(pool.accounts)} dự án Google Cloud.")

    for idx, acc in enumerate(pool.accounts, 1):
        print(f"\n--- [{idx}/{len(pool.accounts)}] Dự án: {acc.project_id} ---")
        print(f"File secret: {acc.client_secret_path}")
        print(f"File token : {acc.token_path}")

        if acc.is_authenticated() and not args.force:
            print("👉 Đã có file token. Đang kiểm tra kết nối...")
            acc.authenticate(interactive=False)
            if acc.service:
                print(f"✅ Dự án {acc.project_id} đã kết nối! Kênh: '{acc.channel_title}'")
            else:
                print(f"⚠️ Token của dự án {acc.project_id} không hợp lệ hoặc đã hết hạn.")
                choice = input("Bạn có muốn đăng nhập lại để làm mới token? (y/N): ").strip().lower()
                if choice == "y":
                    acc.authenticate(interactive=True)
        else:
            print(f"👉 Dự án {acc.project_id} chưa có token. Chuẩn bị mở trình duyệt đăng nhập...")
            input("Nhấn ENTER để mở trình duyệt đăng nhập Google... ")
            acc.authenticate(interactive=True)

    print("\n" + "=" * 65)
    print("🎉 HOÀN TẤT KIỂM TRA VÀ XÁC THỰC POOL TÀI KHOẢN!")
    pool.print_status()

if __name__ == "__main__":
    main()
