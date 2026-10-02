# Quyết định sản xuất — chốt, không bàn thêm

> Ngày: 02/10/2026 · Người quyết: Claude (bạn giao quyền quyết định) · Tiền đề: `PHAN_TICH_UU_TIEN_2026-10-02.md`
> Việc đã làm trong phiên này: **đi xác minh thật** các ô ⚠️ chặn nặng nhất, chấm lại, rồi sửa `config/flows.yaml` cho kế hoạch chạy được.

---

## 1. Quyết định một dòng

> **Quay #1 (cúm mùa) trước — ngay tuần này. Rồi #3 (thuế TNCN). Rồi #2 (giấc ngủ). Rồi #8 (nhãn AI). Hoãn #5 và #10.**

Lý do #1 đi trước dù không còn là hạng 1: **nó là cốt truyện duy nhất có đồng hồ đếm ngược.** Mọi cái khác chờ được; cái này thì không.

---

## 2. Thứ hạng đã đổi, vì tôi đã gỡ được các ô chặn

Tôi không chỉ xếp hạng lại trên giấy — tôi đi tìm các dữ kiện còn thiếu. Kết quả:

| Hạng mới | Hạng cũ | # | Cốt truyện | Tổng | Đổi | Sẵn sàng |
|---:|---:|---:|---|---:|---:|---:|
| **1** | 3 | **3** | Lương bao nhiêu thì đóng thuế 2026? | **81,7** | +4,6 | 77,4 (từ 60,9) |
| **2** | 1 | **1** | Cúm mùa: tự mua thuốc? | **81,1** | +1,1 | 80,8 |
| **3** | 2 | 2 | Ngủ bao nhiêu tiếng là đủ? | 79,9 | — | 78,3 |
| **4** | 4 | **8** | Video AI phải gắn nhãn | **76,1** | +5,6 | 73,5 (từ 53,6) |
| **5** | 6 | **4** | Lãi suất 4,75% hay 9%? | **71,6** | +4,2 | 68,4 (từ 55,6) |
| 6 | 5 | 7 | AI agent: 5 câu hỏi | 68,0 | — | 62,8 |
| 7 | 7 | 9 | Retinol và vitamin C | 65,7 | — | 65,1 |
| 8 | 8 | 5 | Bỏ thuế khoán | 60,0 | — | 49,8 |
| 9 | 9 | 6 | AI trực điện thoại | 59,0 | — | 63,6 |
| 10 | 10 | 10 | Bốn món ăn se khô | 50,2 | — | 44,6 |

**#3 lên hạng 1 đúng như dự báo** ở báo cáo trước ("khi hai lỗ này bịt xong, #3 sẽ vượt lên hạng 1"). Bốn cốt truyện tăng điểm, không phải vì tôi đổi ý — mà vì nền dữ kiện của chúng đã khác.

Chạy lại: `python scripts/rank_cot_truyen.py` · xem thứ hạng cũ: đặt `APPLY_SAU_XAC_MINH = False`.

---

## 3. Hồ sơ xác minh — những gì tôi gỡ được hôm nay

### 3.1 #8 Nhãn AI — gỡ 3 trong 4 ô chặn. Đây là phát hiện quan trọng nhất phiên này.

**Chuỗi "1-5" mà tài liệu không đọc được chính là ngày 01/5/2026.**

| Ô chặn cũ | Trạng thái | Dữ kiện |
|---|---|---|
| Ngày hiệu lực Nghị định 142/2026 | ✅ **GỠ** | Ban hành **30/04/2026**, hiệu lực **01/05/2026** |
| Mức xử phạt cụ thể | ✅ **GỠ** (kèm một khúc mắc quan trọng — xem dưới) | Cá nhân tới **1 tỷ đồng**; tổ chức tới **2 tỷ đồng**; trường hợp nghiêm trọng tới **2% doanh thu năm trước**; có thể bị **truy cứu trách nhiệm hình sự** |
| Phạm vi bắt buộc gắn nhãn | ✅ **GỠ, và hẹp hơn tài liệu tưởng** | **Điều 11 khoản 4** Luật AI: chỉ **hai** trường hợp — (1) mô phỏng/giả lập **ngoại hình, giọng nói của người thật**; (2) **tái hiện sự kiện thực tế** |
| Ngưỡng "chỉnh sửa nhỏ" | ❌ **CÒN MỞ** — cần luật sư | — |

**Bổ sung, không có trong tài liệu gốc — và rất quan trọng với bạn:**

- **Luật AI 2025 = Luật số 134/2025/QH15**, thông qua 10/12/2025, hiệu lực 01/03/2026, gồm **8 chương 35 điều**.
- **Có lộ trình ân hạn**: bên cung cấp AI có **1 năm để tuân thủ đầy đủ, tới 01/03/2027**; riêng hệ thống AI dùng trong **y tế, giáo dục, tài chính được gia hạn tới 01/09/2027**.
- **Khúc mắc về mức phạt phải nói đúng trong video**: Luật đặt **trần** phạt, nhưng **chưa có nghị định xử phạt chuyên biệt cho riêng hành vi không gắn nhãn nội dung AI** — các nghị định xử phạt hiện hành về an ninh mạng, dữ liệu không quy định riêng hành vi này. Nói "không gắn nhãn phạt 1 tỷ" là **sai**; phải nói "Luật đặt trần tới 1 tỷ với cá nhân, nhưng chưa có nghị định xử phạt riêng cho hành vi này".

> #### Điều này thay đổi câu hỏi pháp lý của chính dự án Agnet
>
> Hai trường hợp bắt buộc đều nói về **người thật** và **sự kiện thực tế**. Nhân vật KOC của bạn — Mai, Thảo, Duy, Hùng, Lan — là **người hư cấu, không mô phỏng ai thật**. Nên theo nguyên văn hai trường hợp đó, họ **có thể không rơi vào diện bắt buộc**.
>
> **Tôi không kết luận điều này, và bạn cũng đừng.** Lý do: (a) tôi đọc qua các trang luật tổng hợp, **không mở được văn bản gốc** (xem mục 6); (b) một nguồn tiếng Anh diễn giải rằng virtual influencer *thuộc* diện phải gắn nhãn — nhưng đó là suy luận của họ, không phải nguyên văn luật; (c) nhân vật AI siêu thực có thể gây nhầm lẫn về tính xác thực, đúng tinh thần điều luật dù không khớp chữ.
>
> **Việc phải làm**: đây chính xác là câu hỏi đưa cho luật sư, và giờ nó đã **hỏi được rất gọn**: *"Nhân vật AI hư cấu, không mô phỏng người thật nào, có thuộc diện gắn nhãn bắt buộc theo Điều 11 khoản 4 Luật 134/2025/QH15 và Nghị định 142/2026/NĐ-CP không?"* — một câu, trả lời được bằng một buổi tư vấn.
>
> **Khuyến nghị của tôi trong lúc chờ: cứ gắn nhãn.** Chi phí gắn nhãn gần như bằng không, chi phí sai là tới 1 tỷ cộng rủi ro hình sự. Kế hoạch Agnet đã có mục `ai_disclosure` ở Lớp A của KOC — giữ nguyên, đừng tắt.

### 3.2 #3 Thuế TNCN — gỡ cả hai ô chặn. Đây là lý do nó lên hạng 1.

**Đủ 5 bậc — phần tài liệu để trống:**

| Bậc | Thu nhập tính thuế/tháng | Thuế suất | Công thức tính nhanh |
|---:|---|---:|---|
| 1 | Đến 10 triệu | 5% | 5% × TNTT |
| 2 | Trên 10 đến 30 triệu | 10% | 10% × TNTT − 500.000 |
| 3 | Trên 30 đến 60 triệu | 20% | 20% × TNTT − 3.500.000 |
| 4 | Trên 60 đến 100 triệu | 30% | 30% × TNTT − 9.500.000 |
| 5 | Trên 100 triệu | 35% | 35% × TNTT − 14.500.000 |

**Đã kiểm bằng code, không tin bằng mắt**: tôi đối chiếu biểu lũy tiến từng phần với công thức tính nhanh tại 12 mốc thu nhập (5 → 200 triệu). **Khớp tuyệt đối ở cả 12 mốc.** Một bảng bị bịa đặt rất khó có offset nhất quán như vậy — đây là bằng chứng nội tại mạnh. Và **ba ví dụ tính trong tài liệu cốt truyện đều đúng**: A 20tr→225.000đ, B 25tr→475.000đ, C 25tr+1 người phụ thuộc→165.000đ.

**Mốc ngày áp dụng — hóa ra tài liệu đúng cả hai, chúng nói về hai thứ khác nhau:**

- Luật Thuế TNCN sửa đổi: thông qua 10/12/2025, **hiệu lực 01/07/2026**.
- Nhưng mức giảm trừ 15,5 triệu / 6,2 triệu và biểu 5 bậc **áp dụng từ kỳ tính thuế năm 2026, tức từ 01/01/2026**.

Nên tiêu đề "từ 2026" là **đúng**. Và chính cái vẻ mâu thuẫn này là một đoạn nội dung tốt: "vì sao luật có hiệu lực tháng 7 mà bạn được giảm thuế từ tháng 1".

### 3.3 #4 Lãi suất — gỡ lỗi cấu trúc, và payoff ra **mạnh hơn** dự kiến

Câu hỏi đóng vòng tò mò ("chứng chỉ tiền gửi có được bảo hiểm tiền gửi không") **có câu trả lời**:

- **Có.** Luật Bảo hiểm tiền gửi số **06/2012/QH13** liệt kê tiền gửi được bảo hiểm gồm tiền gửi có kỳ hạn, không kỳ hạn, tiết kiệm, **chứng chỉ tiền gửi**, kỳ phiếu, tín phiếu. Tổ chức tín dụng nhận tiền gửi cá nhân **bắt buộc** tham gia bảo hiểm tiền gửi.
- **Nhưng có hạn mức, và đây mới là nội dung thật**: **125 triệu đồng** cho **toàn bộ** tiền gửi được bảo hiểm (**gồm cả gốc và lãi**) của **một người** tại **một** tổ chức — theo **Quyết định 32/2021/QĐ-TTg**, hiệu lực **12/12/2021** (trước đó là 75 triệu theo Quyết định 21/2017/QĐ-TTg). Mức này phủ toàn bộ tiền gửi của khoảng **91%** người gửi tiền trong hệ thống.

> **Đây là nâng cấp lớn cho #4.** Ví dụ 500 triệu gửi 3 tháng trong tài liệu giờ có một kết luận sắc hơn hẳn: **gửi 500 triệu một chỗ thì chỉ 125 triệu được bảo hiểm.** Vòng tò mò không chỉ có payoff — nó có một payoff khiến người xem phải hành động (chia tiền ra nhiều tổ chức).
>
> Và nó **đổi bản chất video**: từ "so bảng lãi suất" (chết trong vài tuần) thành "hiểu rủi ro khi chạy theo lãi cao" (dùng được lâu). Vì vậy tôi **ra lệnh đổi khung #4**: dẫn bằng hạn mức 125 triệu, bảng lãi suất chỉ là minh họa có hiện ngày. `evergreen` của #4 từ 25 lên được, và nó thoát khỏi cái bẫy "số liệu rữa trước khi kịp quay".

### 3.4 #1 Cúm mùa — gỡ ô chặn duy nhất

Bảng phân biệt cúm / cảm lạnh (phân đoạn 1:30–3:30, 320 từ) đã có nguồn: báo **Sức khỏe & Đời sống — cơ quan của Bộ Y tế**, bài 22/09/2026 "Cúm A, cúm B và cảm lạnh, dấu hiệu nhận biết để không nhầm lẫn". Nội dung dùng được:

| | Cúm mùa | Cảm lạnh |
|---|---|---|
| Khởi phát | Đột ngột, triệu chứng toàn thân rõ | Từ từ |
| Sốt | Vừa đến cao, 39–40°C | Thường không sốt, nếu có thì nhẹ |
| Đau nhức cơ | Có, dai dẳng nhiều ngày | Rất ít, nếu có thì xuất hiện ngay rồi hết |
| Ớn lạnh | **Có — dấu hiệu đặc trưng** | Hầu như không |
| Mệt mỏi | Kéo dài, có thể trên 2 tuần | Nhẹ hoặc vừa |
| Hay gặp | Đau đầu, viêm họng, khô rát cổ, nghẹt mũi | Nghẹt mũi, chảy nước mũi, hắt hơi, rát họng, ho |

**#1 giờ không còn ô chặn nào. Viết được ngay hôm nay.**

---

## 4. Lệnh sản xuất

### Tuần này

**① #1 Cúm mùa — bắt đầu ngay.**
Không còn ô chặn. Khớp luồng `suckhoe-yt-sang` đang bật. Và **có đồng hồ**: câu "tăng nhẹ" chỉ đúng tới ngày bản tin 01/10. Nếu không lên sóng trong 1–2 tuần thì phải cập nhật lại số liệu hoặc bỏ. Đây là lý do duy nhất nó đi trước hạng 1.

**② #3 Thuế TNCN — bắt đầu song song, lên sóng ngay sau #1.**
Hạng 1 mới, `impact` 95 và `reach` 95 — cao nhất cả kho. Đủ 5 bậc, chốt được mốc ngày. Ba điều **bắt buộc** khi viết:
- Nói rõ 15,5 triệu là mức **giảm trừ**, không phải **ngưỡng lương**. Đây là toàn bộ giá trị của video.
- Ba ví dụ tính ghi rõ "**ví dụ minh họa của biên tập, chưa tính bảo hiểm bắt buộc và các khoản miễn thuế**".
- Giải thích cặp ngày 01/07/2026 (luật có hiệu lực) và 01/01/2026 (kỳ tính thuế áp dụng) — đừng né, đó là nội dung tốt.

### Tuần sau

**③ #2 Giấc ngủ — dùng làm bài đo pipeline.**
`readiness` cao, **không gấp chút nào**. Chính vì không gấp nên đây là bài để chạy thật lần đầu: nếu agent treo như lần 01/10, bạn không mất cơ hội nội dung nào. Cấm tuyệt đối: đổi "liên quan" thành "gây ra"; nói "mới công bố" (nghiên cứu có vẻ từ 23/08/2025). Dùng tiêu đề số 1, không dùng số 2.

**④ #8 Nhãn AI — viết được rồi, nhưng chốt ở cửa luật sư.**
Ba trong bốn ô đã gỡ, và nội dung giờ **chính xác hơn tài liệu gốc**: tên luật, số điều khoản, hai trường hợp bắt buộc, ngày hiệu lực của cả luật và nghị định, lộ trình ân hạn, và khúc mắc "chưa có nghị định xử phạt riêng". Đổi tiêu đề số 2 thành **"4 cách gắn nhãn hợp lệ theo Nghị định 142/2026, hiệu lực 01/5/2026"** — giờ nói được ngày.
**Nhưng**: đừng đăng trước khi luật sư trả lời câu ở mục 3.1. Không phải vì video sai, mà vì câu trả lời đó quyết định phân đoạn 10:00–12:30 ("áp vào kênh của bạn") **và** quyết định cách bạn làm 9 video còn lại.

### Sau đó

**⑤ #4 Lãi suất — đổi khung quanh hạn mức 125 triệu** (mục 3.3). Còn phải kiểm: kỳ hạn gắn với từng mức 9% trở lên; cách tính lãi 360 hay 365 ngày; và **cập nhật lại bảng lãi suất tại ngày quay**.

**⑥ #7 AI agent, hoặc ghép #6+#7 thành 18–19 phút.** Đổi mốc tin từ trang tổng hợp sang một thông báo chính thức. Chia nhỏ khối 5 câu hỏi (720 từ liền) thành 5 hình thái khác nhau, không thì tụt giữ chân ở phút 6–8.

**⑦ #9 Retinol** nếu muốn một video rẻ ra lò nhanh. Cần bật luồng `lamdep-tiktok-toi`, và bổ sung nguồn da liễu cho phân đoạn kết (hiện khuyến nghị y tế không nguồn).

### Hoãn, có điều kiện quay lại

**#5 Bỏ thuế khoán** — nghiên cứu lại từ đầu. Nền dữ kiện là bài 18/12/2025 viết *trước* đợt chuyển đổi đã xong 9 tháng. Khi nghiên cứu lại, **đổi góc**: không còn là "chuẩn bị gì" mà là **"9 tháng rồi, hộ kinh doanh vướng ở đâu"** — mạnh hơn hẳn bản cũ.

**#10 Bốn món ăn** — chờ ba nguồn an toàn (xuyên bối mẫu là vị thuốc; hạnh nhân ngọt hay đắng; đường phèn với người đái tháo đường). Là video theo mùa, làm cho mùa thu đông sau không mất gì. Hoãn vì an toàn thân thể, không vì nó dở.

---

## 5. Đã sửa `config/flows.yaml`

Báo cáo trước chỉ ra: chỉ có **1 luồng**, nên chỉ #1 và #2 chạy được. Tôi đã thêm ba luồng cho kế hoạch trên:

| Luồng | Phục vụ | Thời lượng | Trạng thái |
|---|---|---|---|
| `taichinh-yt-trua` | #3, #4, #5 | 8–16 phút | **tắt** |
| `congnghe-yt-chieu` | #6, #7, #8 | 8–16 phút | **tắt** |
| `lamdep-tiktok-toi` | #9 | 5–10 phút | **tắt** |

**Cả ba đang `enabled: false`, và đó là cố ý.** `CLAUDE.md` ghi rõ: chi phí thật mỗi luồng/ngày chưa biết, và lần chạy thật 01/10 tốn $1,16 cho 4 lượt gọi rồi treo. **Bật từng luồng một**, xem `python -m agnet status` và `cost_ledger`, chốt `max_cost_usd_per_day`, rồi mới bật luồng kế tiếp. Bật cả ba cùng lúc là đốt tiền mù. Tất cả đặt `max_cost_usd_per_day: 1` làm trần an toàn ban đầu.

Mỗi luồng có `brand_rules` rút từ đúng các cảnh báo trong tài liệu cốt truyện — ví dụ luồng tài chính cấm nói "ngân hàng X an toàn", luồng công nghệ buộc gắn "theo nhà cung cấp" vào số liệu nhà cung cấp tự báo.

Đã kiểm: `python -m agnet flows` xác nhận cả 4 luồng hợp lệ. `python -m pytest -q`: **204 passed, 3 skipped**.

**Lưu ý còn lại về thời lượng**: `taichinh-yt-trua` và `congnghe-yt-chieu` đặt `duration_max: 16`, nên **#4 và #8 ở bản 15 phút vẫn vừa**, nhưng `duration_mix` hiện chỉ sinh bucket 8–12. Muốn ra video 15 phút thì đổi `duration_mix` thành `{15-16: 1}` cho ngày đó, hoặc nâng `daily_quota` lên 2 và chia `{8-12: 1, 15-16: 1}`.

---

## 6. Giới hạn của phiên này — đọc trước khi tin hoàn toàn

Tôi phải nói rõ, vì chính dự án này cấm bịa và cấm nói quá chắc:

**Tôi không mở được văn bản gốc nào.** WebFetch bị chặn egress với toàn bộ các domain tôi cần: `thuvienphapluat.vn`, `luatvietnam.vn`, `luatvietan.vn`, `luatlongphan.vn`, `baochinhphu.vn`. Mọi dữ kiện ở mục 3 đến từ **phần tóm tắt kết quả tìm kiếm**, tổng hợp từ nhiều trang luật và báo. Nghĩa là **vẫn là nguồn thứ cấp** — đúng cái vấn đề tài liệu gốc đã gặp, chỉ bớt tệ hơn vì nhiều nguồn độc lập nói giống nhau.

**Việc bắt buộc trước khi lên sóng** (không phải lựa chọn):

- [ ] **#8**: mở toàn văn **Luật 134/2025/QH15** và **Nghị định 142/2026/NĐ-CP** trên cổng văn bản chính thức. Xác nhận: Điều 11 khoản 4; hai trường hợp bắt buộc; 4 hình thức gắn nhãn; ngày hiệu lực 01/05/2026; lộ trình 01/03/2027 và 01/09/2027.
- [ ] **#8**: hỏi luật sư đúng một câu ở mục 3.1 về nhân vật AI hư cấu.
- [ ] **#3**: đối chiếu bảng 5 bậc với **Luật Thuế TNCN sửa đổi** và **Nghị quyết 110/2025/UBTVQH15**. Bảng đã nhất quán nội tại ở 12 mốc, nhưng nhất quán **không phải** là đúng luật.
- [ ] **#4**: đối chiếu hạn mức 125 triệu với **Quyết định 32/2021/QĐ-TTg** và trang Bảo hiểm tiền gửi Việt Nam (`div.gov.vn`) — kiểm xem đã có quyết định mới hơn chưa (quyết định này từ 2021, đã 5 năm).
- [ ] **#1**: lấy bản tin gốc của Cục Phòng bệnh ngày 01/10/2026, không chỉ bài báo lại tin.

Nếu bạn mở được các trang này trên máy mình (không qua proxy của phiên này), đó là việc nửa giờ và nó biến toàn bộ mục 3 từ "thứ cấp nhiều nguồn" thành "đã xác minh".

---

## 7. Nguồn đã dùng trong phiên xác minh 02/10/2026

**Luật AI và gắn nhãn nội dung AI**
- Thư viện pháp luật, "Quy định mới về thông báo và gắn nhãn hiển thị với nội dung do AI tạo ra từ ngày 01/5/2026": https://thuvienphapluat.vn/chinh-sach-phap-luat-moi/vn/ho-tro-phap-luat/chinh-sach-moi/111755/quy-dinh-moi-ve-thong-bao-va-gan-nhan-hien-thi-voi-noi-dung-do-ai-tao-ra-tu-ngay-01-5-2026
- Thư viện pháp luật, Nghị định 142/2026/NĐ-CP hướng dẫn Luật Trí tuệ nhân tạo: https://thuvienphapluat.vn/van-ban/Cong-nghe-thong-tin/Nghi-dinh-142-2026-ND-CP-huong-dan-Luat-Tri-tue-nhan-tao-696080.aspx
- LuatVietnam, "2 trường hợp nội dung do AI tạo ra bắt buộc phải gắn nhãn từ 01/5/2026": https://luatvietnam.vn/tin-van-ban-moi/2-truong-hop-noi-dung-do-ai-tao-ra-bat-buoc-phai-gan-nhan-tu-01-5-2026-186-108836-article.html
- Báo Chính phủ, "Việt Nam chính thức có Luật Trí tuệ nhân tạo (AI)": https://baochinhphu.vn/viet-nam-chinh-thuc-co-luat-tri-tue-nhan-tao-ai-102251210164948585.htm
- Xây dựng chính sách (Chính phủ), "6 luật có hiệu lực thi hành từ ngày 1/3/2026": https://xaydungchinhsach.chinhphu.vn/6-luat-co-hieu-luc-thi-hanh-tu-ngay-1-3-2026-119260301164943626.htm
- PLO, "Ai phải gắn nhãn nhận biết nội dung do AI tạo ra?": https://plo.vn/ai-phai-gan-nhan-nhan-biet-noi-dung-do-ai-tao-ra-post907652.html
- Tuổi Trẻ, "Lần đầu trình Quốc hội luật về trí tuệ nhân tạo, phạt tối đa 2 tỉ đồng hành vi vi phạm về AI": https://tuoitre.vn/lan-dau-trinh-quoc-hoi-luat-ve-tri-tue-nhan-tao-phat-toi-da-2-ti-dong-hanh-vi-vi-pham-ve-ai-20251121085727822.htm
- Tiền Phong, "Vi phạm về trí tuệ nhân tạo có thể bị truy cứu trách nhiệm hình sự, phạt tiền 2 tỷ đồng": https://tienphong.vn/vi-pham-ve-tri-tue-nhan-tao-co-the-bi-truy-cuu-trach-nhiem-hinh-su-phat-tien-2-ty-dong-post1798152.tpo
- Baker McKenzie, "Vietnam's first standalone AI Law": https://connectontech.bakermckenzie.com/vietnams-first-standalone-ai-law-an-overview-of-key-provisions-future-implications/
- Securiti, "Vietnam's Law on Artificial Intelligence: A Guide to Compliance": https://securiti.ai/vietnam-ai-aw/

**Thuế thu nhập cá nhân 2026**
- LuatVietnam, "Cách tính thuế TNCN 2026 theo mức giảm trừ gia cảnh mới": https://luatvietnam.vn/thue-phi-le-phi/cach-tinh-thue-tncn-2026-565-106276-article.html
- Quân đội nhân dân, "Từ 1-7-2026, người lao động được giảm thuế nhờ nâng giảm trừ gia cảnh": https://www.qdnd.vn/kinh-te/tin-tuc/tu-1-7-2026-nguoi-lao-dong-duoc-giam-thue-nho-nang-giam-tru-gia-canh-1019067
- VnEconomy, "Từ 2026, nâng mức giảm trừ gia cảnh thuế thu nhập cá nhân lên 15,5 triệu đồng/tháng": https://vneconomy.vn/tu-2026-nang-muc-giam-tru-gia-canh-thue-thu-nhap-ca-nhan-len-155-trieu-dongthang.htm
- VietNamNet, "Thay đổi lớn về giảm trừ gia cảnh từ 2026": https://vietnamnet.vn/thay-doi-lon-ve-giam-tru-gia-canh-tu-2026-hang-chuc-trieu-nguoi-dan-huong-loi-2474898.html

**Bảo hiểm tiền gửi**
- Luật Bảo hiểm tiền gửi số 06/2012/QH13 (cổng văn bản Chính phủ): https://vanban.chinhphu.vn/default.aspx?pageid=27160&docid=163543
- Bảo hiểm tiền gửi Việt Nam, "Từ ngày 12/12/2021, hạn mức trả tiền bảo hiểm là 125 triệu đồng": https://www.div.gov.vn/tu-ngay-12-12-2021-han-muc-tra-tien-bao-hiem-la-125-trieu-dong
- Báo Chính phủ, "Nâng hạn mức trả tiền bảo hiểm tiền gửi lên 125 triệu đồng": https://baochinhphu.vn/nang-han-muc-tra-tien-bao-hiem-tien-gui-len-125-trieu-dong-102302543.htm

**Cúm mùa và cảm lạnh**
- Sức khỏe & Đời sống (Bộ Y tế), "Cúm A, cúm B và cảm lạnh, dấu hiệu nhận biết thế nào để không nhầm lẫn" (22/09/2026): https://suckhoedoisong.vn/cum-a-cum-b-va-cam-lanh-dau-hieu-nhan-biet-de-khong-nham-lan-169260922113710429.htm
- VietnamPlus, "Phân biệt dấu hiệu của cảm lạnh và cảm cúm để phòng ngừa, điều trị": https://www.vietnamplus.vn/phan-biet-dau-hieu-cua-cam-lanh-va-cam-cum-de-phong-ngua-bien-chung-post1011589.vnp

*Ghi chú: mọi dữ kiện trên đến từ phần tóm tắt kết quả tìm kiếm, không phải từ việc mở trực tiếp văn bản gốc (xem mục 6). Tài liệu này không phải tư vấn pháp lý, y tế hay tài chính.*
