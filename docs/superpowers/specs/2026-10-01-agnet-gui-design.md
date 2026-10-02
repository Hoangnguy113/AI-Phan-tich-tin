# Agnet GUI — phần mềm quản lý desktop (PySide6)

Ngày: 2026-10-01 · Trạng thái: chờ người dùng duyệt spec

## 1. Mục tiêu
App desktop Windows để quản lý Agnet bằng chuột (thay dòng lệnh) và để pipeline chạy bằng **tài khoản Claude đã đăng nhập (Claude Code login), không cần `ANTHROPIC_API_KEY`**. Dùng cá nhân, trên máy của người dùng.

**Tiêu chí thành công**
1. `python -m agnet gui` mở cửa sổ với 6 màn hình dưới đây.
2. Màn Tài khoản hiện đúng trạng thái đăng nhập; nút Đăng nhập mở `claude login`.
3. Khi có `ANTHROPIC_API_KEY`, app cảnh báo và pipeline do app khởi chạy KHÔNG dùng khóa đó.
4. Lưu luồng không bao giờ làm hỏng `flows.yaml` (kiểm tra hợp lệ + ghi nguyên tử + `.bak`).
5. `python -m pytest -q` xanh; không đổi `script.schema.json`, `validate.py`, `realism_engine.json`.

**Ngoài phạm vi (bản đầu):** Radar xu hướng, Analytics, tự chạy lại kịch bản "cần viết lại", sinh ảnh KOC, đóng gói `.exe`.

## 2. Giả định (đã nêu với người dùng)
- Chỉ dùng cá nhân; chia sẻ/bán cho người khác phải dùng API key (chính sách Anthropic).
- Hạn mức gói đăng ký có thể không đủ cho 10 kịch bản dài/ngày.
- `claude` có trong PATH và đã `claude login`.
- Python ≥ 3.10 (repo đang dùng 3.10).

## 3. Kiến trúc
- Package mới `agnet/ui/`; thêm lệnh con `gui` vào `agnet/cli.py`; phụ thuộc tùy chọn `gui = ["PySide6>=6.6"]` trong `pyproject.toml`.
- Tách **logic thuần (không import Qt)** khỏi **widget**:

| Module | Vai trò |
|---|---|
| `ui/auth.py` | `claude auth status` → `AuthStatus`; phát hiện `ANTHROPIC_API_KEY`; dựng lệnh đăng nhập/đăng xuất |
| `ui/procs.py` | Quản lý tiến trình con (`run <flow>`, `catchup`, `serve`): khởi chạy, dừng, đọc log |
| `ui/flows_store.py` | Đọc/ghi `flows.yaml` an toàn |
| `ui/library.py` | Quét `output/`, đọc `script.json`/`script.md`, `review.json` |
| `ui/koc_view.py` | Đọc `config/characters*`, `koc_prompts.json` (chỉ đọc) |
| `ui/main_window.py` + `ui/pages/*.py` | Widget PySide6, mỏng, chỉ gọi các module trên |

- Việc tốn tiền/chạy lâu luôn là **tiến trình con** `python -m agnet run|serve|catchup` → UI không treo, tái dùng khóa một bản chạy, log, bù lịch đã có test. UI đọc trạng thái qua `Store` (SQLite) và `logs/agnet.log`.

## 4. Đăng nhập bằng tài khoản
- `auth.status()`: chạy `claude auth status` (timeout 10s, không ném lỗi) → `{logged_in, email, plan, raw}`; không có lệnh `claude` → `logged_in=False, reason="thiếu claude CLI"`.
- Nút Đăng nhập: mở tiến trình `claude auth login` (trình duyệt); app tự kiểm tra lại sau khi tiến trình thoát. Không bao giờ nhập hay lưu mật khẩu/token.
- **Chống tính tiền API nhầm:** `ANTHROPIC_API_KEY` ghi đè tài khoản. App (a) hiện cảnh báo đỏ, (b) khi khởi chạy tiến trình con thì loại khóa khỏi môi trường tiến trình con (mặc định bật, tắt được ở Cài đặt).
- `SdkRunner` (`pipeline/agents.py`) thêm `env={"ANTHROPIC_API_KEY": ""}` cho SDK **chỉ khi** chế độ tài khoản bật; mặc định giữ hành vi cũ. **CHƯA KIỂM CHỨNG** chuỗi rỗng có được Claude Code coi là không có khóa; bước đầu của kế hoạch phải kiểm thực tế (probe 1 lệnh `claude -p` rẻ, không chạy pipeline), nếu không được thì chỉ dựa vào việc loại khóa khỏi môi trường tiến trình con.
- `max_cost_usd_per_day` giữ làm chốt chặn (số quy đổi, không phải tiền thật với gói đăng ký).

## 5. Màn hình
1. **Tài khoản Claude** — trạng thái đăng nhập, nút Đăng nhập/Đăng xuất/Kiểm tra lại, cảnh báo API key, bảng kết quả `doctor` (gọi `cmd_doctor` bắt stdout).
2. **Bảng điều khiển** — mỗi luồng: hôm nay đã chạy?, số kịch bản đạt, chi phí/trần, trạng thái daemon; bảng `recent_runs`; ô xem log đuôi file; nút Chạy ngay / Chạy bù / Dừng / Bật-Tắt lịch (`serve`) / "Đánh dấu bị gián đoạn" (`finish_running`).
3. **Quản lý luồng** — form các trường mục 3.1 kế hoạch; kiểm tra bằng model `Flow`; tạo/nhân bản/bật-tắt/xóa. Luồng `sensitive` không cho tắt `human_review`.
4. **Kho kịch bản** — cây ngày → luồng → kịch bản; xem `script.md`; chạy `validate`; hiện điểm QA; nút **Duyệt / Cần viết lại (kèm góp ý) / Loại** → ghi `review.json` cạnh `script.json` (không sửa schema). "Cần viết lại" chỉ lưu góp ý.
5. **Nhân vật KOC** — chỉ đọc: ADN, `status` draft/ready, prompt theo cảnh. Không sửa Lớp B/`negative`/`consistency_lock`.
6. **Cài đặt** — đường dẫn flows/db, Telegram (qua `.env`, hiển thị che), tùy chọn loại API key.

## 6. Luồng dữ liệu
UI → (module logic) → `flows.yaml` / `agnet.db` / `output/` / `logs/`; hành động tốn tiền → tiến trình con. UI làm mới theo `QTimer` (3s) đọc `Store` và log; không có kênh IPC riêng.

## 7. Xử lý lỗi
- Chưa đăng nhập/hết phiên: khóa mọi nút chạy, hiện hướng dẫn.
- `flows.yaml` sai: không lưu, hiện lỗi từng trường.
- Lưu: ghi file tạm → kiểm tra bằng `load_flows` → thay thế, giữ `flows.yaml.bak`.
- Tiến trình con chết: hiện mã thoát + 20 dòng log cuối.
- Mọi lỗi I/O hiện hộp thoại; không để ngoại lệ làm app thoát.

## 8. Kiểm thử
- pytest cho `auth`, `procs`, `flows_store`, `library`, `koc_view` bằng `claude`/subprocess giả và thư mục tạm; không gọi API thật.
- Smoke test widget với `QT_QPA_PLATFORM=offscreen`, bỏ qua nếu PySide6 chưa cài.
- Giữ nguyên 109 test hiện có xanh.
- **Chưa kiểm chứng và sẽ nói rõ:** pipeline chạy thật qua tài khoản; hạn mức gói đủ hay không.

## 9. Rủi ro
| Rủi ro | Xử lý |
|---|---|
| Chuỗi rỗng không vô hiệu khóa API | Probe ở bước 1; phương án dự phòng loại khỏi env tiến trình con |
| Lệnh `claude auth status` đổi định dạng | Phân tích mềm, hiện `raw` khi không hiểu |
| Hết hạn mức gói giữa chừng | Hiện lỗi từ tiến trình con; không tự thử lại |
| PySide6 nặng/không cài được | Phụ thuộc tùy chọn; lõi CLI không bị ảnh hưởng |
