"""Đổi giờ:phút <-> cron, và lưu khoá API vào .env (không bao giờ vào settings/log)."""
from __future__ import annotations

import pytest

from agnet.ui import env_store
from agnet.ui import flows_store as fs


# ---- giờ chạy <-> cron ----------------------------------------------------
def test_gio_sang_cron():
    assert fs.times_to_cron(["05:30"]) == ["30 5 * * *"]
    assert fs.times_to_cron(["17:00", "05:30"]) == ["30 5 * * *", "0 17 * * *"]   # đã sắp xếp
    assert fs.times_to_cron(["05:30", "05:30"]) == ["30 5 * * *"]                 # bỏ trùng


def test_cron_sang_gio():
    assert fs.cron_to_times(["30 5 * * *"]) == ["05:30"]
    assert fs.cron_to_times(["0 17 * * *", "30 5 * * *"]) == ["05:30", "17:00"]
    assert fs.cron_to_times([]) == []


@pytest.mark.parametrize("cron", ["*/15 * * * *", "0 9 * * 1", "0 9 1 * *", "0 */2 * * *", "1 2 3"])
def test_cron_phuc_tap_tra_none_de_khong_ghi_de(cron):
    assert fs.cron_to_times([cron]) is None
    assert fs.cron_to_times(["30 5 * * *", cron]) is None


@pytest.mark.parametrize("bad", ["25:00", "12:60", "abc", "", "5", "05:3x"])
def test_gio_sai_bi_tu_choi(bad):
    with pytest.raises(ValueError):
        fs.times_to_cron([bad])


def test_khu_hoi_dung():
    for t in (["00:00"], ["23:59"], ["05:30", "12:15", "17:45"]):
        assert fs.cron_to_times(fs.times_to_cron(t)) == sorted(t)


# ---- khoá API trong .env --------------------------------------------------
def test_them_khoa_vao_file_moi(tmp_path):
    p = tmp_path / ".env"
    env_store.set_key(p, "GEMINI_API_KEY", "abc123")
    assert p.read_text(encoding="utf-8") == "GEMINI_API_KEY=abc123\n"
    assert env_store.has_key(p, "GEMINI_API_KEY")


def test_thay_khoa_giu_nguyen_dong_khac_va_comment(tmp_path):
    p = tmp_path / ".env"
    p.write_text("# ghi chú\nANTHROPIC_API_KEY=\nGEMINI_API_KEY=cu\nTELEGRAM_CHAT_ID=42\n", encoding="utf-8")
    env_store.set_key(p, "GEMINI_API_KEY", "moi")
    lines = p.read_text(encoding="utf-8").splitlines()
    assert lines == ["# ghi chú", "ANTHROPIC_API_KEY=", "GEMINI_API_KEY=moi", "TELEGRAM_CHAT_ID=42"]


def test_them_khoa_cuoi_file_khong_co_dong_moi(tmp_path):
    p = tmp_path / ".env"
    p.write_text("A=1", encoding="utf-8")
    env_store.set_key(p, "B", "2")
    assert p.read_text(encoding="utf-8") == "A=1\nB=2\n"


def test_has_key_rong_la_false(tmp_path):
    p = tmp_path / ".env"
    p.write_text("GEMINI_API_KEY=\n", encoding="utf-8")
    assert not env_store.has_key(p, "GEMINI_API_KEY")
    assert not env_store.has_key(tmp_path / "khong_co", "GEMINI_API_KEY")


def test_xoa_khoa_de_trong_gia_tri_nhung_giu_ten(tmp_path):
    p = tmp_path / ".env"
    p.write_text("GEMINI_API_KEY=abc\n", encoding="utf-8")
    env_store.clear_key(p, "GEMINI_API_KEY")
    assert p.read_text(encoding="utf-8") == "GEMINI_API_KEY=\n"


@pytest.mark.parametrize("bad", ["co dau cach", "xuong\ndong", "co#thang", ""])
def test_gia_tri_nguy_hiem_bi_tu_choi(tmp_path, bad):
    with pytest.raises(ValueError):
        env_store.set_key(tmp_path / ".env", "GEMINI_API_KEY", bad)


def test_ten_khoa_sai_bi_tu_choi(tmp_path):
    with pytest.raises(ValueError):
        env_store.set_key(tmp_path / ".env", "ten sai", "x")


def test_che_khoa():
    assert env_store.mask("") == ""
    assert env_store.mask("abcd") == "••••"
    m = env_store.mask("AIzaSyABCDEFGH1234")
    assert "ABCDEFGH" not in m and m.startswith("AIza") and m.endswith("1234")
