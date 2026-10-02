# Agnet — hướng dẫn cho Claude khi làm việc trong dự án này

Hệ thống đa agent tự săn xu hướng và viết **kịch bản đạo diễn** video 3–20 phút. Kế hoạch gốc: `KE_HOACH_AGNET.md` (đọc mục liên quan trước khi sửa).
Đầu ra duy nhất: `script.md` + `script.json` (+ `koc_prompts.json`). **Không** dựng video, không TTS.

## Phân vai: LLM phán đoán, code kiểm chứng
| Việc | Ai làm |
|---|---|
| Chiến lược, nghiên cứu, viết, đạo diễn, QA, hook | Agent Claude (`.claude/agents/`, kỹ năng ở `.claude/skills/`) |
| Thời lượng/đếm từ, schema, trùng đề tài 30 ngày, ngân sách, điểm, hợp đồng KOC, ghi file | **Code Python** (`agnet/`) — không bao giờ giao cho LLM |

Agent **không có quyền Write/Edit**: file đầu ra do `agnet/pipeline/export.py` ghi.

## Lệnh
```
python -m pytest -q                      # phải xanh trước khi báo hoàn thành
python -m agnet flows                    # kiểm tra config/flows.yaml
python -m agnet validate <script.json> --flow <id>
python -m agnet budget --minutes 10 --wpm 160 --weights 1,3,3,3,2,1
python -m agnet count --wpm 140 --file voiceover.txt
python -m agnet dedup "<đề tài>"  |  claim <flow_id> "<đề tài>"
python -m agnet run <flow_id>            # CHẠY THẬT, tốn chi phí API
python -m agnet doctor                   # kiểm tra điều kiện chạy tự động (không tốn API)
python -m agnet serve                    # daemon: lịch + bù lịch + log + Telegram
python -m agnet status [--flow X]        # lịch sử chạy & chi phí
python -m agnet catchup [flow_id] [--force]   # chạy bù luồng hôm nay chưa chạy
```

## Quy tắc cứng (đừng nới)
1. **Không bịa số liệu**: Trend Score từ chối chấm khi thiếu thành phần/evidence. Đừng "ước lượng cho đủ".
2. **Ngưỡng QA ≥ 8 không hạ** để đủ sản lượng; thiếu thì lấy đề tài dự phòng.
3. **Luồng `sensitive` bắt buộc `human_review`** — đừng tắt cho nhanh.
4. **Tiêu đề phải có `truth_check`**; cấm khẳng định sai/chưa xác minh về người thật; cấm tự bịa tin đồn rồi "bác bỏ".
5. **KOC**: không sửa Lớp B (`agnet/koc/realism_engine.json`), `negative`, `consistency_lock` trong từng nhân vật; nhân vật ≥ 22 tuổi; không mô tả gợi dục/số đo; không mạo danh bác sĩ/luật sư; luôn `ai_disclosure`. `build_prompt` và test chặn các lỗi này — đừng gỡ test để qua.
6. Tốc độ đọc dùng `wpm` của luồng (vi 160 · de 140 · en 150).
7. Đổi schema `script.json` ⇒ sửa `schemas/script.schema.json` + `agnet/core/validate.py` + test, và báo người dùng (phần mềm dựng đọc file này).

## Cấu trúc
```
.claude/agents/   17 agent (frontmatter: name, model theo tầng, tools, skills)
.claude/skills/   agnet-script-director · qa-editor · trend-scoring · koc-studio · hook-title · flow-config
agnet/core/       models (Flow) · timing · scoring · validate
agnet/koc/        master_prompt · adapters · export · realism_engine.json
agnet/pipeline/   agents (nạp + SdkRunner) · pipeline (điều phối, vòng QA ≤ 2) · export
agnet/storage/    db (SQLite: chống trùng, chi phí)
agnet/scheduler.py  APScheduler từ flows.yaml (sync: thêm/sửa/gỡ job)
agnet/daemon.py   vận hành: khoá 1 bản chạy · bù lịch · nạp lại flows.yaml · trần thời gian · báo lỗi
agnet/notify.py   Telegram + webhook (không bao giờ ném lỗi ra ngoài, không log token)
agnet/logging_setup.py · agnet/env.py   log ngày trong logs/ (che khoá) · nạp .env
scripts/          start_agnet.bat · run_flow.bat · register_task.ps1 · unregister_task.ps1 (Task Scheduler)
config/           flows.yaml · scoring.yaml · characters.yaml · characters/*.json
schemas/          script.schema.json
tests/            xem `python -m pytest -q`
```

## Trạng thái — nói đúng những gì CHƯA kiểm chứng
- **Đã kiểm bằng test** (109 test): cấu hình luồng, toán thời lượng, chấm điểm, chống trùng, cổng `validate`, hợp đồng KOC, điều phối (agent giả lập), lịch chạy, và lớp vận hành — quyết định bù lịch, khoá một bản chạy, trần thời gian mỗi lần chạy, nạp lại `flows.yaml` khi file đổi, định dạng & gửi thông báo (transport giả).
- **Lần chạy thật 01/10/2026 07:38 bỏ dở**: đã có `ANTHROPIC_API_KEY`, 4 lượt gọi agent tốn $1,16 rồi tiến trình không kết thúc (bản ghi `runs` còn `running`). Chưa biết nguyên nhân treo ở agent nào — vì vậy daemon nay có `run_timeout_min` (mặc định 180 phút) và đánh dấu `interrupted`. Lần chạy thật tiếp theo nên theo dõi `logs/agnet.log` để xem agent nào chậm.
- **Chưa gửi Telegram thật**: `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` trong `.env` đang trống; mã gửi chỉ được kiểm bằng transport giả. `agnet doctor` sẽ báo thiếu.
- **Chưa đăng ký tác vụ Windows**: script `scripts/register_task.ps1` chưa được chạy trên máy này (phải chạy từ PowerShell trên Windows, không chạy được từ phiên này).
- **Chưa chạy với API thật**: `SdkRunner` mới được kiểm là khớp chữ ký SDK, **chưa** có một lần chạy thật; chất lượng viết/QA của agent chưa đo. Chi phí thực tế/luồng/ngày chưa biết — chạy 1 luồng 1–2 kịch bản trước, xem `cost_ledger`, rồi mới chốt `max_cost_usd_per_day` và `daily_quota`.
- **Chưa có**: connector số liệu thật (YouTube Data API, Trends, RSS — scout hiện chỉ có prompt + WebSearch, **không có** view/giờ chính xác), Web UI, Analytics Learner, embedding/pgvector, Telegram. Google Trends và TikTok Creative Center không có API chính thức — thiết kế scout chịu lỗi từng nguồn.
- Nhân vật KOC mới có **chữ** (`status: draft`); chưa có ảnh gốc/bảng 9 ảnh nên chưa được bật cho luồng thật.
- Chốt `script.json` với phần mềm dựng video thật **trước** khi đầu tư thêm phần xuất.
