"""Thanh điều hướng trái: chọn mục đổi trang, chữ dịch được, cửa sổ chính dùng nó."""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6", reason="chưa cài PySide6")

from PySide6.QtWidgets import QApplication, QLabel     # noqa: E402

from agnet.ui import i18n                              # noqa: E402
from agnet.ui.app import MainWindow                    # noqa: E402
from agnet.ui.sidebar import SidebarShell              # noqa: E402

app = QApplication.instance() or QApplication([])


def test_chon_muc_doi_trang():
    sh = SidebarShell("A")
    a, b = QLabel("a"), QLabel("b")
    sh.add_page("Một", a)
    sh.add_page("Hai", b)
    assert sh.current() == 0
    got = []
    sh.page_changed.connect(got.append)
    sh.nav.setCurrentRow(1)
    assert sh.stack.currentWidget() is b and got == [1]


def test_cua_so_chinh_co_6_muc_va_dich(tmp_path):
    flows = tmp_path / "flows.yaml"
    flows.write_text('flows:\n  - id: a\n    name: "A"\n    topic: "t"\n    daily_quota: 1\n    schedule: ["0 5 * * *"]\n', encoding="utf-8")
    w = MainWindow(flows, tmp_path / "a.db", tmp_path / "s.json", tmp_path / ".env", tmp_path / "out")
    nav = w.shell.nav
    assert [nav.item(i).text() for i in range(nav.count())][:2] == ["Bảng điều khiển", "Kho kịch bản"]
    assert nav.count() == 6
    i18n.apply(w, "en")
    assert nav.item(0).text() == "Dashboard"
    i18n.apply(w, "vi")
    assert nav.item(0).text() == "Bảng điều khiển"
