---
name: agnet-koc-studio
description: "Sinh prompt ảnh/video cho nhân vật KOC AI siêu thực của Agnet theo chuẩn koc-master-1.0 (3 lớp, consistency lock ở cuối), chuyển sang Nano Banana / Midjourney / Flux / Veo-Kling, chấm rubric ảnh, giữ đồng nhất nhân vật. Dùng khi làm người dẫn KOC, tạo ảnh/video nhân vật, hoặc tạo nhân vật mới."
---

# Agnet — KOC Studio

Một nhân vật được khai báo **một lần** (Character Bible), mọi cảnh của mọi kịch bản dùng lại → khán giả nhận ra "người quen".

## Kiến trúc prompt 3 lớp

```
LỚP A  CHARACTER BIBLE   khoá cứng, không bao giờ đổi   config/characters/<id>.json  (khối identity)
LỚP B  REALISM ENGINE    dùng chung mọi nhân vật         agnet/koc/realism_engine.json
LỚP C  SHOT              đổi theo từng cảnh              script.json → scene.visual.koc
PROMPT CUỐI = A + B + C + NEGATIVE + CONSISTENCY LOCK (đặt CUỐI)
```

**Không tự viết prompt tay.** Dùng code để ghép — nó đảm bảo B, `negative`, `consistency_lock` không bị sửa:

```python
from agnet.koc.master_prompt import build_prompt, load_character
from agnet.koc.adapters import to_midjourney, to_veo
p = build_prompt(load_character("KOC-02-THAO"), shot, platform="youtube", render_target="image")
```

Chạy `python -m pytest tests/test_koc.py` sau khi đổi bất cứ thứ gì trong `agnet/koc/`.

## Hai quy tắc kỹ thuật

1. **Consistency lock ở cuối prompt** — model đánh trọng số cao phần đuôi.
2. **Ảnh tham chiếu > chữ miêu tả.** Luôn kèm ảnh gốc; chữ chỉ để neo và chống trôi, không để "vẽ lại" mặt. Mô tả mặt quá dài mà lệch ảnh gốc là nguyên nhân số 1 làm nhân vật đổi mặt.

## Bảy quy tắc "giống người thật"

| # | Quy tắc | Viết thế nào |
|---|---|---|
| 1 | Bất đối xứng có chủ ý | "left eyebrow 2mm higher", "smile pulls to the left" |
| 2 | Micro-texture da | "visible pores, uneven tone, peach fuzz, sebum sheen, no retouching" |
| 3 | Dấu hiệu riêng (neo nhận diện) | 2–3 dấu có **vị trí chính xác** |
| 4 | Ánh sáng có hướng, có nguồn | "one key source" + hướng; bóng nhất quán |
| 5 | Ống kính & phim cụ thể | "85mm f/1.8 @ f/2.0, ISO 400, Kodak Portra 400" |
| 6 | Micro-expression đang diễn ra | "a half-formed smile", không "giữ pose" |
| 7 | Bố cục không hoàn hảo | "slightly off-centre, as if captured in the moment" |

**Từ phải LOẠI khỏi prompt** (code từ chối): `perfect · flawless · masterpiece · 8k · ultra/hyper detailed · beautiful woman · supermodel · doll-like · porcelain skin · symmetrical face · 90-60-90`, mọi số đo cơ thể, `instagram filter`. Đây là token "trung bình hoá" → mặt chung chung, da nhựa. Muốn đẹp thì tả **ánh sáng và ống kính đẹp**, đừng tả "đẹp".

## Chẩn đoán: thấy dấu hiệu → sửa chỗ này

| Dấu hiệu lộ AI | Nguyên nhân | Sửa |
|---|---|---|
| Da bóng sáp, không lỗ chân lông | thiếu `skin_rendering` / có "flawless" | thêm pores/peach fuzz/blemish; xoá từ hoàn hảo |
| Mặt cân đối bất thường | thiếu `asymmetry` | thêm 2–3 điểm lệch bằng số |
| Ảnh phẳng, không rõ nguồn sáng | không khai báo key light | 1 nguồn + hướng + kiểm bóng |
| Mắt 2–3 điểm sáng, vô hồn | model tự thêm catchlight | `exactly one specular catchlight per eye` |
| Tay 6 ngón, ngón dính | tay ngoài vùng nét / không mô tả | tả tay cụ thể; cho tay có việc (cầm cốc, tựa bàn) |
| Trang sức/tóc bay lơ lửng | không mô tả tiếp xúc | "chain resting on the collarbone" |
| Đổi mặt giữa các ảnh | mô tả mặt dài hơn ảnh tham chiếu / thiếu lock | rút gọn mô tả mặt, luôn kèm ảnh, lock ở cuối |
| Giống render 3D | có `8k`, `octane`, `cinematic lighting` | thay bằng thông số máy ảnh + film emulation |

## Giữ nhân vật đồng nhất (4 bước)

1. **Ảnh gốc** — 1 ảnh chính diện, biểu cảm trung tính, sáng đều nhẹ; duyệt ở zoom 100%. Xấu ở đây = sai suốt đời nhân vật.
2. **Bảng nhân vật 9 ảnh** — góc: chính diện · 3/4 trái · 3/4 phải · bán diện · sau vai; biểu cảm: trung tính · cười hé · cười lớn · nghiêm/suy nghĩ. Mỗi ảnh đính kèm ảnh B1 + consistency_lock. Lưu `config/characters/<id>/refs/`.
3. **LoRA (tuỳ chọn)** — 20–30 ảnh, ≥ 1024px; caption = 1 trigger token cố định + chỉ tả phần **thay đổi**, không tả lại mặt. Khởi điểm thử: rank 16, alpha 8, lr 1e-4, ~10 epoch; lưu checkpoint từng epoch, thử cùng một bộ prompt, **đổi một biến mỗi lần**.
4. **Sinh theo cảnh** — kiểm lại `identity_marks`; mất thì sinh lại.

> Không có công thức nào đảm bảo giống 100%. Cách đúng: thử có kiểm soát — đổi một biến, so trên cùng bộ prompt, chỉ giữ thay đổi khi tốt hơn rõ ràng.

## Adapter — một schema, bốn công cụ

| | Nano Banana Pro / Gemini | Midjourney v7 | Flux / SDXL + LoRA | Veo 3 / Kling |
|---|---|---|---|---|
| Định dạng | JSON có cấu trúc | văn xuôi 1 đoạn | văn xuôi + trigger token | văn xuôi: camera → hành động → sáng → texture → âm thanh |
| Neo nhân vật | 1–3 ảnh tham chiếu | `--cref <url> --cw 100` | trigger token, weight 0.8–1.0 | ảnh đầu (image-to-video) |
| Tham số | `output.aspect_ratio` | `--ar … --stylize 50 --raw` | steps/CFG 3.5 (Flux) | `duration_sec`, `fps` |
| Dùng cho | ảnh hook, thumbnail, ảnh cảnh | ảnh nghệ thuật, cover | sản xuất số lượng lớn | cảnh người dẫn nói |

Tên công cụ/tham số có thể đã đổi — kiểm lại tài liệu của công cụ trước khi chạy hàng loạt.

## Agent 17 — KOC Character Director

Chạy **sau Director, trước QA**; luồng `koc.enabled = false` thì bỏ qua.

1. Chọn cảnh cần mặt người (hook, chuyển đoạn, CTA, cảnh cảm xúc): **25–40%** số cảnh. Không lạm dụng.
2. Mỗi cảnh người: `render_target` ảnh hay video; prompt theo `koc-master-1.0`.
3. **Một kịch bản = một nhân vật = 1–2 bộ phục trang** (cùng "ngày quay").
4. Ghi `koc_prompts.json` (JSON + bản Midjourney + bản Veo/Kling cho từng cảnh) và điền `scene.visual.koc` (`prompt_ref = "koc_prompts.json#<scene_id>"`).
5. Tự chấm rubric ảnh. Lưu vết: `character_id`, prompt, engine, thời điểm.

**Cứng:** không sửa `realism_engine`, `negative`, `consistency_lock`; không thêm mô tả khuôn mặt ngoài `identity`.

## Rubric QA hình ảnh (thang 10, đạt ≥ 8)

| Tiêu chí | Điểm | Đạt khi |
|---|---|---|
| Đồng nhất khuôn mặt | 3 | khớp ảnh gốc; đủ `identity_marks`; không bị làm đẹp/trẻ/đổi nét |
| Chân thực da & texture | 2 | thấy lỗ chân lông, tông da không đều; không bóng sáp |
| Ánh sáng & bóng nhất quán | 2 | một nguồn rõ hướng; bóng mặt–cổ–tường–sàn cùng hướng; 1 catchlight/mắt |
| Giải phẫu & tiếp xúc | 1,5 | tay đúng số ngón; trang sức/tóc có điểm tiếp xúc |
| Phù hợp cảnh & nền tảng | 1 | đúng tỉ lệ, cỡ cảnh, phục trang nhất quán |
| Không dấu hiệu AI | 0,5 | bố cục không căn giữa máy móc; không glow/HDR/chữ rác/watermark |

< 8 → sinh lại tối đa 2 lần → vẫn không đạt thì chuyển cảnh đó sang B-roll và gắn cờ `human_review`.

## Pháp lý, chính sách, đạo đức (cứng)

- **Khai báo AI**: bật nhãn nội dung tổng hợp theo từng nền tảng; mô tả có dòng "Người dẫn trong video là nhân vật do AI tạo." (`packaging.ai_disclosure: true`).
- **Không mượn mặt người thật**: không prompt theo tên người nổi tiếng, không dùng ảnh người thật làm ảnh gốc/dataset nếu không có quyền.
- **Không mạo danh chuyên môn**: KOC không được giới thiệu là bác sĩ/dược sĩ/luật sư/chuyên gia tài chính có chứng chỉ; nội dung y tế/tài chính chỉ "chia sẻ thông tin đã kiểm chứng" kèm miễn trừ và nguồn.
- **Không gợi dục, không khai thác hình thể**: không số đo, không trang phục hở/bó gợi dục, không tư thế khoe thân. Tiêu chí là **đáng tin**, không phải **gợi cảm**.
- **Nhân vật trưởng thành**: mọi nhân vật ≥ 22 tuổi và được mô tả rõ là người trưởng thành.
- **Minh bạch tài trợ**: có quảng cáo thì có nhãn trong lời thoại và caption.

## Tạo nhân vật thứ 6 trở đi

1. Chốt ngách & nền tảng → tuổi, vùng miền, giọng **đáng tin với chủ đề** (đông y đừng dùng người 20 tuổi).
2. Viết `identity` (copy một file trong `config/characters/`): **≥ 2 điểm bất đối xứng bằng số, ≥ 2 dấu hiệu riêng có vị trí chính xác**, tuổi ≥ 22 — `build_prompt` và test sẽ từ chối nếu thiếu.
3. Sinh ảnh gốc → duyệt zoom 100% → chưa đạt thì sinh lại, **không đi tiếp**.
4. Sinh bảng 9 ảnh → `config/characters/<id>/refs/`.
5. (Tuỳ chọn) LoRA.
6. Test 3 cảnh khác hẳn nhau (ngoài trời trưa / trong nhà tối / cận đặc tả) → kiểm `identity_marks` → ghi vào `config/characters.yaml`, gán cho luồng.
