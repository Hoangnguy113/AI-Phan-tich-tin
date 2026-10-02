# Phân tích & xếp hạng 10 cốt truyện theo mức ưu tiên

> Ngày phân tích: 02/10/2026 · Đối tượng: `Claude outputs/COT_TRUYEN_2026-10-01.md` (10 cốt truyện, lập 01/10/2026)
> Mục đích: trả lời "cốt truyện nào nên làm trước, cái nào hút người xem hơn" và chỉ ra chỗ hỏng phải sửa trước khi viết kịch bản.

---

## 0. Đọc cảnh báo này trước

**Đây KHÔNG phải Trend Score.** Theo `.claude/skills/agnet-trend-scoring/SKILL.md` và quy tắc cứng số 1 của dự án, Trend Score chỉ có giá trị khi mọi thành phần dựa trên số liệu thật. Ba thành phần quan trọng nhất của Trend Score — chiếm **55% trọng số** (`velocity` 0,22 + `volume` 0,18 + `engagement` 0,15) — **hiện không có dữ liệu**:

- Chưa có connector số liệu thật (YouTube Data API, Google Trends, RSS) — xem mục "Chưa có" trong `CLAUDE.md`.
- Tài liệu cốt truyện không chứa view/giờ, % tăng truy vấn, hay tỉ lệ tương tác của video cùng đề tài.
- Cũng không có bước phân tích đối thủ (competitor-gap) nên `gap` chỉ suy luận được định tính, không đo được.

Vì vậy tôi **không chấm Trend Score và không ước lượng cho đủ**. Nếu đưa 10 đề tài này vào `agnet.core.scoring.rank()`, code sẽ loại sạch cả 10 vì thiếu thành phần — đó là hành vi đúng, không phải lỗi.

Thay vào đó, bảng dưới là **Điểm ưu tiên biên tập**: chấm bằng những gì đọc được và kiểm được từ chính tài liệu (ngày nguồn, chất lượng nguồn, số ô ⚠️ chặn phần lời thoại, chất lượng hook, độ rộng khán giả). Nó trả lời được "nên quay cái nào trước", nhưng **không thay thế** việc đo nhu cầu thật khi đã có connector.

### Thang điểm và trọng số

| Thành phần | Trọng số | Chấm bằng gì |
|---|---|---|
| `suc_hut` | 0,20 | Chất lượng hook 0–5s, vòng tò mò mở/đóng, số liệu dễ nhớ và dễ chụp màn hình |
| `impact` | 0,14 | Hệ quả thật với người xem: tiền, sức khoẻ, nghĩa vụ pháp lý |
| `reach` | 0,14 | Độ rộng tập khán giả Việt Nam có thể chạm tới |
| `evergreen` | 0,12 | Còn giá trị sau 30 ngày, có được xem lại/lưu lại |
| `freshness` | 0,12 | **Tuổi của mốc tin, tính theo ngày ghi trong tài liệu** (đây là dữ kiện kiểm được, không phải velocity) |
| `source_trust` | 0,10 | Nguồn gốc: văn bản pháp luật / cơ quan nhà nước > báo lớn > trang tổng hợp |
| `readiness` | 0,11 | Nghịch đảo của số ô ⚠️ **chặn phần lõi** lời thoại |
| `risk_low` | 0,07 | Nghịch đảo của rủi ro QA / pháp lý / an toàn thân thể |

---

## 1. Kết quả xếp hạng 1 → 10

| Hạng | # | Cốt truyện | Tổng | Hút xem | Sẵn sàng |
|---:|---:|---|---:|---:|---:|
| **1** | 1 | Cúm mùa: có nên tự mua thuốc? | **80,0** | 81,2 | 76,8 |
| **2** | 2 | Ngủ bao nhiêu tiếng là đủ? | **79,9** | 80,6 | 78,3 |
| **3** | 3 | Lương bao nhiêu thì đóng thuế từ 2026? | **77,1** | 83,4 | 60,9 |
| **4** | 8 | Video AI phải gắn nhãn từ 2026 | **70,5** | 77,1 | 53,6 |
| **5** | 7 | AI agent: 5 câu hỏi trước khi bấm "Cho phép" | **68,0** | 70,1 | 62,8 |
| **6** | 4 | Lãi suất tiết kiệm 4,75% hay 9%? | **67,4** | 72,0 | 55,6 |
| **7** | 9 | Retinol và vitamin C | **65,7** | 65,9 | 65,1 |
| **8** | 5 | Bỏ thuế khoán: hộ kinh doanh | **60,0** | 64,0 | 49,8 |
| **9** | 6 | AI trực điện thoại tiếng Việt | **59,0** | 57,2 | 63,6 |
| **10** | 10 | Bốn món ăn ngày se khô | **50,2** | 52,3 | 44,6 |

### Bảng thành phần (xếp theo hạng)

| # | suc_hut | impact | reach | evergreen | freshness | source_trust | readiness | risk_low |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 80 | 85 | 90 | 55 | **95** | 85 | 75 | 68 |
| 2 | 88 | 78 | 88 | 88 | 55 | 80 | **82** | 70 |
| 3 | 85 | **95** | **95** | 75 | 62 | 88 | *40* | 55 |
| 8 | 80 | 90 | 62 | 82 | 70 | 85 | *35* | *38* |
| 7 | 74 | 65 | 55 | 85 | 72 | *38* | 68 | **90** |
| 4 | **92** | 82 | 60 | *25* | 88 | 78 | *42* | *45* |
| 9 | 84 | 55 | 72 | **92** | *15* | 62 | 70 | 62 |
| 5 | 72 | 90 | *48* | 68 | *35* | 70 | *30* | 52 |
| 6 | 64 | *52* | *35* | 50 | 85 | *45* | 65 | 88 |
| 10 | 66 | *40* | 68 | 70 | *8* | *42* | 50 | *40* |

(**đậm** = mạnh nhất bảng · *nghiêng* = điểm yếu đáng lo)

---

## 2. Thứ hạng đổi thế nào nếu đổi mục tiêu

Xếp hạng tổng ở trên cân cả "hút xem" và "có làm được ngay không". Nếu chỉ chọn một mục tiêu, thứ tự khác rõ rệt — đây là chỗ bạn nên tự quyết:

| Hạng | Chỉ tối ưu LƯỢNG XEM | Chỉ tối ưu TỐC ĐỘ LÊN SÓNG |
|---:|---|---|
| 1 | #3 Thuế TNCN (83,4) | #2 Giấc ngủ (78,3) |
| 2 | #1 Cúm mùa (81,2) | #1 Cúm mùa (76,8) |
| 3 | #2 Giấc ngủ (80,6) | #9 Retinol (65,1) |
| 4 | #8 Nhãn AI (77,1) | #6 AI trực máy (63,6) |
| 5 | #4 Lãi suất (72,0) | #7 AI agent (62,8) |
| 6 | #7 AI agent (70,1) | #3 Thuế TNCN (60,9) |
| 7 | #9 Retinol (65,9) | #4 Lãi suất (55,6) |
| 8 | #5 Thuế khoán (64,0) | #8 Nhãn AI (53,6) |
| 9 | #6 AI trực máy (57,2) | #5 Thuế khoán (49,8) |
| 10 | #10 Món ăn (52,3) | #10 Món ăn (44,6) |

**Điều cần nhớ**: hai đề tài hút xem nhất (#3 thuế, #8 nhãn AI) lại **nằm cuối bảng sẵn sàng**. Đó không phải trùng hợp — chúng hút xem vì chạm vào tiền và nghĩa vụ pháp lý, và chính vì thế mà sai một con số là hậu quả thật. Đừng đảo thứ tự để chạy theo lượt xem mà bỏ bước xác minh.

---

## 3. Phân tích từng cốt truyện

### Hạng 1 — #1 Cúm mùa: có nên tự mua thuốc? (80,0)

**Vì sao đứng đầu**: đây là đề tài duy nhất có mốc tin **cách ngày lập tài liệu đúng 1 ngày** (Cục Phòng bệnh, 01/10/2026) — `freshness` 95, cao nhất bảng. Cộng thêm `reach` 90 (mùa cúm, nhà nào cũng có người ho) và nguồn là Bộ Y tế qua Nhân Dân / Báo Tin tức.

**Tài sản mạnh nhất**: động lực chia sẻ tự nhiên. CTA "gửi cho người thân trên 65 tuổi hoặc đang mang thai" không phải lời kêu gọi suông — 5 nhóm nguy cơ có nguồn chính là 5 lý do để người xem gửi video cho người cụ thể trong nhà. Đây là cơ chế lan truyền tốt nhất trong cả 10 cốt truyện.

**Chỗ phải sửa**: phân đoạn 1:30–3:30 "Cúm hay cảm lạnh?" là 320 từ (**20% lời thoại**) và đang treo ⚠️ chờ nguồn Bộ Y tế. Đây là ô trống dễ bịt nhất trong cả bộ — một trang hướng dẫn của Bộ Y tế là xong. Làm việc này trước.

**Điểm yếu cố hữu**: `evergreen` chỉ 55. Câu "tăng nhẹ" chỉ đúng tới ngày nguồn đăng. Video này **có hạn sử dụng tính theo tuần** — nếu không quay trong 1–2 tuần, phải cập nhật lại số liệu hoặc bỏ.

---

### Hạng 2 — #2 Ngủ bao nhiêu tiếng là đủ? (79,9)

**Vì sao sát hạng 1**: điểm tổng gần như bằng #1 nhưng vì lý do ngược lại. #1 thắng bằng độ nóng, #2 thắng bằng **cấu trúc**: `evergreen` 88 và `readiness` 82 — cao nhất bảng về mức sẵn sàng.

**Tài sản mạnh nhất**: hook có xung đột số học thật — "một chuyên gia nói 6–7 tiếng, một nghiên cứu 9.641 người nói 7–8 tiếng, ai đúng?" Và câu trả lời không phải mẹo rẻ: hai con số nói về **tối thiểu** và **tối ưu**, hai thứ khác nhau. Vòng tò mò mở ở 0:30, đóng ở 7:15 — đóng đúng chỗ, không đóng quá sớm. Bộ số 9.641 người / 15,5 năm / 27% / 28% rất dễ nhớ và dễ chụp màn hình.

**Chỗ phải sửa**: hai việc rẻ. (a) Ngày đăng bài Thanh Niên hiện **chỉ suy ra từ đường dẫn** (có vẻ 23/08/2025) — nếu đúng thì bài đã hơn một năm, **cấm nói "mới công bố"**. (b) Lấy liên kết gốc Scientific Reports để xác nhận đây là nghiên cứu quan sát.

**Bẫy QA nghiêm trọng**: tiêu đề số 2 ("Ngủ nhiều hơn 8 tiếng cũng có thể là dấu hiệu xấu?") đang treo ⚠️ vì nghiên cứu là quan sát. Dùng tiêu đề số 1. Và trong lời thoại, "liên quan" không bao giờ được đổi thành "gây ra" — đây là lỗi nặng theo rubric QA, trượt thẳng.

---

### Hạng 3 — #3 Lương bao nhiêu thì đóng thuế từ 2026? (77,1)

**Đề tài hút xem nhất cả bộ** (`Hút xem` 83,4): `impact` 95 và `reach` 95 — cao nhất cả hai cột. Mọi người đi làm ăn lương đều liên quan. Nguồn là Nghị quyết 110/2025/UBTVQH15 và Luật TNCN 2025 — `source_trust` 88.

**Tài sản mạnh nhất**: video này sửa **đúng một hiểu lầm phổ biến nhất** — 15,5 triệu là mức *giảm trừ*, không phải *ngưỡng lương*. Phần lớn báo chí chỉ in lại con số; gần như không ai giải thích chênh lệch này bằng ví dụ tính từng bước. Đó là khoảng trống thật. Ba ví dụ tính (20 triệu → 225.000đ; 25 triệu → 475.000đ; 25 triệu + 1 người phụ thuộc → 165.000đ) là nội dung người xem sẽ lưu lại.

**Vì sao không đứng hạng 1 dù hút xem nhất**: `readiness` 40. Hai lỗ hổng chặn ngang:

1. **Mốc các bậc 10% / 20% / 30% chưa kiểm.** Tài liệu ghi thẳng "Để trống tới khi xác minh". Phân đoạn 3:30–5:30 (320 từ) là bảng thuế 5 bậc — **không thể viết khi còn trống 3 trong 5 bậc**.
2. **Ngày áp dụng chưa rõ: 01/01/2026 hay 01/07/2026.** Đây không phải chi tiết phụ — nó là **tiền đề của tiêu đề** ("từ 2026"). Luật có hiệu lực 01/07/2026 nhưng mức giảm trừ và biểu 5 bậc áp dụng từ kỳ tính thuế 2026. Nói sai mốc này là nói sai toàn bộ video.

**Việc cần làm**: đọc văn bản gốc Nghị quyết 110/2025/UBTVQH15 và Luật TNCN 2025 trên cổng văn bản chính thức. Khi hai lỗ này bịt xong, #3 sẽ **vượt lên hạng 1**.

---

### Hạng 4 — #8 Video AI phải gắn nhãn từ 2026 (70,5)

**Giá trị chiến lược cao nhất cả bộ, không phải vì lượt xem.** Đề tài này điều chỉnh **chính sản phẩm Agnet**: nhân vật KOC là người AI, nên mỗi video dùng KOC đều rơi vào diện gắn nhãn. Nghiên cứu cho video này **đồng thời là nghiên cứu pháp lý cho dự án của bạn** — một công đôi việc. Tài liệu cốt truyện đã đặt cảnh báo này ở đầu file, và đúng.

**Tài sản mạnh nhất**: `impact` 90 + `evergreen` 82. Luật có hiệu lực nhiều năm, nên đây là video tham chiếu — loại được dẫn lại, được lưu, được gửi cho nhau trong giới làm nội dung. 15 phút ở đây là **chính đáng** (4 phần rõ + 4 tình huống áp dụng), khác với #4 nơi 15 phút là rủi ro.

**Vì sao chỉ hạng 4**: `readiness` 35 và `risk_low` 38 — **đôi điểm thấp nhất cả bộ về mặt làm được**.

- **Ngày hiệu lực Nghị định 142/2026 không đọc được**: tài liệu ghi nguồn chỉ trích được chuỗi "1-5", không rõ năm. Thế mà tiêu đề số 2 lại hứa "4 cách làm hợp lệ theo Nghị định 142/2026" — **hứa theo một văn bản mà bạn chưa biết nó có hiệu lực khi nào**.
- **Mức xử phạt cụ thể: nguồn không nêu.**
- **Ngưỡng "chỉnh sửa nhỏ" cần luật sư**, và tài liệu khuyến nghị luật sư đọc trước khi đăng.

**Hậu quả nếu sai**: người làm nội dung hành động theo video của bạn và bị xử phạt. Đây là con đường gây hại trực tiếp nhất về mặt pháp lý trong cả 10 đề tài. Ngược lại, đây cũng là đề tài mà khâu `human_review` bắt buộc của dự án **thật sự đáng tiền**.

**Việc cần làm**: đọc toàn văn Luật Trí tuệ nhân tạo 2025 và Nghị định 142/2026/NĐ-CP trên cổng văn bản chính thức, rồi mới viết. Đừng viết từ bản tóm tắt báo chí.

---

### Hạng 5 — #7 AI agent: 5 câu hỏi trước khi bấm "Cho phép" (68,0)

**Vì sao vào top 5 dù nguồn yếu nhất**: `evergreen` 85 và `risk_low` 90. Khung "5 câu hỏi trước khi cấp quyền" là tài sản bền — nó còn dùng được khi Muse, Jev và mọi cái tên trong bản tin đã bị lãng quên. Và vì không nhạy cảm, nó **không cần `human_review`** — đường ra sóng rẻ và nhanh nhất trong nhóm có `evergreen` cao.

**Khuyết điểm nặng nhất: `source_trust` 38, thấp nhất cả bộ.** Mốc tin (Meta Muse lên macOS) đến từ `aiagentsdirectory` — một trang **tổng hợp**, **một nguồn duy nhất**, và bản tin cùng loạt ngày 27/09 **trả về 404**. Thông báo chính thức của Meta chưa đọc. Trong cùng bản tin còn có tin đồn về Anthropic mà tài liệu đã đúng khi gạch bỏ.

**Nhưng đây là khuyết điểm sửa được bằng cách đổi khung**: 5 câu hỏi là khung của biên tập, **không phụ thuộc vào Muse**. Nếu không xác minh được Muse, thay mốc tin bằng bất kỳ bản phát hành AI agent nào có thông báo chính thức — giá trị video còn nguyên. Đó là lý do nó xếp trên #4 dù nguồn kém hơn nhiều.

**Rủi ro dựng phim cần nói rõ**: phân đoạn 5:00–9:30 là **720 từ / 4,5 phút / 37% video** cho một danh sách 5 mục, mỗi mục ~54 giây. Đây là khối đơn điệu dài nhất trong cả 10 cốt truyện. Director phải có 5 cách hình hoá khác nhau, không thì tụt giữ chân ở phút 6–8.

---

### Hạng 6 — #4 Lãi suất tiết kiệm 4,75% hay 9%? (67,4)

**Hook mạnh nhất cả bộ**: `suc_hut` 92. "Cùng một ngân hàng, một chỗ 4,75%, một chỗ trên 9%. Đây không phải lỗi gõ máy." Cộng với con số tiền thật — 500 triệu gửi 3 tháng chênh 4.312.500đ — và chi tiết có vị "nội bộ" nhưng **có nguồn thật**: phần lớn mức 9% áp dụng qua mã giới thiệu nhân viên, **không niêm yết công khai** (VnExpress 23/09/2026). Đó là thứ làm người ta bấm vào.

**Nhưng đây là cốt truyện có lỗi cấu trúc nghiêm trọng nhất cả bộ:**

> **Vòng tò mò của video có payoff chưa được xác minh.**
>
> Tài liệu mở vòng ở 0:40 — "có một câu hỏi ngân hàng ít khi chủ động nói, tôi để cuối video" — và đóng ở 12:00–14:00 bằng "sản phẩm này có được bảo hiểm tiền gửi không". Nhưng mục "Cần xác minh" lại ghi: *"Chứng chỉ tiền gửi có thuộc diện bảo hiểm tiền gửi không"* — **chưa biết**.
>
> Nghĩa là: bạn hứa một câu trả lời ở phút 0:40, và ở phút 12 bạn vẫn chưa có câu trả lời đó. Nếu viết kịch bản bây giờ, hoặc phải trả lời mơ hồ (vỡ lời hứa, trượt QA), hoặc phải đổi payoff (phải viết lại cả vòng mở).

**Các điểm yếu khác**:
- `evergreen` 25, **thấp nhất cả bộ**. Bảng lãi suất chết trong vài tuần. Tài liệu tự ghi "lãi suất đổi nhanh".
- **Kỳ hạn gắn với các mức 9% chưa trích được** — nên không được nói "gửi 12 tháng được 9%". Mà kỳ hạn chính là thông tin người xem cần nhất.
- `risk_low` 45: nêu tên 9+ ngân hàng kèm con số, trong một video về tiền. Lệnh cấm "không nói ngân hàng X an toàn / không an toàn" phải được giữ tuyệt đối.
- 15 phút cho một đề tài bảng số là dài. Cân nhắc cắt xuống 10–12 phút.

**Kết luận về #4**: hook tốt nhất, nền móng yếu nhất. **Đừng viết cho tới khi trả lời được câu bảo hiểm tiền gửi** (nguồn: Bảo hiểm tiền gửi Việt Nam hoặc NHNN). Và vì số liệu rữa nhanh, đề tài này chỉ nên làm khi pipeline đã chạy được end-to-end trong vài ngày — hiện tại chưa chứng minh được điều đó (lần chạy thật 01/10 bỏ dở).

---

### Hạng 7 — #9 Retinol và vitamin C (65,7)

**Hai mặt đối lập rõ nhất cả bộ**: `evergreen` 92 (cao nhất) nhưng `freshness` 15 (gần thấp nhất). Nguồn Vinmec cập nhật **22/07/2024 — hơn 2 năm**. Tài liệu tự thừa nhận: "không phải xu hướng 2026". Trên thang *xu hướng*, đây là đề tài yếu nhất nhóm trên. Trên thang *thư viện nội dung*, nó thuộc nhóm mạnh nhất.

**Tài sản mạnh nhất**: hook cụ thể và dễ nhớ bất thường — "một con số pH giải thích vì sao hai hoạt chất này cần cách nhau 20 phút". pH 2,5–3,5 so với 5,5–6, và mốc "20 phút" là thứ người xem chụp màn hình và lưu lại. Thêm nữa đây là **phá bỏ định kiến có nguồn bệnh viện**: "nghe nói retinol và vitamin C kỵ nhau — một bệnh viện nói điều ngược lại". Phá định kiến + dẫn nguồn uy tín là công thức tương tác ổn định.

**Lợi thế vận hành lớn nhất cả bộ**: 6 phút, TikTok/YouTube. **Rẻ nhất, nhanh nhất, dễ cắt Shorts nhất.** Nếu mục tiêu là có một video hoàn chỉnh ra lò sớm để kiểm chứng pipeline, đây là ứng viên tốt nhất về mặt chi phí.

**Nhưng lệch cấu hình luồng** (xem mục 4): 6 phút **nằm ngoài** `duration_mix {8-12: 1}` của luồng duy nhất đang bật; TikTok không khớp `platform: youtube`; KOC-01 Mai và khán giả làm đẹp không khớp `audience: "Người 30–55 tuổi quan tâm phòng bệnh"`. Muốn làm #9 thì **phải tạo luồng mới**, không chạy ghép được.

**Chỗ phải sửa**: nguồn đơn lẻ (chỉ Vinmec). Ba việc cần nguồn da liễu: nồng độ và thời gian làm quen; retinol và thai kỳ; người da nhạy cảm. Đáng chú ý — **lời khuyên ở phân đoạn kết (5:15–6:00) hiện chưa có nguồn**, tài liệu ghi rõ "chưa có nguồn trong đợt này". Kết video bằng một khuyến nghị y tế không nguồn là chỗ QA sẽ chặn.

---

### Hạng 8 — #5 Bỏ thuế khoán: hộ kinh doanh (60,0)

**Nghịch lý của cốt truyện này**: `impact` 90 — ngang #8, cao hơn #1 và #2. Với hộ kinh doanh, đây không phải nội dung "hay biết" mà là **nghĩa vụ bắt buộc**: hoá đơn điện tử từ 1 tỷ, sổ sách từ 500 triệu, tài khoản ngân hàng riêng, khai theo quý từ 30/04/2026. Động lực xem cực mạnh. Thiết bị tương tác "bạn thuộc nhóm nào trong 4 nhóm doanh thu?" là một trong những cách giữ chân tốt nhất cả bộ.

**Vậy vì sao chỉ hạng 8?** Vì **toàn bộ nền tảng dữ kiện đã cũ, và cũ theo cách tệ nhất**:

> Nguồn chính là VietNamNet **18/12/2025** — viết **trước** mốc 01/01/2026, về một đợt chuyển đổi mà **nay đã diễn ra xong 9 tháng**. Tức là bạn đang chuẩn bị làm video hướng dẫn "cần làm gì để chuẩn bị" cho một việc đã xảy ra.

Thêm vào đó: tỷ lệ tính thuế theo ngành chưa kiểm; trạng thái hướng dẫn hiện hành chưa kiểm; và bài Tuổi Trẻ 28/12/2025 "Chậm hướng dẫn, hộ kinh doanh lo lắng với ngưỡng tính thuế" **chỉ thấy tiêu đề trong kết quả tìm kiếm, chưa mở đọc**. `readiness` 30 — thấp nhất cả bộ, và `freshness` 35.

`reach` 48 cũng là hạn chế thật: hộ kinh doanh hẹp hơn người đi làm ăn lương (#3) nhiều.

**Việc cần làm**: đây là đề tài **phải nghiên cứu lại gần như từ đầu**, không phải bịt vài lỗ. Trạng thái pháp lý hiện hành tháng 10/2026 mới là nội dung; bài tháng 12/2025 chỉ còn là bối cảnh. Nếu nghiên cứu lại tử tế, góc hay nhất bây giờ không còn là "chuẩn bị gì" mà là **"9 tháng rồi, hộ kinh doanh vướng ở đâu"** — và đó là một cốt truyện khác, mạnh hơn.

**Gợi ý giữ nguyên từ tài liệu**: ghép #3 + #5 thành "Thuế 2026 cho người đi làm và hộ kinh doanh" (~16–17 phút). Hợp lý, vì #3 gánh được phần `reach` mà #5 thiếu.

---

### Hạng 9 — #6 AI trực điện thoại tiếng Việt (59,0)

**Điểm mạnh thật**: `freshness` 85 (Webie 29/09/2026) và `risk_low` 88 (không nhạy cảm, không cần duyệt tay). Và một lợi thế hiếm: **khoảng trống nội dung rõ ràng** — tiếng Việt vừa mới được thêm vào nền tảng năm 2026, nên gần như chưa có nội dung Việt về chủ đề này. Lợi thế người đi trước là thật.

**Nhưng ba điểm yếu cộng dồn**:

1. **`reach` 35 — thấp nhất cả bộ.** Khán giả là chủ tiệm nhỏ có lượng gọi đến đủ nhiều để cần tự động hoá. Đây là tập hẹp, và là tập khó chạm nhất bằng YouTube phổ thông ở Việt Nam.
2. **`source_trust` 45.** Một bài duy nhất trên một trang gần giới nhà cung cấp, và **mọi con số nổi bật đều do nhà cung cấp tự báo**: 35%, 30%, 50%, 9–30%, 69%. Tài liệu xử lý đúng — dành hẳn phân đoạn 3:30–5:00 (240 từ) để nói "đây là số theo bài, không kiểm độc lập". Nhưng hãy thấy ý nghĩa của việc đó: **bạn dùng 240 từ của video để hạ giá trị bằng chứng của chính mình**. Về biên tập thì liêm chính; về nền móng thì yếu.
3. Con số thị trường 2,4 tỷ → 47,5 tỷ USD (2034) là **dự báo** — hầu như không mang thông tin.

**Giá trị còn lại**: khung "thử 1 tuần, 5 bước" là của biên tập và là phần dùng được lâu. Nếu làm, hãy xem đây là **video kỹ năng vận hành cho chủ tiệm nhỏ**, đừng xem là bản tin công nghệ.

**Gợi ý từ tài liệu**: ghép #6 + #7 thành "AI vào đời sống: tiệm nhỏ và máy cá nhân" (~18–19 phút). Hợp lý — #7 bù `reach` và `evergreen` cho #6, #6 bù `freshness` cho #7. Ghép lại thì cặp này mạnh hơn hẳn từng cái riêng.

---

### Hạng 10 — #10 Bốn món ăn ngày se khô (50,2)

**Đây là cốt truyện tôi khuyên hoãn, và lý do không phải vì nó dở.**

Khung biên tập thật ra **dũng cảm và đúng tinh thần dự án**: lấy 4 món Đông y rồi phân loại thành ba nhóm — "nguồn nêu theo Đông y", "khoa học chưa rõ", "cần thận trọng". Tài liệu còn ghi thẳng: nếu không tìm được bằng chứng khoa học thì **nói "chưa có bằng chứng", đó cũng là nội dung**. Đó là thái độ đúng.

**Nhưng có bốn vấn đề, và vấn đề thứ nhất là vấn đề cấu trúc:**

1. **Lời hứa của video có thể không trả lời được.** Tiêu đề hỏi "cái gì có cơ sở?" nhưng nguồn CDC Quảng Ninh chỉ mô tả công dụng theo Đông y, **không có bằng chứng lâm sàng**. Khả năng cao kết luận sẽ là "cả bốn món đều chưa có bằng chứng". Trung thực, nhưng là một đường cong giữ chân đi xuống: người xem ở lại 8 phút để nghe "không có gì được chứng minh". Rubric QA sẽ phải trả lời câu "video có giữ đúng lời hứa không".
2. **`freshness` 8 — thấp nhất cả bộ.** Nguồn đăng **03/11/2022**, bốn năm trước. Không có mốc tin nào.
3. **An toàn thân thể: ba điểm chưa có nguồn, và đều là điểm thật.** Tài liệu tự liệt kê: *xuyên bối mẫu là vị thuốc cần thầy thuốc kê*; *loại hạnh nhân dùng là gì (ngọt hay đắng)*; *người đái tháo đường và đường phèn*. Đây là video dạy nấu một món **có vị thuốc trong công thức**, phát cho khán giả Facebook, mà cả ba lưu ý an toàn đều đang trống. Đó là con đường gây hại thân thể trực tiếp nhất trong cả 10 đề tài — `risk_low` 40.
4. `impact` 40 — thấp nhất. Món ăn dễ chịu ngày se khô, không phải việc hệ quả lớn.

**Điểm mạnh không nên bỏ qua**: nền tảng Facebook + nội dung ẩm thực truyền thống là tổ hợp có tỉ lệ chia sẻ cao ở Việt Nam, và `evergreen` 70 theo mùa (thu đông, lặp lại hằng năm). Nếu bịt được ba lỗ an toàn và tìm được nguồn y khoa, đây là một video theo mùa tốt — **cho mùa sau**, không phải bây giờ.

---

## 4. Những phát hiện phải xử lý trước khi viết bất cứ kịch bản nào

### 4.1 Chỉ có 1 luồng đang cấu hình — 6 trong 10 cốt truyện không có luồng để chạy

`config/flows.yaml` hiện chỉ có **một** luồng: `suckhoe-yt-sang` (sức khoẻ · YouTube · `audience: "Người 30–55 tuổi tại Việt Nam, quan tâm phòng bệnh"` · `duration_mix {8-12: 1}` · `daily_quota: 1` · `sensitive: true`).

| Cốt truyện | Khớp luồng hiện có? |
|---|---|
| #1 (10 phút, sức khoẻ, YouTube) | ✅ khớp hoàn toàn |
| #2 (12 phút, sức khoẻ, YouTube) | ✅ khớp hoàn toàn |
| #10 (8 phút, Đông y/ẩm thực, Facebook) | ⚠️ thời lượng khớp, nền tảng và chủ đề lệch |
| #9 (6 phút, làm đẹp, TikTok) | ❌ **6 phút nằm ngoài `duration_mix {8-12}`**, nền tảng và khán giả lệch |
| #3 #5 (tài chính/thuế) | ❌ chưa có luồng tài chính |
| #6 #7 (công nghệ AI) | ❌ chưa có luồng công nghệ |
| #4 #8 (15 phút) | ❌ **15 phút nằm trong bucket `15-20` đang đặt quota 0** |

**Hệ quả thực tế**: ngay bây giờ, chỉ #1 và #2 chạy được qua pipeline mà không sửa cấu hình. Mọi cốt truyện khác cần tạo luồng mới (tài chính, công nghệ, làm đẹp) hoặc mở bucket thời lượng. Đây là việc cấu hình, không phải việc viết.

### 4.2 Đã kiểm bằng code — hai điểm này tốt

Tôi đã chạy kiểm chứng bằng code, không bằng mắt:

- **Toán thời lượng/số từ: cả 10 cốt truyện đều đúng.** Tổng số từ các phân đoạn khớp `phút × 160 wpm`, lệch tối đa 1 từ do làm tròn. Đối chiếu với `agnet.core.timing.word_budget()`: 6 phút→960, 8→1280, 9→1440, 10→1600, 12→1920, 15→2400 — khớp hết. Tài liệu đã tính đúng ngân sách từ.
- **Chống trùng 30 ngày: cả 10 tiêu đề đều sạch.** `python -m agnet dedup` trả `{"duplicate": false}` cho cả 10. Không có đề tài nào đụng kho 30 ngày.

### 4.3 Bốn lỗi cấu trúc phải sửa, theo mức nặng

1. **#4 — vòng tò mò có payoff chưa xác minh** (bảo hiểm tiền gửi). Nặng nhất, vì nó làm hỏng xương sống kịch bản, không chỉ một ô dữ liệu. Sửa trước khi viết.
2. **#3 — tiền đề tiêu đề chưa chốt** (01/01 hay 01/07/2026) **và 3/5 bậc thuế còn trống**. Một đề tài hút xem nhất bộ mà không viết được phân đoạn lõi.
3. **#8 — hứa theo một nghị định chưa biết ngày hiệu lực.** Tiêu đề số 2 nói "4 cách hợp lệ theo Nghị định 142/2026" trong khi nguồn chỉ trích được "1-5", không rõ năm.
4. **#5 — nền dữ kiện cũ 9 tháng và viết trước đợt chuyển đổi.** Cần nghiên cứu lại, không phải bịt lỗ.

### 4.4 Ba cốt truyện không có mốc tin nào

#9 (nguồn 22/07/2024), #10 (03/11/2022), và một phần #2 (nghiên cứu ~23/08/2025). Ba cái này **không được quảng bá như tin mới**. Chúng là nội dung thư viện — giá trị thật, nhưng phải định vị đúng, nếu không thì tiêu đề sẽ vi phạm `truth_check`.

### 4.5 Nhân vật KOC chưa dùng được cho luồng thật

Tài liệu gán KOC-01…KOC-05 cho 10 cốt truyện. Nhưng theo `CLAUDE.md`: nhân vật KOC mới có **chữ** (`status: draft`), **chưa có ảnh gốc / bảng 9 ảnh**, nên **chưa được bật cho luồng thật**. Nghĩa là các gán nhân vật trong tài liệu hiện là dự kiến, chưa thi hành được. Cộng thêm #8: mỗi video dùng KOC cần nhãn nội dung AI rõ ràng.

---

## 5. Khuyến nghị: thứ tự làm thật

Tôi khuyên **không** làm theo đúng thứ tự xếp hạng, vì xếp hạng là thước đo giá trị, còn thứ tự sản xuất phải tính cả việc "cái nào đang chặn cái nào". Thứ tự tôi khuyên:

**Bước 0 — trước mọi việc viết: #8, nhưng làm phần nghiên cứu pháp lý trước, chưa quay.**
Đọc toàn văn Luật Trí tuệ nhân tạo 2025 và Nghị định 142/2026/NĐ-CP. Lý do không phải vì #8 hạng 4, mà vì **nó quyết định cách bạn được phép làm 9 video còn lại** — mọi video dùng KOC đều cần nhãn AI. Nghiên cứu này là điều kiện tiên quyết của cả kho, và nó cũng chính là nội dung của #8. Nhờ luật sư xác nhận.

**Bước 1 — quay trước: #1 Cúm mùa.**
Hạng 1, khớp hoàn toàn luồng duy nhất đang bật, và **có hạn sử dụng tính theo tuần**. Chỉ cần bịt một lỗ (bảng phân biệt cúm/cảm lạnh từ nguồn Bộ Y tế). Để chậm là mất.

**Bước 2 — quay ngay sau: #2 Giấc ngủ.**
Hạng 2, `readiness` cao nhất, khớp luồng, không có hạn sử dụng. Đây là video nên dùng để **đo thật chất lượng viết và QA của pipeline** (hiện chưa có lần chạy thật nào hoàn tất) — vì nó không gấp, nên nếu agent chạy chậm hay treo, bạn không mất cơ hội nội dung nào.

**Bước 3 — song song, không quay: mở ba việc xác minh.**
(a) #3: mốc bậc thuế + ngày áp dụng. (b) #4: bảo hiểm tiền gửi + kỳ hạn các mức 9%. (c) #5: trạng thái pháp lý hộ kinh doanh tháng 10/2026. Khi (a) xong, **#3 lên hạng 1 và nên quay ngay** — nó là đề tài hút xem nhất cả bộ.

**Bước 4 — #7, hoặc ghép #6+#7.**
Không nhạy cảm nên không cần duyệt tay; `evergreen` cao. Đổi mốc tin sang một nguồn chính thức thay cho bản tin tổng hợp. Nếu ghép với #6 thành 18–19 phút thì mạnh hơn từng cái.

**Bước 5 — #9 nếu muốn một video rẻ ra lò nhanh.**
6 phút, dễ cắt Shorts, `evergreen` cao nhất. Nhưng phải tạo luồng làm đẹp riêng (TikTok, 6 phút không khớp luồng hiện có) và bổ sung nguồn da liễu cho phần kết.

**Hoãn: #10.** Chờ bịt ba lỗ an toàn (xuyên bối mẫu, loại hạnh nhân, đường phèn với người đái tháo đường) và tìm nguồn y khoa. Là video theo mùa — làm cho mùa thu đông sau cũng không mất gì.

---

## 6. Cách dùng lại phân tích này

Trọng số ở mục 0 là lựa chọn biên tập, không phải chân lý. Nếu bạn ưu tiên khác — ví dụ coi `freshness` quan trọng hơn `evergreen`, hoặc bỏ hẳn `readiness` vì bạn sẵn sàng đầu tư xác minh — thứ hạng sẽ đổi. Mục 2 đã cho thấy hai cực của việc đổi trọng số.

Và nhắc lại điều quan trọng nhất: **khi đã có connector số liệu thật (YouTube Data API, Google Trends), hãy chấm lại bằng Trend Score thật.** Bảng này tốt nhất trong điều kiện không có số liệu nhu cầu — nhưng nó vẫn chỉ là phán đoán biên tập về *mức độ hấp dẫn*, không phải *đo lường nhu cầu*. Ba thành phần nặng nhất của Trend Score (55% trọng số) vẫn đang thiếu.
