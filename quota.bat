@echo off
chcp 65001 >nul
ssh vpsoracle "cd /home/ubuntu/BotDota2 && ./venv/bin/python check_quota.py"
