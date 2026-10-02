---
name: agnet-hook-title
description: "Tạo hook 0–5 giây, tiêu đề gây tò mò có kiểm soát (kể cả tiêu đề ngược \"tin đồn – kiểm chứng\"), thumbnail, mô tả SEO, hashtag, chapter cho video Agnet; có danh sách cấm để không giật tít sai sự thật. Dùng khi viết hoặc duyệt tiêu đề, hook, đóng gói video."
---

# Agnet — Hook & Tiêu đề

Mục tiêu: **gây tò mò mà vẫn đúng sự thật**. Tiêu đề hay mà sai bị nền tảng phạt, mất lòng tin, có thể vi phạm pháp luật về danh dự.

## Đầu ra mỗi kịch bản

- **5 hook** 0–5 giây (dùng cho A/B)
- **5 tiêu đề**, mỗi tiêu đề kèm `technique` và **`truth_check`** (đối chiếu sự thật, bắt buộc — thiếu thì `validate` chặn)
- **3 ý tưởng thumbnail/cover**
- Mô tả SEO, tag/hashtag, chapter (YouTube), caption (TikTok/FB), bình luận ghim
- `ai_disclosure: true` nếu có người dẫn do AI tạo (kèm dòng trong mô tả: "Người dẫn trong video là nhân vật do AI tạo.")

## Kỹ thuật được phép

| Kỹ thuật (`technique`) | Ví dụ | Điều kiện |
|---|---|---|
| Mâu thuẫn bất ngờ (`contrast`) | "20 Jahre – und NIE eine Solo-Nr. 1?! Bis zu DIESEM Tag" | **Cả hai vế đều đúng** |
| Câu đố (`riddle`) | "Warum Deutschlands größter Hit NIE auf Platz 1 war" | Video giải đáp được |
| Tin đồn – kiểm chứng (`rumor_check`) | "Helene Fischer & der 16. Oktober – Gerücht oder Wahrheit?" | Tin đồn **có thật, có nguồn**; tiêu đề ở dạng **câu hỏi**; video tách rõ ✅ FAKT / ⚠️ UNBESTÄTIGT / ❌ FALSCH trong 60 giây đầu phân đoạn đó |
| Con số gây sốc (`number`) | "750.000 Menschen, keine Rückseite" | Số liệu có nguồn trong `sources` |
| Trung tính (`plain`) | mô tả thẳng nội dung | — |

Luồng `title_style`: `curiosity` (mặc định các kỹ thuật trên) · `rumor_check` (ưu tiên tin đồn – kiểm chứng) · `neutral` (chỉ `plain`/`number`).

## CẤM — QA loại ngay

- Khẳng định điều **sai** về người thật, nhất là đời tư, sức khỏe, con cái, hôn nhân, qua đời. (Ví dụ cấm: "X đã sinh con" khi chưa có; "X chưa có con" khi đã có.)
- **Tự bịa tin đồn** để rồi "bác bỏ" nó. Tin đồn phải có thật và có nguồn.
- Tiêu đề hoặc thumbnail **mâu thuẫn** với nội dung.
- Nêu điều chưa xác minh như sự thật.

`entity_type: person` → bật `privacy_guard`: không suy đoán đời tư, không bịa lời trích dẫn.

## Hook 0–5 giây

Cụ thể và có hình: số liệu gây sốc / câu hỏi đúng nỗi đau / kết quả nói trước. Không chào hỏi dài. Ba con số trong 5 giây (pattern interrupt) hoạt động tốt; sau đó đặt câu hỏi lớn của video ở ~15–20s và nêu lộ trình xem.

## Theo nền tảng

| | YouTube | TikTok | Facebook |
|---|---|---|---|
| Đóng gói | Tiêu đề SEO, mô tả, chapter, tag | Caption ngắn + 3–5 hashtag | Caption mở bằng câu hỏi |
| Hook | 0–5s có lời hứa giá trị | 0–2s hình/chữ gây sốc | 0–3s chữ to (tắt tiếng) |

## Bản đồ giữ chân

Xuất một bảng "thời điểm → kỹ thuật" (pattern interrupt · curiosity gap · open loop · re-hook · payoff · callback · CTA). Mỗi open loop phải có điểm đóng.

## Tự kiểm trước khi giao

1. Mỗi tiêu đề đọc lại cùng `truth_check`: có thể chứng minh bằng `sources` không?
2. Thumbnail có hứa điều video không làm không?
3. Có tên người thật + đời tư/sức khỏe → gắn cờ `human_review`.
