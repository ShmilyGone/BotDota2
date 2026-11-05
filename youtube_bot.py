import os
import sys
import time
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

class YouTubeLiveChatBot:
    def __init__(
        self,
        dota_client: OpenDotaClient,
        client_secrets_file: str = "client_secret.json",
        token_file: str = "token.json",
        video_id: Optional[str] = None,
        command_cooldown: float = 8.0,
        global_cooldown: float = 3.0
    ):
        self.dota = dota_client
        self.client_secrets_file = client_secrets_file
        self.token_file = token_file
        self.video_id = video_id
        self.command_cooldown = command_cooldown
        self.global_cooldown = global_cooldown
        
        self.youtube = None
        self.live_chat_id: Optional[str] = None
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
                logger.info("Mở trình duyệt để xác thực tài khoản Google...")
                flow = InstalledAppFlow.from_client_secrets_file(self.client_secrets_file, SCOPES)
                creds = flow.run_local_server(port=0)

            # Save credentials for next run
            with open(self.token_file, "w", encoding="utf-8") as token:
                token.write(creds.to_json())
            logger.info(f"Đã lưu thông tin xác thực vào '{self.token_file}'.")

        self.youtube = build("youtube", "v3", credentials=creds)

        # Get the authenticated user's channel ID to ignore own messages
        try:
            channels_resp = self.youtube.channels().list(part="id,snippet", mine=True).execute()
            if channels_resp.get("items"):
                my_channel = channels_resp["items"][0]
                self.bot_channel_id = my_channel["id"]
                title = my_channel.get("snippet", {}).get("title", "Unknown")
                logger.info(f"Đã xác thực thành công kênh Bot: {title} (ID: {self.bot_channel_id})")
        except Exception as e:
            logger.warning(f"Không thể lấy thông tin kênh bot: {e}")

    def resolve_live_chat_id(self) -> str:
        """Find the active liveChatId either from video_id or active broadcast."""
        if self.video_id:
            logger.info(f"Đang tìm live chat từ Video ID: {self.video_id}...")
            resp = self.youtube.videos().list(
                part="liveStreamingDetails,snippet",
                id=self.video_id
            ).execute()
            items = resp.get("items", [])
            if not items:
                raise ValueError(f"Không tìm thấy video với ID: {self.video_id}")
            
            streaming_details = items[0].get("liveStreamingDetails")
            if not streaming_details:
                raise ValueError(f"Video {self.video_id} không phải là một luồng phát trực tiếp (Live Stream).")
            
            chat_id = streaming_details.get("activeLiveChatId")
            if not chat_id:
                raise ValueError(f"Không tìm thấy live chat đang hoạt động trên video {self.video_id}. Hãy kiểm tra xem luồng live đã bật chat chưa.")
            
            title = items[0].get("snippet", {}).get("title", "")
            logger.info(f"Đã kết nối Live Chat cho luồng: '{title}' (Chat ID: {chat_id})")
            return chat_id

        # Auto-detect from mine=True liveBroadcasts
        logger.info("Đang tự động tìm luồng phát trực tiếp đang chạy trên kênh...")
        for status in ["active", "all", "upcoming"]:
            resp = self.youtube.liveBroadcasts().list(
                part="snippet,status",
                broadcastStatus=status,
                mine=True
            ).execute()
            for broadcast in resp.get("items", []):
                snippet = broadcast.get("snippet", {})
                chat_id = snippet.get("liveChatId")
                if chat_id:
                    title = snippet.get("title", "Live Stream")
                    logger.info(f"Đã tìm thấy buổi phát trực tiếp ({status}): '{title}' (Chat ID: {chat_id})")
                    return chat_id

        raise ValueError(
            "Không tìm thấy luồng phát trực tiếp đang hoạt động trên kênh của bạn.\n"
            "Gợi ý: Nếu đang dùng tài khoản bot riêng hoặc livestream chưa bắt đầu, "
            "hãy điền YOUTUBE_VIDEO_ID trong file .env hoặc tham số --video-id=<ID>!"
        )

    def send_chat_message(self, text: str):
        """Send a message to YouTube Live Chat, ensuring it doesn't exceed 200 characters."""
        if not self.live_chat_id:
            logger.warning("Chưa có live_chat_id, không thể gửi tin nhắn.")
            return

        # YouTube live chat max length is 200 chars
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

    def handle_command(self, command: str, author_name: str) -> Optional[str]:
        """Process chat command and return response string if applicable."""
        cmd = command.strip().lower()
        now = time.time()

        # Check global cooldown
        if now - self.last_global_reply_time < self.global_cooldown:
            return None

        # Check command specific cooldown
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
        elif cmd in ["!lastmatch", "!last"]:
            reply = self.dota.get_last_match_message()
        elif cmd in ["!dotabuff", "!profile", "!opendota"]:
            reply = self.dota.get_profile_message()
        elif cmd in ["!help", "!lenh", "!bot"]:
            reply = "📜 Lệnh có sẵn: !today (kết quả hôm nay), !rank (rank hiện tại), !mmr (thông tin MMR), !lastmatch (trận vừa xong), !profile (link Dotabuff)."

        if reply:
            self.last_command_time[cmd] = now
            return reply
        return None

    def start_polling(self):
        """Main loop: Poll live chat messages and dispatch commands."""
        if not self.youtube:
            self.authenticate()

        self.live_chat_id = self.resolve_live_chat_id()
        next_page_token = None
        is_first_poll = True

        logger.info("🚀 Bot Dota 2 đang hoạt động và lắng nghe live chat YouTube!")

        while True:
            try:
                params = {
                    "liveChatId": self.live_chat_id,
                    "part": "snippet,authorDetails"
                }
                if next_page_token:
                    params["pageToken"] = next_page_token

                resp = self.youtube.liveChatMessages().list(**params).execute()
                next_page_token = resp.get("nextPageToken")
                poll_interval = resp.get("pollingIntervalMillis", 4000) / 1000.0
                poll_interval = max(poll_interval, 3.0)  # Never poll faster than 3s to preserve quota

                items = resp.get("items", [])

                if is_first_poll:
                    # On first poll, record current messages as seen so we don't reply to past chat
                    for item in items:
                        self.seen_message_ids.add(item.get("id"))
                    is_first_poll = False
                    logger.info(f"Đã khởi tạo, bỏ qua {len(items)} tin nhắn cũ trong lịch sử.")
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

                # Prune seen message set if it grows too large
                if len(self.seen_message_ids) > 1000:
                    self.seen_message_ids = set(list(self.seen_message_ids)[-500:])

                time.sleep(poll_interval)

            except HttpError as e:
                logger.error(f"Lỗi YouTube API: {e}")
                time.sleep(10)
            except KeyboardInterrupt:
                logger.info("Đã dừng bot theo yêu cầu người dùng.")
                break
            except Exception as e:
                logger.error(f"Lỗi không mong muốn: {e}")
                time.sleep(5)
