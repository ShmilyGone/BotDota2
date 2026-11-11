import os
import sys
import time
import re
import logging
import threading
from typing import Optional, Set, Dict, List, Any, Tuple
import requests
import pytchat
from pytchat import util as pytchat_util, config as pytchat_config

# Configure pytchat with modern user-agent and Google consent cookies to avoid consent blocks on VPS IPs
pytchat_config.headers.update({
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "cookie": "SOCS=CAESEwgDEgk0ODE3Nzk3MjQaAmVuIAEaBgiA_LyaBg; CONSENT=PENDING+999"
})
pytchat_config.m_headers.update({
    "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "cookie": "SOCS=CAESEwgDEgk0ODE3Nzk3MjQaAmVuIAEaBgiA_LyaBg; CONSENT=PENDING+999"
})

# Global map of video_id -> channel_id
KNOWN_VIDEO_CHANNEL_IDS: Dict[str, str] = {
    "8d1kyZkhryA": "UCP1MRNDMG9t9vJPaVpiCh4w"
}
DEFAULT_TARGET_CHANNEL_ID = "UCP1MRNDMG9t9vJPaVpiCh4w"

_orig_pytchat_get_channelid = pytchat_util.get_channelid

def _patched_get_channelid(client, video_id):
    if video_id in KNOWN_VIDEO_CHANNEL_IDS:
        return KNOWN_VIDEO_CHANNEL_IDS[video_id]
    if DEFAULT_TARGET_CHANNEL_ID:
        return DEFAULT_TARGET_CHANNEL_ID
    return _orig_pytchat_get_channelid(client, video_id)

pytchat_util.get_channelid = _patched_get_channelid

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

        badge_pos = html_s.find("THUMBNAIL_OVERLAY_BADGE_STYLE_LIVE")
        if badge_pos != -1:
            chunk = html_s[max(0, badge_pos - 1500):min(len(html_s), badge_pos + 1500)]
            # Match animationActivationTargetId
            m = re.search(r'"animationActivationTargetId":"([a-zA-Z0-9_-]{11})"', chunk)
            if m:
                return m.group(1)
            # Match thumbnail URL /vi/ID/
            m = re.search(r'/vi/([a-zA-Z0-9_-]{11})/', chunk)
            if m:
                return m.group(1)
            # Match addedVideoId or videoId
            m = re.search(r'"(?:addedVideoId|videoId)":"([a-zA-Z0-9_-]{11})"', chunk)
            if m:
                return m.group(1)

        # Fallback: check any occurrences of LIVE style
        if "LIVE" in html_s:
            for m in re.finditer(r'"videoId":"([a-zA-Z0-9_-]{11})"', html_s):
                vid_cand = m.group(1)
                start = max(0, m.start() - 300)
                end = min(len(html_s), m.end() + 300)
                window = html_s[start:end]
                if '"style":"LIVE"' in window or "LIVE_NOW" in window:
                    return vid_cand
    except Exception as e:
        logger.warning(f"Không thể quét tab streams '{url_streams}': {e}")

    return None

class YouTubeLiveChatBot:
    COMMAND_ALIASES = {
        "!homnay": "!today",
        "!homqua": "!yesterday",
        "!prev": "!yesterday",
        "!lenh": "!help",
        "!bot": "!help",
        "!commands": "!help",
        "!chuoi": "!streak",
        "!5tran": "!recent",
        "!10tran": "!recent",
        "!besthero": "!hero",
        "!heroes": "!hero",
        "!meta": "!hero",
        "!trending": "!hero",
        "!458": "!dh",
        "!thocac": "!dh",
        "!rampages": "!rampage",
        "!5kill": "!rampage",
        "!pentakill": "!rampage",
        "!totals": "!career",
        "!sunghiep": "!career",
        "!su-nghiep": "!career",
        "!ditat": "!funfact",
        "!fact": "!funfact",
        "!collapse": "!connapse",
        "!hopvia": "!duo",
        "!synergy": "!duo",
        "!dongdoi": "!mate",
        "!ban": "!mate",
        "!dangdanh": "!live",
        "!chitiet": "!last",
        "!match": "!last",
        "!pmp": "!last",
        "!vy": "!covy",
        "!hanvy": "!covy",
        "!leminhhanvy": "!covy",
    }

    LOCKED_COMMANDS = {"!streak", "!recent", "!mate", "!covy"}

    SUPPORTED_COMMANDS = {
        "!today", "!yesterday", "!homqua", "!rank", "!pro", "!pros", "!hero", "!heroes", "!meta", "!trending",
        "!dh", "!458", "!thocac",
        "!live", "!career", "!funfact", "!quota", "!2rax", "!tnc", "!2raxtnc",
        "!dieback", "!rampage", "!last", "!help", "!connapse", "!duo"
    }

    def __init__(
        self,
        dota_client: OpenDotaClient,
        account_pool: Optional[AccountPool] = None,
        target_channel: Optional[str] = None,
        video_id: Optional[str] = None,
        command_cooldown: float = 20.0,
        global_cooldown: float = 10.0,
        dedup_window: float = 60.0,
        queue_mode: str = "auto",
        queue_max_size: int = 5,
        queue_delay_normal: float = 10.0,
        queue_delay_medium: float = 15.0,
        queue_delay_low: float = 25.0,
        queue_ttl: float = 90.0,
    ):
        self.dota = dota_client
        self.account_pool = account_pool or AccountPool()
        self.target_channel = target_channel
        self.video_id = extract_video_id(video_id) if video_id else None
        self.command_cooldown = command_cooldown
        self.global_cooldown = global_cooldown
        # Trong bao lâu thì một câu trả lời giống hệt lần trước sẽ bị bỏ qua
        # (60s = 1 phút: đủ để chặn spam lặp lại liên tục nhưng không bỏ qua người xem mới).
        self.dedup_window = dedup_window

        # Cấu hình Command Queue & Điều tiết giãn cách
        self.queue_mode = (queue_mode or "auto").strip().lower()
        self.queue_max_size = queue_max_size
        self.queue_delay_normal = queue_delay_normal
        self.queue_delay_medium = queue_delay_medium
        self.queue_delay_low = queue_delay_low
        self.queue_ttl = queue_ttl

        self.live_chat_id: Optional[str] = None
        self.current_video_id: Optional[str] = None

        # Cooldown trackers
        self.last_command_time = {}
        self.last_global_reply_time = 0.0
        # Chống trùng lặp: câu trả lời đã gửi gần nhất cho từng lệnh + thời điểm gửi
        self.last_reply = {}
        self.last_reply_time = {}

        # Trạng thái hàng đợi & luồng worker ngầm
        self.command_queue: List[Dict[str, Any]] = []
        self.queue_lock = threading.Lock()
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def get_effective_cooldown(self) -> float:
        """
        Tính toán khoảng cách gửi tin (giây) dựa trên chế độ cấu hình và Quota khả dụng.
        - Chế độ 'off': dùng global_cooldown
        - Chế độ 'fixed': dùng queue_delay_normal
        - Chế độ 'auto': tự động thích ứng theo số tin còn lại của toàn bộ Account Pool
        """
        if self.queue_mode == "off":
            return self.global_cooldown

        if self.queue_mode == "fixed":
            return self.queue_delay_normal

        # Auto mode:
        try:
            summary = self.account_pool.get_quota_summary()
            rem = summary.get("total_remaining_messages", 0)
            if rem > 150:
                return self.queue_delay_normal    # 10s (mặc định dồi dào)
            elif rem >= 50:
                return self.queue_delay_medium    # 15s (trung bình)
            else:
                return self.queue_delay_low       # 25s (gần cạn)
        except Exception as e:
            logger.warning(f"Không thể đọc quota summary cho cooldown: {e}")
            return self.queue_delay_normal

    def get_effective_max_queue_size(self) -> int:
        """
        Xác định sức chứa tối đa của hàng đợi lệnh.
        Ở chế độ auto, hàng đợi sẽ tự động thu hẹp khi quota gần cạn để bảo vệ pool.
        """
        if self.queue_mode == "off":
            return 0

        if self.queue_mode == "fixed":
            return self.queue_max_size

        # Auto mode:
        try:
            summary = self.account_pool.get_quota_summary()
            rem = summary.get("total_remaining_messages", 0)
            if rem > 150:
                return self.queue_max_size
            elif rem >= 50:
                return max(2, self.queue_max_size - 2)
            else:
                return 2
        except Exception:
            return self.queue_max_size

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

    def execute_command(self, cmd_key: str, arg: str = "") -> Optional[str]:
        """Tạo nội dung câu trả lời cho lệnh Dota 2 tương ứng."""
        try:
            if cmd_key in ["!today"]:
                return self.dota.get_today_message()
            elif cmd_key in ["!yesterday", "!homqua", "!prev"]:
                return self.dota.get_yesterday_message()
            elif cmd_key in ["!rank"]:
                return self.dota.get_rank_message()
            elif cmd_key in ["!dh", "!458", "!thocac"]:
                return self.dota.get_dh_message()
            elif cmd_key in ["!hero", "!heroes", "!meta", "!trending", "!besthero"]:
                return self.dota.get_hero_message(arg)
            elif cmd_key in ["!pro", "!pros"]:
                if arg:
                    return self.dota.get_pro_message(arg)
                return self.dota.get_today_pros_message()
            elif cmd_key in ["!live"]:
                return self.dota.get_live_message()
            elif cmd_key in ["!career"]:
                return self.dota.get_career_message()
            elif cmd_key in ["!funfact"]:
                return self.dota.get_funfact_message()
            elif cmd_key in ["!quota"]:
                return self.account_pool.get_quota_chat_message()
            elif cmd_key in ["!2rax", "!tnc", "!2raxtnc"]:
                return self.dota.get_tworax_message()
            elif cmd_key in ["!dieback"]:
                return self.dota.get_dieback_message(arg)
            elif cmd_key in ["!rampage", "!rampages", "!5kill", "!pentakill"]:
                return self.dota.get_rampage_message(arg)
            elif cmd_key in ["!last"]:
                return self.dota.get_last_message()
            elif cmd_key in ["!connapse", "!collapse"]:
                return self.dota.get_connapse_message()
            elif cmd_key in ["!duo", "!hopvia", "!synergy"]:
                return self.dota.get_duo_message()
            elif cmd_key in ["!help"]:
                return (
                    "📜 Lệnh: !today, !yesterday, !last, !rank, !hero, !dh, !rampage, !live, !pro, !career, !funfact. "
                    "⏱️ Chờ 10s giữa các lệnh, 1p nếu lặp lại. "
                    "Chưa kịp rep hãy gõ lại nhé! Gõ !quota kiểm tra quota BOT."
                )
        except Exception as e:
            logger.error(f"Lỗi khi thực thi lệnh '{cmd_key}': {e}", exc_info=True)
            return None
        return None

    def enqueue_command(self, command: str, author_name: str) -> bool:
        """
        Phân tích và đưa lệnh vào hàng đợi (Command Queue).
        Tự động chống spam, loại bỏ lệnh trùng lặp và kiểm tra quota khả dụng.
        """
        parts = command.strip().split(maxsplit=1)
        if not parts:
            return False

        cmd_raw = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""
        cmd_key = self.COMMAND_ALIASES.get(cmd_raw, cmd_raw)

        if cmd_key in self.LOCKED_COMMANDS:
            logger.info(f"Lệnh '{cmd_key}' đang tạm thời bị khóa. Bỏ qua.")
            return False

        if cmd_key not in self.SUPPORTED_COMMANDS:
            logger.info(f"Lệnh không hỗ trợ: '{cmd_raw}'. Bỏ qua.")
            return False

        now = time.time()

        # Kiểm tra dedup: Nếu lệnh vừa được gửi trong dedup_window, bỏ qua để tránh spam trùng lặp
        dedup_key = f"{cmd_key}:{arg.lower()}" if arg else cmd_key
        if (now - self.last_reply_time.get(dedup_key, 0) < self.dedup_window):
            wait_left = self.dedup_window - (now - self.last_reply_time[dedup_key])
            logger.info(
                f"Lệnh '{dedup_key}' vừa được trả lời cách đây {(now - self.last_reply_time[dedup_key]):.1f}s "
                f"(còn {wait_left:.1f}s dedup cooldown). Bỏ qua trùng lặp."
            )
            return False

        # Kiểm tra quota còn lại
        try:
            summary = self.account_pool.get_quota_summary()
            if summary.get("total_remaining_messages", 0) <= 0:
                logger.warning("Toàn bộ tài khoản đã hết quota, không nhận lệnh vào hàng đợi.")
                return False
        except Exception:
            pass

        with self.queue_lock:
            # Kiểm tra xem lệnh này đã có sẵn trong hàng đợi chưa
            for item in self.command_queue:
                if item["cmd_key"] == cmd_key and item["arg"] == arg:
                    logger.info(f"Lệnh '{cmd_key}' đã có sẵn trong hàng đợi (đang chờ tới lượt). Bỏ qua trùng lặp.")
                    return False

            # Kiểm tra độ dài hàng đợi
            max_size = self.get_effective_max_queue_size()
            if len(self.command_queue) >= max_size:
                logger.info(f"Hàng đợi lệnh đã đầy ({len(self.command_queue)}/{max_size}). Bỏ qua lệnh '{cmd_key}' từ [{author_name}].")
                return False

            self.command_queue.append({
                "raw_cmd": command,
                "cmd_key": cmd_key,
                "arg": arg,
                "author_name": author_name,
                "enqueued_at": now
            })
            pos = len(self.command_queue)
            delay = self.get_effective_cooldown()
            logger.info(f"📥 Đã thêm lệnh '{cmd_key}' từ [{author_name}] vào hàng đợi (Vị trí #{pos}, giãn cách: {delay:.0f}s).")
            return True

    def _process_queue_tick(self):
        """Xử lý 1 nhịp của hàng đợi lệnh."""
        now = time.time()
        effective_cooldown = self.get_effective_cooldown()

        # Kiểm tra khoảng cách tối thiểu giữa 2 tin nhắn gửi ra chat
        if now - self.last_global_reply_time < effective_cooldown:
            return

        item = None
        with self.queue_lock:
            # Hủy các lệnh quá hạn trong queue (TTL)
            while self.command_queue and (now - self.command_queue[0]["enqueued_at"] > self.queue_ttl):
                expired = self.command_queue.pop(0)
                logger.info(f"⏳ Lệnh '{expired['cmd_key']}' từ [{expired['author_name']}] đã chờ quá {self.queue_ttl:.0f}s trong queue. Bỏ qua.")

            if not self.command_queue:
                return

            item = self.command_queue.pop(0)

        if not item:
            return

        cmd_key = item["cmd_key"]
        arg = item["arg"]
        author_name = item["author_name"]

        reply = self.execute_command(cmd_key, arg)
        if not reply:
            return

        dedup_key = f"{cmd_key}:{arg.lower()}" if arg else cmd_key
        # Kiểm tra dedup lần cuối trước khi gửi (trường hợp cùng nội dung)
        if (
            self.last_reply.get(dedup_key) == reply
            and now - self.last_reply_time.get(dedup_key, 0) < self.dedup_window
        ):
            logger.info(f"Lệnh '{dedup_key}' trả về nội dung giống lần trước (trong {self.dedup_window:.0f}s), bỏ qua để tiết kiệm quota.")
            self.last_command_time[cmd_key] = now
            return

        success = self.send_chat_message(reply)
        if success:
            self.last_reply[dedup_key] = reply
            self.last_reply_time[dedup_key] = now
            self.last_command_time[cmd_key] = now
            with self.queue_lock:
                q_left = len(self.command_queue)
            logger.info(f"🚀 [QUEUE] Đã trả lời lệnh '{dedup_key}' cho [{author_name}] thành công! (Còn lại trong queue: {q_left} lệnh).")

    def _start_queue_worker(self):
        """Khởi chạy worker thread xử lý hàng đợi lệnh ngầm."""
        if self._worker_thread and self._worker_thread.is_alive():
            return
        self._stop_event.clear()
        self._worker_thread = threading.Thread(
            target=self._queue_worker_loop,
            daemon=True,
            name="CommandQueueWorker"
        )
        self._worker_thread.start()
        logger.info("🧵 Đã khởi động luồng CommandQueueWorker chạy ngầm.")

    def _queue_worker_loop(self):
        """Vòng lặp ngầm liên tục kiểm tra và gửi các lệnh trong hàng đợi."""
        while not self._stop_event.is_set():
            try:
                self._process_queue_tick()
            except Exception as e:
                logger.error(f"Lỗi trong _queue_worker_loop: {e}", exc_info=True)
            time.sleep(0.5)

    def handle_command(self, command: str, author_name: str) -> Optional[str]:
        """Xử lý lệnh trực tiếp không qua hàng đợi (dùng khi queue_mode == 'off')."""
        parts = command.strip().split(maxsplit=1)
        if not parts:
            return None

        cmd_raw = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""
        cmd_key = self.COMMAND_ALIASES.get(cmd_raw, cmd_raw)

        if cmd_key in self.LOCKED_COMMANDS:
            logger.info(f"Lệnh '{cmd_key}' đang tạm thời bị khóa. Bỏ qua.")
            return None

        if cmd_key not in self.SUPPORTED_COMMANDS:
            logger.info(f"Lệnh không hỗ trợ: '{cmd_raw}'. Bỏ qua.")
            return None

        now = time.time()
        effective_cooldown = self.get_effective_cooldown()

        if now - self.last_global_reply_time < effective_cooldown:
            wait_left = effective_cooldown - (now - self.last_global_reply_time)
            logger.info(
                f"Bot vừa gửi tin nhắn khác cách đây {(now - self.last_global_reply_time):.1f}s "
                f"(cooldown {effective_cooldown:.0f}s, còn {wait_left:.1f}s). Bỏ qua để tránh spam."
            )
            return None

        if cmd_key in self.last_command_time:
            if now - self.last_command_time[cmd_key] < self.command_cooldown:
                wait_left = self.command_cooldown - (now - self.last_command_time[cmd_key])
                logger.info(f"Lệnh '{cmd_key}' đang trong thời gian chờ (còn {wait_left:.1f}s cooldown). Bỏ qua.")
                return None

        reply = self.execute_command(cmd_key, arg)
        if reply:
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
        eff_cd = self.get_effective_cooldown()
        eff_q = self.get_effective_max_queue_size()
        logger.info(f"🚦 [COMMAND QUEUE] Chế độ: {self.queue_mode.upper()} | Giãn cách hiện tại: {eff_cd:.0f}s | Hàng đợi tối đa: {eff_q} lệnh | TTL: {self.queue_ttl:.0f}s")

        if self.queue_mode != "off":
            self._start_queue_worker()

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
                ch_id = self.account_pool.video_channel_map.get(vid)
                if ch_id:
                    KNOWN_VIDEO_CHANNEL_IDS[vid] = ch_id

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
                                if self.queue_mode != "off":
                                    self.enqueue_command(msg_text, author_name)
                                else:
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
                self._stop_event.set()
                break
            except Exception as e:
                logger.error(f"Lỗi không mong muốn trong vòng lặp bot: {e}")
                time.sleep(10)
