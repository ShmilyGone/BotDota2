import os
import glob
import json
import logging
from typing import List, Optional, Set, Dict
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
logger = logging.getLogger("AccountPool")

class YouTubeAccount:
    def __init__(self, client_secret_path: str, token_path: str, project_id: str):
        self.client_secret_path = client_secret_path
        self.token_path = token_path
        self.project_id = project_id
        self.service = None
        self.channel_title = "Unknown"
        self.channel_id = None
        self.quota_exhausted = False

    def is_authenticated(self) -> bool:
        return os.path.exists(self.token_path)

    def authenticate(self, interactive: bool = False) -> bool:
        """Load credentials from token file or run OAuth flow if interactive."""
        creds = None
        if os.path.exists(self.token_path):
            try:
                creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            except Exception as e:
                logger.warning(f"Không thể đọc {self.token_path}: {e}")
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    logger.info(f"Token cho dự án {self.project_id} đã hết hạn, đang làm mới...")
                    creds.refresh(Request())
                except Exception as e:
                    logger.warning(f"Lỗi refresh token {self.project_id}: {e}")
                    creds = None

            if not creds:
                if not interactive:
                    logger.warning(f"Dự án {self.project_id} chưa có token. Cần chạy xác thực trước.")
                    return False
                logger.info(f"\n👉 Đang mở trình duyệt để xác thực cho Dự án: {self.project_id} ({self.client_secret_path})")
                flow = InstalledAppFlow.from_client_secrets_file(self.client_secret_path, SCOPES)
                creds = flow.run_local_server(port=0)

            # Save token
            with open(self.token_path, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
            logger.info(f"Đã lưu token vào '{self.token_path}'.")

        self.service = build("youtube", "v3", credentials=creds)

        # Retrieve channel info
        try:
            resp = self.service.channels().list(part="id,snippet", mine=True).execute()
            if resp.get("items"):
                item = resp["items"][0]
                self.channel_id = item.get("id")
                self.channel_title = item.get("snippet", {}).get("title", f"Account-{self.project_id}")
                logger.info(f"✅ Tài khoản [{self.channel_title}] (Dự án: {self.project_id}, Channel ID: {self.channel_id}) sẵn sàng!")
        except HttpError as e:
            if "quotaExceeded" in str(e):
                self.quota_exhausted = True
                logger.warning(f"⚠️ Dự án {self.project_id} đã chạm trần Quota hôm nay.")
            else:
                logger.warning(f"Lỗi lấy thông tin kênh cho dự án {self.project_id}: {e}")
        except Exception as e:
            logger.warning(f"Lỗi không xác định khi kết nối dự án {self.project_id}: {e}")

        return True


class AccountPool:
    def __init__(self, workspace_dir: str = "."):
        self.workspace_dir = workspace_dir
        self.accounts: List[YouTubeAccount] = []
        self.current_index = 0
        self.all_bot_channel_ids: Set[str] = set()
        self.chat_id_cache: Dict[str, str] = {}
        self.video_channel_map: Dict[str, str] = {}
        self.discover_accounts()

    def discover_accounts(self):
        """Find all unique client_secret files in the workspace directory."""
        self.accounts = []
        seen_projects = set()

        files = glob.glob(os.path.join(self.workspace_dir, "*client_secret*.json"))
        for f in sorted(files):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                cfg = data.get("installed") or data.get("web") or {}
                client_id = cfg.get("client_id", "")
                if not client_id:
                    continue
                project_id = client_id.split("-")[0]
                if project_id in seen_projects:
                    continue
                seen_projects.add(project_id)

                token_path = os.path.join(self.workspace_dir, f"token_{project_id}.json")
                if not os.path.exists(token_path) and os.path.exists("token.json"):
                    try:
                        with open("token.json", "r", encoding="utf-8") as tf:
                            tdata = json.load(tf)
                            if tdata.get("client_id", "").startswith(project_id):
                                token_path = "token.json"
                    except Exception:
                        pass

                account = YouTubeAccount(
                    client_secret_path=f,
                    token_path=token_path,
                    project_id=project_id
                )
                self.accounts.append(account)
            except Exception as e:
                logger.warning(f"Không thể đọc file {f}: {e}")

        logger.info(f"🔍 Đã tìm thấy {len(self.accounts)} dự án Google Cloud trong thư mục.")

    def authenticate_all(self, interactive: bool = False):
        """Authenticate all discovered accounts."""
        for acc in self.accounts:
            try:
                acc.authenticate(interactive=interactive)
                if acc.channel_id:
                    self.all_bot_channel_ids.add(acc.channel_id)
            except Exception as e:
                logger.error(f"Lỗi khi xác thực tài khoản {acc.project_id}: {e}")

    def get_ready_accounts(self) -> List[YouTubeAccount]:
        """Return list of accounts with active services and available quota."""
        return [acc for acc in self.accounts if acc.service and not acc.quota_exhausted]

    def fetch_live_chat_id(self, target_vid: str) -> Optional[str]:
        """
        Fetch activeLiveChatId for a video using any available account in the pool.
        Costs 1 quota unit and is cached for the stream.
        """
        if target_vid in self.chat_id_cache:
            return self.chat_id_cache[target_vid]

        for acc in self.accounts:
            if not acc.service or acc.quota_exhausted:
                continue
            try:
                resp = acc.service.videos().list(
                    part="liveStreamingDetails,snippet",
                    id=target_vid
                ).execute()
                items = resp.get("items", [])
                if items:
                    streaming_details = items[0].get("liveStreamingDetails")
                    snippet = items[0].get("snippet", {})
                    live_broadcast_content = snippet.get("liveBroadcastContent", "none")
                    channel_id = snippet.get("channelId")
                    if channel_id:
                        self.video_channel_map[target_vid] = channel_id

                    if streaming_details and live_broadcast_content == "live":
                        chat_id = streaming_details.get("activeLiveChatId")
                        if chat_id:
                            title = snippet.get("title", "")
                            channel_title = snippet.get("channelTitle", "")
                            logger.info(f"✅ [Dự án {acc.project_id}] Đã kết nối Live Chat [{channel_title}]: '{title}' (Chat ID: {chat_id})")
                            self.chat_id_cache[target_vid] = chat_id
                            return chat_id
            except HttpError as e:
                if "quotaExceeded" in str(e):
                    acc.quota_exhausted = True
                    logger.warning(f"⚠️ Dự án {acc.project_id} đã hết Quota khi lấy chat ID. Đang thử dự án khác...")
                else:
                    logger.warning(f"Lỗi lấy liveChatId qua dự án {acc.project_id}: {e}")
            except Exception as e:
                logger.warning(f"Lỗi không xác định qua dự án {acc.project_id}: {e}")

        logger.error("❌ Không thể lấy liveChatId từ bất kỳ dự án nào trong pool (có thể tất cả đã hết quota hoặc video không phát trực tiếp)!")
        return None

    def send_chat_message(self, live_chat_id: str, text: str) -> bool:
        """
        Send message using Account Rotation (Round-Robin) and Automatic Failover:
        Tries current account, on quotaExceeded marks it and rotates to the next available account.
        """
        if len(text) > 200:
            text = text[:197] + "..."

        ready = self.get_ready_accounts()
        if not ready:
            logger.error("❌ Toàn bộ các tài khoản trong pool đã hết Quota hôm nay!")
            return False

        # Attempt to send with available accounts
        for _ in range(len(self.accounts)):
            acc = self.accounts[self.current_index % len(self.accounts)]
            self.current_index = (self.current_index + 1) % len(self.accounts)

            if not acc.service or acc.quota_exhausted:
                continue

            try:
                acc.service.liveChatMessages().insert(
                    part="snippet",
                    body={
                        "snippet": {
                            "liveChatId": live_chat_id,
                            "type": "textMessageEvent",
                            "textMessageDetails": {
                                "messageText": text
                            }
                        }
                    }
                ).execute()
                logger.info(f"🤖 [{acc.channel_title} | Dự án {acc.project_id}] Đã trả lời: {text}")
                return True
            except HttpError as e:
                if "quotaExceeded" in str(e):
                    acc.quota_exhausted = True
                    logger.warning(f"⚠️ Dự án {acc.project_id} đã hết Quota hôm nay! Đang tự động chuyển sang dự án tiếp theo trong pool...")
                elif "liveChatEnded" in str(e):
                    logger.warning("Buổi livestream đã kết thúc.")
                    return False
                else:
                    logger.error(f"Lỗi khi gửi tin nhắn qua dự án {acc.project_id}: {e}")

        logger.error("❌ Không thể gửi tin nhắn qua bất kỳ tài khoản nào trong pool.")
        return False

    def print_status(self):
        """Display current pool status."""
        print("=" * 65)
        print("📊 DANH SÁCH TÀI KHOẢN TRONG ACCOUNT POOL:")
        for idx, acc in enumerate(self.accounts, 1):
            status = "Sẵn sàng ✅"
            if not acc.is_authenticated():
                status = "Chưa xác thực (cần tạo token) ⚠️"
            elif acc.quota_exhausted:
                status = "Hết Quota hôm nay (chờ reset) ⏳"
            print(f"  {idx}. Dự án: {acc.project_id}")
            print(f"     - Kênh: {acc.channel_title} (ID: {acc.channel_id})")
            print(f"     - Secret: {os.path.basename(acc.client_secret_path)}")
            print(f"     - Token: {os.path.basename(acc.token_path)}")
            print(f"     - Trạng thái: {status}")
        print("=" * 65)
