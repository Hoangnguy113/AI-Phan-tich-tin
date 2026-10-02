---
name: agnet-script-director
description: "Viết kịch bản đạo diễn video 3–20 phút cho dự án Agnet — chọn khung kịch bản, viết theo phân đoạn với ngân sách từ, chia cảnh/shot, xuất script.md + script.json đúng hợp đồng. Dùng khi viết, chia cảnh hoặc sửa kịch bản video theo luồng."
---

# Agnet — Viết kịch bản đạo diễn

Đầu ra duy nhất của Agnet là **kịch bản đạo diễn**: `script.md` (người đọc) + `script.json` (phần mềm dựng đọc). Không dựng video, không TTS.

## Quy trình bắt buộc

1. **Đọc luồng**: nền tảng, ngôn ngữ đầu ra, `wpm`, thời lượng mục tiêu, `tone`, `narrator_persona` (skill `agnet-flow-config`).
2. **Tính ngân sách từ bằng lệnh, không tự nhẩm**:
   `python -m agnet budget --minutes <phút> --wpm <wpm> --weights <trọng số phân đoạn>`
3. **Chọn khung** (bảng dưới) theo đề tài và độ sâu.
4. **Viết TỪNG PHÂN ĐOẠN** (1–3 phút/phân đoạn) đúng ngân sách từ; sau mỗi phân đoạn ghi "bản tóm tắt chạy" 3 dòng (đã nói gì, vòng tò mò đang mở, callback đã gieo) để phân đoạn sau giữ mạch.
5. **Chia cảnh**: mỗi cảnh một ý, `duration_sec = số từ ÷ (wpm/60) + nghỉ` — lấy bằng `python -m agnet count --wpm <wpm>`.
6. **Xuất `script.json` rồi chạy** `python -m agnet validate <file> --flow <id>`. Còn `[ERROR]` thì sửa, **không** báo hoàn thành.

## Khung kịch bản

| Khung | Phù hợp | Cấu trúc |
|---|---|---|
| Giải thích | Tin nóng, khái niệm mới | Hook → Bối cảnh → Chuyện gì xảy ra → Vì sao → Ảnh hưởng tới bạn → Nên làm gì → CTA |
| Danh sách (Top N) | Mẹo, sai lầm, xu hướng | Hook → Lời hứa → N mục (đếm ngược, mục hay nhất cuối) → Tổng kết → CTA |
| Vấn đề – Giải pháp | Sức khỏe, tài chính, kỹ năng | Hook nỗi đau → Hậu quả → Nguyên nhân gốc → Giải pháp từng bước → Bằng chứng → CTA |
| Kể chuyện | Nhân vật, sự kiện, case study | Hook giữa cao trào → Bối cảnh → Xung đột → Bước ngoặt → Kết quả → Bài học |
| Điều tra / Phân tích sâu | 15–20 phút, chủ đề lớn | Hook bí ẩn → Câu hỏi lớn → Các lớp bằng chứng → Phản biện → Kết luận → Hàm ý |
| Hỏi đáp | Từ câu hỏi cộng đồng | Hook câu hỏi → 5–10 câu hỏi thật → trả lời ngắn gọn có nguồn |
| So sánh / Tranh luận | Sản phẩm, phương pháp | Hook "A hay B?" → Tiêu chí → So từng tiêu chí → Kết luận cho từng nhóm người |
| Lật mặt lầm tưởng | Tin đồn, hiểu sai phổ biến | Hook lầm tưởng → Vì sao ai cũng tin → Sự thật + bằng chứng → Nên hiểu đúng thế nào |

## Quy tắc giữ chân người xem (bắt buộc)

- **0–5s**: hook cụ thể (số liệu gây sốc / câu hỏi đúng nỗi đau / kết quả trước). Không chào hỏi dài dòng.
- **5–30s**: nêu rõ lời hứa giá trị — "xem hết bạn sẽ biết…".
- **Re-hook** mỗi 45–90 giây (vòng tò mò mới).
- **Đổi hình** mỗi 3–6s (TikTok 1,5–3s).
- **Mỗi phân đoạn** ≥ 1 ví dụ cụ thể hoặc số liệu.
- **CTA** tự nhiên ở khoảng 60–70% thời lượng và ở cuối.
- Mọi vòng tò mò mở phải được **trả lời** trong video (mở ở đâu, đóng ở đâu ghi vào "Bản đồ giữ chân").

## Số từ theo thời lượng (≈150–170 từ/phút tiếng Việt)

| Phút | Từ | Phân đoạn | Cảnh |
|---|---|---|---|
| 3 | 450–510 | 3–4 | 30–45 |
| 5 | 750–850 | 4–5 | 50–75 |
| 10 | 1.500–1.700 | 6–8 | 100–150 |
| 15 | 2.250–2.550 | 8–10 | 150–220 |
| 20 | 3.000–3.400 | 10–12 | 200–300 |

Với tiếng Đức (140 wpm) hay tiếng Anh (150 wpm) **luôn dùng `wpm` của luồng**, đừng dùng bảng này.

## Khác biệt theo nền tảng

| | YouTube | TikTok | Facebook |
|---|---|---|---|
| Tỉ lệ | 16:9 | 9:16 | 4:5 / 1:1 (feed), 9:16 (Reels) |
| Nhịp đổi cảnh | 3–6s | 1,5–3s | 3–5s |
| Hook | 0–5s, có lời hứa giá trị | 0–2s, hình/chữ gây sốc ngay | 0–3s, chữ to (nhiều người tắt tiếng) |
| Chữ trên màn hình | Nhấn ý chính | Phụ đề toàn bộ + chữ lớn | Phụ đề toàn bộ bắt buộc |
| Cấu trúc | Chapter, re-hook 60–90s | Chia "Phần 1/2/3" nếu > 3 phút | Kể chuyện cảm xúc, dễ chia sẻ |

## Mỗi cảnh phải có (để phần mềm dựng không phải đoán)

`id` (S{đoạn}.{cảnh}) · `start_sec` · `duration_sec` · `voiceover` · `visual.type` + `description` (+ `search_keywords`, `ai_image_prompt`, `camera`) · `overlay` · `transition_out` · `sfx` · `source_ids` cho mọi câu có số liệu/khẳng định.

`visual.type` hợp lệ: `broll · stock · ai_image · motion_graphic · chart · text_card · editorial_photo · montage · avatar · koc`.

## Đầu ra

Thư mục: `output/<YYYY-MM-DD>/<flow_id>/<NN>_<slug>/` gồm `script.md · script.json · voiceover.txt · sources.md · packaging.md` (+ `koc_prompts.json` khi bật KOC).

`script.md` mở đầu bằng khối thông tin: luồng, nền tảng, thời lượng, **số từ @ wpm**, số phân đoạn/cảnh, khung, Trend Score, lời hứa giá trị, lý do chọn; rồi **Bản đồ giữ chân** (thời điểm → kỹ thuật); rồi từng phân đoạn dạng bảng cảnh. Kết thúc bằng "Ghi chú đạo diễn" (nhạc, màu, cảnh báo/miễn trừ).

Schema đầy đủ: `schemas/script.schema.json`. Tham chiếu mẫu thật: `Claude outputs/script.md`.

## Không bao giờ

- Tự nhẩm thời lượng/số từ — dùng `python -m agnet count/budget`.
- Bịa số liệu, trích dẫn, lời nói của người thật. Thiếu nguồn → bỏ câu đó hoặc ghi "chưa xác minh" và để Fact-checker xử lý.
- Viết cả kịch bản 20 phút trong một lượt — luôn theo phân đoạn.
