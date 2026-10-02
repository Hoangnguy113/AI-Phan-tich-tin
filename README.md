# Agnet

Hệ thống đa agent săn xu hướng & viết kịch bản đạo diễn video. Xem `KE_HOACH_AGNET.md` (kế hoạch) và `CLAUDE.md` (cách làm việc/quy tắc/trạng thái).

## Bắt đầu
```
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -e ".[dev]"
copy .env.example .env                               # điền ANTHROPIC_API_KEY
python -m pytest -q
python -m agnet flows
```
Dùng thủ công (không cần API riêng): mở thư mục này trong Claude, các skill/agent ở `.claude/` tự nạp.
Chạy tự động: `python -m agnet run <flow_id>` hoặc `python -m agnet serve`.

## Xác thực để chạy thật
`SdkRunner` dùng Claude Agent SDK, cần **một** trong hai:
1. Biến môi trường `ANTHROPIC_API_KEY` (đặt trong `.env` hoặc hệ thống — bạn tự điền, đừng gửi khoá qua chat); hoặc
2. Đã đăng nhập Claude Code trên máy chạy (`claude` → `/login`).
Thử nhanh: `python -m agnet run suckhoe-yt-sang` sẽ báo `Not logged in` nếu chưa xác thực.

## Chạy tự động hằng ngày (Windows)
```powershell
python -m agnet doctor                                                  # kiểm tra trước, không tốn API
powershell -ExecutionPolicy Bypass -File scripts\register_task.ps1      # đăng ký tác vụ "Agnet-Daemon"
Get-Content logs\agnet.log -Tail 40 -Wait                               # xem nhật ký đang chạy
python -m agnet status                                                  # lịch sử chạy & chi phí
powershell -ExecutionPolicy Bypass -File scripts\unregister_task.ps1    # tắt chạy tự động
```
Tác vụ chạy `scripts\start_agnet.bat` → `python -m agnet serve`:
- chạy theo cron trong `config/flows.yaml` (sửa file là lịch tự nạp lại trong 30 giây, không cần khởi động lại);
- **bù lịch**: máy tắt đúng giờ chạy → chạy ngay khi bật lại, với điều kiện hôm nay chưa chạy và còn trước
  `catchup_until` của luồng (mặc định 12:00);
- **một bản duy nhất**: khoá `agnet.lock`, hai tiến trình không thể cùng tiêu tiền API;
- **trần thời gian** `run_timeout_min` phút mỗi lần chạy — treo thì dừng cứng và báo lỗi;
- lần chạy bỏ dở (mất điện) được đánh dấu `interrupted` để hôm sau còn chạy bù;
- log ngày trong `logs/` (giữ 30 ngày, tự che giá trị khoá), báo cáo trong `output/<ngày>/<luồng>/_BAO_CAO_NGAY.md`;
- báo Telegram khi xong: điền `TELEGRAM_BOT_TOKEN` và `TELEGRAM_CHAT_ID` trong `.env`
  (chat id lấy bằng cách nhắn cho bot rồi mở `https://api.telegram.org/bot<token>/getUpdates`).

Chạy bù thủ công: `python -m agnet catchup [flow_id] [--force]`. Chạy một luồng ngay: `scripts\run_flow.bat <flow_id>`.
