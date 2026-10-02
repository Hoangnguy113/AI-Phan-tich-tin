"""Test khói giao diện, chạy ẩn màn hình. Bỏ qua nếu chưa cài PySide6.

Trọng tâm: đổi SỐ TIN TRONG NGÀY trên giao diện phải tự chia lại bảng thời lượng
và lưu được — vì models.py bắt tổng duration_mix == daily_quota.
"""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6", reason="chưa cài PySide6")

from PySide6.QtWidgets import QApplication            # noqa: E402

from agnet.core.models import load_flows              # noqa: E402
from agnet.ui.page_flows import FlowsPage             # noqa: E402

YAML = """\
# comment đầu file
flows:
  - id: luong-a
    name: "Luồng A"
    enabled: true
    topic: "Chủ đề A"
    duration_min: 3
    duration_max: 20
    duration_mix: {"3-5": 3, "8-12": 5, "15-20": 2}
    daily_quota: 10
    schedule: ["30 5 * * *"]
    max_cost_usd_per_day: 8
  - id: luong-b
    name: "Luồng B"
    topic: "Chủ đề B"
    daily_quota: 4
    schedule: ["0 16 * * *"]
"""


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def cfg(tmp_path):
    p = tmp_path / "flows.yaml"
    p.write_text(YAML, encoding="utf-8")
    return p


def test_mo_duoc_va_nap_dung_luong(qapp, cfg):
    page = FlowsPage(cfg)
    assert [page.list.item(i).text() for i in range(page.list.count())] == ["luong-a", "luong-b"]
    assert page.quota.value() == 10
    assert page.mix.rowCount() == 3


def test_doi_so_tin_trong_ngay_tu_chia_lai_bang(qapp, cfg):
    page = FlowsPage(cfg)
    page.quota.setValue(20)
    assert sum(page._read_mix().values()) == 20          # giao diện tự khớp tổng
    assert page.btn_save.isEnabled()


def test_luu_so_tin_trong_ngay_vao_file(qapp, cfg):
    page = FlowsPage(cfg)
    page.quota.setValue(6)
    page.save()
    f = next(x for x in load_flows(cfg) if x.id == "luong-a")
    assert f.daily_quota == 6 and sum(f.duration_mix.values()) == 6
    assert "# comment đầu file" in cfg.read_text(encoding="utf-8")


def test_tong_lech_thi_chan_khong_cho_luu(qapp, cfg):
    page = FlowsPage(cfg)
    page.mix.item(0, 1).setText("99")                   # người dùng sửa tay thành sai
    assert not page.btn_save.isEnabled()
    assert "chưa lưu được" in page.mix_sum.text()


def test_luong_khong_co_bang_thoi_luong_van_luu_duoc(qapp, cfg):
    page = FlowsPage(cfg)
    page.list.setCurrentRow(1)                          # luong-b không có duration_mix
    assert page.mix.rowCount() == 0 and page.btn_save.isEnabled()
    page.quota.setValue(7)
    page.save()
    assert next(x for x in load_flows(cfg) if x.id == "luong-b").daily_quota == 7


def test_bat_tat_luong_tu_giao_dien(qapp, cfg):
    page = FlowsPage(cfg)
    page.list.setCurrentRow(1)
    page.enabled.setChecked(False)
    page.save()
    assert next(x for x in load_flows(cfg) if x.id == "luong-b").enabled is False
