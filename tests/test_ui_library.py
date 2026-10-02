"""Kho kịch bản: đọc output/<ngày>/<luồng>/<nn_slug>/ — cùng thư mục pipeline ghi ra."""
from __future__ import annotations

import json

import pytest

from agnet.ui import library as L


def _mk(root, day, flow, slug, *, title="Tiêu đề thử", score=8.7, dur=286, lang="vi", md=True, js=True,
        extra=None):
    d = root / day / flow / slug
    d.mkdir(parents=True)
    if js:
        (d / "script.json").write_text(json.dumps(
            {"title": title, "language": lang, "target_duration_sec": dur,
             "qa": {"score": score, "flags": ["cờ A"], "human_review_required": True}},
            ensure_ascii=False), encoding="utf-8")
    if md:
        (d / "script.md").write_text(f"# {title}\n\nNội dung", encoding="utf-8")
    for name, body in (extra or {}).items():
        (d / name).write_text(body, encoding="utf-8")
    return d


@pytest.fixture()
def out(tmp_path):
    root = tmp_path / "output"
    _mk(root, "2026-10-01", "luong-a", "01_bai-mot", title="Bài một")
    _mk(root, "2026-10-02", "luong-a", "01_bai-hai", title="Bài hai", score=9.1)
    _mk(root, "2026-10-02", "luong-b", "02_bai-ba", title="Bài ba", lang="de")
    return root


def test_quet_thay_du_kich_ban_moi_nhat_truoc(out):
    es = L.scan(out)
    assert [e.title for e in es] == ["Bài hai", "Bài ba", "Bài một"]
    assert es[0].day == "2026-10-02" and es[0].flow_id == "luong-a" and es[0].slug == "01_bai-hai"


def test_doc_diem_qa_thoi_luong_ngon_ngu(out):
    e = L.scan(out)[0]
    assert e.qa_score == 9.1 and e.duration_sec == 286 and e.language == "vi"
    assert e.flags == ["cờ A"] and e.human_review_required is True


def test_thu_muc_khong_ton_tai_thi_rong(tmp_path):
    assert L.scan(tmp_path / "khong_co") == []


def test_tieu_de_lay_tu_markdown_khi_json_hong(tmp_path):
    root = tmp_path / "o"
    d = _mk(root, "2026-10-01", "f", "01_x", title="Từ markdown", js=False)
    (d / "script.json").write_text("{hỏng", encoding="utf-8")
    e = L.scan(root)[0]
    assert e.title == "Từ markdown" and e.qa_score is None


def test_chi_co_script_md_van_hien(tmp_path):
    root = tmp_path / "o"
    _mk(root, "2026-10-01", "f", "01_x", title="Chỉ md", js=False)
    assert L.scan(root)[0].title == "Chỉ md"


def test_thu_muc_khong_co_kich_ban_bi_bo_qua(tmp_path):
    root = tmp_path / "o"
    (root / "2026-10-01" / "f" / "rong").mkdir(parents=True)
    (root / ".gitkeep").parent.mkdir(exist_ok=True)
    assert L.scan(root) == []


# ---- đọc nội dung ---------------------------------------------------------
def test_doc_cac_tep_noi_dung(tmp_path):
    root = tmp_path / "o"
    _mk(root, "2026-10-01", "f", "01_x", extra={"voiceover_de.txt": "Hallo", "packaging.md": "# gói",
                                               "sources.md": "nguồn", "koc_prompts.json": "{}"})
    e = L.scan(root)[0]
    assert L.read_text(e, "script").startswith("# Tiêu đề")
    assert L.read_text(e, "voiceover") == "Hallo"
    assert L.read_text(e, "packaging") == "# gói"
    assert L.read_text(e, "sources") == "nguồn"
    assert L.read_text(e, "koc") == "{}"
    assert '"title"' in L.read_text(e, "json")


def test_tep_khong_co_tra_none(out):
    assert L.read_text(L.scan(out)[0], "koc") is None


def test_khong_doc_duoc_ngoai_thu_muc_kich_ban(out):
    e = L.scan(out)[0]
    for bad in ("../../../../etc/passwd", r"..\x", "script.md/../../x"):
        with pytest.raises(ValueError):
            L.read_text(e, bad)


def test_bao_cao_ngay(out):
    (out / "2026-10-02" / "luong-a" / "_BAO_CAO_NGAY.md").write_text("# báo cáo", encoding="utf-8")
    assert L.day_report(out, "2026-10-02", "luong-a") == "# báo cáo"
    assert L.day_report(out, "2026-10-02", "luong-b") is None


# ---- duyệt / loại -----------------------------------------------------------
def test_mac_dinh_chua_duyet(out):
    assert L.scan(out)[0].status == "pending"


def test_duyet_loai_viet_lai_ghi_review_json(out):
    e = L.scan(out)[0]
    L.set_review(e.folder, "approved")
    assert json.loads((e.folder / "review.json").read_text(encoding="utf-8"))["status"] == "approved"
    assert L.scan(out)[0].status == "approved"
    L.set_review(e.folder, "rewrite", "viết lại hook cho gọn")
    again = L.scan(out)[0]
    assert again.status == "rewrite" and again.note == "viết lại hook cho gọn"
    L.set_review(e.folder, "rejected")
    assert L.scan(out)[0].status == "rejected"


def test_viet_lai_bat_buoc_co_gop_y(out):
    with pytest.raises(ValueError):
        L.set_review(L.scan(out)[0].folder, "rewrite", "   ")


def test_trang_thai_la_bi_tu_choi(out):
    with pytest.raises(ValueError):
        L.set_review(L.scan(out)[0].folder, "xoa-het")


def test_review_hong_van_la_pending(out):
    e = L.scan(out)[0]
    (e.folder / "review.json").write_text("rác", encoding="utf-8")
    assert L.scan(out)[0].status == "pending"


def test_duyet_khong_dong_den_script_json(out):
    e = L.scan(out)[0]
    before = (e.folder / "script.json").read_bytes()
    L.set_review(e.folder, "approved")
    assert (e.folder / "script.json").read_bytes() == before        # không đổi schema (quy tắc 7)


# ---- phát hiện kịch bản mới ---------------------------------------------------
def test_chu_ky_doi_khi_co_kich_ban_moi(out):
    s1 = L.signature(out)
    _mk(out, "2026-10-03", "luong-a", "01_moi", title="Mới")
    assert L.signature(out) != s1


def test_chu_ky_doi_khi_duyet(out):
    s1 = L.signature(out)
    L.set_review(L.scan(out)[0].folder, "approved")
    assert L.signature(out) != s1
