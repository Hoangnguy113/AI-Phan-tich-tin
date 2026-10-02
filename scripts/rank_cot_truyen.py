# -*- coding: utf-8 -*-
"""Xếp hạng ưu tiên 10 cốt truyện trong 'Claude outputs/COT_TRUYEN_2026-10-01.md'.

ĐÂY KHÔNG PHẢI Trend Score. Ba thành phần nặng nhất của Trend Score —
velocity (0,22), volume (0,18), engagement (0,15), tổng 55% trọng số — hiện
KHÔNG có dữ liệu thật vì chưa có connector (xem mục "Chưa có" trong CLAUDE.md).
Theo quy tắc cứng số 1, không ước lượng cho đủ: script này chỉ chấm những
thành phần đọc và kiểm được từ chính tài liệu cốt truyện.

Khi đã có connector số liệu thật, hãy chấm lại bằng agnet.core.scoring.

Đổi trọng số trong W rồi chạy lại:  python scripts/rank_cot_truyen.py
Báo cáo đi kèm: Claude outputs/PHAN_TICH_UU_TIEN_2026-10-02.md
"""

W = {  # tong = 1.00
    "suc_hut":      0.20,  # hook + vong to mo + so lieu de nho
    "impact":       0.14,  # he qua voi nguoi xem (tien / suc khoe / phap ly)
    "reach":        0.14,  # do rong tap khan gia VN
    "evergreen":    0.12,  # con gia tri sau 30 ngay
    "freshness":    0.12,  # tuoi cua moc tin (theo NGAY ghi trong tai lieu)
    "source_trust": 0.10,
    "readiness":    0.11,  # nguoc cua so o trong chan phan loi thoai
    "risk_low":     0.07,  # nguoc cua rui ro QA / phap ly / an toan
}
PULL = ["suc_hut", "impact", "reach", "evergreen", "freshness"]
SHIP = ["source_trust", "readiness", "risk_low"]

# id: (ten ngan, {thanh phan: diem})
S = {
 1: ("Cum mua: co nen tu mua thuoc?",
     dict(suc_hut=80, impact=85, reach=90, evergreen=55, freshness=95, source_trust=85, readiness=75, risk_low=68)),
 2: ("Ngu bao nhieu tieng la du?",
     dict(suc_hut=88, impact=78, reach=88, evergreen=88, freshness=55, source_trust=80, readiness=82, risk_low=70)),
 3: ("Luong bao nhieu thi dong thue 2026?",
     dict(suc_hut=85, impact=95, reach=95, evergreen=75, freshness=62, source_trust=88, readiness=40, risk_low=55)),
 4: ("Lai suat 4,75% hay 9%?",
     dict(suc_hut=92, impact=82, reach=60, evergreen=25, freshness=88, source_trust=78, readiness=42, risk_low=45)),
 5: ("Bo thue khoan: ho kinh doanh",
     dict(suc_hut=72, impact=90, reach=48, evergreen=68, freshness=35, source_trust=70, readiness=30, risk_low=52)),
 6: ("AI truc dien thoai tieng Viet",
     dict(suc_hut=64, impact=52, reach=35, evergreen=50, freshness=85, source_trust=45, readiness=65, risk_low=88)),
 7: ("AI agent: 5 cau hoi truoc khi Cho phep",
     dict(suc_hut=74, impact=65, reach=55, evergreen=85, freshness=72, source_trust=38, readiness=68, risk_low=90)),
 8: ("Video AI phai gan nhan tu 2026",
     dict(suc_hut=80, impact=90, reach=62, evergreen=82, freshness=70, source_trust=85, readiness=35, risk_low=38)),
 9: ("Retinol va vitamin C",
     dict(suc_hut=84, impact=55, reach=72, evergreen=92, freshness=15, source_trust=62, readiness=70, risk_low=62)),
10: ("Bon mon an ngay se kho",
     dict(suc_hut=66, impact=40, reach=68, evergreen=70, freshness=8,  source_trust=42, readiness=50, risk_low=40)),
}

# ---------------------------------------------------------------------------
# Cập nhật 02/10/2026 — sau khi ĐÃ XÁC MINH bằng tìm kiếm thật.
# Chỉ sửa thành phần nào có bằng chứng mới; mọi thành phần khác giữ nguyên.
# Nguồn và nội dung từng phát hiện: Claude outputs/QUYET_DINH_SAN_XUAT_2026-10-02.md
# ---------------------------------------------------------------------------
SAU_XAC_MINH = {
    # Bảng phân biệt cúm/cảm lạnh: có nguồn báo Sức khỏe & Đời sống (Bộ Y tế) 22/09/2026
    1: dict(readiness=85),
    # Đủ 5 bậc thuế (đã kiểm nhất quán bằng code) + chốt được mốc ngày áp dụng
    3: dict(readiness=82),
    # Trả lời được câu bảo hiểm tiền gửi; hạn mức 125 triệu làm hook mạnh hơn trước
    4: dict(readiness=70, suc_hut=95, risk_low=52),
    # Nghị định 142/2026 hiệu lực 01/05/2026, Điều 11.4, mức phạt, lộ trình tuân thủ
    8: dict(readiness=72, source_trust=88, risk_low=55),
}

APPLY_SAU_XAC_MINH = True   # đặt False để xem lại thứ hạng ngày 01/10 (trước xác minh)
if APPLY_SAU_XAC_MINH:
    for _i, _patch in SAU_XAC_MINH.items():
        S[_i][1].update(_patch)

assert abs(sum(W.values()) - 1.0) < 1e-9, sum(W.values())
for i, (n, c) in S.items():
    assert set(c) == set(W), (i, set(W) ^ set(c))

def wavg(c, keys):
    tot = sum(W[k] for k in keys)
    return sum(W[k] * c[k] for k in keys) / tot

rows = []
for i, (name, c) in S.items():
    rows.append((round(sum(W[k] * c[k] for k in W), 1), round(wavg(c, PULL), 1), round(wavg(c, SHIP), 1), i, name, c))
rows.sort(key=lambda r: -r[0])

hdr = f"{'Hang':<5}{'#':<4}{'Cot truyen':<40}{'Tong':>6}{'Hut':>6}{'San sang':>10}"
print(hdr); print("-" * len(hdr))
for rank, (tot, pull, ship, i, name, c) in enumerate(rows, 1):
    print(f"{rank:<5}{i:<4}{name:<40}{tot:>6}{pull:>6}{ship:>10}")

print("\n--- Chi tiet thanh phan (theo hang) ---")
ks = list(W)
print(f"{'#':<4}" + "".join(f"{k[:9]:>11}" for k in ks))
for tot, pull, ship, i, name, c in rows:
    print(f"{i:<4}" + "".join(f"{c[k]:>11}" for k in ks))

print("\n--- Neu chi toi uu LUONG XEM (bo readiness/risk/source_trust) ---")
for rank, r in enumerate(sorted(rows, key=lambda r: -r[1]), 1):
    print(f"{rank:<3} #{r[3]:<3} {r[4]:<40} {r[1]}")
print("\n--- Neu chi toi uu TOC DO LEN SONG ---")
for rank, r in enumerate(sorted(rows, key=lambda r: -r[2]), 1):
    print(f"{rank:<3} #{r[3]:<3} {r[4]:<40} {r[2]}")
