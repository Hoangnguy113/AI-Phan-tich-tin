---
name: agnet-flow-config
description: "Đọc và áp dụng cấu hình Luồng (flows.yaml) của Agnet — chủ đề, nền tảng, tỉ lệ khung hình, thời lượng, wpm theo ngôn ngữ, ngân sách, kiểm soát nhạy cảm. Dùng khi tạo/sửa luồng, hoặc khi agent cần biết luật của một luồng trước khi làm việc."
---

# Agnet — Cấu hình Luồng

Luồng là đơn vị chạy. Một chủ đề có thể có nhiều luồng (vd sáng YouTube 12 phút, chiều TikTok 3 phút). Mỗi luồng chạy độc lập.

## Luôn làm đầu tiên

```
python -m agnet flows        # kiểm tra + liệt kê luồng; sai cấu hình sẽ báo lỗi cụ thể
```

Đọc `config/flows.yaml`, lấy đúng luồng theo `flow_id` trong yêu cầu. **Không suy đoán** giá trị thiếu — đã có mặc định trong code (`agnet/core/models.py`).

## Các trường & ràng buộc (được code kiểm)

| Nhóm | Trường | Ràng buộc |
|---|---|---|
| Định danh | `id`, `name`, `enabled` | `id` chỉ chữ/số/`-`/`_`, duy nhất |
| Chủ đề | `topic`, `seed_keywords`, `exclude_keywords` | từ khoá loại trừ là **loại hẳn** |
| Đối tượng | `audience`, `region`, `language` | |
| Nền tảng | `platform` | `youtube` · `tiktok` · `facebook` |
| Khung hình | `aspect_ratio` | mặc định 16:9 / 9:16 / 4:5 theo nền tảng |
| Thời lượng | `duration_min`, `duration_max`, `duration_mix` | trong 3–20 phút; tổng `duration_mix` = `daily_quota` |
| Sản lượng | `daily_quota` | mặc định 10 |
| Lịch | `schedule` (cron), `timezone`, `mode`, `interval_hours`, `min_trend_score` | `breaking` cần `interval_hours`; `scheduled` bật phải có cron |
| Ngôn ngữ | `language`, `output_language`, `source_languages`, `review_translation`, `wpm` | `wpm` mặc định: vi 160 · de 140 · en 150 |
| Phong cách | `tone`, `narrator_persona`, `cta_style`, `brand_rules` | |
| Tiêu đề | `title_style` | `curiosity` · `rumor_check` · `neutral` |
| Kiểm soát | `strict_factcheck`, `sensitive`, `human_review` | **`sensitive: true` bắt buộc `human_review: true`** |
| Nhân vật | `entity_type`, `privacy_guard`, `koc.*` | `koc.enabled` cần `koc.character_id`; `human_scene_ratio` 25–40% |
| Ngân sách | `max_tokens_per_run`, `max_cost_usd_per_day` | vượt thì dừng + báo |
| Đầu ra | `output_dir`, `webhook_url`, `notify` | `notify: [telegram]` để báo khi chạy xong |
| Chạy tự động | `catchup`, `catchup_until`, `run_timeout_min` | máy tắt đúng giờ cron → bù nếu còn trước `catchup_until` (giờ của `timezone`); quá `run_timeout_min` phút thì dừng cứng |

## Hệ quả cho từng agent

- **Tốc độ đọc**: luôn dùng `wpm` của luồng khi tính từ/thời lượng — đừng dùng bảng tiếng Việt cho luồng tiếng Đức.
- **Ngôn ngữ**: kịch bản viết bằng `output_language`; nếu có `review_translation`, mỗi cảnh thêm `voiceover_review` bản dịch để người duyệt đọc. Nguồn tìm bằng `source_languages`.
- **Nhạy cảm** (`sensitive`/y tế/tài chính/pháp luật): Fact-checker bắt buộc, thêm câu miễn trừ, `qa.human_review_required = true`, nhân vật KOC **không** được giới thiệu là bác sĩ/dược sĩ/luật sư/chuyên gia có chứng chỉ.
- **Luồng `breaking`**: ưu tiên Velocity, chỉ nhận đề tài đạt `min_trend_score`.

## Tạo luồng mới

1. Sao chép một luồng gần nhất trong `config/flows.yaml`, đổi `id`/`name`.
2. Chạy `python -m agnet flows` — sửa đến khi hết lỗi.
3. Khi `sensitive`, đừng bao giờ tắt `human_review` để cho nhanh.
4. Ví dụ luồng tiếng Đức: `output_language: de`, `source_languages: [de, en]`, `review_translation: vi`.

Chi phí thực tế phải đo ở lần chạy đầu rồi mới chốt `max_cost_usd_per_day` và `daily_quota` — đừng hứa trước.
