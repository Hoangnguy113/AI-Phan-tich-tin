"""Ngôn ngữ, chủ đề, trang Cài đặt chung, bộ chọn giờ chạy. Chạy ẩn màn hình."""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6", reason="chưa cài PySide6")

from PySide6.QtWidgets import (QApplication, QGroupBox, QLabel, QLineEdit, QPushButton,  # noqa: E402
                               QTabWidget, QVBoxLayout, QWidget)

from agnet.core import settings as S                  # noqa: E402
from agnet.core.models import load_flows              # noqa: E402
from agnet.ui import env_store, i18n, theme           # noqa: E402
from agnet.ui.page_flows import FlowsPage             # noqa: E402
from agnet.ui.page_settings import SettingsPage       # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


# ---- dịch giao diện -------------------------------------------------------
def _tree():
    root = QWidget()
    lay = QVBoxLayout(root)
    lbl, btn = QLabel("Lưu"), QPushButton("Bỏ thay đổi")
    box = QGroupBox("Tài khoản Claude")
    edit = QLineEdit()
    edit.setPlaceholderText("Kết quả kiểm tra hệ thống hiện ở đây.")
    tabs = QTabWidget()
    tabs.addTab(QWidget(), "Bảng điều khiển")
    for w in (lbl, btn, box, edit, tabs):
        lay.addWidget(w)
    return root, lbl, btn, box, edit, tabs


def test_dich_sang_tieng_anh_va_tra_lai(qapp):
    root, lbl, btn, box, edit, tabs = _tree()
    i18n.apply(root, "en")
    assert lbl.text() == "Save" and btn.text() == "Discard changes"
    assert box.title() == "Claude account"
    assert edit.placeholderText() == "System check results appear here."
    assert tabs.tabText(0) == "Dashboard"
    i18n.apply(root, "vi")
    assert lbl.text() == "Lưu" and btn.text() == "Bỏ thay đổi" and tabs.tabText(0) == "Bảng điều khiển"


def test_dich_di_dich_lai_khong_hong_goc(qapp):
    root, lbl, *_ = _tree()
    for lang in ("en", "vi", "en", "en", "vi"):
        i18n.apply(root, lang)
    assert lbl.text() == "Lưu"


def test_chu_khong_co_trong_tu_dien_giu_nguyen(qapp):
    root = QWidget()
    lbl = QLabel("Chữ lạ chưa có bản dịch")
    QVBoxLayout(root).addWidget(lbl)
    i18n.apply(root, "en")
    assert lbl.text() == "Chữ lạ chưa có bản dịch"


def test_chu_dong_do_ung_dung_doi_sau_khi_dich_van_dung(qapp):
    """Thông báo trạng thái bị đổi lúc chạy (ví dụ 'Lưu' -> 'Hủy') phải được coi là gốc mới."""
    root, lbl, *_ = _tree()
    i18n.apply(root, "en")
    lbl.setText("Bỏ thay đổi")
    i18n.apply(root, "vi")
    assert lbl.text() == "Bỏ thay đổi"
    i18n.apply(root, "en")
    assert lbl.text() == "Discard changes"


def test_moi_chu_tieng_viet_trong_tu_dien_deu_co_ban_dich_khac_nhau():
    assert i18n.EN and all(v.strip() and v != k for k, v in i18n.EN.items())


# ---- chủ đề ---------------------------------------------------------------
def test_chu_de_toi_va_sang(qapp):
    from PySide6.QtGui import QPalette
    theme.apply_theme(qapp, "dark")
    assert qapp.palette().color(QPalette.Window).lightness() < 100
    theme.apply_theme(qapp, "light")
    assert qapp.palette().color(QPalette.Window).lightness() > 150
    assert theme.apply_theme(qapp, "system") in ("light", "dark")
    assert theme.apply_theme(qapp, "linh tinh") in ("light", "dark")


# ---- trang Cài đặt chung --------------------------------------------------
@pytest.fixture()
def paths(tmp_path):
    return tmp_path / "app_settings.json", tmp_path / ".env"


def test_trang_nap_gia_tri_hien_co(qapp, paths):
    sp, ep = paths
    S.save(S.Settings(language="en", theme="dark", concurrency=5), sp)
    page = SettingsPage(sp, ep)
    assert page.concurrency.value() == 5
    assert page.language.currentData() == "en" and page.theme.currentData() == "dark"


def test_luu_cai_dat_va_phat_tin_hieu(qapp, paths):
    sp, ep = paths
    page = SettingsPage(sp, ep)
    got = []
    page.changed.connect(got.append)
    page.concurrency.setValue(7)
    page.theme.setCurrentIndex(page.theme.findData("dark"))
    page.language.setCurrentIndex(page.language.findData("en"))
    page.save()
    s = S.load(sp)
    assert (s.concurrency, s.theme, s.language) == (7, "dark", "en")
    assert got and got[-1].concurrency == 7


def test_khoa_gemini_vao_env_khong_vao_settings(qapp, paths):
    sp, ep = paths
    page = SettingsPage(sp, ep)
    page.provider.setCurrentIndex(page.provider.findData("gemini_api"))
    page.gemini_key.setText("AIzaSyKHOA1234567890")
    page.save()
    assert env_store.has_key(ep, "GEMINI_API_KEY")
    assert "AIzaSyKHOA1234567890" not in sp.read_text(encoding="utf-8")
    assert page.gemini_key.text() == ""                          # ô nhập được xoá sau khi lưu
    assert "AIzaSyKHOA1234567890" not in page.msg.text()         # và không lặp lại ở thông báo
    assert page.gemini_key.echoMode().name == "Password"


def test_khong_go_khoa_thi_khong_ghi_de_khoa_cu(qapp, paths):
    sp, ep = paths
    env_store.set_key(ep, "GEMINI_API_KEY", "khoacu123")
    page = SettingsPage(sp, ep)
    page.provider.setCurrentIndex(page.provider.findData("gemini_api"))
    page.save()                                                   # không nhập khoá mới
    assert "khoacu123" in ep.read_text(encoding="utf-8")


def test_khoa_sai_dinh_dang_bi_chan_va_khong_luu(qapp, paths):
    sp, ep = paths
    page = SettingsPage(sp, ep)
    page.provider.setCurrentIndex(page.provider.findData("gemini_api"))
    page.gemini_key.setText("co dau cach")
    page.save()
    assert not env_store.has_key(ep, "GEMINI_API_KEY")
    assert "không hợp lệ" in page.msg.text().lower()


# ---- bộ chọn giờ chạy trên trang luồng -------------------------------------
YAML = """\
flows:
  - id: luong-a
    name: "A"
    topic: "T"
    daily_quota: 4
    schedule: ["30 5 * * *"]
    timezone: Asia/Bangkok
  - id: luong-b
    name: "B"
    topic: "T"
    daily_quota: 4
    schedule: ["0 9 * * 1"]
"""


@pytest.fixture()
def cfg(tmp_path):
    p = tmp_path / "flows.yaml"
    p.write_text(YAML, encoding="utf-8")
    return p


def test_hien_gio_chay_tu_cron(qapp, cfg):
    page = FlowsPage(cfg)
    assert [page.times.item(i).text() for i in range(page.times.count())] == ["05:30"]


def test_them_gio_va_luu_ra_cron(qapp, cfg):
    from PySide6.QtCore import QTime
    page = FlowsPage(cfg)
    page.time_edit.setTime(QTime(17, 0))
    page._add_time()
    page.save()
    assert next(f for f in load_flows(cfg) if f.id == "luong-a").schedule == ["30 5 * * *", "0 17 * * *"]


def test_xoa_gio(qapp, cfg):
    from PySide6.QtCore import QTime
    page = FlowsPage(cfg)
    page.time_edit.setTime(QTime(8, 15))
    page._add_time()
    page.times.setCurrentRow(0)
    page._remove_time()
    page.save()
    assert next(f for f in load_flows(cfg) if f.id == "luong-a").schedule == ["15 8 * * *"]


def test_cron_phuc_tap_khong_bi_ghi_de(qapp, cfg):
    """luong-b chạy theo thứ Hai — bộ chọn giờ không được âm thầm đổi thành 'hằng ngày'."""
    page = FlowsPage(cfg)
    page.list.setCurrentRow(1)
    assert not page.time_edit.isEnabled() and "tùy chỉnh" in page.times_note.text().lower()
    page.quota.setValue(5)
    page.save()
    assert next(f for f in load_flows(cfg) if f.id == "luong-b").schedule == ["0 9 * * 1"]


def test_so_tin_toi_da_50(qapp, cfg):
    assert FlowsPage(cfg).quota.maximum() == 50


# ---- quét toàn cửa sổ: không sót chữ Việt cố định khi chuyển English --------
VN = set("ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ")


def _texts(root):
    from PySide6.QtWidgets import (QAbstractButton, QComboBox, QGroupBox, QLabel, QLineEdit,
                                   QPlainTextEdit, QTabWidget, QTableWidget)
    for w in root.findChildren(object):
        if isinstance(w, (QLabel, QAbstractButton)) and w.text():
            yield w, "text", w.text()
        elif isinstance(w, QGroupBox):
            yield w, "title", w.title()
        elif isinstance(w, (QLineEdit, QPlainTextEdit)) and w.placeholderText():
            yield w, "placeholder", w.placeholderText()
        elif isinstance(w, QTabWidget):
            for i in range(w.count()):
                yield w, f"tab{i}", w.tabText(i)
        elif isinstance(w, QTableWidget):
            for c in range(w.columnCount()):
                it = w.horizontalHeaderItem(c)
                if it is not None:
                    yield w, f"header{c}", it.text()


def test_khong_sot_chu_viet_co_dinh_khi_chuyen_english(qapp, tmp_path):
    from agnet.ui.app import MainWindow
    flows = tmp_path / "flows.yaml"
    flows.write_text(YAML, encoding="utf-8")
    win = MainWindow(flows, tmp_path / "a.db", tmp_path / "s.json", tmp_path / ".env", tmp_path / "out")
    i18n.apply(win, "en")
    # nhãn động do ứng dụng dựng lúc chạy (f-string) — đã nêu là giới hạn trong i18n.py
    dong = {"info", "msg", "note", "state", "warn", "key_state", "times_note", "mix_sum", "count", "head", "flags", "msg", "summary", "cool_note", "header", "status_note"}
    sot = []
    for w, slot, text in _texts(win):
        if any(ch in VN for ch in text.lower()) and not any(getattr(win, a, None) is w or
                                                           getattr(getattr(win, p, None), a, None) is w
                                                           for p in ("runs", "library", "flows", "general", "account", "koc", "cost")
                                                           for a in dong):
            sot.append((type(w).__name__, slot, text))
    assert not sot, f"còn chữ Việt chưa có bản dịch: {sot}"


def test_mui_gio_sai_bi_chan(qapp, cfg):
    page = FlowsPage(cfg)
    page.tz.setCurrentText("Khong/Co_That")
    page.save()
    assert "không hợp lệ" in page.msg.text().lower()
    assert next(f for f in load_flows(cfg) if f.id == "luong-a").timezone == "Asia/Bangkok"
