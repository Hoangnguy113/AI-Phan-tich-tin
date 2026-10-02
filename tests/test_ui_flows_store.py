"""Sửa config/flows.yaml an toàn từ GUI: giữ comment, kiểm tra hợp lệ, có bản .bak.

Trọng tâm: người dùng đặt SỐ TIN TRONG NGÀY (daily_quota). models.py bắt
tổng duration_mix phải bằng daily_quota, nên đổi quota phải chia lại mix.
"""
from __future__ import annotations

import pytest

from agnet.core.models import load_flows
from agnet.ui import flows_store as fs

YAML = """\
# Ghi chú đầu file phải còn
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
    catchup: true            # ghi chú cuối dòng phải còn
  - id: luong-b
    name: "Luồng B"
    topic: "Chủ đề B"
    daily_quota: 4
    schedule: ["0 16 * * *"]
"""


@pytest.fixture()
def cfg(tmp_path):
    p = tmp_path / "flows.yaml"
    p.write_text(YAML, encoding="utf-8")
    return p


# ---- chia lại duration_mix theo số tin trong ngày ------------------------
@pytest.mark.parametrize("quota", [1, 2, 3, 5, 7, 10, 13, 25, 100])
def test_chia_lai_mix_luon_bang_dung_quota(quota):
    mix = fs.rescale_mix({"3-5": 3, "8-12": 5, "15-20": 2}, quota)
    assert sum(mix.values()) == quota
    assert set(mix) == {"3-5", "8-12", "15-20"}
    assert all(v >= 0 for v in mix.values())


def test_chia_lai_mix_giu_ty_le_gan_nhat():
    assert fs.rescale_mix({"3-5": 3, "8-12": 5, "15-20": 2}, 20) == {"3-5": 6, "8-12": 10, "15-20": 4}


def test_mix_rong_thi_van_rong():
    assert fs.rescale_mix({}, 7) == {}


# ---- đặt số tin trong ngày ----------------------------------------------
def test_dat_so_tin_trong_ngay_va_giu_comment(cfg):
    fs.set_fields(cfg, "luong-a", {"daily_quota": 6, "duration_mix": fs.rescale_mix(
        {"3-5": 3, "8-12": 5, "15-20": 2}, 6)})
    txt = cfg.read_text(encoding="utf-8")
    assert "# Ghi chú đầu file phải còn" in txt
    assert "# ghi chú cuối dòng phải còn" in txt
    a = next(f for f in load_flows(cfg) if f.id == "luong-a")
    assert a.daily_quota == 6 and sum(a.duration_mix.values()) == 6


def test_doi_quota_khong_chia_mix_thi_bi_tu_choi(cfg):
    """Chốt chặn: lưu sai không được phá file đang chạy được."""
    with pytest.raises(fs.InvalidFlows):
        fs.set_fields(cfg, "luong-a", {"daily_quota": 6})
    assert cfg.read_text(encoding="utf-8") == YAML     # file gốc còn nguyên


def test_khong_sua_lan_sang_luong_khac(cfg):
    fs.set_fields(cfg, "luong-b", {"daily_quota": 9})
    flows = {f.id: f for f in load_flows(cfg)}
    assert flows["luong-b"].daily_quota == 9
    assert flows["luong-a"].daily_quota == 10          # luồng A không bị đụng


def test_co_ban_bak_sau_khi_luu(cfg):
    fs.set_fields(cfg, "luong-b", {"daily_quota": 5})
    assert (cfg.parent / "flows.yaml.bak").read_text(encoding="utf-8") == YAML


def test_them_truong_chua_co_trong_file(cfg):
    fs.set_fields(cfg, "luong-b", {"daily_quota": 2, "timezone": "Asia/Bangkok"})
    assert next(f for f in load_flows(cfg) if f.id == "luong-b").timezone == "Asia/Bangkok"


def test_bat_tat_luong(cfg):
    fs.set_fields(cfg, "luong-b", {"enabled": False})
    assert next(f for f in load_flows(cfg) if f.id == "luong-b").enabled is False


def test_luong_khong_ton_tai(cfg):
    with pytest.raises(KeyError):
        fs.set_fields(cfg, "khong-co", {"daily_quota": 3})


def test_quota_phai_tu_1(cfg):
    with pytest.raises(fs.InvalidFlows):
        fs.set_fields(cfg, "luong-b", {"daily_quota": 0})


def test_doc_duoc_danh_sach_luong(cfg):
    assert fs.flow_ids(cfg) == ["luong-a", "luong-b"]
