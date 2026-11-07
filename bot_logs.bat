@echo off
chcp 65001 >nul
ssh vpsoracle "sudo journalctl -u dota2bot -n 30 --no-pager"
