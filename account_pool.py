import os
import glob
import json
import logging
import re
import shutil
import subprocess
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Set, Dict, Any
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
logger = logging.getLogger("AccountPool")

class QuotaTracker:
    """
    Theo dõi và ước tính số lượng tin nhắn và quota tiêu tốn theo chu kỳ ngày của Google YouTube API.
    Google reset quota vào lúc 00:00 Pacific Time (15:00 GMT+7, tương đương 08:00 UTC).
    """
    def __init__(self, filepath: str = "quota_tracker.json"):
        self.filepath = filepath

    @staticmethod
    def get_cycle_key() -> str:
        """Lấy chu kỳ ngày hiện tại theo giờ Pacific (UTC-8)."""
        now_utc = datetime.now(timezone.utc)
        pt_date = (now_utc - timedelta(hours=8)).strftime("%Y-%m-%d")
        return pt_date

    def load_data(self) -> Dict[str, Any]:
        cycle = self.get_cycle_key()
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("cycle") == cycle:
                        return data
            except Exception:
                pass
        return {"cycle": cycle, "counts": {}}

    def save_data(self, data: Dict[str, Any]):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Không thể lưu {self.filepath}: {e}")

    def record_send(self, project_id: str):
        data = self.load_data()
        counts = data.setdefault("counts", {})
        counts[project_id] = counts.get(project_id, 0) + 1
        self.save_data(data)

    def get_counts(self) -> Dict[str, int]:
        data = self.load_data()
        counts = data.get("counts", {})
        # Tự động đồng bộ từ systemd journalctl nếu đang chạy trên VPS Linux
        journal_counts = self.sync_from_journal()
        changed = False
        for pid, cnt in journal_counts.items():
            if cnt > counts.get(pid, 0):
                counts[pid] = cnt
                changed = True
        if changed:
            data["counts"] = counts
            self.save_data(data)
        return counts

    def sync_from_journal(self) -> Dict[str, int]:
        """Đọc số tin nhắn từ journalctl kể từ đầu chu kỳ Quota (08:00 UTC) nếu khả dụng."""
        if shutil.which("journalctl") is None:
            return {}
        try:
            now_utc = datetime.now(timezone.utc)
            if now_utc.hour >= 8:
                start_dt = now_utc.replace(hour=8, minute=0, second=0, microsecond=0)
            else:
                yesterday = now_utc - timedelta(days=1)
                start_dt = yesterday.replace(hour=8, minute=0, second=0, microsecond=0)
            since_str = start_dt.strftime("%Y-%m-%d %H:%M:%S UTC")

            cmd = ["journalctl", "-u", "dota2bot", "--since", since_str, "--no-pager"]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            if proc.returncode != 0:
                return {}

            counts: Dict[str, int] = {}
            for line in proc.stdout.splitlines():
                if "Đã trả lời:" in line and "Dự án " in line:
                    m = re.search(r"Dự án\s+(\d+)", line)
                    if m:
                        pid = m.group(1)
                        counts[pid] = counts.get(pid, 0) + 1
            return counts
        except Exception:
            return {}

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
        self.quota_tracker = QuotaTracker(filepath=os.path.join(self.workspace_dir, "quota_tracker.json"))
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
                self.quota_tracker.record_send(acc.project_id)
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

    def get_quota_summary(self) -> Dict[str, Any]:
        """Tính toán thống kê quota chi tiết cho từng tài khoản và toàn pool."""
        counts = self.quota_tracker.get_counts()
        rows = []
        tot_msgs = 0
        tot_units = 0

        for acc in self.accounts:
            msgs = counts.get(acc.project_id, 0)
            units = msgs * 50
            pct = min(100.0, (units / 10000.0) * 100.0)
            status = "Hết Quota ⏳" if (acc.quota_exhausted or units >= 10000) else "Sẵn sàng ✅"
            rows.append({
                "project_id": acc.project_id,
                "title": acc.channel_title if acc.channel_title != "Unknown" else f"Dự án {acc.project_id}",
                "channel_id": acc.channel_id,
                "messages": msgs,
                "units_used": units,
                "percent": pct,
                "status": status
            })
            tot_msgs += msgs
            tot_units += units

        num_acc = max(1, len(self.accounts))
        tot_limit = num_acc * 10000
        tot_max_msgs = num_acc * 200  # 10000 / 50 = 200 msgs/account
        tot_pct = min(100.0, (tot_units / tot_limit) * 100.0)
        rem_msgs = max(0, tot_max_msgs - tot_msgs)

        return {
            "cycle": self.quota_tracker.get_cycle_key(),
            "accounts": rows,
            "total_messages": tot_msgs,
            "total_max_messages": tot_max_msgs,
            "total_units": tot_units,
            "total_limit": tot_limit,
            "total_percent": tot_pct,
            "total_remaining_messages": rem_msgs
        }

    def print_quota_table(self):
        """In bảng ước lượng Quota YouTube API đẹp mắt trên Terminal."""
        summary = self.get_quota_summary()
        cycle = summary["cycle"]
        print("=" * 86)
        print(f"📊 BẢNG ƯỚC LƯỢNG QUOTA YOUTUBE DATA API (Chu kỳ: {cycle}):")
        print("   (Mỗi tin nhắn gửi đi tốn 50 units. Quota reset hàng ngày lúc 15:00 GMT+7)")
        print("-" * 86)
        print(f"| {'STT':<3} | {'Tài khoản Bot':<14} | {'Dự án Google Cloud':<20} | {'Tin đã gửi':<10} | {'Quota đã dùng':<16} | {'Trạng thái':<10} |")
        print("-" * 86)
        for idx, row in enumerate(summary["accounts"], 1):
            stt = str(idx)
            title = row["title"][:14]
            pid = row["project_id"][:20]
            msgs = f"{row['messages']} tin"
            quota_str = f"{row['units_used']:,}/10,000 ({row['percent']:.1f}%)"
            status = row["status"]
            print(f"| {stt:<3} | {title:<14} | {pid:<20} | {msgs:<10} | {quota_str:<16} | {status:<10} |")
        print("-" * 86)
        tot_m = summary["total_messages"]
        tot_max = summary["total_max_messages"]
        tot_u = summary["total_units"]
        tot_lim = summary["total_limit"]
        tot_p = summary["total_percent"]
        rem = summary["total_remaining_messages"]
        print(f"| Tổng: {tot_m}/{tot_max} tin (~{tot_u:,}/{tot_lim:,} units - {tot_p:.1f}%) | Còn lại: ~{rem} tin nhắn |")
        print("=" * 86)

    def get_quota_chat_message(self) -> str:
        """Tạo thông điệp báo cáo quota ngắn gọn (<= 195 ký tự) cho YouTube Live Chat."""
        summary = self.get_quota_summary()
        acc_parts = []
        for a in summary["accounts"]:
            acc_parts.append(f"{a['title']}: {a['messages']} tin")
        acc_str = ", ".join(acc_parts)
        tot = summary["total_messages"]
        tot_max = summary["total_max_messages"]
        rem = summary["total_remaining_messages"]
        pct = summary["total_percent"]
        msg = f"📊 Quota hôm nay: {acc_str} | Tổng: {tot}/{tot_max} tin ({pct:.1f}%), còn ~{rem} tin nữa!"
        if len(msg) > 195:
            msg = f"📊 Quota hôm nay: Đã gửi {tot}/{tot_max} tin ({pct:.1f}%), còn lại ~{rem} tin nhắn!"
        return msg
