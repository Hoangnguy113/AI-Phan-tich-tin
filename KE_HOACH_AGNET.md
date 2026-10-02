# KẾ HOẠCH DỰ ÁN AGNET
## Hệ thống đa agent tự động săn xu hướng & viết kịch bản đạo diễn video (3–20 phút)

> Phiên bản: 1.2 — 02/10/2026 (mục 18: Claude chỉ huy, Gemini thực thi, 20 tin/ngày, giao diện desktop; mục 17: KOC Studio)
> Thư mục dự án: `D:\DEV\Agnet`
> Đầu ra duy nhất: **Kịch bản đạo diễn chi tiết** (bản đọc cho người + bản JSON cho phần mềm dựng video)

---

## 0. Tóm tắt điều hành

| Hạng mục | Quyết định |
|---|---|
| Chủ đề | Không cố định — người dùng tạo trong **Cài đặt Luồng** (Flow), mỗi luồng có giờ chạy riêng |
| Nền tảng | YouTube / TikTok / Facebook — chọn trong cài đặt từng luồng, ảnh hưởng tới văn phong, tỉ lệ khung hình, nhịp |
| Sản lượng | **20 tin/ngày** (v1.2; người dùng đặt trong giao diện, 1–50). Bản gốc: tối thiểu 10 kịch bản/chủ đề/ngày |
| Thời lượng | **3–20 phút** mỗi kịch bản (cấu hình theo luồng) |
| Đầu ra | `script.md` (người đọc) + `script.json` (máy đọc, phần mềm dựng video nhập trực tiếp) |
| Không làm | Dựng video, TTS, render — giao cho phần mềm khác |
| Số agent | 17 agent, 6 tầng (+ tầng học) |
| Người dẫn | Nhân vật **KOC AI siêu thực** cố định theo luồng; prompt 3 lớp dùng chung cho mọi nhân vật (mục 17) |
| Công nghệ | Python · Claude (đăng nhập tài khoản, không cần API key) · **Gemini** (khảo sát & tìm kiếm mạng) · APScheduler · SQLite · **ứng dụng desktop PySide6** (v1.2; Web UI ở mục 12 là phương án cũ) |

---

## 1. Mục tiêu & tiêu chí thành công

1. **Đúng xu hướng**: mỗi đề tài có bằng chứng xu hướng (điểm Trend Score ≥ ngưỡng, có dữ liệu tăng trưởng 24–72h).
2. **Người xem cần**: trả lời câu hỏi thật người dùng đang tìm (từ autocomplete, bình luận, "People also ask").
3. **Có giá trị & ảnh hưởng**: mỗi kịch bản có ≥ 3 insight cụ thể, ≥ 2 số liệu có nguồn, có hành động người xem làm được.
4. **Chính xác**: mọi luận điểm quan trọng có ≥ 2 nguồn độc lập; nội dung nhạy cảm gắn cờ duyệt tay.
5. **Đủ chi tiết để dựng tự động**: mỗi cảnh có lời thoại, thời lượng, hình ảnh/B-roll, chữ trên màn hình, chuyển cảnh, âm thanh.
6. **Đủ sản lượng**: ≥ 10 kịch bản đạt QA ≥ 8/10 mỗi chủ đề mỗi ngày.

**KPI hệ thống**: tỉ lệ đạt QA lần 1 ≥ 70% · sai lệch thời lượng ≤ ±10% · 0 lỗi thông tin bị phát hiện sau đăng · retention trung bình tăng theo tháng (nhờ vòng học).

---

## 2. Kiến trúc tổng thể

```
                         ┌───────────────────────────────┐
                         │  WEB UI CÀI ĐẶT (FastAPI)     │
                         │  Luồng · Chủ đề · Nền tảng ·  │
                         │  Giờ chạy · Thời lượng · Nguồn│
                         └──────────────┬────────────────┘
                                        │ flows (DB)
                         ┌──────────────▼────────────────┐
                         │  SCHEDULER (APScheduler)      │
                         │  cron theo từng luồng         │
                         └──────────────┬────────────────┘
                                        │ khởi chạy run_id
 ┌──────────────────────────────────────▼──────────────────────────────────────┐
 │                       ORCHESTRATOR (LangGraph)                              │
 │                                                                             │
 │  T1 ĐIỀU TRA  →  T2 PHÂN TÍCH  →  T3 CHIẾN LƯỢC  →  T4 NGHIÊN CỨU SÂU        │
 │  (5 scout       (gom cụm,        (góc tiếp cận,    (fact-check,             │
 │   song song)     chấm điểm,       cấu trúc,         tư liệu cho             │
 │                  từ khóa)         thời lượng)       từng phần)              │
 │                                                        ↓                    │
 │  T6 KIỂM SOÁT  ←────────────  T5 SÁNG TẠO  ←───────────┘                    │
 │  (QA, chính sách,             (Outline → Viết theo phân đoạn →              │
 │   kiểm thời lượng)             Đạo diễn → KOC nhân vật → Hook)              │
 │        │  <8/10: trả về T5 (tối đa 2 vòng)                                  │
 │        ▼                                                                    │
 │  XUẤT: script.md + script.json + báo cáo ngày                               │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
             ┌──────────────────────────┼─────────────────────────┐
             ▼                          ▼                         ▼
     Thư mục output/            Webhook/API cho              Telegram / Sheets
     (phần mềm dựng đọc)        phần mềm dựng video          (thông báo, theo dõi)
                                        │
                         ┌──────────────▼────────────────┐
                         │  T7 HỌC (Analytics Learner)   │
                         │  số liệu video thật → chỉnh   │
                         │  trọng số & prompt            │
                         └───────────────────────────────┘
```

---

## 3. Mô hình cài đặt: "Luồng" (Flow)

Luồng là đơn vị chạy. Một chủ đề có thể có nhiều luồng (ví dụ: luồng sáng cho YouTube 12 phút, luồng chiều cho TikTok 3 phút). Mỗi luồng chạy độc lập và song song.

### 3.1 Các trường cấu hình

| Nhóm | Trường | Ví dụ / Ghi chú |
|---|---|---|
| Định danh | `name`, `enabled` | "Sức khỏe – YouTube sáng" |
| Chủ đề | `topic`, `seed_keywords`, `exclude_keywords` | "dinh dưỡng", loại trừ "thuốc kê đơn" |
| Đối tượng | `audience`, `region`, `language` | "30–55 tuổi, VN", `vi` |
| Nền tảng | `platform` | `youtube` / `tiktok` / `facebook` |
| Định dạng | `aspect_ratio` | 16:9 (YouTube), 9:16 (TikTok/Reels), 1:1/4:5 (FB feed) |
| Thời lượng | `duration_min`, `duration_max`, `duration_mix` | 3–20 phút; mix: `{3-5: 4, 8-12: 4, 15-20: 2}` |
| Sản lượng | `daily_quota` | mặc định 10 |
| Lịch | `schedule` (cron, nhiều mốc), `timezone` | `["30 5 * * *", "0 17 * * *"]`, `Asia/Bangkok` |
| Nguồn | `sources` (bật/tắt từng scout, RSS riêng, tài khoản nội bộ) | trends, youtube, tiktok_cc, rss, reddit, domain, internal |
| Phong cách | `tone`, `narrator_persona`, `cta_style`, `brand_rules` | "chuyên gia gần gũi", "xưng mình – bạn" |
| Kiểm soát | `strict_factcheck`, `sensitive`, `human_review` | true cho y tế/tài chính/pháp luật |
| Ngôn ngữ | `output_language`, `source_languages`, `review_translation`, `wpm` | `de` (kịch bản tiếng Đức), nguồn `[de, en]`, kèm dịch `vi` để duyệt; tốc độ đọc theo ngôn ngữ: vi 160, de 140, en 150 từ/phút |
| Tiêu đề | `title_style` | `curiosity` (gây tò mò) / `rumor_check` (tin đồn – kiểm chứng) / `neutral`, xem mục 7A |
| Nhân vật | `entity_type`, `privacy_guard` | `person`: không suy đoán đời tư, không bịa lời trích dẫn |
| Ngân sách | `max_tokens_per_run`, `max_cost_usd_per_day` | dừng an toàn khi vượt |
| Đầu ra | `output_dir`, `webhook_url`, `notify` | `D:\DEV\Agnet\output`, Telegram |
| Chế độ | `mode` | `scheduled` / `breaking` (quét mỗi N giờ, chỉ lấy tin điểm ≥ 85) |

### 3.2 Ví dụ `flows.yaml` (cũng có thể sửa qua UI)

```yaml
flows:
  - id: suckhoe-yt-sang
    name: "Sức khỏe – YouTube sáng"
    enabled: true
    topic: "Sức khỏe & dinh dưỡng thường thức"
    seed_keywords: ["tiểu đường", "huyết áp", "giấc ngủ", "ăn uống lành mạnh"]
    exclude_keywords: ["quảng cáo thuốc"]
    audience: "Người 30–55 tuổi tại Việt Nam, quan tâm phòng bệnh"
    platform: youtube
    aspect_ratio: "16:9"
    duration_min: 3
    duration_max: 20
    duration_mix: {"3-5": 3, "8-12": 5, "15-20": 2}
    daily_quota: 10
    schedule: ["30 5 * * *"]
    timezone: Asia/Bangkok
    sources: [google_trends, youtube, rss_vn, pubmed, who, moh]
    tone: "Chuyên gia gần gũi, dễ hiểu, có số liệu"
    narrator_persona: "Bác sĩ trẻ, xưng 'mình', gọi 'bạn'"
    strict_factcheck: true
    sensitive: true
    human_review: true
    max_cost_usd_per_day: 8

  - id: ai-tiktok-chieu
    name: "Công nghệ AI – TikTok chiều"
    platform: tiktok
    aspect_ratio: "9:16"
    duration_min: 3
    duration_max: 5
    daily_quota: 10
    schedule: ["0 16 * * *"]
    mode: scheduled

  - id: ai-tin-nong
    name: "AI – Tin nóng"
    platform: youtube
    mode: breaking
    interval_hours: 3
    min_trend_score: 85
    daily_quota: 3
```

---

## 4. Đội hình 17 agent

### Tầng 1 — ĐIỀU TRA (chạy song song)

| # | Agent | Nguồn & nhiệm vụ | Model |
|---|---|---|---|
| 1 | **Trend Scout** | Google Trends (VN, 24h/7 ngày, rising queries), Google/YouTube autocomplete | Haiku |
| 2 | **Video Platform Scout** | YouTube Data API (trending, tìm theo từ khóa, video mới nhiều view/giờ), TikTok Creative Center (hashtag, bài hát, chủ đề đang lên), Facebook (trang/nhóm công khai qua API được phép) | Haiku |
| 3 | **News Scout** | RSS báo VN (VnExpress, Tuổi Trẻ, Thanh Niên, Dân trí, VietnamNet, CafeF…), Google News, báo quốc tế (Reuters, BBC…) | Haiku |
| 4 | **Community Scout** | Bình luận YouTube/TikTok của video top, Reddit, diễn đàn, "People also ask" → **câu hỏi thật của người xem** | Haiku |
| 5 | **Domain & Internal Scout** | Nguồn chuyên ngành theo chủ đề (PubMed, WHO, Bộ Y tế, Tổng cục Thống kê, Ngân hàng NN…) + hệ thống nội bộ (Google Drive, Notion, Sheets, email, CSDL) + **kênh đối thủ** người dùng khai báo | Haiku |

> Mỗi scout chuẩn hóa về một định dạng `RawItem {title, url, source, published_at, metrics, snippet, lang}`.

### Tầng 2 — PHÂN TÍCH

| # | Agent | Nhiệm vụ | Model |
|---|---|---|---|
| 6 | **Dedup & Cluster** | Embedding + gom cụm → "Câu chuyện" (Story); loại đề tài đã làm 30 ngày qua (bộ nhớ vector) | Embedding |
| 7 | **Trend Scorer** | Chấm điểm (mục 5), chọn top `quota × 1.5` | Sonnet |
| 8 | **Keyword Miner** | Từ khóa chính, long-tail, câu hỏi, hashtag theo nền tảng, ý định tìm kiếm | Sonnet |
| 9 | **Competitor Gap Analyst** | Xem 5–10 video top cùng đề tài: họ nói gì, bỏ sót gì, bình luận phàn nàn gì → **khoảng trống để thắng** | Sonnet |

### Tầng 3 — CHIẾN LƯỢC

| # | Agent | Nhiệm vụ | Model |
|---|---|---|---|
| 10 | **Content Strategist** | Mỗi đề tài đề xuất 3 góc tiếp cận → chọn 1; chọn **khung kịch bản** (mục 7), **thời lượng mục tiêu** theo độ sâu đề tài và `duration_mix`; xác định lời hứa giá trị (value promise) | Opus |

### Tầng 4 — NGHIÊN CỨU SÂU

| # | Agent | Nhiệm vụ | Model |
|---|---|---|---|
| 11 | **Deep Researcher** | Với mỗi phần trong dàn ý: gom số liệu, ví dụ, câu chuyện thật, trích dẫn chuyên gia; tạo "hồ sơ tư liệu" | Sonnet |
| 12 | **Fact-checker** | Mỗi luận điểm ≥ 2 nguồn độc lập; phân loại: đã xác minh / chưa chắc / sai → loại bỏ; gắn nguồn vào từng câu | Sonnet |

### Tầng 5 — SÁNG TẠO

| # | Agent | Nhiệm vụ | Model |
|---|---|---|---|
| 13 | **Script Writer** (nhiều instance) | Viết **theo phân đoạn** (mỗi phân đoạn 1–3 phút) để kịch bản 20 phút vẫn sắc nét; giữ mạch bằng "bản tóm tắt chạy" (running summary) | Sonnet |
| 14 | **Director** (Đạo diễn hình ảnh) | Chia lời thoại thành **cảnh/shot**: thời lượng từng shot, loại hình ảnh (B-roll, stock, AI image, đồ họa, biểu đồ, avatar), prompt tìm/sinh hình, chữ trên màn hình, chuyển cảnh, nhạc, SFX, nhịp cắt theo nền tảng | Sonnet |
| 15 | **Hook & Packaging** | 5 hook 0–5s, 5 tiêu đề, 3 ý tưởng thumbnail/cover, mô tả SEO, tag/hashtag, chapter (YouTube), caption (TikTok/FB), ghim bình luận | Sonnet |
| 17 | **KOC Character Director** (Đạo diễn nhân vật) | Chọn cảnh cần mặt người (25–40% số cảnh); sinh prompt ảnh/video nhân vật theo chuẩn `koc-master-1.0` (3 lớp: ADN nhân vật + lớp siêu thực dùng chung + cảnh); giữ phục trang nhất quán trong cùng kịch bản; xuất `koc_prompts.json` — **chi tiết đầy đủ ở mục 17** | Sonnet |

### Tầng 6 — KIỂM SOÁT

| # | Agent | Nhiệm vụ | Model |
|---|---|---|---|
| 16 | **Editor-in-Chief (QA)** | Chấm rubric (mục 9), kiểm thời lượng (đếm từ), kiểm chính sách nền tảng & bản quyền, kiểm trùng với nội dung cũ; < 8/10 → trả về Writer/Director kèm góp ý cụ thể (tối đa 2 vòng) | Opus |

### Tầng 7 — HỌC (chạy hằng ngày, tách khỏi pipeline)

| # | Agent | Nhiệm vụ |
|---|---|---|
| + | **Analytics Learner** | Người dùng nhập/kết nối link video đã đăng → lấy view, CTR, thời gian xem trung bình, retention sau 48h & 7 ngày → điều chỉnh trọng số Trend Score, lưu "hook thắng", "cấu trúc thắng" vào thư viện mẫu để Writer dùng làm few-shot |

---

## 5. Công thức chấm điểm đề tài (Trend Score 0–100)

```
TrendScore = 0.22·Velocity      (tốc độ tăng 24–72h)
           + 0.18·Volume        (quy mô quan tâm/tìm kiếm)
           + 0.15·Engagement    (tương tác trên video/bài cùng đề tài)
           + 0.15·Gap           (khoảng trống: ít video chất lượng / bình luận chưa được trả lời)
           + 0.10·Audience Fit  (khớp đối tượng & chủ đề luồng)
           + 0.08·Evergreen     (còn giá trị sau 30 ngày)
           + 0.07·Impact        (mức ảnh hưởng tới đời sống/tiền/sức khỏe người xem)
           + 0.05·Source Trust  (độ tin cậy nguồn gốc)
```

- Trọng số lưu trong DB, chỉnh được trên UI, và **tự học** qua Analytics Learner.
- Luồng `breaking` ưu tiên Velocity; luồng thường cân bằng giữa trend và evergreen.

---

## 6. Đảm bảo sản lượng ≥ 10 kịch bản/ngày

Mỗi bước lấy dư để bù cho phần bị loại ở bước sau:

```
Thu thập 200–400 RawItem
  → Gom cụm còn 40–60 Story
  → Chấm điểm, chọn top 15 (quota × 1.5)
  → Strategist duyệt 13–15 đề tài
  → Viết 13–15 kịch bản
  → QA: đạt ≥ 10
```

**Cơ chế dự phòng** khi < quota:
1. Lấy tiếp đề tài hạng 16–25.
2. Kho **evergreen** (câu hỏi người xem tích lũy, từ khóa long-tail ổn định).
3. "Remix" đề tài thắng trước đây với góc mới (series, phần 2, so sánh, giải đáp bình luận).

**Bắt đầu sớm**: lịch nên đặt trước giờ cần kịch bản 1,5–2 giờ (pipeline 1 luồng 10 kịch bản dài ước tính 40–90 phút, chạy song song).

---

## 7. Thư viện khung kịch bản (Strategist chọn theo đề tài)

| Khung | Phù hợp | Cấu trúc |
|---|---|---|
| **Giải thích (Explainer)** | Tin nóng, khái niệm mới | Hook → Bối cảnh → Chuyện gì xảy ra → Vì sao → Ảnh hưởng tới bạn → Nên làm gì → CTA |
| **Danh sách (Top N)** | Mẹo, sai lầm, xu hướng | Hook → Lời hứa → N mục (đếm ngược, mục hay nhất cuối) → Tổng kết → CTA |
| **Vấn đề – Giải pháp** | Sức khỏe, tài chính, kỹ năng | Hook nỗi đau → Hậu quả → Nguyên nhân gốc → Giải pháp từng bước → Bằng chứng → CTA |
| **Kể chuyện (Story)** | Nhân vật, sự kiện, case study | Hook giữa cao trào → Bối cảnh → Xung đột → Bước ngoặt → Kết quả → Bài học |
| **Điều tra/Phân tích sâu** | 15–20 phút, chủ đề lớn | Hook bí ẩn → Câu hỏi lớn → Các lớp bằng chứng → Phản biện → Kết luận → Hàm ý |
| **Hỏi đáp (Q&A)** | Từ câu hỏi cộng đồng | Hook câu hỏi gây tò mò → 5–10 câu hỏi thật → trả lời ngắn gọn có nguồn |
| **So sánh / Tranh luận** | Sản phẩm, phương pháp | Hook "A hay B?" → Tiêu chí → So từng tiêu chí → Kết luận cho từng nhóm người |
| **Lật mặt lầm tưởng (Myth busting)** | Tin đồn, hiểu sai phổ biến | Hook lầm tưởng → Vì sao ai cũng tin → Sự thật + bằng chứng → Nên hiểu đúng thế nào |

### Quy tắc giữ chân người xem (bắt buộc)

- **0–5s**: hook cụ thể (số liệu gây sốc / câu hỏi đúng nỗi đau / kết quả trước). Không chào hỏi dài dòng.
- **5–30s**: nêu rõ lời hứa giá trị — "xem hết bạn sẽ biết…".
- **Re-hook** mỗi 45–90 giây (vòng tò mò mới, "nhưng điều quan trọng nhất là…").
- **Đổi hình ảnh** mỗi 3–6 giây (TikTok 1,5–3 giây).
- **Mỗi phân đoạn** có ít nhất 1 ví dụ cụ thể hoặc số liệu.
- **CTA** đặt tự nhiên ở khoảng 60–70% thời lượng và ở cuối.

---

## 7A. Chiến lược tiêu đề gây tò mò & "tiêu đề ngược" (có kiểm soát)

**Được phép (Hook & Packaging agent dùng mặc định):**

| Kỹ thuật | Ví dụ (DE) | Điều kiện |
|---|---|---|
| Mâu thuẫn bất ngờ | "20 Jahre – und NIE eine Solo-Nr. 1?! Bis zu DIESEM Tag" | Cả hai vế đều đúng |
| Câu đố | "Warum Deutschlands größter Hit NIE auf Platz 1 war" | Video giải đáp được |
| Tin đồn – kiểm chứng (tiêu đề ngược) | "Helene Fischer & der 16. Oktober – Gerücht oder Wahrheit?" | Tin đồn **có thật, có nguồn**; tiêu đề ở dạng câu hỏi; video tách rõ ✅ FAKT / ⚠️ UNBESTÄTIGT / ❌ FALSCH trong 60 giây đầu của phân đoạn |
| Con số gây sốc | "750.000 Menschen, keine Rückseite" | Số liệu có nguồn |

**Cấm (QA loại ngay):**

- Khẳng định điều sai về người thật, nhất là đời tư, sức khỏe, con cái, hôn nhân hay qua đời. Ví dụ cấm: "X đã sinh con" khi chưa có, hoặc "X chưa có con" khi đã có.
- Tự bịa tin đồn để rồi "bác bỏ" nó.
- Đặt tiêu đề hoặc thumbnail mâu thuẫn với nội dung.

Lý do cấm: YouTube xử lý "misleading metadata" (gỡ video, cảnh cáo kênh); có rủi ro pháp lý xúc phạm danh dự, nhất là theo luật Đức; và làm mất lòng tin, kéo retention xuống. Mỗi tiêu đề trong `script.json` có trường `truth_check` để QA đối chiếu.

---

## 8. Kiểm soát thời lượng 3–20 phút

| Thời lượng | Số từ tiếng Việt (≈150–170 từ/phút) | Số phân đoạn | Số cảnh (≈) |
|---|---|---|---|
| 3 phút | 450–510 | 3–4 | 30–45 |
| 5 phút | 750–850 | 4–5 | 50–75 |
| 10 phút | 1.500–1.700 | 6–8 | 100–150 |
| 15 phút | 2.250–2.550 | 8–10 | 150–220 |
| 20 phút | 3.000–3.400 | 10–12 | 200–300 |

- Tốc độ đọc (`wpm`) cấu hình được theo giọng đọc thực tế của phần mềm dựng.
- Writer viết **từng phân đoạn** theo ngân sách từ; QA đếm lại tổng, sai lệch > ±10% thì cân chỉnh.
- Mỗi cảnh có `duration_sec` = số từ / (wpm/60) + khoảng nghỉ; tổng các cảnh = thời lượng mục tiêu.

---

## 9. Rubric QA (Editor-in-Chief) — thang 10, đạt ≥ 8

| Tiêu chí | Trọng số | Câu hỏi kiểm tra |
|---|---|---|
| Hook | 15% | 5 giây đầu có khiến người xem ở lại không? |
| Giá trị | 20% | Có ≥ 3 insight cụ thể, hành động làm được? |
| Chính xác | 20% | Mọi số liệu có nguồn? Không có luận điểm chưa xác minh? |
| Cấu trúc & nhịp | 15% | Có re-hook, không lan man, đúng khung? |
| Độc đáo | 10% | Có góc mới so với video đối thủ? |
| Chỉ dẫn đạo diễn | 10% | Mỗi cảnh đủ thông tin để phần mềm dựng không cần đoán? |
| Tuân thủ | 10% | Chính sách nền tảng, bản quyền, không giật tít sai sự thật, không nội dung nhạy cảm vi phạm |

**Loại ngay (không cần chấm)**: thông tin sai · lời khuyên y tế/tài chính nguy hiểm · sao chép nguyên văn > 15% · vi phạm chính sách cộng đồng.

---

## 10. Định dạng đầu ra

### 10.1 Cấu trúc thư mục

```
output/
└─ 2026-10-02/
   └─ suckhoe-yt-sang/
      ├─ _BAO_CAO_NGAY.md            # tổng hợp 10+ kịch bản, điểm, lý do chọn
      ├─ 01_an-sang-sai-cach/
      │  ├─ script.md                # bản đọc cho người
      │  ├─ script.json              # bản máy đọc cho phần mềm dựng
      │  ├─ koc_prompts.json         # prompt ảnh/video nhân vật KOC theo từng cảnh
      │  ├─ voiceover.txt            # lời thoại thuần, đã chia đoạn
      │  ├─ sources.md               # nguồn tham khảo đã kiểm chứng
      │  └─ packaging.md             # tiêu đề, mô tả, tag, thumbnail
      └─ 02_.../
```

### 10.2 Mẫu `script.md` (rút gọn)

```markdown
# [Tiêu đề chính]
- Luồng: Sức khỏe – YouTube sáng | Nền tảng: YouTube 16:9 | Thời lượng: 10:30
- Khung: Vấn đề – Giải pháp | Trend Score: 87 | Từ khóa: "ăn sáng", "đường huyết"
- Lời hứa giá trị: Sau video, người xem biết 5 sai lầm khi ăn sáng và cách sửa.
- Lý do chọn: Tìm kiếm "bỏ bữa sáng" +240% trong 48h; 3 video top không nói về chỉ số GI.

## PHÂN ĐOẠN 1 — HOOK (00:00–00:20)
| Cảnh | Thời gian | Lời thoại (VO) | Hình ảnh / B-roll | Chữ trên màn hình | Chuyển cảnh / Âm thanh |
|---|---|---|---|---|---|
| 1.1 | 00:00–00:04 | "Bữa sáng bạn ăn mỗi ngày có thể đang làm đường huyết tăng gấp đôi." | Cận cảnh bát phở, đồ họa đường huyết vọt lên | **ĐƯỜNG HUYẾT x2?** | Cut nhanh · SFX "whoosh" |
| 1.2 | ... | ... | ... | ... | ... |

## PHÂN ĐOẠN 2 — ...
...
## CTA & KẾT
...
## Ghi chú đạo diễn
- Nhạc nền: lo-fi nhẹ, 90 BPM, giảm 6dB khi có VO
- Màu chủ đạo: xanh lá – trắng
- Cảnh báo: thêm dòng "Nội dung tham khảo, không thay thế tư vấn y tế"
```

### 10.3 Schema `script.json` (hợp đồng với phần mềm dựng)

```json
{
  "schema_version": "1.0",
  "id": "2026-10-02_suckhoe-yt-sang_01",
  "flow_id": "suckhoe-yt-sang",
  "platform": "youtube",
  "aspect_ratio": "16:9",
  "language": "vi",
  "target_duration_sec": 630,
  "wpm": 160,
  "title": "5 sai lầm khi ăn sáng khiến đường huyết tăng vọt",
  "hook_variants": ["...", "..."],
  "narrator": {"persona": "Bác sĩ trẻ", "voice_style": "ấm, rõ, tốc độ vừa", "gender": "female"},
  "koc": {"enabled": true, "character_id": "KOC-01-MAI", "wardrobe_set": "oatmeal linen shirt + light jeans", "human_scene_ratio": 0.33, "engines": {"image": "nano_banana_pro", "video": "veo_3"}},
  "music": [{"from_sec": 0, "to_sec": 630, "mood": "lofi calm", "bpm": 90, "duck_under_vo_db": -6}],
  "segments": [
    {
      "id": "S1",
      "name": "Hook",
      "start_sec": 0,
      "end_sec": 20,
      "scenes": [
        {
          "id": "S1.1",
          "start_sec": 0,
          "duration_sec": 4,
          "voiceover": "Bữa sáng bạn ăn mỗi ngày có thể đang làm đường huyết tăng gấp đôi.",
          "emotion": "nghiêm túc, gây chú ý",
          "visual": {
            "type": "broll",
            "description": "Cận cảnh bát phở bốc khói trên bàn gỗ",
            "search_keywords": ["pho bowl closeup", "vietnamese breakfast"],
            "ai_image_prompt": "Close-up of steaming Vietnamese pho bowl, morning light, cinematic, 16:9",
            "camera": "slow push-in"
          },
          "overlay": [{"type": "graphic", "text": "ĐƯỜNG HUYẾT x2?", "position": "center", "style": "bold-red"}],
          "transition_out": "cut",
          "sfx": ["whoosh"],
          "source_ids": ["src_03"]
        }
      ]
    }
  ],
  "cta": [{"at_sec": 420, "text": "Đăng ký kênh để nhận phần 2"}],
  "chapters": [{"at_sec": 0, "title": "Mở đầu"}],
  "packaging": {"titles": [], "description": "", "tags": [], "hashtags": [], "thumbnail_ideas": []},
  "sources": [{"id": "src_03", "title": "...", "url": "...", "verified": true}],
  "qa": {"score": 8.6, "flags": [], "human_review_required": true},
  "trend": {"score": 87, "keywords": [], "evidence": []}
}
```

> Phần mềm dựng chỉ cần đọc `segments[].scenes[]` theo thứ tự: lời thoại → TTS; `visual` → lấy stock/sinh ảnh; `overlay` → chữ; `transition_out`, `sfx`, `music` → âm thanh và chuyển cảnh. Có thể bổ sung trường theo yêu cầu riêng của phần mềm bạn đang dùng. Cảnh có người dẫn dùng `visual.type = "koc"` kèm khối `visual.koc` — xem mục 17.9.

### 10.4 Khác biệt theo nền tảng (Director tự áp dụng)

| | YouTube | TikTok | Facebook |
|---|---|---|---|
| Tỉ lệ | 16:9 | 9:16 | 4:5 / 1:1 (feed), 9:16 (Reels) |
| Nhịp đổi cảnh | 3–6s | 1,5–3s | 3–5s |
| Hook | 0–5s, có lời hứa giá trị | 0–2s, hình ảnh/chữ gây sốc ngay | 0–3s, chữ to vì nhiều người xem không bật tiếng |
| Chữ trên màn hình | Nhấn ý chính | Phụ đề toàn bộ + chữ lớn | Phụ đề toàn bộ bắt buộc |
| Cấu trúc | Chapter, re-hook mỗi 60–90s | Chia "Phần 1/2/3" nếu > 3 phút | Kể chuyện cảm xúc, chia sẻ được |
| Đóng gói | Tiêu đề SEO, mô tả, chapter, tag | Caption ngắn + 3–5 hashtag | Caption mở đầu bằng câu hỏi |

---

## 11. Công nghệ & cấu trúc dự án

### 11.1 Stack

| Thành phần | Lựa chọn | Lý do |
|---|---|---|
| Ngôn ngữ | Python 3.12 | Hệ sinh thái AI/scraping đầy đủ |
| Điều phối agent | **LangGraph** | Đồ thị trạng thái, vòng lặp QA, chạy song song, checkpoint chạy tiếp khi lỗi |
| LLM | Claude API (Haiku / Sonnet / Opus theo tầng) | Chất lượng viết tiếng Việt tốt; prompt caching giảm chi phí |
| Lập lịch | APScheduler (cron theo luồng, lưu job trong DB) | Đổi giờ trên UI không cần khởi động lại |
| Hàng đợi | Redis + RQ/Celery (giai đoạn 2) | Chạy nhiều luồng song song |
| CSDL | PostgreSQL + pgvector (MVP: SQLite) | Lưu luồng, đề tài, kịch bản; chống trùng bằng vector |
| API & UI | FastAPI + giao diện web (React hoặc HTMX) | Cài đặt luồng, xem/duyệt kịch bản, dashboard |
| Thông báo | Telegram Bot, email | Báo cáo hằng ngày, cảnh báo lỗi |
| Triển khai | Docker Compose; chạy trên máy Windows (Docker Desktop) hoặc VPS | Ổn định, khởi động cùng hệ thống |

### 11.2 Cấu trúc thư mục `D:\DEV\Agnet`

```
Agnet/
├─ README.md
├─ docker-compose.yml
├─ .env.example                 # API keys: ANTHROPIC, YOUTUBE, TELEGRAM...
├─ config/
│  ├─ flows.yaml                # cấu hình luồng (đồng bộ với DB)
│  ├─ sources.yaml              # danh sách RSS, trang nguồn theo chủ đề
│  ├─ scoring.yaml              # trọng số Trend Score
│  ├─ characters.yaml           # nhân vật KOC & nhân vật mặc định của từng luồng
│  ├─ characters/               # identity.json + bộ ảnh tham chiếu + LoRA từng nhân vật
│  └─ prompts/                  # prompt từng agent (versioned)
├─ agnet/
│  ├─ core/                     # models (pydantic), state, config loader
│  ├─ agents/
│  │  ├─ scouts/                # trend, platform, news, community, domain_internal
│  │  ├─ analysis/              # cluster, scorer, keyword, competitor_gap
│  │  ├─ strategy/              # strategist
│  │  ├─ research/              # deep_researcher, fact_checker
│  │  ├─ creative/              # writer, director, koc_director, packaging
│  │  ├─ qa/                    # editor_in_chief
│  │  └─ learning/              # analytics_learner
│  ├─ graph/pipeline.py         # LangGraph workflow
│  ├─ koc/                      # nhân vật KOC: master prompt, adapter, realism engine, QA ảnh
│  ├─ connectors/               # youtube, trends, tiktok_cc, rss, reddit, gdrive, notion, telegram
│  ├─ exporters/                # md, json, voiceover, report
│  ├─ storage/                  # db, vector, cache
│  ├─ scheduler/                # đăng ký cron từ bảng flows
│  └─ api/                      # FastAPI: flows CRUD, runs, scripts, webhook
├─ web/                         # giao diện cài đặt & duyệt
├─ templates/                   # khung kịch bản, few-shot "hook thắng"
├─ tests/                       # unit + test chất lượng đầu ra
└─ output/
```

---

## 12. Giao diện phần mềm (Web UI)

1. **Bảng điều khiển**: số kịch bản hôm nay theo luồng, đạt/chưa đạt, chi phí, lỗi.
2. **Quản lý luồng**: tạo/sửa/nhân bản/tạm dừng; chọn chủ đề, nền tảng, thời lượng, lịch (trình chọn giờ trực quan), nguồn.
3. **Kho kịch bản**: lọc theo ngày/luồng/điểm; xem bản đọc + bảng cảnh; nút **Duyệt / Yêu cầu viết lại (kèm góp ý) / Loại**; tải `.md`, `.json`, `.docx`.
4. **Radar xu hướng**: đề tài đang lên theo chủ đề, kể cả những đề tài chưa được viết.
5. **Hiệu suất**: nhập link video đã đăng → biểu đồ retention, CTR; hệ thống tự học.
6. **Quản lý nhân vật KOC**: xem/sửa ADN nhân vật, bộ ảnh tham chiếu, nút "Sinh lại bảng nhân vật", xem prompt từng cảnh, gán nhân vật cho luồng (mục 17).
6. **Cài đặt chung**: API key, tốc độ đọc (wpm), ngân sách, webhook phần mềm dựng, Telegram.

---

## 13. Chi phí & tối ưu

- **Phân model theo tầng**: Haiku cho thu thập/phân loại (khối lượng lớn), Sonnet cho viết/đạo diễn, Opus chỉ cho Strategist và QA.
- **Prompt caching** cho system prompt, khung kịch bản, few-shot (lặp lại mỗi lần chạy).
- **Batch API** cho các bước không gấp (ví dụ chấm điểm đêm trước) để giảm chi phí.
- **Cache nguồn**: không tải lại bài báo/video đã xử lý.
- **Giới hạn cứng**: `max_cost_usd_per_day` mỗi luồng; vượt thì dừng và báo Telegram.
- Ước tính sơ bộ: vài USD/luồng/ngày cho 10 kịch bản dài; con số thực tế sẽ đo ở giai đoạn 1 và hiển thị trên dashboard.

---

## 14. Rủi ro & kiểm soát

| Rủi ro | Kiểm soát |
|---|---|
| Thông tin sai (đặc biệt y tế, tài chính, pháp luật) | Fact-checker bắt buộc; `strict_factcheck`; cờ `human_review`; câu miễn trừ trách nhiệm |
| Bản quyền / "reused content" | Chỉ tổng hợp, diễn giải; kiểm trùng nguyên văn; nguồn hình ảnh ưu tiên stock có giấy phép hoặc AI |
| Vi phạm điều khoản nền tảng khi thu thập | Ưu tiên API chính thức, RSS, dữ liệu công khai; tôn trọng robots.txt và rate limit |
| Nội dung AI bị đánh giá thấp | Góc nhìn riêng (Gap Analyst), persona nhất quán, ví dụ địa phương Việt Nam; khai báo nội dung AI khi nền tảng yêu cầu |
| Nhân vật AI bị nền tảng gắn cờ hoặc mất tin cậy | Bật nhãn nội dung AI; không mạo danh bác sĩ/chuyên gia; không mô tả gợi dục; nhân vật ≥ 22 tuổi (mục 17.11) |
| Nhân vật "trôi mặt" giữa các video | Ảnh gốc + bảng nhân vật 9 ảnh + consistency lock đặt cuối prompt; rubric ảnh ≥ 8/10; tùy chọn LoRA (mục 17.5, 17.10) |
| API nguồn thay đổi/hỏng | Mỗi scout độc lập, lỗi một nguồn không dừng pipeline; cảnh báo qua Telegram |
| Trùng đề tài giữa các luồng | Bộ nhớ vector dùng chung + khóa đề tài theo ngày |
| Chi phí tăng đột biến | Giới hạn ngân sách theo luồng, theo ngày |

---

## 15. Lộ trình triển khai

| Giai đoạn | Thời gian | Phạm vi | Tiêu chí hoàn thành |
|---|---|---|---|
| **1. MVP** | Tuần 1–2 | 1 luồng (đọc từ YAML); Trend + YouTube + News Scout; Cluster, Scorer, Strategist, Writer theo phân đoạn, Director, QA; xuất `script.md` + `script.json` | Chạy theo giờ, ra ≥ 10 kịch bản 3–20 phút đạt QA |
| **2. Đa luồng** | Tuần 3–4 | Đủ 16 agent lõi; nhiều luồng song song; Fact-checker, Gap Analyst, Community Scout; Postgres + pgvector; Telegram | 3+ luồng chạy đồng thời ổn định 7 ngày |
| **3. Phần mềm hoàn chỉnh** | Tuần 5–6 | Web UI cài đặt luồng/lịch/nền tảng; kho kịch bản + duyệt; webhook cho phần mềm dựng; **KOC Studio**: agent 17, thư viện 5 nhân vật, bộ ảnh tham chiếu, `koc_prompts.json` | Người dùng tự cấu hình không cần sửa file |
| **4. Tự học** | Tuần 7–8 | Analytics Learner, thư viện hook/cấu trúc thắng, tự chỉnh trọng số | Điểm QA và retention tăng theo tuần |
| **5. Mở rộng** | Sau đó | Internal connectors (Drive, Notion…), đa ngôn ngữ, A/B hook, gợi ý lịch đăng tối ưu | Theo nhu cầu |

---

## 16. Việc cần chuẩn bị từ phía người dùng

1. **API key**: Anthropic (Claude), YouTube Data API v3 (Google Cloud), Telegram Bot (tùy chọn).
2. **Định dạng đầu vào của phần mềm dựng video** đang dùng (tên phần mềm, file mẫu nếu có) để khớp `script.json`.
3. **Tốc độ đọc** của giọng TTS (từ/phút) để tính thời lượng chính xác.
4. **Danh sách kênh đối thủ / nguồn tin ưu tiên** cho từng chủ đề (nếu có).
5. **Môi trường chạy**: máy Windows luôn bật (Docker Desktop) hay VPS.
6. **Công cụ sinh hình nhân vật KOC** sẽ dùng và API key tương ứng: ảnh (Nano Banana Pro/Gemini, Midjourney, Flux) và video (Veo 3, Kling) — xem bảng so sánh ở mục 17.6.

---

## 17. KOC STUDIO — Hệ thống nhân vật AI siêu thực

> Mục này là **chuẩn chung** để sinh hình ảnh/video người dẫn (KOC) cho mọi luồng. Một nhân vật được khai báo **một lần** trong `Character Bible`, sau đó mọi cảnh của mọi kịch bản đều dùng lại — nhờ vậy khán giả nhận ra "người quen" và kênh có thương hiệu.

### 17.1 Vì sao cần nhân vật cố định

| Vấn đề của B-roll thuần | Nhân vật KOC giải quyết |
|---|---|
| Không có "mặt" để khán giả nhớ → khó xây kênh | Một khuôn mặt xuyên suốt = thương hiệu |
| Hook 0–3s khó gây chú ý bằng hình stock | Mặt người + mắt nhìn thẳng ống kính giữ người xem tốt hơn |
| Thuê người dẫn cho 10 kịch bản/ngày = bất khả thi | Nhân vật AI chạy không giới hạn, 0 chi phí nhân sự |
| Nội dung dễ bị coi là "AI vô hồn" | Persona nhất quán (giọng, tính cách, bối cảnh) tạo cảm giác thật |

### 17.2 Nguyên lý cốt lõi: prompt 3 lớp

```
   ┌──────────────────────────────────────────────────────────────┐
   │  LỚP A — CHARACTER BIBLE (KHÓA CỨNG, không bao giờ đổi)      │
   │  ADN khuôn mặt · bất đối xứng · dấu hiệu riêng · da · tóc    │
   │  · vật bất ly thân · giọng · tính cách                       │
   └──────────────────────────────────────────────────────────────┘
   ┌──────────────────────────────────────────────────────────────┐
   │  LỚP B — REALISM ENGINE  (DÙNG CHUNG CHO MỌI NHÂN VẬT)       │
   │  Máy ảnh · ống kính · khẩu độ · phim · hạt · quang sai ·     │
   │  quy tắc da · quy tắc sáng · quy tắc bố cục · micro-biểu cảm │
   └──────────────────────────────────────────────────────────────┘
   ┌──────────────────────────────────────────────────────────────┐
   │  LỚP C — SHOT  (ĐỔI THEO TỪNG CẢNH trong script.json)        │
   │  Bối cảnh · ánh sáng cảnh · phục trang · tư thế · biểu cảm · │
   │  cỡ cảnh · đạo cụ · tỉ lệ khung hình theo nền tảng           │
   └──────────────────────────────────────────────────────────────┘
                              ↓
   PROMPT CUỐI = A + B + C + NEGATIVE + CONSISTENCY LOCK (đặt CUỐI)
```

**Hai quy tắc kỹ thuật quan trọng:**

1. **Consistency lock phải ở cuối prompt** — các model ảnh/video đánh trọng số cao cho phần đuôi prompt, nên câu "không được thay đổi khuôn mặt trong ảnh tham chiếu" đặt cuối hiệu quả hơn đặt đầu.
2. **Ảnh tham chiếu > chữ miêu tả** — đừng mong tả mặt bằng lời rồi khuôn mặt tự khớp. Luôn kèm ảnh gốc; phần chữ chỉ để **neo** và **chống trôi**, không để "vẽ lại" mặt. Mô tả mặt quá dài mà lệch ảnh gốc là nguyên nhân số 1 làm nhân vật đổi mặt.

### 17.3 PROMPT TỔNG THỂ — `koc-master-1.0` (dán nguyên, thay 3 chỗ)

Đây là mẫu gốc duy nhất. Agent chỉ điền `identity` (lấy từ thư viện nhân vật), `shot` (lấy từ cảnh trong `script.json`), và `output.aspect_ratio` (theo nền tảng). **Khối `realism_engine` và `negative` giữ nguyên tuyệt đối.**

```json
{
  "prompt_version": "koc-master-1.0",
  "render_target": "image",
  "engine": "nano_banana_pro",
  "output": { "aspect_ratio": "9:16", "resolution": "2K", "count": 1 },

  "identity": {
    "character_id": "KOC-01-MAI",
    "reference_images": ["refs/master_front.png", "refs/sheet_three_quarter.png", "refs/sheet_profile.png"],
    "demographics": "Vietnamese woman, 22 years old, from Hanoi",
    "face_structure": "oval face with a slightly wide forehead, soft jawline, medium-high cheekbones, small chin",
    "asymmetry": "left eyebrow sits about 2mm higher than the right; smile pulls slightly to the left; right eye opens marginally wider",
    "identity_marks": [
      "small flat mole 1cm below the outer corner of the left eye",
      "faint 4mm pale scar through the tail of the right eyebrow",
      "two tiny freckles on the bridge of the nose"
    ],
    "eyes": "dark brown, almond-shaped, thin natural crease, faint under-eye shadow, slightly uneven lower lash line",
    "nose": "straight bridge, rounded tip, narrow nostrils",
    "lips": "medium-full, defined cupid's bow, natural mauve tone, faint vertical lip lines, lower lip slightly chapped",
    "teeth": "natural off-white, upper left incisor overlaps the neighbour by 0.5mm",
    "hair": "black-brown, shoulder-length with a soft middle part, individual loose strands at the hairline, a few frizzy ends, natural scalp visible at the parting",
    "skin": "warm light-medium beige, visible pores on cheeks and nose, light peach fuzz along the jaw, faint redness on the chin and around the nostrils, natural sebum sheen on the T-zone, no retouching",
    "build": "slim, 1m62, natural shoulder line, relaxed posture",
    "hands": "slender fingers, short nude manicure, visible knuckle creases and fine skin texture, one faint vein on the back of the hand",
    "signature_items": ["thin gold chain with a tiny crescent-moon pendant", "small freshwater pearl stud earrings"],
    "persona": "friendly, quick-witted, speaks fast with short sentences; habit of tilting her head when she asks a question"
  },

  "realism_engine": {
    "medium": "unretouched digital photograph, straight out of camera",
    "camera_body": "Sony A7 IV",
    "lens": "85mm f/1.8 prime",
    "aperture": "f/2.0",
    "exposure": "1/250s, ISO 400",
    "focus": "critical focus on the near eye, shallow depth of field, background falls softly out of focus",
    "film_emulation": "Kodak Portra 400 colour response, gentle highlight rolloff",
    "grain": "fine natural sensor grain, slightly stronger in the shadows",
    "optical_truth": [
      "subtle chromatic aberration at the frame edges",
      "mild lens vignetting",
      "exactly one soft specular catchlight per eye, matching the key-light direction",
      "a few loose hair strands slightly out of place"
    ],
    "skin_rendering": "visible pores, micro-texture, uneven tone, peach fuzz catching the light, natural sebum highlights, faint blemish left in place — never smoothed, never plastic, never airbrushed",
    "lighting_rule": "exactly one identifiable key source with a stated direction; shadows must fall consistently on face, neck, clothing, wall and floor",
    "composition_rule": "slightly off-centre, imperfect framing as if captured in the moment, with breathing room around the subject",
    "expression_rule": "one micro-expression in progress — a half-formed smile, eyes focused on something specific — never a held, posed look",
    "colour": "natural white balance, no HDR, no global glow, contrast of a lightly curved RAW file"
  },

  "shot": {
    "scene_id": "S1.1",
    "setting": "small Hanoi apartment kitchen, white tiled wall, wooden countertop, a half-peeled orange on a plate",
    "time_and_light": "08:00 morning",
    "key_light": "soft daylight through a window at camera-left, 45 degrees to her face",
    "fill": "white wall bounce on her right cheek, no artificial fill",
    "wardrobe": {
      "top": "oatmeal cotton-linen oversized shirt, sleeves rolled to the elbow",
      "details": "natural wrinkles at the elbow and waist, one collar point slightly lifted, visible weave texture",
      "bottom": "light-wash straight jeans"
    },
    "pose_action": "standing at the counter, weight on her left leg, right hand resting on the countertop edge, turning her head toward the camera as if just interrupted",
    "expression": "eyebrows a little raised, a half-smile just beginning, eyes on the lens",
    "framing": "medium close-up from chest up, eye level, camera slightly to her left",
    "props": ["a glass of water, half full, with condensation"],
    "on_screen_text": null
  },

  "negative": "plastic skin, airbrushed, poreless, wax figure, doll-like, beauty filter, smoothing, perfect symmetry, flawless, masterpiece, 8k, ultra detailed, hyperdetailed, HDR, global glow, bloom, oversaturated, teal-and-orange grade, studio flat lighting with no direction, two or more catchlights per eye, inconsistent shadows, extra fingers, fused fingers, six fingers, deformed hands, warped ears, crossed eyes, mismatched irises, floating jewellery, text artefacts, watermark, logo, body-measurement look, exaggerated proportions, CGI render, 3D render, illustration, anime, oil painting",

  "consistency_lock": "The face must stay exactly as in the reference images: identical bone structure, eye shape and spacing, nose, lips, teeth, the mole below the left eye, the eyebrow scar and the eyebrow asymmetry. Do not beautify, slim, smooth, re-age or re-ethnicise the face. Keep the hair length and the crescent-moon necklace. Only the pose, wardrobe, background and lighting described in `shot` may change."
}
```

#### Biến thể cho VIDEO (`render_target: "video"`)

Giữ nguyên `identity`, `realism_engine`, `negative`, `consistency_lock`; thay `shot` bằng `shot` + `motion`:

```json
{
  "render_target": "video",
  "engine": "veo_3",
  "output": { "aspect_ratio": "9:16", "duration_sec": 8, "fps": 24 },
  "motion": {
    "camera_move": "locked-off tripod, almost imperceptible handheld drift",
    "subject_motion": "she sets the glass down, turns her shoulders toward the lens, blinks once naturally, gestures with her right hand on the second sentence",
    "physics_notes": "hair moves with the head turn and settles half a second later; shirt fabric creases follow the shoulder movement; water in the glass ripples when it touches the counter",
    "dialogue": "[Mai, 22, bright warm Hanoi accent, fast but clear]: \"Bữa sáng của bạn có thể đang làm đường huyết tăng gấp đôi.\"",
    "lip_sync": "lip shapes must match the Vietnamese dialogue; no mouth morphing between words",
    "ambience": "quiet kitchen room tone, faint street noise outside, no music",
    "no_cut": "single continuous take, no cut, no zoom punch"
  },
  "negative_video": "morphing face, identity drift between frames, sliding features, warping hands, jittery teeth, mouth flapping out of sync, sudden lighting change, extra limbs appearing, background objects popping in and out"
}
```

### 17.4 Bảy quy tắc làm nhân vật "giống người thật"

| # | Quy tắc | Vì sao hiệu quả | Cách viết trong prompt |
|---|---|---|---|
| 1 | **Bất đối xứng có chủ ý** | Mặt người thật không bao giờ cân đối; model mặc định sinh ra mặt cân đối hoàn hảo → lộ AI ngay | "left eyebrow 2mm higher", "smile pulls to the left" |
| 2 | **Micro-texture da** | Da "mịn như sứ" là dấu hiệu AI rõ nhất | "visible pores, uneven tone, peach fuzz, sebum sheen, no retouching" |
| 3 | **Dấu hiệu riêng (identity marks)** | Vừa làm thật, vừa là **neo nhận diện** để phát hiện nhân vật bị "trôi mặt" | 2–3 dấu: nốt ruồi, vết sẹo mờ, tàn nhang — luôn ghi vị trí chính xác |
| 4 | **Ánh sáng có hướng, có nguồn** | AI hay cho sáng đều khắp → phẳng, không thật | "one key source", ghi rõ hướng; bóng phải nhất quán trên mặt, cổ, tường, sàn |
| 5 | **Ống kính & phim cụ thể** | Tên máy/ống/khẩu/ISO kéo model về phân bố ảnh chụp thật | "85mm f/1.8 @ f/2.0, ISO 400, Kodak Portra 400" |
| 6 | **Micro-expression đang diễn ra** | Biểu cảm "giữ pose" trông như tượng | "a half-formed smile", "eyes focused on something specific" |
| 7 | **Bố cục không hoàn hảo** | Căn giữa tuyệt đối là dấu vân tay của AI | "slightly off-centre, as if captured in the moment" |

#### Từ phải LOẠI khỏi prompt

`perfect` · `flawless` · `masterpiece` · `8k` · `ultra/hyper detailed` · `beautiful woman` · `supermodel` · `doll-like` · `porcelain skin` · `symmetrical face` · `90-60-90` và mọi dạng số đo cơ thể · `instagram filter`

> Lý do: đây là các token "trung bình hóa" — model sẽ trả về phiên bản **xác suất cao nhất** = khuôn mặt chung chung, da nhựa. Riêng mô tả số đo/khoe thân còn làm tăng rủi ro vi phạm chính sách nền tảng và làm ảnh mất tự nhiên. Muốn nhân vật đẹp thì **tả ánh sáng và ống kính đẹp**, đừng tả "đẹp".

#### Bảng chẩn đoán: thấy dấu hiệu này → sửa chỗ này

| Dấu hiệu lộ ảnh AI | Nguyên nhân | Sửa |
|---|---|---|
| Da bóng như sáp, không lỗ chân lông | Thiếu `skin_rendering`, có từ "flawless" | Thêm pores/peach fuzz/blemish; xóa từ hoàn hảo |
| Mặt cân đối bất thường | Thiếu `asymmetry` | Thêm 2–3 điểm lệch cụ thể bằng số |
| Ảnh "phẳng", không biết sáng từ đâu | Không khai báo key light | 1 nguồn + hướng + kiểm tra bóng nhất quán |
| Mắt có 2–3 điểm sáng, nhìn vô hồn | Model tự thêm catchlight | `exactly one specular catchlight per eye` + negative |
| Tay 6 ngón, ngón dính | Tay nằm ngoài vùng nét, không mô tả | Tả tay cụ thể, cho tay có việc (cầm cốc, tựa mặt bàn) |
| Trang sức/tóc "bay lơ lửng" | Không mô tả tiếp xúc | Tả điểm tiếp xúc: "chain resting on the collarbone" |
| Nhân vật đổi mặt giữa các ảnh | Mô tả mặt dài hơn ảnh tham chiếu, hoặc thiếu lock | Rút gọn mô tả mặt, luôn kèm ảnh, lock ở cuối |
| Ảnh trông như render 3D | Có `8k`, `octane`, `cinematic lighting` | Thay bằng thông số máy ảnh + film emulation |

### 17.5 Quy trình giữ nhân vật đồng nhất 100% (4 bước)

```
B1. ẢNH GỐC (Master Reference)
    1 ảnh chính diện, biểu cảm trung tính, sáng đều nhẹ, độ phân giải cao nhất có thể.
    → Đây là "giấy khai sinh". Mọi thứ sau này tham chiếu về đây.
    Duyệt bằng mắt ở 100% zoom; xấu ở bước này = sai suốt đời nhân vật.

B2. BẢNG NHÂN VẬT (Character Sheet) — 9 ảnh
    Góc:     chính diện · 3/4 trái · 3/4 phải · bán diện · sau vai
    Biểu cảm: trung tính · cười hé · cười lớn · nghiêm/suy nghĩ
    Mỗi ảnh đều đính kèm ảnh B1 + consistency_lock.
    → Đây là bộ ảnh tham chiếu nạp kèm mọi prompt về sau.

B3. BỘ DỮ LIỆU & LoRA (tùy chọn, cho độ đồng nhất cao nhất)
    20–30 ảnh từ B2 (đa góc, đa biểu cảm, đa sáng, đa cỡ cảnh), 1024px trở lên.
    Caption: 1 trigger token cố định (vd "koc01mai woman") + chỉ tả phần THAY ĐỔI
             (góc, biểu cảm, phục trang) — KHÔNG tả lại khuôn mặt.
    Khởi điểm thử nghiệm (SDXL/Flux): rank 16, alpha 8, lr 1e-4, ~10 epoch.
    Lưu checkpoint từng epoch, test cùng 1 bộ prompt → chọn checkpoint cân bằng
    giữa "giống mặt" và "còn nghe theo prompt". Đổi MỘT biến mỗi lần thử.

B4. SINH THEO CẢNH (chạy hằng ngày trong pipeline)
    Agent 17 lấy identity + realism_engine + shot của từng cảnh → prompt → ảnh/video.
    Kiểm tra lại identity_marks (nốt ruồi, sẹo) còn đúng → nếu mất thì sinh lại.
```

> **Lưu ý thực tế:** không có công thức nào đảm bảo 100% giống nhau. Cách làm đúng là **thử có kiểm soát**: đổi một biến, so sánh trên cùng một bộ prompt kiểm tra, chỉ giữ thay đổi khi kết quả tốt hơn rõ ràng.

### 17.6 Adapter — một schema, bốn công cụ

| | Nano Banana Pro / Gemini | Midjourney v7 | Flux / SDXL + LoRA | Veo 3 / Kling 3 |
|---|---|---|---|---|
| **Định dạng prompt** | JSON có cấu trúc (dán nguyên mục 17.3) | Văn xuôi 1 đoạn, mệnh đề nối bằng dấu phẩy | Văn xuôi + trigger token | Văn xuôi theo trình tự camera → hành động → sáng → texture → âm thanh |
| **Neo nhân vật** | Nạp 1–3 ảnh tham chiếu (hỗ trợ nhiều ảnh trong 1 prompt) | `--cref <url> --cw 100` | Trigger token của LoRA, weight 0.8–1.0 | Ảnh đầu (image-to-video) từ B2 |
| **Tỉ lệ/tham số** | `output.aspect_ratio` | `--ar 9:16 --stylize 50 --raw` | sampler/steps/CFG 3.5 (Flux) | `duration_sec`, `fps` |
| **Negative** | Trường `negative` | `--no plastic skin, ...` | Negative prompt riêng | `negative_video` |
| **Điểm mạnh** | Sửa cục bộ (đổi nền, giữ người), tiếng Việt trên ảnh tốt | Thẩm mỹ ảnh, ánh sáng | Đồng nhất tuyệt đối, chạy offline, không giới hạn | Người nói, khẩu hình, âm thanh gốc |
| **Điểm yếu** | Dễ "làm đẹp" quá tay → phải khóa chặt | Khó khóa mặt tuyệt đối | Cần GPU + thời gian train | Giá cao, clip ngắn 8–15s |
| **Dùng cho** | Ảnh hook, thumbnail, ảnh cảnh | Ảnh nghệ thuật, cover | Sản xuất số lượng lớn | Cảnh người dẫn nói |

**Chuyển JSON → Midjourney (quy tắc máy làm được):**
`identity.demographics` + `face_structure` + `asymmetry` + `identity_marks` + `skin` → `shot.framing` + `pose_action` + `expression` → `shot.wardrobe` → `shot.setting` + `key_light` → `realism_engine.lens/exposure/film_emulation/grain` → `--ar <platform> --stylize 50 --raw --cref <url> --cw 100 --no <negative>`

**Chuyển JSON → Veo/Kling (công thức 5 khối):**
`[Camera] + [Chủ thể & vật lý chuyển động] + [Bối cảnh/ánh sáng] + [Texture & chi tiết] + [Âm thanh/thoại]`, nêu rõ thời lượng, thoại theo cú pháp `[Tên, mô tả, tông giọng]: "lời thoại"`.

### 17.7 Thư viện nhân vật — 5 KOC phủ các nhóm chủ đề

Mỗi nhân vật là một file `config/characters/<id>.json` theo đúng khối `identity` ở mục 17.3. Dưới đây là **ADN** của từng nhân vật (các cụm tiếng Anh là phần dán thẳng vào prompt).

#### KOC-01-MAI — Nguyễn Hà Mai · nữ 22 · Hà Nội
*Ngách: làm đẹp, thời trang, review đồ dùng, xu hướng giới trẻ · Nền tảng chính: TikTok/Reels*

- **Mặt & dấu riêng**: `oval face, slightly wide forehead, soft jawline` · nốt ruồi phẳng dưới đuôi mắt trái 1cm · sẹo mờ 4mm ở đuôi mày phải · 2 tàn nhang sống mũi · mày trái cao hơn 2mm, cười lệch sang trái
- **Tóc & da**: `black-brown shoulder-length, soft middle part, frizzy ends` · `warm light-medium beige, visible pores, chin redness, T-zone sheen`
- **Dáng & tay**: slim 1m62, vai thả lỏng · `short nude manicure`
- **Vật bất ly thân**: dây chuyền vàng mảnh mặt trăng khuyết · bông tai ngọc trai nhỏ
- **Giọng & tính cách**: Bắc, trẻ, nói nhanh câu ngắn, hay nghiêng đầu khi hỏi; thân thiện, bắt trend nhanh
- **Bối cảnh mặc định**: căn hộ nhỏ Hà Nội — tường gạch men trắng, bàn gỗ, cửa sổ sáng tự nhiên
- **Phục trang**: tông kem/be/xanh nhạt, cotton–linen oversize, jeans sáng màu
- **Sáng mặc định**: `soft window daylight 45° camera-left, white wall bounce fill`

#### KOC-02-THAO — Lê Thu Thảo · nữ 30 · Đà Nẵng
*Ngách: sức khỏe thường thức, mẹ & bé, dinh dưỡng, chăm sóc gia đình · Nền tảng chính: YouTube/Facebook*

- **Mặt & dấu riêng**: `round-oval face, full cheeks, gentle rounded jaw` · nốt ruồi nhỏ mép phải · vết rạn chân chim nhẹ ở đuôi mắt khi cười · mũi hơi lệch sang phải rất nhẹ
- **Tóc & da**: `dark brown, low loose bun, a few strands escaping at the temples` · `medium warm tone, light melasma patch on the right cheekbone, slight under-eye pigmentation, no concealer`
- **Dáng & tay**: trung bình 1m58, hơi tròn sau sinh, lưng thẳng · `bare short nails, a faint ring mark on the left hand`
- **Vật bất ly thân**: nhẫn cưới vàng trơn · kẹp tóc gỗ
- **Giọng & tính cách**: Trung pha Bắc, chậm rãi rõ ràng, hay dừng để nhấn; điềm đạm, đáng tin, giọng "người chị"
- **Bối cảnh mặc định**: bếp gia đình sáng, kệ gỗ, rổ rau; hoặc góc phòng khách có cây xanh
- **Phục trang**: sơ mi linen pastel, áo len mỏng, tạp dề vải thô
- **Sáng mặc định**: `large soft window light from the front-left, warm 5000K, soft shadow under the chin`

#### KOC-03-DUY — Trần Anh Duy · nam 28 · TP.HCM
*Ngách: công nghệ, AI, tài chính cá nhân, năng suất · Nền tảng chính: YouTube*

- **Mặt & dấu riêng**: `angular face, defined jaw, straight thick eyebrows` · râu lún phún 2 ngày không đều, bên trái dày hơn · nốt ruồi nhỏ cạnh cánh mũi phải · mí mắt phải hơi sụp
- **Tóc & da**: `black, short textured crop, slightly messy fringe, visible scalp at the crown` · `medium olive tone, enlarged pores on the nose, one small healing blemish on the left cheek, oily forehead`
- **Dáng & tay**: 1m74, gầy chắc, hay hơi chúi vai về trước · `clean square-cut nails, prominent knuckles`
- **Vật bất ly thân**: đồng hồ dây da nâu mặt tròn · kính không độ gọng mảnh đen
- **Giọng & tính cách**: Nam, nhanh, rõ, hay dùng con số; thẳng thắn, thích "bóc" sự thật, hơi tếu
- **Bối cảnh mặc định**: góc làm việc tối giản — màn hình mờ phía sau, giá sách, đèn LED ấm sau vai
- **Phục trang**: áo thun trơn đen/xám, sơ mi oxford xanh nhạt, áo khoác bomber mỏng
- **Sáng mặc định**: `key softbox camera-right at 30°, warm practical lamp behind his left shoulder as rim light, dark falloff background`

#### KOC-04-HUNG — Phạm Quốc Hùng · nam 45 · Hà Nội
*Ngách: kinh doanh, quản trị, bài học thương trường, bất động sản · Nền tảng chính: YouTube/Facebook*

- **Mặt & dấu riêng**: `broad square face, heavy brow ridge, deep nasolabial folds` · 2 nếp nhăn ngang trán không đều · tóc bạc hai bên thái dương không cân · vết chai nhỏ ngón giữa phải
- **Tóc & da**: `black with grey at the temples, side part, thinning at the hairline` · `tanned weathered skin, coarse texture, visible pores, sun spots on the forehead, five-o-clock shadow`
- **Dáng & tay**: 1m72, vững, vai rộng, ngồi hơi ngả về sau · `broad hands, thick fingers, dry skin`
- **Vật bất ly thân**: đồng hồ thép bản lớn · bút kim loại cài túi áo
- **Giọng & tính cách**: Bắc, trầm, chậm, ngắt câu dứt khoát; từng trải, hay kể chuyện thật, không hoa mỹ
- **Bối cảnh mặc định**: phòng họp nhỏ hoặc quán cà phê cũ — gỗ sẫm, rèm, cửa sổ lớn phía sau
- **Phục trang**: sơ mi trắng/xanh than xắn tay, blazer tối không cà vạt
- **Sáng mặc định**: `window light camera-left, deeper contrast, visible shadow side, no fill on camera-right`

#### KOC-05-LAN — Bùi Thị Lan · nữ 55 · Huế
*Ngách: đông y, ẩm thực truyền thống, mẹo dân gian, sống khỏe tuổi trung niên · Nền tảng chính: Facebook/YouTube*

- **Mặt & dấu riêng**: `soft heart-shaped face, hollowing under the cheekbones, crow's feet and smile lines kept` · nốt ruồi lớn mờ ở gò má trái · mí mắt trên sụp nhẹ không đều · 1 chiếc răng khểnh bên phải
- **Tóc & da**: `black with natural grey strands, pulled back into a low knot, thinner at the parting` · `warm medium tone, mature texture, visible fine wrinkles, age spots on the temples and the back of the hands, no retouching`
- **Dáng & tay**: 1m55, hơi đầy, lưng hơi cong tự nhiên · `working hands, short nails, prominent veins, slightly swollen finger joints`
- **Vật bất ly thân**: vòng ngọc trai nhỏ ở cổ tay trái · khăn vải vắt vai
- **Giọng & tính cách**: Huế nhẹ, chậm, ấm, hay dùng thành ngữ; hiền, dạy việc như dặn con cháu
- **Bối cảnh mặc định**: sân/bếp nhà vườn miền Trung — nong tre, thảo mộc phơi, tường vôi vàng
- **Phục trang**: áo bà ba vải thô, áo sơ mi hoa nhỏ, khăn rằn
- **Sáng mặc định**: `open shade daylight from the courtyard, soft wrap, warm bounce from the yellow wall`

#### Quy trình tạo nhân vật thứ 6 trở đi (6 bước, 30 phút)

1. **Chốt ngách & nền tảng** → quyết tuổi, vùng miền, giọng (nhân vật phải "đáng tin" với chủ đề: đông y đừng dùng gái 20).
2. **Viết `identity`**: copy khối ở 17.3, thay 9 trường — `demographics, face_structure, asymmetry, identity_marks, eyes/nose/lips, hair, skin, build, signature_items, persona`. **Bắt buộc có ≥ 2 điểm bất đối xứng bằng số và ≥ 2 dấu hiệu riêng có vị trí chính xác.**
3. **Sinh ảnh gốc** (B1) → duyệt ở 100% zoom → chưa đạt thì sinh lại, **không đi tiếp**.
4. **Sinh bảng nhân vật 9 ảnh** (B2) → lưu `config/characters/<id>/refs/`.
5. (Tùy chọn) **Train LoRA** từ 20–30 ảnh (B3).
6. **Chạy test 3 cảnh** khác hẳn nhau (ngoài trời trưa / trong nhà tối / cận đặc tả) → kiểm `identity_marks` còn nguyên → ghi nhân vật vào `characters.yaml` và gán cho luồng.

### 17.8 Agent 17 — KOC Character Director (Tầng 5)

| Trường | Nội dung |
|---|---|
| **Vị trí** | Tầng 5 — Sáng tạo, chạy **sau** Director (agent 14), **trước** QA |
| **Đầu vào** | `script.json` đã có `segments[].scenes[]` · `character_id` của luồng · `config/characters/<id>.json` · nền tảng & tỉ lệ |
| **Nhiệm vụ** | 1) Quyết cảnh nào cần mặt người (hook, chuyển đoạn, CTA, cảnh cảm xúc) và cảnh nào để B-roll — **không lạm dụng**, 25–40% số cảnh là đủ. 2) Với mỗi cảnh người: sinh prompt theo `koc-master-1.0`, chọn `render_target` ảnh hay video. 3) Chọn phục trang **nhất quán trong cùng một kịch bản** (cùng một "ngày quay"): cả video chỉ 1–2 bộ. 4) Xuất `koc_prompts.json` + ghi vào từng `scene.visual`. 5) Tự kiểm bằng rubric 17.10. |
| **Đầu ra** | `koc_prompts.json` (prompt đầy đủ từng cảnh, kèm bản Midjourney và bản Veo/Kling), bổ sung `scene.visual.koc` |
| **Model** | Sonnet (ghép prompt theo khuôn mẫu, không cần Opus) |
| **Quy tắc cứng** | Không bao giờ sửa `realism_engine`, `negative`, `consistency_lock`. Không thêm mô tả khuôn mặt ngoài `identity`. Một kịch bản = một nhân vật = một bộ trang phục. |

> Cập nhật đội hình: **17 agent**. Agent 17 nằm giữa agent 14 (Director) và agent 16 (QA) trong đồ thị LangGraph; nếu luồng tắt `koc.enabled` thì node này bị bỏ qua.

### 17.9 Mở rộng `script.json` cho KOC

Thêm một khối ở cấp cao nhất và một khối con trong mỗi cảnh có người:

```json
{
  "koc": {
    "enabled": true,
    "character_id": "KOC-01-MAI",
    "wardrobe_set": "oatmeal linen shirt + light jeans",
    "shoot_day_continuity": "all human scenes in this script share one wardrobe and one location set",
    "engines": { "image": "nano_banana_pro", "video": "veo_3" },
    "human_scene_ratio": 0.33
  },
  "segments": [{
    "scenes": [{
      "id": "S1.1",
      "visual": {
        "type": "koc",
        "koc": {
          "render_target": "video",
          "duration_sec": 8,
          "prompt_ref": "koc_prompts.json#S1.1",
          "framing": "medium close-up, eye level",
          "pose_action": "turns toward the camera, right hand on the counter",
          "expression": "half-smile beginning, eyebrows slightly raised",
          "dialogue_vi": "Bữa sáng của bạn có thể đang làm đường huyết tăng gấp đôi.",
          "identity_check": ["mole below left eye", "scar on right eyebrow tail"]
        }
      }
    }]
  }]
}
```

Thư mục đầu ra của mỗi kịch bản (bổ sung mục 10.1):

```
01_an-sang-sai-cach/
├─ script.md
├─ script.json
├─ koc_prompts.json        # prompt ảnh/video từng cảnh có người (3 bản: JSON, MJ, Veo)
├─ voiceover.txt
├─ sources.md
└─ packaging.md
```

### 17.10 Rubric QA hình ảnh nhân vật (thang 10, đạt ≥ 8)

| Tiêu chí | Điểm | Đạt khi |
|---|---|---|
| **Đồng nhất khuôn mặt** | 3 | Khớp ảnh gốc; đủ `identity_marks`; không bị "làm đẹp", làm trẻ, đổi nét |
| **Chân thực da & texture** | 2 | Thấy lỗ chân lông, tông da không đều; không bóng sáp |
| **Ánh sáng & bóng nhất quán** | 2 | Một nguồn rõ hướng; bóng trên mặt–cổ–tường–sàn cùng hướng; 1 catchlight/mắt |
| **Giải phẫu & tiếp xúc** | 1,5 | Tay đúng số ngón; trang sức/tóc có điểm tiếp xúc; không vật thể lơ lửng |
| **Phù hợp cảnh & nền tảng** | 1 | Đúng tỉ lệ khung hình, cỡ cảnh, phục trang nhất quán trong kịch bản |
| **Không dấu hiệu AI** | 0,5 | Bố cục không căn giữa máy móc; không glow/HDR; không chữ rác, watermark |

< 8 điểm → sinh lại tối đa 2 lần; vẫn không đạt → chuyển cảnh đó sang B-roll và gắn cờ `human_review`.

### 17.11 Pháp lý, chính sách nền tảng & đạo đức

| Nguyên tắc | Thực hiện |
|---|---|
| **Khai báo nội dung AI** | Bật nhãn "nội dung tổng hợp/AI" theo yêu cầu của từng nền tảng khi video có người do AI tạo; thêm 1 dòng trong mô tả: "Người dẫn trong video là nhân vật do AI tạo." |
| **Không mượn mặt người thật** | Tuyệt đối không prompt theo tên người nổi tiếng, không lấy ảnh người thật làm ảnh gốc hay dataset nếu không có quyền. Nhân vật phải là khuôn mặt tổng hợp mới. |
| **Không mạo danh chuyên môn** | Nhân vật KOC **không** được giới thiệu là bác sĩ, dược sĩ, luật sư, chuyên gia tài chính có chứng chỉ. Nội dung y tế/tài chính: nhân vật chỉ "chia sẻ thông tin đã kiểm chứng", kèm câu miễn trừ và nguồn (nối với Fact-checker ở mục 4 và rủi ro ở mục 14). |
| **Không gợi dục, không khai thác hình thể** | Không mô tả số đo, không trang phục hở/bó gợi dục, không tư thế khoe thân — vừa vi phạm chính sách kiếm tiền của nền tảng, vừa làm ảnh mất vẻ tự nhiên. Tiêu chí hình ảnh là **đáng tin**, không phải **gợi cảm**. |
| **Nhân vật trưởng thành** | Mọi nhân vật ≥ 22 tuổi và được mô tả rõ là người trưởng thành. |
| **Minh bạch tài trợ** | Nếu kịch bản có nội dung quảng cáo, bắt buộc có nhãn quảng cáo trong lời thoại và caption. |
| **Lưu vết** | Mỗi ảnh/video sinh ra ghi `character_id`, prompt, engine, thời điểm vào `output/.../koc_prompts.json` để truy xuất khi cần. |

### 17.12 Cấu trúc thư mục bổ sung cho `D:\DEV\Agnet`

```
config/
├─ characters.yaml              # danh sách nhân vật, nhân vật mặc định của từng luồng
└─ characters/
   ├─ koc-01-mai.json           # khối identity
   ├─ koc-01-mai/refs/          # master_front.png + 9 ảnh character sheet
   ├─ koc-01-mai/lora/          # (tùy chọn) file .safetensors + ghi chú cấu hình train
   └─ koc-02-thao.json ...
agnet/
├─ agents/creative/koc_director.py      # agent 17
├─ koc/
│  ├─ master_prompt.py                  # koc-master-1.0: ghép A+B+C+negative+lock
│  ├─ adapters.py                       # → nano_banana | midjourney | flux | veo/kling
│  ├─ realism_engine.json               # LỚP B dùng chung, versioned
│  └─ qa_image.py                       # rubric 17.10
```

Thêm vào **Cài đặt Luồng** (mục 3.1): `koc.enabled`, `koc.character_id`, `koc.human_scene_ratio`, `koc.image_engine`, `koc.video_engine`.
Thêm vào **Web UI** (mục 12): màn hình **Quản lý nhân vật** — xem/sửa `identity`, xem bộ ảnh tham chiếu, nút "Sinh lại bảng nhân vật", xem prompt từng cảnh, gán nhân vật cho luồng.

---

## 18. KIẾN TRÚC v1.3 — Claude chỉ huy, Gemini thực thi việc không cần nguồn, 20 tin/ngày

> Cập nhật 02/10/2026 (v1.2 → v1.3). Mục này thay đổi mục 4 (đội hình), mục 6 (sản lượng) và mục 12 (giao diện). v1.2 giả định Gemini làm được khảo sát có bám nguồn; **phép đo thật ở 18.2 cho thấy giả định đó không đúng ở gói hiện tại**, nên 18.3 đổi thành hai phương án chờ người dùng quyết. Phần nào đã/chưa kiểm chứng ghi rõ ở 18.11.

### 18.1 Quyết định

| Hạng mục | v1.1 | v1.3 |
|---|---|---|
| Sản lượng | 10 kịch bản/luồng/ngày | **20 tin/ngày** (đặt trong giao diện, 1–50) |
| Khảo sát thị trường, tìm kiếm mạng | Claude (WebSearch/WebFetch) | **CHỜ NGƯỜI DÙNG CHỌN** (18.3): (a) Gemini bám nguồn Google nếu bật thanh toán, hoặc (b) giữ Claude WebSearch |
| Phân loại, gom cụm, tóm tắt, viết nháp (không cần nguồn) | Claude | Gemini được phép làm (đã đo gọi thường chạy 200) |
| Phán đoán, viết chính, đạo diễn, QA, khóa nhân vật | Claude | Claude (**tổng chỉ huy**, không đổi) |
| Số liệu, đếm từ, schema, chống trùng, ngân sách | Code Python | Code Python (không đổi) |
| Xác thực Claude | API key | **Tài khoản Claude đã đăng nhập** (đã kiểm chứng 01/10/2026) |
| Xác thực Gemini | — | **Khóa Google AI Studio** (`GEMINI_API_KEY` trong `.env`); danh sách model tự cập nhật, hết định mức thì hạ bậc (18.4) |
| Giao diện | Dòng lệnh | Ứng dụng desktop PySide6, thanh điều hướng trái (18.9) |

### 18.2 Kết quả đo THẬT với khoá Google AI Studio — 02/10/2026

Đây là lần đầu gọi Gemini thật. Khoá nằm trong `.env`, không ghi vào tài liệu hay log.

| Phép đo | Kết quả |
|---|---|
| Liệt kê model | Được **44 model** |
| `gemini-3.8-flash`, gọi thường (không công cụ) | **200** — dùng được |
| `gemini-2.5-pro` / `2.5-flash` / `2.5-flash-lite` | **404** "no longer available to new users" |
| `gemini-3.1-pro-preview` | **429**, `limit: 0` (gói miễn phí không có hạn mức bậc pro này) |
| `google_search` (bám nguồn) trên 3.8-flash, 3.5-flash, 3.5-flash-lite, 3.1-flash-lite, 3-flash-preview | **429 trên TẤT CẢ**, trong khi cùng model gọi thường vẫn 200 |
| Lỗi tạm | **503** "high demand" thoáng qua — thử lại là qua |

**Kết luận đo:** 429 của `google_search` xảy ra trên mọi model nên đó là **hạn mức của công cụ tìm kiếm** (gói miễn phí), **không phải hạn mức của model**. Hạ xuống model thấp hơn không giải quyết được.

**Hệ quả kiến trúc:** ở gói hiện tại Gemini **không thể là nguồn dữ liệu có bằng chứng** — không có bám nguồn thì không có URL/grounding metadata để nghiệm thu (18.5), còn để Gemini "nhớ" tin tức từ trọng số mô hình thì vi phạm quy tắc cứng số 1 (không bịa số liệu). Mục 18.2 của v1.2 (bảng 7 agent khảo sát chạy bằng Gemini) **tạm treo** cho tới khi người dùng chọn ở 18.3.

**Client đã xử lý các tình huống trên** (`agnet/gemini/client.py`, `ladder.py`; kiểm bằng transport giả, nay có thêm một lượt đo thật):

| Tình huống | Cách xử lý |
|---|---|
| Công cụ bám nguồn bị 429 | `GroundingUnavailable` — tách khỏi lỗi model; **nghỉ riêng cho công cụ** (khoá `*search`), không làm hỏng model đang dùng được cho gọi thường |
| 429 `limit: 0` | Model nghỉ **24 giờ** (không hạn mức thì chờ phút cũng vô ích) |
| 404 "no longer available" | Model nghỉ **24 giờ** và bị bỏ khỏi thang |
| 429 có `retry_after` / hết hạn mức ngày | Nghỉ theo `retry_after` / tới lúc Google đặt lại |
| 503 / lỗi máy chủ | Thử lại có giới hạn (`server_retries`) |
| `probe()` | Đo nhanh: gọi thường và gọi bám nguồn riêng rẽ, trả bảng model/công cụ nào dùng được; dùng khi đổi khoá hoặc đổi gói, và hiển thị trên giao diện (18.9) |
| Hết cả thang / khoá sai | Chuyển lượt sang Claude, ghi cảnh báo, pipeline không dừng |

### 18.3 Quyết định cần người dùng

> **ĐÃ CHỐT 02/10/2026 (người dùng): chọn (a) — Gemini PHẢI bám nguồn tìm kiếm cho phân tích thị trường.** Cài đặt `gemini_require_grounding` (mặc định bật, sửa ở mục Gemini): Gemini không bám được thì nguồn đó bị LOẠI (`grounding_required`), Claude KHÔNG làm thay; nếu mọi nguồn khảo sát rỗng thì lần chạy dừng ("dừng: khảo sát không thu được mục nào có nguồn"), không viết kịch bản từ dữ liệu trống. Hệ quả hiện tại: cho tới khi bật thanh toán/hạn mức tìm kiếm Google, luồng khảo sát sẽ dừng — đây là chủ đích, không phải lỗi. Cũng chốt: không nới ngày (`published_at` bắt buộc), bật `keyword-miner` + `competitor-gap-analyst` mặc định.

| Phương án | Nội dung | Được | Mất |
|---|---|---|---|
| **(a) Bật thanh toán / hạn mức tìm kiếm Google** | Nâng gói Google AI Studio để `google_search` có hạn mức | Giữ nguyên thiết kế v1.2: 7 scout chạy Gemini có bám nguồn, nhẹ gánh hạn mức Claude | Phát sinh chi phí Google (chưa đo: số lượt tìm kiếm/ngày × giá); phải chạy lại `probe()` để chắc 429 đã hết |
| **(b) Giữ khảo sát bằng Claude WebSearch** | Scout vẫn là agent Claude như v1.1; Gemini chỉ làm việc **không cần nguồn**: phân loại, gom cụm, tóm tắt, viết nháp | Không tốn thêm; không phụ thuộc hạn mức tìm kiếm; hợp quy tắc cứng | Tiêu hao hạn mức gói Claude nhiều hơn (chưa biết có chịu nổi 20 tin/ngày — 18.11) |

Đã chốt (a) (xem khung ở đầu mục này): `gemini_provider=gemini_api`, `gemini_require_grounding=true`. Khi bám nguồn chưa chạy được, luồng khảo sát dừng thay vì chuyển sang Claude.

### 18.4 Xác thực & thang model Gemini

- **Claude**: tài khoản đã đăng nhập (`claude auth login`). Khoá API được ưu tiên hơn tài khoản, nên giao diện cảnh báo khi còn `ANTHROPIC_API_KEY` và loại khoá khỏi tiến trình con.
- **Gemini**: khoá Google AI Studio, giao diện luôn che. Đã có khoá và đã gọi thật (18.2).
  - **Tự cập nhật danh sách model**: gọi API liệt kê (mặc định 24 giờ, đặt 1–168 giờ), phân tích tên → họ, phiên bản, bậc (`pro` > `flash` > `flash-lite`), xếp **thang model**. Bản ghi nhớ `config/gemini_models.json` (không chứa khoá).
  - **Hết định mức thì xuống bậc thấp hơn** (429): hết phiên bản này sang phiên bản thấp hơn cùng bậc rồi mới sang bậc thấp hơn. Bản preview chỉ dùng khi không còn bản ổn định. Tắt được bằng `gemini_fallback`.
  - Quan sát thật: bậc `pro` trong gói miễn phí gần như không dùng được (`limit: 0`), nên thực tế thang bắt đầu từ `flash`.
  - Hết cả thang hoặc khoá sai: lượt đó chuyển sang Claude và ghi cảnh báo.

### 18.5 Hợp đồng nhiệm vụ — chỉ áp dụng cho việc Gemini mang dữ liệu có nguồn về

Chỉ huy không "nhắc khéo" mà **ràng buộc bằng hợp đồng, nghiệm thu bằng code**. Phần này chỉ có hiệu lực khi chọn phương án (a); với việc không cần nguồn (phân loại, gom cụm…) chỉ áp dụng kiểm schema và số mục tối thiểu.

1. **Giao**: `TaskContract` gồm mục tiêu, luồng, schema JSON đầu ra, **số mục tối thiểu**, nguồn bắt buộc quét, thời hạn.
2. **Nộp**: JSON đúng schema; mỗi mục có `title`, `url`, `source`, `published_at`, `snippet` và bằng chứng bám nguồn.
3. **Nghiệm thu bằng code**: đúng schema · `url` hợp lệ và có trong metadata bám nguồn · tuổi tin trong cửa sổ · không trùng · đủ số mục tối thiểu · số liệu có nguồn. Mục thiếu bằng chứng bị **loại**, không "ước lượng cho đủ".
4. **Trả lại**: không đạt thì gửi lại **một lần** kèm danh sách lỗi cụ thể; vẫn không đạt thì ghi `compliance=fail`, loại nguồn đó khỏi lượt chạy và báo trên giao diện. Claude không tự bịa dữ liệu thay Gemini.
5. **Chỉ số**: tỉ lệ đạt hợp đồng theo từng agent Gemini, hiển thị ở màn "Hợp đồng & tỉ lệ đạt" (18.9).

### 18.6 Sản lượng 20 tin/ngày

- Lấy dư theo mục 6: thu 400–800 RawItem → gom 80–120 Story → chấm điểm → chọn **30** đề tài (20 × 1,5) → viết 30 → QA đạt ≥ 20. Ngưỡng QA ≥ 8 **không hạ**; thiếu thì lấy đề tài dự phòng.
- Bảng thời lượng khi quota = 20: `{3-5: 6, 8-12: 10, 15-20: 4}`; giao diện tự chia lại, tổng luôn bằng quota.
- `run_timeout_min` nâng 180 → **240** cho luồng 20 tin; lịch đặt sớm hơn giờ cần 3 giờ.
- `max_cost_usd_per_day` là chốt chặn cứng. Với tài khoản đăng ký, chi phí chỉ là số quy đổi nhưng **hạn mức gói vẫn bị tiêu hao**.

### 18.7 Song song & giới hạn thực tế

- Số agent song song đặt trong giao diện (mặc định 3, tối đa 8) → `Pipeline.concurrency`.
- **Phát hiện 02/10/2026**: nhiều tiến trình Claude Code dùng chung một lần đăng nhập có thể đua nhau làm mới token (`Failed to refresh OAuth token: another Claude Code process is refreshing it`); lần chạy thật đầu chết ở agent đầu tiên. Đối sách bắt buộc: **thử lại lùi dần** cho lỗi tạm và **khởi động ấm** bằng một lượt gọi đơn lẻ trước khi bung song song (việc của B4).
- Đo 01/10/2026: mỗi lượt gọi tốn 61.517 token đầu vào nếu không tắt nạp cấu hình máy; đã vá còn ~7.000 (`SdkRunner`).

### 18.8 Mô hình thi công 4 giai đoạn

Mỗi agent **sở hữu một tập tệp riêng** để không ghi đè nhau và **không commit**; chỉ **tổng chỉ huy** commit sau khi giai đoạn xanh test.

| Giai đoạn | Việc | Chạy |
|---|---|---|
| **GĐ1 — Nền** | B2 hợp đồng & nghiệm thu · B3 agent Gemini · UI-Gemini (mục Gemini trên giao diện) · Kế hoạch (tài liệu này) | **Song song**, tập tệp rời nhau |
| **GĐ2 — Nối** | B4 nối pipeline (định tuyến theo `engine`, `concurrency`, thử lại OAuth, khởi động ấm, quota 20) + các màn hình còn lại (Đội agent, Hợp đồng, KOC, Chi phí) | B4 trước (cần giao diện hàm của B1–B2), màn hình song song |
| **GĐ3 — Kiểm tra** | Nhóm kiểm: (1) kiểm kê tệp, (2) chạy test, (3) rà khoá/bảo mật, (4) đối chiếu quy tắc cứng trong CLAUDE.md | **Song song**, chỉ đọc (không sửa) |
| **GĐ4 — Đánh giá** | Agent **tổng đánh giá** gộp báo cáo GĐ3 + agent **phản biện độc lập** (không thấy kết luận của tổng, tự tìm lỗi) | Tuần tự rồi đối chiếu; bất đồng thì ghi cả hai ý kiến cho người dùng |

| Luồng | Phạm vi | Tệp sở hữu | Trạng thái |
|---|---|---|---|
| B1 Gemini client | `GeminiClient`, thang model, bám nguồn, `probe()`, transport giả | `agnet/gemini/*`, `tests/test_gemini_*` | **Xong** + đã đo thật (18.2) |
| B2 Hợp đồng & nghiệm thu | `TaskContract`, nghiệm thu bằng code, đo `compliance` | `agnet/commander/*`, `tests/test_commander_*` | **ĐÃ XONG** (02/10) |
| B3 Agent Gemini | khai `engine` cho 7 agent, viết lại prompt theo hợp đồng; **phụ thuộc quyết định 18.3** | `.claude/agents/01–05,08,09`, `tests/test_agents_files.py` | **ĐÃ XONG** (02/10) |
| UI-Gemini | Mục Gemini trên giao diện: trạng thái khoá, thang model, `probe()`, nghỉ hạn mức | `agnet/ui/page_gemini.py` (+ nối trong `app.py`) | **ĐÃ XONG** |
| Kế hoạch | Mục 18–19 tài liệu | `KE_HOACH_AGNET.md` | **ĐÃ XONG** |
| B4 Nối pipeline | định tuyến `engine`, `concurrency`, thử lại OAuth, khởi động ấm, quota 20 | `agnet/pipeline/*`, `agnet/runner.py` | **ĐÃ XONG** (chưa chạy thật) |
| B5 Màn hình còn lại | Đội agent, Hợp đồng & tỉ lệ đạt, Nhân vật KOC, Chi phí & hạn mức | `agnet/ui/page_agents.py`, `page_contracts.py`, `page_koc.py`, `page_cost.py` | **ĐÃ XONG** |
| B6 Kiểm chứng | GĐ3–GĐ4; chạy thử 1 tin thật, báo cáo chi phí & agent chậm | `tests/*`, báo cáo | GĐ3–GĐ4 đã chạy; **chạy thử 1 tin thật CHƯA** (bị chặn: bám nguồn 429) |

### 18.9 Bản đồ giao diện (PySide6, thanh điều hướng trái)

Thanh trái (`agnet/ui/sidebar.py`, rộng 210 px, phím nhanh Ctrl+1…9). Hiện **5 mục**, thứ tự đăng ký trong `agnet/ui/app.py`; các mục mới thêm vào bằng `add_page`.

| # | Mục | Tình trạng | Điều khiển có thể sửa | Lưu ở |
|---|---|---|---|---|
| 1 | Bảng điều khiển (`page_runs.py`) | Hiện có | Chạy luồng, chạy bù, xem lịch sử & chi phí, điều khiển tiến trình | Chỉ đọc `agnet.db`; chạy qua `procs.py` |
| 2 | Kho kịch bản (`page_library.py`, `library.py`) | Hiện có | Duyệt thư mục đầu ra, xem kịch bản. Nút Duyệt / Viết lại / Loại **chưa kiểm chứng đầy đủ** | Thư mục đầu ra (`output_root`) |
| 3 | Cài đặt luồng (`page_flows.py`, `flows_store.py`) | Hiện có | Chủ đề, nền tảng, thời lượng, giờ chạy + múi giờ, số tin 1–50, trần chi phí/ngày, KOC | `config/flows.yaml` |
| 4 | Cài đặt chung (`page_settings.py`, `env_store.py`) | Hiện có | Ngôn ngữ, chủ đề, số agent song song 1–8, nhà cung cấp Gemini, khoá (che) | `config/app_settings.json`; khoá trong `.env` |
| 5 | Tài khoản Claude (`page_account.py`, `auth.py`) | Hiện có | Trạng thái đăng nhập, đăng nhập/đăng xuất, cảnh báo khoá API | Phiên đăng nhập của Claude CLI (không lưu ở dự án) |
| 6 | **Gemini** | Có (02/10) | Bật/tắt, xem thang model và model đang nghỉ, nút `probe()`, bật/tắt `gemini_fallback`, chu kỳ làm mới | `config/app_settings.json`; trạng thái nghỉ ở `config/gemini_models.json`; khoá `.env` |
| 7 | **Đội agent** | Có (02/10) | Xem & sửa engine (`claude`/`gemini`) và **model của từng agent**, bật/tắt agent; mở prompt để đọc | Frontmatter `.claude/agents/*.md` (code ghi, không để LLM ghi); thay đổi qua ghi nguyên tử + test `test_agents_files` |
| 8 | **Hợp đồng & tỉ lệ đạt** | Có (02/10) | Số mục tối thiểu, nguồn bắt buộc, cửa sổ tuổi tin theo agent; xem `compliance` pass/fail theo ngày | Cấu hình hợp đồng (`config/`, do B2 chốt); số đo ở `agnet.db` |
| 9 | **Nhân vật KOC** | Có (02/10) | Xem/sửa `identity`, xem ảnh tham chiếu, gán nhân vật cho luồng, xem prompt từng cảnh. **Không cho sửa** Lớp B, `negative`, `consistency_lock` (quy tắc cứng số 5) | `config/characters/*.json`; gán ở `flows.yaml` |
| 10 | **Chi phí & hạn mức** | Có (02/10) | Trần `max_cost_usd_per_day`, hạn mức Gemini còn lại, cảnh báo gần trần | `flows.yaml`; số liệu ở `cost_ledger` trong `agnet.db` |

Với 10 mục, phím Ctrl+1…9 không phủ hết mục 10; cần bổ sung phím hoặc gộp mục khi làm B5.

### 18.10 Ràng buộc khi sửa từ giao diện

Mọi điều khiển chỉ **ghi cấu hình**, không ghi đầu ra kịch bản (đó là việc của `agnet/pipeline/export.py`). Mục "Đội agent" sửa tệp agent nên phải: chỉ cho đổi `model`/`engine`/bật-tắt, **không** cho sửa `tools` thành có Write/Edit (agent không có quyền ghi), và chạy lại kiểm tra tệp agent sau mỗi lần lưu. Luồng `sensitive` không được tắt `human_review` từ giao diện (quy tắc cứng số 3).

### 18.11 Đã kiểm chứng và chưa kiểm chứng

**Đã kiểm chứng (đo thật):**
- Chạy Claude bằng tài khoản không cần khoá; khoá API ghi đè tài khoản; `setting_sources=[]` + `tools=` giảm 88,6% token mỗi lượt; khoá daemon sửa xong; ứng dụng desktop mở được.
- **Gemini 02/10/2026** (18.2): liệt kê được 44 model; gọi thường chạy với `gemini-3.8-flash`; 404 với dòng 2.5; 429 `limit: 0` với `3.1-pro-preview`; **429 bám nguồn trên mọi model thử**; 503 thoáng qua.

**Chưa kiểm chứng:**
- **Bám nguồn Gemini hoàn toàn chưa chạy được lần nào** → chất lượng bám nguồn, tỉ lệ đạt hợp đồng, thang chi phí Google khi bật thanh toán đều chưa biết. Không có cơ sở nào để khẳng định phương án (a) sẽ gỡ 429 cho tới khi `probe()` chạy lại sau khi bật.
- Bám nguồn có dùng được cùng lúc với đầu ra JSON ép schema hay không (vì vậy prompt yêu cầu JSON, KHÔNG ép schema).
- Chất lượng Gemini cho việc không cần nguồn (phân loại/gom cụm/viết nháp) so với Claude **chưa đo**; mới biết là gọi được.
- Lần chạy thật Claude 02/10/2026 chết ở agent đầu tiên (lỗi làm mới token); chưa có số đo chi phí/thời gian của một kịch bản trọn vẹn.
- Gói Claude có đủ hạn mức cho 20 tin/ngày hay không — càng đáng lo nếu chọn (b).
- Cấu hình hiện đang để `max_cost_usd_per_day: 1` và `daily_quota: 1` (cho lần chạy thử); `$1` chắc chắn quá thấp cho một kịch bản dài, cần đặt lại trước khi chạy thật.
- Các mục giao diện 6–10 chưa tồn tại hoặc đang làm; mô tả ở 18.9 là thiết kế, không phải hiện trạng.

---

## 19. Bước tiếp theo

Trạng thái (02/10/2026, 405 test xanh): **B1–B5 và 10 mục giao diện đã có mã + test; GĐ3 (kiểm kê, rà mã, bảo mật, đối chiếu quy tắc cứng) đã chạy và các lỗi tìm được đã vá (`tests/test_hardening.py`); B6 (chạy thử 1 tin thật) CHƯA làm** vì bám nguồn Gemini đang bị 429.

| # | Việc | Ai | Trạng thái |
|---|---|---|---|
| 1 | Bật thanh toán/hạn mức tìm kiếm Google cho khoá, bấm "Kiểm tra khóa" (mục Gemini) tới khi báo "bám nguồn: ok" | Người dùng | **Chặn mọi lần chạy thật** |
| 2 | Thu hồi khoá Gemini đã lộ trong chat, tạo khoá mới, dán vào mục Gemini | Người dùng | Cần làm |
| 3 | Đặt lại `max_cost_usd_per_day` (hiện 1) và `daily_quota` (hiện 1); `run_timeout_min` 240 cho 20 tin | Người dùng | Cần làm |
| 4 | Chạy thử **1 tin thật**, đọc `logs/agnet.log` + `cost_ledger` để biết chi phí và agent chậm; kiểm chứng thử lại OAuth/khởi động ấm | Người dùng + B6 | Chưa làm |
| 5 | Siết nghiệm thu bám nguồn (hiện khớp theo tên miền) dựa trên dữ liệu `groundingMetadata` thật; nối `core/scoring.py` vào pipeline; dừng được luồng Gemini khi timeout | Dev | Chưa làm (cần số liệu thật) |
| 6 | Chốt schema `script.json` với phần mềm dựng video thật | Người dùng | Chưa làm |
| 7 | Chọn 1 nhân vật KOC (mục 17.7) → ảnh gốc + bảng 9 ảnh → chạy thử 3 cảnh trước khi bật `koc.enabled` | Người dùng | Chưa làm |
| 8 | Đăng ký tác vụ Windows (`scripts/register_task.ps1`), nhập Telegram vào `.env` | Người dùng | Chưa làm |
