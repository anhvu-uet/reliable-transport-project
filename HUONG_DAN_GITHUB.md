# Hướng dẫn từng bước – Reliable Transport (Ubuntu VMware + GitHub)

## A. Hiểu cấu trúc và code

- `RTP-base/sender.py`: gửi `START`, gửi dữ liệu UDP theo cửa sổ trượt, nhận **cumulative ACK**, hết 500 ms thì gửi lại toàn bộ các gói chưa ACK.
- `RTP-base/receiver.py`: kiểm tra CRC32, giữ các gói đến sai thứ tự, chỉ xuất dữ liệu đúng thứ tự và ACK số thứ tự gói đang chờ.
- `RTP-opt/sender.py`: lưu trạng thái đã ACK của từng gói; khi timeout chỉ gửi lại những gói chưa ACK.
- `RTP-opt/receiver.py`: gửi **ACK riêng** (`ACK(seq)=seq của DATA`), không gửi cumulative ACK cho DATA.
- `utils.py`: định nghĩa cấu trúc gói và CRC, giữ nguyên. Các file trong `test_scripts/`: **giữ nguyên**, không chỉnh proxy hay bộ chấm.

## B. Chuẩn bị trên Ubuntu VM

1. Chép và giải nén `reliable_transport_project.zip` vào thư mục Home/Downloads trên máy ảo. Mở Ubuntu Terminal trong thư mục `reliable_transport_project`.
2. Chạy các lệnh sau (mỗi lệnh ấn Enter):

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git lsof
python3 -m venv .venv
source .venv/bin/activate
python -m pip install scapy
python -c "import scapy; print('Scapy OK:', scapy.__version__)"
chmod +x test_scripts/test.sh test_scripts/compare.sh
```

**Giải thích:** `venv` tạo môi trường Python riêng, `source` kích hoạt nó, `pip` cài Scapy cho `utils.py` và `proxy.py`. Đề gốc ghi `scapy==2.4.0`, nhưng bản này có thể không tương thích với Python hiện đại; dùng đúng phiên bản của VM/thầy nếu có yêu cầu riêng. Sau mỗi lần mở Terminal mới, chạy `source .venv/bin/activate` trong thư mục project.

## C. Kiểm thử tự động (giữ nguyên script của thầy)

```bash
./test_scripts/test.sh RTP-base
./test_scripts/test.sh RTP-opt
```

Mục tiêu:

```text
SUCCESS: Message received matches message sent!
```

**Lưu ý:** `test_scripts/test.sh` do thầy cấp sử dụng nhầm tên `SENDER_ID` ở bước kill trong khi biến được đặt tên `SENDER_PID`. Script cũng chỉ đợi 10 giây. **Không sửa script trong bài nộp**. Nếu có lỗi cổng bận hoặc script kết thúc khi file chưa truyền xong, dừng các tiến trình thử nghiệm cũ và kiểm thử thủ công như phần D.

## D. Kiểm thử thủ công: 3 cửa sổ Terminal

Giữ 3 Terminal ở cùng thư mục `reliable_transport_project`, đã kích hoạt `.venv` trong mỗi Terminal.

**Terminal 1 – Khởi động Receiver:**

```bash
python RTP-base/receiver.py localhost 40000 128 > RTP-base/output.txt
```

**Terminal 2 – Khởi động bộ giả lập lỗi mạng:**

```bash
python test_scripts/proxy.py localhost 50000 localhost 40000 0123
```

`0123`: thử gói bị hỏng, trễ, đảo thứ tự và mất. Proxy sẽ chạy liên tục và hiển thị log.

**Terminal 3 – Gửi file và so sánh:**

```bash
python RTP-base/sender.py localhost 50000 128 < test_scripts/test_message.txt
./test_scripts/compare.sh RTP-base/output.txt test_scripts/test_message.txt
```

Nếu màn hình hiện `SUCCESS: Message received matches message sent!` là dữ liệu bên nhận trùng với đầu vào. Dừng **proxy** bằng `Ctrl+C` ở Terminal 2 và bảo đảm Receiver đã kết thúc trước lượt chạy tiếp. **Để kiểm thử Part 3**, lặp lại toàn bộ ba Terminal nhưng thay tất cả `RTP-base` bằng `RTP-opt`.

**Nếu `Address already in use`:** kiểm tra cổng bằng `sudo lsof -iUDP:40000 -iUDP:50000` (cài `lsof` nếu cần), dừng tiến trình còn chạy hoặc dùng hai cổng khác đồng thời ở cả ba lệnh.

## E. Đưa lên GitHub lần đầu

**Bước 1 – Tạo repo:** Đăng nhập https://github.com → nhấn `+` → `New repository`, đặt tên `reliable-transport-project`, chọn Public nếu thầy cần xem mà không có quyền riêng, **không tích tự tạo README/.gitignore** vì các file đã có trong thư mục. Nhấn `Create repository`.

**Bước 2 – Mở Terminal trong thư mục project**, kích hoạt `.venv` nếu chưa có, rồi chạy:

```bash
git init
git branch -M main
git config user.name "TEN CUA BAN"
git config user.email "EMAIL_GITHUB_CUA_BAN"
git status
git add .
git commit -m "Implement reliable transport with base and selective ACK"
```

- `git init`: biến thư mục hiện tại thành Git repository.
- `git branch -M main`: đặt tên nhánh chính là `main`.
- `git config`: đặt thông tin tác giả commit (điền **thông tin thật của bạn**).
- `git status`: kiểm tra các file được Git theo dõi.
- `git add .`: chọn các file đã thay đổi để chuẩn bị commit.
- `git commit`: lưu một mốc lịch sử code ở **máy của bạn** (chưa lên mạng).

**Bước 3 – Kết nối và đẩy code lên GitHub** (thay USERNAME):

```bash
git remote add origin https://github.com/USERNAME/reliable-transport-project.git
git push -u origin main
```

- `git remote add origin`: chỉ đường đến repo online của bạn.
- `git push`: đưa các commit từ máy lên GitHub. Có thể cần xác thực qua trình duyệt hoặc token, không dùng mật khẩu đăng nhập GitHub cho HTTPS Git.
- Refresh trang repository trong trình duyệt và kiểm tra đủ `RTP-base`, `RTP-opt`, `test_scripts`.

**Bước 4 – Tạo tag nộp bài** sau khi đã kiểm thử và push phiên bản cuối:

```bash
git tag -a submission -m "Final Submission"
git push origin submission
```

- `git tag`: đánh dấu commit nộp chính thức.
- `git push origin submission`: đẩy cả dấu mốc lên GitHub để giảng viên thấy.

**Nếu sau đó có sửa code:** dùng `git add .`, `git commit -m "Describe changes"`, `git push` để cập nhật. Nếu muốn cập nhật tag `submission`, cần cân nhắc vì giảng viên có thể yêu cầu tag bất biến; tốt nhất chỉ tạo tag một lần sau khi code đã ổn định.

## F. Kiểm tra trước khi nộp

- [ ] `RTP-base` chạy và so sánh thành công.
- [ ] `RTP-opt` chạy và so sánh thành công.
- [ ] Repo GitHub có đủ 4 file `sender.py`, `receiver.py` trong đúng hai thư mục.
- [ ] Không sửa các file giả lập, `utils.py` hoặc script của thầy.
- [ ] Đã push commit và tag `submission` lên GitHub.
- [ ] Link GitHub mở được từ trình duyệt không đăng nhập (nếu repo Public).

Mẫu nộp do giảng viên yêu cầu:

```text
[MSV] [HoTen] [LinkGithub]
```

Thầy yêu cầu cập nhật mã nguồn lên GitHub **trước ngày 08/11/2026**; nên push hoàn tất **trong ngày 07/11/2026**, theo múi giờ Việt Nam.
