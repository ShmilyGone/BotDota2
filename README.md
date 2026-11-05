# 🤖 YouTube Live Chat Bot cho Dota 2 Streamer

Bot tự động lắng nghe live chat trên YouTube và phản hồi thông tin Dota 2 của streamer thông qua **OpenDota API** (dành cho người chơi [Dotabuff 196931374](https://www.dotabuff.com/players/196931374)).

---

## 📌 Các câu lệnh hỗ trợ trong Chat

| Lệnh | Mô tả | Ví dụ kết quả phản hồi |
| :--- | :--- | :--- |
| `!today` hoặc `!homnay` | Thống kê kết quả thi đấu trong ngày hôm nay (Thắng/Thua, Winrate, Tướng chơi, Trận vừa kết thúc) | `🔥 Hôm nay (05/11): 4W - 2L (66.7%) \| Trận vừa xong: Outworld Devourer (16/2/10) Thắng ✅ \| Tướng: Outworld Devourer (1W-0L), Ember Spirit (1W-0L)...` |
| `!rank` | Xem medal/rank hiện tại của streamer | `🏅 Rank hiện tại của To the Moon and not back: Immortal (Top #215)` |
| `!mmr` | Thông tin MMR hoặc thứ hạng Leaderboard | `📊 To the Moon and not back \| Rank: Immortal (Top #215) \| Bảng xếp hạng: Top #215` |
| `!lastmatch` hoặc `!last` | Chi tiết trận đấu vừa kết thúc gần nhất (Tướng, KDA, Thời lượng, link Dotabuff) | `⚔️ Trận gần nhất: Outworld Devourer \| Kết quả: Chiến Thắng 🏆 \| KDA: 16/2/10 \| Thời lượng: 28p \| Dotabuff: https://www.dotabuff.com/matches/...` |
| `!profile` hoặc `!dotabuff` | Link trang cá nhân Dotabuff & OpenDota | `🌐 Dotabuff: https://www.dotabuff.com/players/196931374 \| OpenDota: https://www.opendota.com/players/196931374` |
| `!help` hoặc `!lenh` | Hiển thị danh sách các lệnh có sẵn | `📜 Lệnh có sẵn: !today, !rank, !mmr, !lastmatch, !profile` |

---

## 📁 Cấu trúc thư mục

```
BotDota2/
├── .env                  # File cấu hình (ID người chơi, múi giờ, video ID...)
├── .env.example          # File mẫu cấu hình
├── requirements.txt      # Danh sách thư viện Python cần thiết
├── opendota_client.py    # Xử lý kết nối OpenDota API, tính toán rank, thống kê hôm nay
├── youtube_bot.py        # Xử lý kết nối YouTube Data API v3, đọc chat và gửi tin nhắn
├── main.py               # Điểm bắt đầu (hỗ trợ cả chạy bot live và test terminal)
└── client_secret.json    # File OAuth 2.0 Client ID tải từ Google Cloud Console
```

---

## 🚀 Hướng dẫn cài đặt & Chạy

### Bước 1: Kích hoạt môi trường Python (Venv)

Môi trường ảo đã được chuẩn bị sẵn trong thư mục `venv/`. Bạn có thể kích hoạt bằng lệnh:

**Trên PowerShell (Windows):**
```powershell
.\venv\Scripts\Activate.ps1
```
*(Nếu gặp lỗi script policy trên Windows, chạy: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

Hoặc chạy trực tiếp với Python của venv:
```powershell
.\venv\Scripts\python main.py --test-dota
```

---

### Bước 2: Test ngay các lệnh Dota 2 (Không cần kết nối YouTube)

Bạn có thể kiểm tra dữ liệu OpenDota và kết quả các câu lệnh trực tiếp trên Terminal:

```powershell
.\venv\Scripts\python main.py --test-dota
```
Gõ các lệnh `!today`, `!rank`, `!mmr`, `!lastmatch` để xem phản hồi tức thì.

---

### Bước 3: Thiết lập kết nối YouTube Live Chat

Để bot có thể đọc và nhắn tin tự động trong luồng live stream của bạn, bạn cần cấp quyền qua Google Cloud Console:

1. **Tạo Project trên Google Cloud Console:**
   - Truy cập: [https://console.cloud.google.com/](https://console.cloud.google.com/)
   - Đăng nhập và tạo một Project mới (ví dụ đặt tên: `Dota2StreamBot`).

2. **Bật YouTube Data API v3:**
   - Trong thanh tìm kiếm, gõ **YouTube Data API v3** và bấm **Enable** (Bật).

3. **Cấu hình OAuth Consent Screen:**
   - Vào mục **APIs & Services** > **OAuth consent screen**.
   - Chọn loại User Type là **External** rồi bấm **Create**.
   - Điền tên App (ví dụ: `Dota 2 Bot`) và email liên hệ.
   - Ở mục **Test users**, hãy thêm email của tài khoản Google/YouTube bạn sẽ dùng để phát trực tiếp hoặc dùng làm bot chat.

4. **Tạo OAuth Client ID:**
   - Vào mục **APIs & Services** > **Credentials** > Bấm **+ CREATE CREDENTIALS** > Chọn **OAuth client ID**.
   - **Application type**: Chọn **Desktop app**.
   - Bấm **Create**.
   - Bấm **Download JSON** (Tải file JSON về máy).
   - Đổi tên file đã tải về thành `client_secret.json` và copy vào thư mục `BotDota2`.

---

### Bước 4: Chạy Bot trên Livestream YouTube

1. Mở file `.env` và kiểm tra cấu hình:
   ```env
   DOTA_ACCOUNT_ID=196931374
   TIMEZONE_OFFSET=7
   # (Tùy chọn) Điền video ID buổi live nếu muốn chỉ định cụ thể:
   # YOUTUBE_VIDEO_ID=abc123xyz
   ```

2. Khởi chạy bot:
   ```powershell
   .\venv\Scripts\python main.py
   ```

3. **Lần đầu chạy:** Trình duyệt sẽ tự động bật lên yêu cầu bạn đăng nhập tài khoản Google và cho phép quyền quản lý chat YouTube. Sau khi đồng ý, bot sẽ lưu lại `token.json` và bạn sẽ không cần phải đăng nhập lại ở các lần sau.

4. Bot sẽ tự động quét buổi livestream đang diễn ra trên kênh của bạn, kết nối vào khung chat và bắt đầu lắng nghe lệnh từ người xem!

---

## ⚡ Các tính năng nổi bật & Tối ưu

- **Bộ nhớ đệm (In-memory Caching):** Lưu cache tên Hero và thông tin hồ sơ trong 30-60 giây, giúp hạn chế tối đa việc gọi trùng lặp lên OpenDota API.
- **Tiết kiệm Quota YouTube API:** Tuân thủ `pollingIntervalMillis` (tối thiểu 3-5 giây mỗi lần quét chat), đảm bảo tài khoản YouTube miễn phí (10,000 units/ngày) có thể stream liên tục nhiều giờ mà không lo hết hạn mức.
- **Chống Spam (Cooldown):** Có thời gian hồi 8 giây cho mỗi lệnh và 3 giây cooldown toàn cục để tránh tình trạng flood khung chat.
- **Giới hạn 200 ký tự:** Tất cả tin nhắn phản hồi được căn chỉnh để không vượt quá giới hạn 200 ký tự của YouTube Live Chat.
