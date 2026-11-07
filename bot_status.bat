@echo off
chcp 65001 >nul
ssh vpsoracle "sudo systemctl status dota2bot --no-pager"
