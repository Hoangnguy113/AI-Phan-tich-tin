"""Trang Hợp đồng & tỉ lệ đạt: số đo thật từ ComplianceStore, rỗng thì nói rõ."""
from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6", reason="chưa cài PySide6")

from PySide6.QtWidgets import QApplication      # noqa: E402

from agnet.commander.metrics import ComplianceStore     # noqa: E402
from agnet.ui import i18n                       # noqa: E402
from agnet.ui.page_contracts import ContractsPage       # noqa: E402

app = QApplication.instance() or QApplication([])


def rec(st, agent, comp, attempts):
    st.record(SimpleNamespace(agent=agent, flow_id="f"),
              SimpleNamespace(report=None, items=[1], compliance=comp, attempts=attempts, errors=[]))


def test_chua_co_du_lieu_noi_ro(tmp_path):
    p = ContractsPage(tmp_path / "a.db")
    assert p.table.rowCount() == 0 and p.info.text() == "Chưa có lượt chạy Gemini nào."


def test_hien_so_do_va_loc_n_luot(tmp_path):
    db = tmp_path / "a.db"
    st = ComplianceStore(db)
    for comp, att in (("fail", 2), ("pass", 2), ("pass", 1), ("pass", 1)):
        rec(st, "news-scout", comp, att)
    p = ContractsPage(db)
    vals = [p.table.item(0, c).text() for c in range(6)]
    assert vals == ["news-scout", "4", "3", "1", "2", "75%"]
    p.last_n.setValue(2)
    p.btn.click()
    assert [p.table.item(0, c).text() for c in range(6)] == ["news-scout", "2", "2", "0", "2", "100%"]
    rec(st, "trend-scout", "pass", 1)
    p.btn.click()
    assert p.table.rowCount() == 2


def test_dich_tieng_anh(tmp_path):
    p = ContractsPage(tmp_path / "a.db")
    i18n.apply(p, "en")
    assert p.info.text() == "No Gemini runs yet." and p.btn.text() == "Refresh"
