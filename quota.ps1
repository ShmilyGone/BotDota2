$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
ssh vpsoracle "cd /home/ubuntu/BotDota2 && ./venv/bin/python check_quota.py"
