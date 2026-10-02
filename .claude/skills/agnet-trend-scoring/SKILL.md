---
name: agnet-trend-scoring
description: "Chấm Trend Score 0–100 cho đề tài Agnet bằng số liệu thật có nguồn, từ chối chấm khi thiếu dữ liệu; gom cụm, chống trùng 30 ngày, chọn top đề tài theo sản lượng. Dùng khi phân tích xu hướng, xếp hạng hoặc chọn đề tài."
---

# Agnet — Chấm điểm & chọn đề tài

**Nguyên tắc số một: không bịa số.** Trend Score chỉ có giá trị khi mỗi thành phần dựa trên dữ liệu có thật. `WebSearch` **không** trả về view/giờ hay chỉ số rising queries — nếu thiếu số liệu, thành phần đó phải được ghi là thiếu và đề tài **bị loại khỏi xếp hạng**, không được "ước lượng cho đủ".

## Công thức (trọng số ở `config/scoring.yaml`, tổng = 1)

```
TrendScore = 0.22·Velocity      tốc độ tăng 24–72h
           + 0.18·Volume        quy mô quan tâm/tìm kiếm
           + 0.15·Engagement    tương tác trên video/bài cùng đề tài
           + 0.15·Gap           khoảng trống: ít video chất lượng / bình luận chưa được trả lời
           + 0.10·Audience Fit  khớp đối tượng & chủ đề luồng
           + 0.08·Evergreen     còn giá trị sau 30 ngày
           + 0.07·Impact        ảnh hưởng tới đời sống/tiền/sức khỏe người xem
           + 0.05·Source Trust  độ tin cậy nguồn gốc
```

Luồng `mode: breaking` dùng bộ trọng số `breaking_overrides` (ưu tiên Velocity).

## Mỗi thành phần phải có `evidence`

Đầu vào chấm là danh sách `{story_id, components: {tên: {value 0–100, evidence}}}`. `evidence` là nguồn cụ thể: URL, tên API + chỉ số, hoặc ghi chú đo được ("Trends VN 7 ngày: +240%"). Chuỗi rỗng bị code từ chối.

Cách quy đổi số liệu thô → 0–100 (ghi cách quy đổi vào evidence):

| Thành phần | Dữ liệu thô nên dùng | Gợi ý quy đổi |
|---|---|---|
| Velocity | % tăng truy vấn 24–72h; view/giờ của video mới | so với phân vị của cùng chủ đề trong 30 ngày |
| Volume | lượng tìm kiếm tương đối; tổng view cụm video | thang log, so với đề tài khác cùng luồng |
| Engagement | (like+comment)/view của video top | so với trung bình kênh/chủ đề |
| Gap | số video chất lượng cao; số bình luận hỏi chưa ai trả lời | nhiều câu hỏi mở + ít video tốt = cao |
| Audience Fit | khớp `audience`, `seed_keywords`, `exclude_keywords` | loại hẳn nếu dính `exclude_keywords` |

## Chạy chấm bằng code

```python
from agnet.core import scoring
w = scoring.load_weights("config/scoring.yaml", breaking=False)
ranked = scoring.rank(items, w, top_n=15)   # tự loại đề tài thiếu thành phần
```

## Quy trình chọn đề tài

1. Mỗi scout trả `RawItem {title, url, source, published_at, metrics, snippet, lang}` — nguồn lỗi thì bỏ qua, ghi log, không dừng pipeline.
2. **Gom cụm** thành "Story"; mỗi Story giữ danh sách RawItem làm bằng chứng.
3. **Chống trùng**: `python -m agnet dedup "<tiêu đề đề tài>"` (30 ngày, dùng chung mọi luồng). Trùng thì loại.
4. Chấm điểm, lấy **top = `daily_quota × 1.5`** (lấy dư để bù phần QA loại).
5. Khoá đề tài đã chọn: `python -m agnet claim <flow_id> "<tiêu đề>"` — `exit 1` nghĩa là luồng khác đã lấy, bỏ đề tài này.
6. Luồng `breaking`: chỉ giữ đề tài có điểm ≥ `min_trend_score`.

## Khi thiếu sản lượng (< quota)

1. Lấy tiếp hạng 16–25 · 2. Kho evergreen (câu hỏi cộng đồng tích luỹ, long-tail ổn định) · 3. Remix đề tài thắng cũ với góc mới (series, phần 2, so sánh, giải đáp bình luận). **Không hạ ngưỡng QA để đủ số.**

## Báo cáo

Với mỗi đề tài chọn/loại ghi: điểm, thành phần mạnh/yếu, `evidence`, lý do loại. Đây là nội dung mục "Lý do chọn" trong `script.md` và `_BAO_CAO_NGAY.md`.
