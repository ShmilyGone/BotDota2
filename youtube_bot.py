import os
import sys
import time
import re
import urllib.request
import logging
from typing import Optional, Set
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from opendota_client import OpenDotaClient

# YouTube OAuth scopes
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

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
    Find active live video ID for a channel handle or URL.
    Supports handles like '@DHDota2' or full URLs 'https://www.youtube.com/@DHDota2'.
    """
    target = target_channel.strip()
    if not target.startswith("http"):
        if not target.startswith("@"):
            target = "@" + target
        url = f"https://www.youtube.com/{target}/live"
    else:
        url = target.rstrip("/")
        if not url.endswith("/live"):
            url += "/live"

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        resp = urllib.request.urlopen(req, timeout=10)
        html = resp.read().decode("utf-8", errors="ignore")

        # 1. Check canonical link
        canonical = re.findall(r'<link rel="canonical" href="https://www\.youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})">', html)
        if canonical:
            return canonical[0]

        # 2. Check videoId in initialData
        vids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
        if vids:
            return vids[0]
    except Exception as e:
        logger.warning(f"Không thể quét trực tiếp link '{url}': {e}")
    return None

class YouTubeLiveChatBot:
    def __init__(
        self,
        dota_client: OpenDotaClient,
        client_secrets_file: str = "client_secret.json",
        token_file: str = "token.json",
        target_channel: Optional[str] = None,
        video_id: Optional[str] = None,
        command_cooldown: float = 8.0,
        global_cooldown: float = 3.0
    ):
        self.dota = dota_client
        self.client_secrets_file = client_secrets_file
        self.token_file = token_file
        self.target_channel = target_channel
        self.video_id = extract_video_id(video_id) if video_id else None
        self.command_cooldown = command_cooldown
        self.global_cooldown = global_cooldown
        
        self.youtube = None
        self.live_chat_id: Optional[str] = None
        self.current_video_id: Optional[str] = None
        self.bot_channel_id: Optional[str] = None
        
        # Cooldown trackers
        self.last_command_time = {}
        self.last_global_reply_time = 0.0
        self.seen_message_ids: Set[str] = set()

    def authenticate(self):
        """Perform OAuth 2.0 authentication and build YouTube API client."""
        creds = None
        if os.path.exists(self.token_file):
            try:
                creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
            except Exception as e:
                logger.warning(f"Không thể đọc {self.token_file}: {e}. Sẽ xác thực lại.")
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Token đã hết hạn, đang làm mới (refresh token)...")
                creds.refresh(Request())
            else:
                if not os.path.exists(self.client_secrets_file):
                    raise FileNotFoundError(
                        f"Không tìm thấy file '{self.client_secrets_file}'.\n"
                        "Vui lòng tạo Google Cloud Console OAuth 2.0 Client Credentials "
                        "và tải về đặt tên là 'client_secret.json'."
                    )
                logger.info("Mở trình duyệt để xác thực tài khoản Google dùng làm bot...")
                flow = InstalledAppFlow.from_client_secrets_file(self.client_secrets_file, SCOPES)
                creds = flow.run_local_server(port=0)

            with open(self.token_file, "w", encoding="utf-8") as token:
                token.write(creds.to_json())
            logger.info(f"Đã lưu thông tin xác thực vào '{self.token_file}'.")

        self.youtube = build("youtube", "v3", credentials=creds)

        try:
            channels_resp = self.youtube.channels().list(part="id,snippet", mine=True).execute()
            if channels_resp.get("items"):
                my_channel = channels_resp["items"][0]
                self.bot_channel_id = my_channel["id"]
                title = my_channel.get("snippet", {}).get("title", "Unknown")
                logger.info(f"Đã xác thực thành công tài khoản Bot: '{title}' (Channel ID: {self.bot_channel_id})")
            else:
                logger.warning("Tài khoản Google này chưa tạo kênh YouTube! Hãy vào youtube.com bấm 'Tạo kênh' để có thể nhắn tin vào Live Chat.")
        except Exception as e:
            logger.warning(f"Không thể lấy thông tin kênh bot: {e}")

    def resolve_live_chat_id(self) -> Optional[str]:
        """Find active liveChatId. Returns None if streamer is currently offline."""
        target_vid = self.video_id

        # 1. If no explicit video_id, try discovering from target_channel
        if not target_vid and self.target_channel:
            target_vid = resolve_channel_live_video(self.target_channel)

        # 2. Check if discovered video is currently live with active chat
        if target_vid:
            try:
                resp = self.youtube.videos().list(
                    part="liveStreamingDetails,snippet",
                    id=target_vid
                ).execute()
                items = resp.get("items", [])
                if items:
                    streaming_details = items[0].get("liveStreamingDetails")
                    snippet = items[0].get("snippet", {})
                    live_broadcast_content = snippet.get("liveBroadcastContent", "none")
                    
                    if streaming_details and live_broadcast_content == "live":
                        chat_id = streaming_details.get("activeLiveChatId")
                        if chat_id:
                            title = snippet.get("title", "")
                            channel_title = snippet.get("channelTitle", "")
                            logger.info(f"✅ Đã kết nối Live Chat luồng của [{channel_title}]: '{title}' (Chat ID: {chat_id})")
                            self.current_video_id = target_vid
                            return chat_id
            except Exception as e:
                logger.warning(f"Lỗi kiểm tra video {target_vid}: {e}")

        # 3. Fallback: Check own broadcasts if streaming from bot's own account
        if not self.target_channel:
            try:
                resp = self.youtube.liveBroadcasts().list(
                    part="snippet,status",
                    broadcastType="all",
                    mine=True
                ).execute()
                for broadcast in resp.get("items", []):
                    snippet = broadcast.get("snippet", {})
                    chat_id = snippet.get("liveChatId")
                    if chat_id:
                        title = snippet.get("title", "Live Stream")
                        logger.info(f"Đã tìm thấy buổi phát trực tiếp: '{title}' (Chat ID: {chat_id})")
                        return chat_id
            except Exception:
                pass

        return None

    def send_chat_message(self, text: str):
        """Send a message to YouTube Live Chat, ensuring it doesn't exceed 200 characters."""
        if not self.live_chat_id:
            logger.warning("Chưa có live_chat_id, không thể gửi tin nhắn.")
            return

        if len(text) > 200:
            text = text[:197] + "..."

        try:
            self.youtube.liveChatMessages().insert(
                part="snippet",
                body={
                    "snippet": {
                        "liveChatId": self.live_chat_id,
                        "type": "textMessageEvent",
                        "textMessageDetails": {
                            "messageText": text
                        }
                    }
                }
            ).execute()
            self.last_global_reply_time = time.time()
            logger.info(f"🤖 Đã trả lời chat: {text}")
        except HttpError as e:
            logger.error(f"Lỗi khi gửi tin nhắn chat: {e}")
            if "liveChatEnded" in str(e):
                logger.warning("Buổi livestream đã kết thúc.")
                self.live_chat_id = None

    def handle_command(self, command: str, author_name: str) -> Optional[str]:
        """Process chat command and return response string if applicable."""
        cmd = command.strip().lower()
        now = time.time()

        if now - self.last_global_reply_time < self.global_cooldown:
            return None

        if cmd in self.last_command_time:
            if now - self.last_command_time[cmd] < self.command_cooldown:
                logger.info(f"Lệnh '{cmd}' đang trong thời gian chờ (cooldown). Bỏ qua.")
                return None

        reply = None

        if cmd in ["!today", "!homnay"]:
            reply = self.dota.get_today_message()
        elif cmd in ["!rank"]:
            reply = self.dota.get_rank_message()
        elif cmd in ["!mmr"]:
            reply = self.dota.get_mmr_message()
        elif cmd in ["!lastmatch", "!last", "!tran"]:
            reply = self.dota.get_last_match_message()
        elif cmd in ["!dotabuff", "!profile", "!opendota", "!player", "!players", "!thongtin"]:
            reply = self.dota.get_profile_message()
        elif cmd in ["!help", "!lenh", "!bot", "!commands"]:
            reply = "📜 Lệnh có sẵn: !today (kết quả ca stream hôm nay), !rank (rank hiện tại), !mmr (thông tin MMR), !lastmatch (trận vừa xong), !profile (link Dotabuff)."

        if reply:
            self.last_command_time[cmd] = now
            return reply
        return None

    def start_polling(self):
        """Main loop: Standby when offline, poll live chat when streamer goes live."""
        if not self.youtube:
            self.authenticate()

        next_page_token = None
        is_first_poll = True

        logger.info(f"🚀 Bot Dota 2 đang ở chế độ chờ sẵn cho kênh: {self.target_channel or 'kênh của bạn'}!")

        while True:
            try:
                # If not currently connected to an active chat, attempt to resolve
                if not self.live_chat_id:
                    self.live_chat_id = self.resolve_live_chat_id()
                    if not self.live_chat_id:
                        # Streamer is offline, wait 30s before checking again
                        time.sleep(30)
                        continue
                    else:
                        next_page_token = None
                        is_first_poll = True
                        logger.info("🟢 Luồng Live đã bắt đầu! Đang lắng nghe chat...")

                params = {
                    "liveChatId": self.live_chat_id,
                    "part": "snippet,authorDetails"
                }
                if next_page_token:
                    params["pageToken"] = next_page_token

                resp = self.youtube.liveChatMessages().list(**params).execute()
                next_page_token = resp.get("nextPageToken")
                poll_interval = resp.get("pollingIntervalMillis", 4000) / 1000.0
                poll_interval = max(poll_interval, 3.0)

                items = resp.get("items", [])

                if is_first_poll:
                    for item in items:
                        self.seen_message_ids.add(item.get("id"))
                    is_first_poll = False
                    logger.info(f"Đã kết nối, bỏ qua {len(items)} tin nhắn cũ trước khi bot vào.")
                else:
                    for item in items:
                        msg_id = item.get("id")
                        if msg_id in self.seen_message_ids:
                            continue
                        self.seen_message_ids.add(msg_id)

                        author_details = item.get("authorDetails", {})
                        author_channel_id = author_details.get("channelId")
                        author_name = author_details.get("displayName", "Viewer")

                        # Ignore messages from the bot itself
                        if self.bot_channel_id and author_channel_id == self.bot_channel_id:
                            continue

                        snippet = item.get("snippet", {})
                        msg_type = snippet.get("type")
                        
                        if msg_type == "textMessageEvent":
                            text_details = snippet.get("textMessageDetails", {})
                            msg_text = text_details.get("messageText", "").strip()

                            if msg_text.startswith("!"):
                                logger.info(f"💬 Nhận lệnh từ [{author_name}]: {msg_text}")
                                reply = self.handle_command(msg_text, author_name)
                                if reply:
                                    self.send_chat_message(reply)

                if len(self.seen_message_ids) > 1000:
                    self.seen_message_ids = set(list(self.seen_message_ids)[-500:])

                time.sleep(poll_interval)

            except HttpError as e:
                logger.error(f"Lỗi YouTube API: {e}")
                if "liveChatEnded" in str(e) or "liveChatNotFound" in str(e):
                    logger.warning("Luồng livestream đã kết thúc hoặc đóng chat. Bot chuyển về chế độ chờ luồng tiếp theo...")
                    self.live_chat_id = None
                    time.sleep(30)
                else:
                    time.sleep(10)
            except KeyboardInterrupt:
                logger.info("Đã dừng bot theo yêu cầu người dùng.")
                break
            except Exception as e:
                logger.error(f"Lỗi không mong muốn: {e}")
                time.sleep(5)
