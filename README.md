# 🤖 YouTube Live Chat Bot cho Dota 2 Streamer

Bot tự động lắng nghe live chat trên YouTube và phản hồi thông tin Dota 2 của streamer thông qua **OpenDota API** (dành cho người chơi [Dotabuff 196931374](https://www.dotabuff.com/players/196931374)).

> **💡 Hỗ trợ chạy tài khoản bot riêng trên kênh của người khác:**  
> Bạn hoàn toàn có thể đăng nhập tài khoản bot của riêng mình để tự động đọc chat và trả lời tin nhắn trên kênh stream của người khác (ví dụ: kênh [**@DHDota2**](https://www.youtube.com/@DHDota2)). Bot có tính năng **tự động quét và phát hiện luồng livestream đang phát** của kênh mà không cần phải copy paste link thủ công!

---

## 📌 Các câu lệnh hỗ trợ trong Chat

| Lệnh | Mô tả | Ví dụ kết quả phản hồi |
| :--- | :--- | :--- |
| `!today` hoặc `!homnay` | Thống kê kết quả thi đấu trong ngày hôm nay, chỉ tính trận bắt đầu từ 0h hôm nay theo múi giờ đã cấu hình (Thắng/Thua, Winrate, Tướng chơi, Trận vừa kết thúc) | `🔥 Hôm nay (05/11): 4W - 2L (66.7%) \| Trận vừa xong: Outworld Devourer (16/2/10) Thắng ✅ \| Tướng: Outworld Devourer (1W-0L), Ember Spirit (1W-0L)...` |
| `!rank` | Xem medal/rank hiện tại của streamer kèm xếp hạng % thế giới (Percentile từ OpenDota `/distributions`) | `🏅 Rank của To the Moon and not back: Immortal (Top #154) \| Trình độ: Top 0.01% thế giới (cao hơn 99.99% người chơi)` |
| `!streak` hoặc `!chuoi` | Chuỗi thắng/thua hiện tại, tính từ các trận gần nhất | `🔥 Đang thắng 4 trận liên tiếp \| Trận gần nhất: OD (16/2/10)` |
| `!recent` hoặc `!5tran` | Kết quả 10 trận gần nhất, theo thứ tự thời gian | `📊 10 trận gần nhất: W W L W W L W W W L (7W-3L)` |
| `!heroes` hoặc `!besthero` | Top 3 tướng hay chơi nhất trong 100 trận gần nhất của streamer (số trận, winrate) | `🏆 Tướng tủ (100 trận gần nhất): OD (40 trận, 70%) \| Ember (30 trận, 60%)` |
| `!mate` | Top 3 người hay duo cùng nhất trong 100 trận gần nhất (số trận cùng đội, số trận thắng khi duo) | `👥 Hay duo với (100 trận gần nhất): ABC (24 trận, 14W)` |
| `!live` | Trận đang diễn ra: phút thi đấu + tỉ lệ thắng ước tính từ chênh vàng/kill (công thức heuristic, không phải Dota Plus) + chênh vàng theo góc streamer ("Dẫn/Kém …k vàng"), kèm tên pro trong trận nếu có. Lọc trận cũ đã kết thúc trong `/live` theo `last_update_time` mới nhất (quá 5 phút không cập nhật thì coi như hết trận). Nếu không thấy trong top 100 thì báo rõ là có thể đang đánh nhưng trận không lọt top 100, thay vì báo là không đang đánh | `🔴 Đang đánh (28:09): ước tính thắng ~79% \| Dẫn 19k vàng` |
| `!help` hoặc `!lenh` | Hiển thị danh sách các lệnh có sẵn | `📜 Lệnh có sẵn: !today, !rank, !streak, !recent, !heroes, !mate, !live` |

---

## ⚙️ Cơ chế khi Bot chạy trên tài khoản khác và chat ở kênh streamer (@DHDota2)

1. **Xác thực:** Bạn đăng nhập tài khoản Google của bot (tạo credentials `client_secret.json` cho tài khoản bot).
2. **Kênh mục tiêu:** Trong `.env`, đặt `TARGET_CHANNEL=@DHDota2`. Khi khởi động, bot sẽ tự động tìm buổi live đang phát trực tiếp của `@DHDota2` và kết nối vào Live Chat.
3. **Phản hồi:** Khi người xem chat `!today`, `!rank`, bot sẽ dùng tài khoản của bạn để gửi câu trả lời vào khung chat của stream.

### ⚠️ Lưu ý quan trọng để Bot hoạt động mượt mà:
1. **Tài khoản bot phải có kênh YouTube:** Đăng nhập tài khoản bot vào `youtube.com` và bấm **Tạo kênh** (chỉ cần tạo kênh trống để YouTube cấp quyền chat).
2. **Đăng ký kênh streamer:** Bấm **Subscribe (Đăng ký)** kênh `@DHDota2` (để tránh trường hợp streamer bật *Chế độ chỉ dành cho người đăng ký chat*).
3. **Cấp quyền Quản trị viên (Cờ lê xanh 🔧) - Khuyến nghị:** Nhờ chủ kênh `@DHDota2` cấp quyền Moderator cho tài khoản bot. Khi có cờ lê:
   - Bot không bị ảnh hưởng bởi chế độ chat chậm (Slow mode).

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

---

## 🐧 Chạy trên Linux / Lubuntu

File `start_bot.bat` chỉ dùng cho Windows. Trên Lubuntu dùng `start_bot.sh` (đã có sẵn trong thư mục này):

```bash
# 1. Cài Python + venv (chỉ cần làm 1 lần)
sudo apt update
sudo apt install -y python3 python3-venv python3-pip

# 2. Giải nén code rồi vào thư mục đó, ví dụ:
cd ~/BotDota2-main
chmod +x start_bot.sh

# 3. Copy file cấu hình và file OAuth vào thư mục này
cp .env.example .env
# sửa .env nếu cần: DOTA_ACCOUNT_ID, TARGET_CHANNEL, ...
# chép client_secret.json (tải theo Bước 3 ở trên) vào đây

# 4. Test lệnh Dota 2 trước, không cần YouTube
./start_bot.sh --test-dota

# 5. Chạy bot thật (lần đầu sẽ mở trình duyệt để đăng nhập tài khoản bot)
./start_bot.sh
```

Muốn chạy ngầm để tắt terminal vẫn chạy, dùng `tmux`:

```bash
tmux new -s bot
./start_bot.sh
# bấm Ctrl+B rồi D để thoát khỏi tmux mà bot vẫn chạy
# xem lại bằng: tmux attach -t bot
```

Tương đương thủ công, không dùng script:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py --test-dota
python main.py
```


---

## ⚡ Kiến trúc Hybrid siêu tiết kiệm Quota YouTube API

YouTube Data API v3 cấp miễn phí **10.000 units/ngày**. 
Nếu dùng API chính thống để liên tục quét đọc tin nhắn (`liveChatMessages.list`), mỗi lần quét tốn **5 units** $\rightarrow$ Sau 2 tiếng stream liên tục là cạn sạch 10.000 units!

**Dự án này đã được tối ưu toàn diện bằng kiến trúc Hybrid:**
1. **Lắng nghe tin nhắn (0 Quota API):** 
   * Sử dụng thư viện `pytchat` để đọc luồng chat trực tiếp từ stream với **chi phí 0 Quota**.
   * Bot có thể cắm máy lắng nghe chat 24/7/365 ngày mà không tốn một đơn vị Quota nào của Google.
2. **Gửi tin nhắn trả lời (20 Quota units/tin):** 
   * Chỉ khi có người xem gõ lệnh (`!today`, `!rank`...), bot mới dùng API OAuth để gửi tin nhắn.
   * Với 10.000 units miễn phí hàng ngày, bot có thể **trả lời tới 500 tin nhắn/ngày** mà không bao giờ lo bị cạn Quota vì quét đọc tin nhắn ngầm!
3. **Tiết kiệm thêm bằng cooldown + chống trùng lặp:**
   * Mỗi lệnh hồi 20 giây (`COMMAND_COOLDOWN`), mọi tin trả lời cách nhau tối thiểu 10 giây (`GLOBAL_COOLDOWN`).
   * Nếu câu trả lời giống hệt lần đã gửi trong 3 phút (`DEDUP_WINDOW_SECONDS=180`), bot sẽ bỏ qua, không tốn 20 units. Sau 3 phút, viewer mới vẫn nhận được câu trả lời bình thường.
   * Alias được gộp về lệnh chuẩn (`!homnay` → `!today`, `!lenh` → `!help`) nên không lách được cooldown bằng cách gõ tên lệnh khác.
