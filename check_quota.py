#!/usr/bin/env python3
"""
Tiện ích kiểm tra và ước lượng Quota YouTube Data API v3 của các tài khoản bot.
Sử dụng:
    python check_quota.py
"""
import sys
import os

# Đảm bảo import được các module trong cùng thư mục
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from account_pool import AccountPool

def main():
    pool = AccountPool()
    pool.authenticate_all(interactive=False)
    pool.print_quota_table()

if __name__ == "__main__":
    main()
