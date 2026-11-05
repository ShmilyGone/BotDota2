# 🤖 YouTube Live Chat Bot cho Dota 2 Streamer

Bot tự động lắng nghe live chat trên YouTube và phản hồi thông tin Dota 2 của streamer thông qua **OpenDota API** (dành cho người chơi [Dotabuff 196931374](https://www.dotabuff.com/players/196931374)).

> **💡 Hỗ trợ chạy tài khoản bot riêng trên kênh của người khác:**  
> Bạn hoàn toàn có thể đăng nhập tài khoản bot của riêng mình để tự động đọc chat và trả lời tin nhắn trên kênh stream của người khác (ví dụ: kênh [**@DHDota2**](https://www.youtube.com/@DHDota2)). Bot có tính năng **tự động quét và phát hiện luồng livestream đang phát** của kênh mà không cần phải copy paste link thủ công!

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

## ⚙️ Cơ chế khi Bot chạy trên tài khoản khác và chat ở kênh streamer (@DHDota2)

1. **Xác thực:** Bạn đăng nhập tài khoản Google của bot (tạo credentials `client_secret.json` cho tài khoản bot).
2. **Kênh mục tiêu:** Trong `.env`, đặt `TARGET_CHANNEL=@DHDota2`. Khi khởi động, bot sẽ tự động tìm buổi live đang phát trực tiếp của `@DHDota2` và kết nối vào Live Chat.
3. **Phản hồi:** Khi người xem chat `!today`, `!rank`, `!mmr`, bot sẽ dùng tài khoản của bạn để gửi câu trả lời vào khung chat của stream.

### ⚠️ Lưu ý quan trọng để Bot hoạt động mượt mà:
1. **Tài khoản bot phải có kênh YouTube:** Đăng nhập tài khoản bot vào `youtube.com` và bấm **Tạo kênh** (chỉ cần tạo kênh trống để YouTube cấp quyền chat).
2. **Đăng ký kênh streamer:** Bấm **Subscribe (Đăng ký)** kênh `@DHDota2` (để tránh trường hợp streamer bật *Chế độ chỉ dành cho người đăng ký chat*).
3. **Cấp quyền Quản trị viên (Cờ lê xanh 🔧) - Khuyến nghị:** Nhờ chủ kênh `@DHDota2` cấp quyền Moderator cho tài khoản bot. Khi có cờ lê:
   - Bot không bị ảnh hưởng bởi chế độ chat chậm (Slow mode).
   - Bot có thể gửi link Dotabuff mà không bị bộ lọc spam của YouTube ẩn tin nhắn.

---

## 🚀 Hướng dẫn cài đặt & Chạy

### Bước 1: Kích hoạt môi trường Python

```powershell
.\venv\Scripts\Activate.ps1
```
Hoặc chạy trực tiếp với Python của venv:
```powershell
.\venv\Scripts\python main.py --test-dota
```

---

### Bước 2: Test ngay các lệnh Dota 2 (Terminal Mode)

Kiểm tra dữ liệu OpenDota trực tiếp trên Terminal:
```powershell
.\venv\Scripts\python main.py --test-dota
```

---

### Bước 3: Lấy file xác thực Google Cloud (client_secret.json)

1. Vào [Google Cloud Console](https://console.cloud.google.com/) bằng tài khoản Google bạn muốn dùng làm Bot.
2. Tạo một Project mới.
3. Bật **YouTube Data API v3**.
4. Vào **OAuth consent screen** $\rightarrow$ chọn **External** $\rightarrow$ Thêm email tài khoản bot vào mục **Test users**.
5. Vào **Credentials** $\rightarrow$ **Create Credentials** $\rightarrow$ **OAuth client ID** $\rightarrow$ Chọn Application type: **Desktop app**.
6. Tải file JSON về, đổi tên thành `client_secret.json` và lưu vào thư mục `BotDota2`.

---

### Bước 4: Chạy Bot

1. Mở file `.env` kiểm tra cấu hình:
   ```env
   DOTA_ACCOUNT_ID=196931374
   TARGET_CHANNEL=@DHDota2
   TIMEZONE_OFFSET=7
   ```

2. Khởi chạy bot:
   ```powershell
   .\venv\Scripts\python main.py
   ```
   Hoặc truyền trực tiếp kênh mục tiêu qua dòng lệnh:
   ```powershell
   .\venv\Scripts\python main.py --channel @DHDota2
   ```

3. Lần đầu chạy, trình duyệt sẽ mở để bạn đăng nhập tài khoản bot và cấp quyền. Các lần tiếp theo bot sẽ tự động chạy ngầm.
