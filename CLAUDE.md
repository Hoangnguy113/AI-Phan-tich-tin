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
python -m agnet gui                      # phần mềm quản lý (PySide6): thanh trái 10 mục
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
agnet/pipeline/   agents (nạp, SdkRunner, chặn công cụ ghi) · pipeline (điều phối, vòng QA ≤ 2) · engine (định tuyến claude/gemini, thử lại OAuth) · survey · export
agnet/gemini/     client Gemini (khoá AI Studio) · ladder (thang model tự cập nhật, hạ bậc khi 429/503) · bám nguồn Google Search
agnet/commander/  hợp đồng nhiệm vụ · nghiệm thu bằng code · thử lại 1 lần · tỉ lệ đạt theo agent
agnet/ui/         ứng dụng desktop: sidebar + 10 trang (điều khiển, kho kịch bản, luồng, Gemini, đội agent, hợp đồng, KOC, chi phí, chung, tài khoản)
agnet/runner.py · core/settings.py   chạy 1 luồng · cài đặt chung (config/app_settings.json)
agnet/storage/    db (SQLite: chống trùng, chi phí)
agnet/scheduler.py  APScheduler từ flows.yaml (sync: thêm/sửa/gỡ job)
agnet/daemon.py   vận hành: khoá 1 bản chạy · bù lịch · nạp lại flows.yaml · trần thời gian · báo lỗi
agnet/notify.py   Telegram + webhook (không bao giờ ném lỗi ra ngoài, không log token)
agnet/logging_setup.py · agnet/env.py   log ngày trong logs/ (che khoá) · nạp .env
scripts/          start_agnet.bat · run_flow.bat · register_task.ps1 · unregister_task.ps1 (Task Scheduler)
config/           flows.yaml · scoring.yaml · characters.yaml · characters/*.json · app_settings.json · gemini_models.json (cache, sinh tự động)
schemas/          script.schema.json
tests/            xem `python -m pytest -q`
```

## Trạng thái — nói đúng những gì CHƯA kiểm chứng
- **Đã kiểm bằng test** (381 test, 02/10/2026): cấu hình luồng, toán thời lượng, chấm điểm, chống trùng, cổng `validate`, hợp đồng KOC, điều phối (agent giả lập), lịch chạy, lớp vận hành, **client Gemini** (thang model, hạ bậc 429/503/400, bám nguồn, cooldown, khoá luồng — bằng transport giả), **hợp đồng & nghiệm thu**, **định tuyến engine**, **10 trang giao diện** (offscreen) và các lỗi do nhóm kiểm tra tìm ra (`tests/test_hardening.py`).
- **Đo thật với khoá Google AI Studio (02/10/2026)**: liệt kê 44 model; gọi thường chạy (200); `google_search` bám nguồn bị **429 trên mọi model** (gói miễn phí) → theo quyết định người dùng, Gemini **bắt buộc bám nguồn** (`gemini_require_grounding`): không bám được thì nguồn bị loại, Claude không làm thay, khảo sát rỗng thì lần chạy dừng. Muốn chạy được cần bật thanh toán/hạn mức tìm kiếm Google rồi bấm "Kiểm tra khóa" ở mục Gemini.
- **Chưa có một lần chạy luồng trọn vẹn nào** với pipeline hiện tại: chưa đo chi phí/thời gian một kịch bản, chưa biết gói Claude có chịu nổi 20 tin/ngày, `max_cost_usd_per_day: 1` và `daily_quota: 1` trong `flows.yaml` vẫn là giá trị thử (chắc chắn quá thấp). Lần chạy thật 01/10 từng bỏ dở (treo, tốn $1,16); lần 02/10 chết vì đua làm mới token OAuth — B4 đã thêm thử lại lùi dần + khởi động ấm nhưng **chưa kiểm bằng lần chạy thật**.
- **Hạn chế đã biết (chưa sửa)**: nghiệm thu bám nguồn khớp theo **tên miền** (URL Gemini trả là chuyển hướng) nên URL bịa trên miền đã được bám vẫn lọt; `published_at` do model tự khai; timeout không dừng được luồng Gemini đang chạy (`to_thread`); scoring.py (đòi evidence) chưa được pipeline gọi, việc "từ chối chấm" dựa vào prompt agent 07; chuỗi trạng thái dựng lúc chạy chưa dịch English.
- **Chưa gửi Telegram thật** (`TELEGRAM_*` trống, chỉ kiểm bằng transport giả); **chưa đăng ký tác vụ Windows** (`scripts/register_task.ps1`).
- **Chưa có**: connector số liệu thật (YouTube Data API, Trends, RSS — `agnet/connectors/` rỗng), Analytics Learner, embedding/pgvector. Google Trends và TikTok Creative Center không có API chính thức.
- Nhân vật KOC mới có **chữ** (`status: draft`); chưa có ảnh gốc/bảng 9 ảnh nên chưa bật được cho luồng thật.
- Chốt `script.json` với phần mềm dựng video thật **trước** khi đầu tư thêm phần xuất (schema chưa đổi trong đợt này).
- **Bảo mật**: agent đọc web không có Bash, không agent nào có Write/Edit (cả hai bị `load_agents` chặn); khoá Gemini chỉ ở `.env` (ghi nguyên tử, 0600), che trong log. Khoá dùng thử đã xuất hiện trong cuộc trò chuyện — nên thu hồi và tạo khoá mới.
