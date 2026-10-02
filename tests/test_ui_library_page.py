"""Trang Kho kịch bản trong phần mềm: hiện đúng thư mục output/ và tự cập nhật. Chạy ẩn màn hình."""
from __future__ import annotations

import json
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6", reason="chưa cài PySide6")

from PySide6.QtWidgets import QApplication                    # noqa: E402

from agnet.ui import library as L                             # noqa: E402
from agnet.ui.page_library import LibraryPage                 # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _mk(root, day, flow, slug, title, score=8.5):
    d = root / day / flow / slug
    d.mkdir(parents=True)
    (d / "script.json").write_text(json.dumps(
        {"title": title, "language": "vi", "target_duration_sec": 300,
         "qa": {"score": score, "flags": [], "human_review_required": False}}, ensure_ascii=False), encoding="utf-8")
    (d / "script.md").write_text(f"# {title}\n\nLời thoại chính của {title}", encoding="utf-8")
    (d / "voiceover.txt").write_text("đây là lời thoại", encoding="utf-8")
    return d


@pytest.fixture()
def out(tmp_path):
    root = tmp_path / "output"
    _mk(root, "2026-10-02", "luong-a", "01_bai-mot", "Bài một")
    _mk(root, "2026-10-02", "luong-a", "02_bai-hai", "Bài hai")
    return root


def test_hien_danh_sach_va_noi_dung_ngay_trong_phan_mem(qapp, out):
    page = LibraryPage(out)
    assert "2" in page.count.text() and page.current_entry() is not None
    e = page.current_entry()
    assert e.title in page.views["script"].toPlainText()
    assert page.views["voiceover"].toPlainText() == "đây là lời thoại"
    assert page.views["koc"].toPlainText() == "(không có tệp này)"


def test_thu_muc_trong_khong_vo(qapp, tmp_path):
    page = LibraryPage(tmp_path / "khong_co")
    assert page.current_entry() is None and not page.btn_ok.isEnabled()


def test_duyet_ghi_review_json_va_cap_nhat_giao_dien(qapp, out):
    page = LibraryPage(out)
    folder = page.current_entry().folder
    page.set_status("approved")
    assert json.loads((folder / "review.json").read_text(encoding="utf-8"))["status"] == "approved"
    assert "ĐÃ DUYỆT" in page.head.text()
    assert page.current_entry().folder == folder                # vẫn đứng ở kịch bản vừa duyệt


def test_viet_lai_phai_co_gop_y(qapp, out):
    page = LibraryPage(out)
    page.set_status("rewrite", "   ")
    assert "Chưa lưu" in page.msg.text()
    assert not (page.current_entry().folder / "review.json").exists()
    page.set_status("rewrite", "gọn hook lại")
    assert "gọn hook lại" in page.head.text()


def test_kich_ban_moi_do_pipeline_ghi_tu_hien_ra(qapp, out):
    page = LibraryPage(out)
    assert len(page._entries) == 2
    _mk(out, "2026-10-03", "luong-a", "01_vua-ghi", "Vừa ghi")      # giả lập pipeline vừa xuất file
    page._poll()                                                    # đúng thứ bộ hẹn giờ gọi
    assert len(page._entries) == 3
    assert any(e.title == "Vừa ghi" for e in page._entries.values())


def test_khong_lam_moi_khi_khong_doi(qapp, out, monkeypatch):
    page = LibraryPage(out)
    calls = []
    monkeypatch.setattr(page, "reload", lambda: calls.append(1))
    page._poll()
    assert calls == []


def test_chon_nut_luong_hien_bao_cao_ngay(qapp, out):
    (out / "2026-10-02" / "luong-a" / "_BAO_CAO_NGAY.md").write_text("# Báo cáo của luồng A", encoding="utf-8")
    page = LibraryPage(out)
    flow_item = page.tree.topLevelItem(0).child(0)
    page.tree.setCurrentItem(flow_item)
    assert "Báo cáo của luồng A" in page.report.toPlainText()
