# 🤖 YouTube Live Chat Bot cho Dota 2 Streamer

Bot tự động lắng nghe live chat trên YouTube và phản hồi thông tin Dota 2 của streamer thông qua **OpenDota API** (dành cho người chơi [Dotabuff 196931374](https://www.dotabuff.com/players/196931374)).

> **💡 Hỗ trợ chạy tài khoản bot riêng trên kênh của người khác:**  
> Bạn hoàn toàn có thể đăng nhập tài khoản bot của riêng mình để tự động đọc chat và trả lời tin nhắn trên kênh stream của người khác (ví dụ: kênh [**@DHDota2**](https://www.youtube.com/@DHDota2)). Bot có tính năng **tự động quét và phát hiện luồng livestream đang phát** của kênh mà không cần phải copy paste link thủ công!

---

## 📌 Các câu lệnh hỗ trợ trong Chat

| Lệnh | Mô tả | Ví dụ kết quả phản hồi |
| :--- | :--- | :--- |
| `!today` hoặc `!homnay` | Thống kê kết quả thi đấu trong ngày hôm nay, chỉ tính trận bắt đầu từ 0h hôm nay theo múi giờ đã cấu hình (Thắng/Thua, Winrate, Tướng chơi, Trận vừa kết thúc) | `🔥 Hôm nay (05/11): 4W - 2L (66.7%) \| Trận vừa xong: Outworld Devourer (16/2/10) Thắng ✅ \| Tướng: Outworld Devourer (1W-0L), Ember Spirit (1W-0L)...` |
| `!yesterday` hoặc `!homqua` | Thống kê kết quả của phiên stream hôm trước (Thắng/Thua, Winrate, Trận chốt ca kết thúc phiên, Tướng chơi) | `📅 Ca hôm trước (09/11): 7W - 5L (58.3%) \| Chốt ca: Storm (11/8/16) Thắng ✅ [Avg MMR 7.5k] \| Tướng: Storm (3W-1L), Axe (2W-0L)...` |
| `!rank` | Xem medal/rank hiện tại của streamer kèm xếp hạng % thế giới (Percentile từ OpenDota `/distributions`) | `🏅 Rank của To the Moon and not back: Immortal (Top #154) \| Trình độ: Top 0.01% thế giới (cao hơn 99.99% người chơi)` |
| `!streak` hoặc `!chuoi` | Chuỗi thắng/thua hiện tại, tính từ các trận gần nhất | `🔥 Đang thắng 4 trận liên tiếp \| Trận gần nhất: OD (16/2/10)` |
| `!recent` hoặc `!5tran` | Kết quả 10 trận gần nhất, theo thứ tự thời gian | `📊 10 trận gần nhất: W W L W W L W W W L (7W-3L)` |
| `!hero` hoặc `!heroes` | Thống kê các tướng streamer hay đánh gần đây nhất (25 trận & 100 trận) kèm top tướng cả đời (All-time) | `🌟 Tướng DH: 25 trận: Lesh (4W-2L), Storm (3W-2L), Axe (4W-0L) \| 100 trận: Lesh (10W-7L), Axe (11W-2L), Storm (5W-6L) \| Cả đời: Invo (865t), Slark (628t), Morph (549t). Soi: !hero <tên>` |
| `!hero <tên hero>` | Thống kê chi tiết phong độ của streamer trên hero cụ thể (số trận, W-L trong 25 trận & 100 trận gần nhất), Sự nghiệp Cả đời (All-time) và tỉ lệ thắng rank Immortal | `⚔️ Storm Spirit của DH: 25 trận: 5 trận (3W-2L) \| 100 trận: 11 trận (5W-6L, 45%) \| Sự nghiệp: 425 trận (212W-213L, 50%) \| Immortal WR: 47.4%` |
| `!dh` hoặc `!458`, `!thocac` | Thông tin tiểu sử, thành tích sự nghiệp thi đấu Dota 2 chuyên nghiệp của streamer DH (Trịnh Văn Thọ) | `🍳🍳🍳🍳 458 (DH QUY hay Thocac) tên thật Trịnh Văn Thọ (sinh 1996), carry người Việt Nam, từng đánh cho 496 Gaming, TNC Tigers và SPAWN. Danh hiệu lớn nhất là vô địch OB.Moon Asian Arena 2021, giải $20.000.` |
| `!pro` hoặc `!pros` | Danh sách các pro player streamer đã gặp trong ca stream hôm nay | `🌟 Pro gặp hôm nay (10/11): Marty (1L đối), Shanks (1W cùng), mj (1L cùng)` |
| `!pro <tên pro>` | Thống kê đối đầu / chung team với pro player cụ thể (vd: `!pro 23savage`, `!pro collapse`, `!pro hunghung`) | `⚔️ Streamer vs 23savage (OG) (tổng 264 trận): Chung team 98 trận (67W-31L, 68.4%) \| Đối đầu 166 trận (70W-96L, 42.2%)` |
| `!mate` | Top 3 người hay duo cùng nhất trong 100 trận gần nhất (số trận cùng đội, số trận thắng khi duo) | `👥 Hay duo với (100 trận gần nhất): ABC (24 trận, 14W)` |
| `!live` | Trận đang diễn ra: phút thi đấu + tỉ lệ thắng ước tính từ chênh vàng/kill (công thức heuristic, không phải Dota Plus) + chênh vàng theo góc streamer ("Dẫn/Kém …k vàng"), kèm tên pro trong trận nếu có. Lọc trận cũ đã kết thúc trong `/live` theo `last_update_time` mới nhất (quá 5 phút không cập nhật thì coi như hết trận). Nếu không thấy trong top 100 thì báo rõ là có thể đang đánh nhưng trận không lọt top 100, thay vì báo là không đang đánh | `🔴 Đang đánh (28:09): ước tính thắng ~79% \| Dẫn 19k vàng` |
| `!career` hoặc `!totals` | Thống kê toàn bộ sự nghiệp Dota 2: Tổng số trận, số giờ chơi, số kills, assists, tổng lượng sát thương | `📜 Sự nghiệp Dota 2 của To the Moon and not back: 16.845 trận (8.685W-8.160L, 51.6%) \| 9.736 giờ chơi (405 ngày đêm) \| 136.933 Kills \| 309 Triệu sát thương!` |
| `!funfact` hoặc `!ditat` | Ngẫu nhiên 1 trong 10 góc fact "dị" độc đáo (gà bị giết, mua Thánh Kiếm Rapier, tốc độ tay APM, thời gian ngắm màn hình đen trắng đếm số, stun đối thủ, phá trụ, tiền xe ôm mua giấy TP...) | `🎭 Fun fact: 🪓 To the Moon and not back đã đồ sát 2.579 con gà (courier)! Cứ trung bình ~6 trận lại có 1 shipper xấu số bay màu.` |
| `!connapse` | Góc Funfact tình đồng chí khi duo cùng tri kỷ connapse (SteamID 968755756): Tỉ lệ thắng, tướng tủ bảo kê, kỷ lục thời gian, KDA... | `🤝 Tri kỷ connapse: 31 trận kề vai sát cánh (18h44p), 100% CÙNG PHE chưa từng đối đầu! Kết quả: 14W - 17L (45.2%).` |
| `!help` hoặc `!lenh` | Hiển thị danh sách các lệnh có sẵn | `📜 Lệnh có sẵn: !today, !yesterday, !last, !rank, !hero, !dh, !live, !pro, !career, !funfact, !connapse` |

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
