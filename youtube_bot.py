import os
import sys
import time
import re
import logging
from typing import Optional, Set, Dict
import requests
import pytchat

from opendota_client import OpenDotaClient
from account_pool import AccountPool

logger = logging.getLogger("YouTubeBot")

def extract_video_id(url_or_id: str) -> str:
    """Extract 11-character YouTube video ID from URL or bare ID."""
    clean = url_or_id.strip()
    match = re.search(r'(?:v=|\/live\/|\/embed\/|youtu\.be\/|\/v\/|^)([a-zA-Z0-9_-]{11})(?:[&?]|$)', clean)
    if match:
        return match.group(1)
    return clean

def resolve_channel_live_video(target_channel: str) -> Optional[str]:
    """
    Find active live video ID for a channel handle or URL without consuming API quota.
    Supports handles like '@DHDota2' or full URLs 'https://www.youtube.com/@DHDota2'.
    Ensures that the resolved video is genuinely LIVE and not an old recording or trailer.
    """
    target = target_channel.strip()
    if not target.startswith("http"):
        if not target.startswith("@"):
            target = "@" + target
        base_url = f"https://www.youtube.com/{target}"
    else:
        base_url = target.rstrip("/")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    session.cookies.set("SOCS", "CAESEwgDEgk0ODE3Nzk3MjQaAmVuIAEaBgiA_LyaBg", domain=".youtube.com")
    session.cookies.set("CONSENT", "PENDING+999", domain=".youtube.com")

    # 1. First attempt: check /live endpoint
    url_live = f"{base_url}/live"
    try:
        r = session.get(url_live, timeout=10, allow_redirects=True)
        html = r.text
        cand_id = None

        # Check if URL redirected directly to watch?v=XYZ
        m_url = re.search(r'[?&]v=([a-zA-Z0-9_-]{11})', r.url)
        if m_url:
            cand_id = m_url.group(1)

        # Check canonical link
        if not cand_id:
            m_canon = re.search(r'<link rel="canonical" href="https://www\.youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})">', html)
            if m_canon:
                cand_id = m_canon.group(1)

        # Check videoDetails in initial player response
        if not cand_id:
            m_details = re.search(r'"videoDetails"\s*:\s*\{"videoId"\s*:\s*"([a-zA-Z0-9_-]{11})"', html)
            if m_details:
                cand_id = m_details.group(1)

        # Verify candidate is ACTUALLY live
        if cand_id:
            is_live = (
                '"isLive":true' in html
                or '"isLiveNow":true' in html
                or '"isLiveContent":true' in html
                or 'THUMBNAIL_OVERLAY_BADGE_STYLE_LIVE' in html
                or 'liveStreamabilityRenderer' in html
            )
            if is_live:
                return cand_id
    except Exception as e:
        logger.warning(f"Không thể quét trực tiếp link '{url_live}': {e}")

    # 2. Second attempt: check /streams tab to find current live broadcast
    url_streams = f"{base_url}/streams"
    try:
        r_s = session.get(url_streams, timeout=10)
        html_s = r_s.text

        patterns = [
            r'badgeStyle":"THUMBNAIL_OVERLAY_BADGE_STYLE_LIVE","animationActivationTargetId":"([a-zA-Z0-9_-]{11})"',
            r'"animationActivationTargetId":"([a-zA-Z0-9_-]{11})"[^}]+?THUMBNAIL_OVERLAY_BADGE_STYLE_LIVE',
            r'/vi/([a-zA-Z0-9_-]{11})/[^"]*?\.jpg[^}]+?THUMBNAIL_OVERLAY_BADGE_STYLE_LIVE',
            r'([a-zA-Z0-9_-]{11})[^\n]+?THUMBNAIL_OVERLAY_BADGE_STYLE_LIVE',
            r'"videoId":"([a-zA-Z0-9_-]{11})"[^}]+?"style":"LIVE"',
            r'"videoId":"([a-zA-Z0-9_-]{11})"[^}]+?LIVE_NOW',
        ]
        for p in patterns:
            m = re.search(p, html_s)
            if m:
                return m.group(1)
    except Exception as e:
        logger.warning(f"Không thể quét tab streams '{url_streams}': {e}")

    return None

class YouTubeLiveChatBot:
    def __init__(
        self,
        dota_client: OpenDotaClient,
        account_pool: Optional[AccountPool] = None,
        target_channel: Optional[str] = None,
        video_id: Optional[str] = None,
        command_cooldown: float = 20.0,
        global_cooldown: float = 10.0,
        dedup_window: float = 180.0
    ):
        self.dota = dota_client
        self.account_pool = account_pool or AccountPool()
        self.target_channel = target_channel
        self.video_id = extract_video_id(video_id) if video_id else None
        self.command_cooldown = command_cooldown
        self.global_cooldown = global_cooldown
        # Trong bao lâu thì một câu trả lời giống hệt lần trước sẽ bị bỏ qua
        # (180s = 3 phút: đủ để chặn spam lặp lại, nhưng viewer mới vào sau
        # đó vẫn nhận được câu trả lời).
        self.dedup_window = dedup_window

        self.live_chat_id: Optional[str] = None
        self.current_video_id: Optional[str] = None

        # Cooldown trackers
        self.last_command_time = {}
        self.last_global_reply_time = 0.0
        # Chống trùng lặp: câu trả lời đã gửi gần nhất cho từng lệnh + thời điểm gửi
        self.last_reply = {}
        self.last_reply_time = {}

    def authenticate(self, interactive: bool = False):
        """Authenticate all accounts in the pool."""
        self.account_pool.authenticate_all(interactive=interactive)

    def resolve_video_id(self) -> Optional[str]:
        """Find the active video ID for target channel without using API quota."""
        if self.video_id:
            return self.video_id
        if self.target_channel:
            return resolve_channel_live_video(self.target_channel)
        return None

    def send_chat_message(self, text: str) -> bool:
        """Send a message to YouTube Live Chat using account pool rotation."""
        if not self.live_chat_id:
            logger.warning("Chưa có live_chat_id, không thể gửi tin nhắn.")
            return False

        success = self.account_pool.send_chat_message(self.live_chat_id, text)
        if success:
            self.last_global_reply_time = time.time()
        return success

    def handle_command(self, command: str, author_name: str) -> Optional[str]:
        """Process chat command and return response string if applicable."""
        cmd = command.strip().lower()
        now = time.time()

        # Gộp alias về lệnh chuẩn để cooldown + chống trùng lặp không bị
        # lách qua bằng cách gõ !homnay thay cho !today, !lenh thay cho !help, ...
        cmd_key = {
            "!homnay": "!today",
            "!lenh": "!help",
            "!bot": "!help",
            "!commands": "!help",
            "!chuoi": "!streak",
            "!5tran": "!recent",
            "!besthero": "!heroes",
        }.get(cmd, cmd)

        if now - self.last_global_reply_time < self.global_cooldown:
            return None

        if cmd_key in self.last_command_time:
            if now - self.last_command_time[cmd_key] < self.command_cooldown:
                logger.info(f"Lệnh '{cmd_key}' đang trong thời gian chờ (cooldown). Bỏ qua.")
                return None

        reply = None

        if cmd_key in ["!today"]:
            reply = self.dota.get_today_message()
        elif cmd_key in ["!rank"]:
            reply = self.dota.get_rank_message()
        elif cmd_key in ["!streak"]:
            reply = self.dota.get_streak_message()
        elif cmd_key in ["!recent"]:
            reply = self.dota.get_recent_message()
        elif cmd_key in ["!heroes"]:
            reply = self.dota.get_heroes_message()
        elif cmd_key in ["!mate"]:
            reply = self.dota.get_mate_message()
        elif cmd_key in ["!live"]:
            reply = self.dota.get_live_message()
        elif cmd_key in ["!help"]:
            reply = "📜 Lệnh có sẵn: !today, !rank, !streak, !recent, !heroes, !mate, !live."

        if reply:
            # Chống trùng lặp: nếu câu trả lời giống hệt lần đã gửi gần đây
            # (trong dedup_window) thì bỏ qua, tiết kiệm 20 quota units/tin.
            # Không cập nhật last_reply_time ở đây để cửa sổ 3 phút không bị
            # kéo dài vô hạn khi có người gõ lệnh liên tục.
            if (
                self.last_reply.get(cmd_key) == reply
                and now - self.last_reply_time.get(cmd_key, 0) < self.dedup_window
            ):
                logger.info(
                    f"Lệnh '{cmd_key}' trả về nội dung giống lần trước "
                    f"(trong {self.dedup_window:.0f}s), bỏ qua để tiết kiệm quota."
                )
                self.last_command_time[cmd_key] = now
                return None
            self.last_reply[cmd_key] = reply
            self.last_reply_time[cmd_key] = now
            self.last_command_time[cmd_key] = now
            return reply
        return None

    def start_polling(self):
        """
        Main loop using HYBRID + ACCOUNT POOL architecture:
        - Chat Reading: via `pytchat` (0 Quota cost, runs 24/7 forever!)
        - Chat Writing: via official YouTube API with Account Rotation & Failover
        """
        self.authenticate(interactive=False)

        ready = self.account_pool.get_ready_accounts()
        if not ready:
            logger.warning("⚠️ Không có tài khoản nào trong pool có Quota khả dụng hoặc chưa xác thực!")
            logger.info("Chạy 'python auth_pool.py' để xác thực các tài khoản mới nếu chưa tạo token.")

        logger.info(f"🚀 Bot Dota 2 đang ở chế độ HYBRID + XOAY ACCOUNT POOL cho kênh: {self.target_channel or 'kênh của bạn'}!")

        while True:
            try:
                vid = self.resolve_video_id()
                if not vid:
                    logger.info("Chưa tìm thấy buổi livestream đang phát. Đang đợi streamer bật live (kiểm tra lại sau 30s)...")
                    time.sleep(30)
                    continue

                self.current_video_id = vid
                logger.info(f"🎯 Đã phát hiện buổi stream: https://www.youtube.com/watch?v={vid} (ID: {vid})")

                # Lấy live_chat_id thông qua pool tài khoản (chỉ tốn 1 unit và được lưu cache)
                self.live_chat_id = self.account_pool.fetch_live_chat_id(vid)

                logger.info("📡 Đang kết nối lắng nghe chat qua pytchat (0 Quota API)...")
                try:
                    chat = pytchat.create(video_id=vid)
                except Exception as e:
                    logger.warning(f"Không thể kết nối pytchat tới video {vid}: {e}. Đợi 15s...")
                    time.sleep(15)
                    continue

                if not chat.is_alive():
                    logger.warning("Không thể mở luồng live chat qua pytchat. Thử lại sau 15s...")
                    time.sleep(15)
                    continue

                logger.info("🟢 ĐÃ KẾT NỐI LIVE CHAT THÀNH CÔNG! Bot đang lắng nghe mọi tin nhắn với 0 QUOTA.")

                # Lắng nghe tin nhắn
                while chat.is_alive():
                    try:
                        for c in chat.get().sync_items():
                            author_name = getattr(c.author, "name", "Viewer")
                            author_channel_id = getattr(c.author, "channelId", "")

                            # Bỏ qua tin nhắn từ bất kỳ tài khoản Bot nào trong pool
                            if author_channel_id and author_channel_id in self.account_pool.all_bot_channel_ids:
                                continue

                            msg_text = getattr(c, "message", "").strip()

                            if msg_text.startswith("!"):
                                logger.info(f"💬 Nhận lệnh từ [{author_name}]: {msg_text}")
                                reply = self.handle_command(msg_text, author_name)
                                if reply:
                                    self.send_chat_message(reply)
                    except Exception as e:
                        logger.warning(f"Lỗi đọc tin nhắn pytchat: {e}")

                    time.sleep(1.0)

                logger.warning("⚠️ Luồng livestream có thể đã kết thúc hoặc chuyển link mới. Đang quét lại sau 15s...")
                time.sleep(15)

            except KeyboardInterrupt:
                logger.info("Đã dừng bot theo yêu cầu người dùng.")
                break
            except Exception as e:
                logger.error(f"Lỗi không mong muốn trong vòng lặp bot: {e}")
                time.sleep(10)
