"""Cài đặt chung: ngôn ngữ, chủ đề, số agent song song, Gemini. File hỏng không được làm vỡ ứng dụng."""
from __future__ import annotations

import json

from agnet.core import settings as S


def test_mac_dinh():
    s = S.Settings()
    assert (s.language, s.theme, s.concurrency, s.gemini_provider) == ("vi", "system", 3, "off")


def test_khong_co_file_thi_dung_mac_dinh(tmp_path):
    assert S.load(tmp_path / "khong_co.json") == S.Settings()


def test_luu_roi_doc_lai(tmp_path):
    p = tmp_path / "s.json"
    S.save(S.Settings(language="en", theme="dark", concurrency=6, gemini_provider="gemini_api",
                      gemini_model="gemini-x"), p)
    s = S.load(p)
    assert (s.language, s.theme, s.concurrency, s.gemini_provider, s.gemini_model) == \
        ("en", "dark", 6, "gemini_api", "gemini-x")


def test_so_agent_song_song_duoc_kep_trong_mien():
    assert S.Settings(concurrency=0).normalized().concurrency == 1
    assert S.Settings(concurrency=99).normalized().concurrency == 8
    assert S.Settings(concurrency="abc").normalized().concurrency == 3
    assert S.Settings(concurrency=None).normalized().concurrency == 3


def test_gia_tri_ngoai_mien_ve_mac_dinh():
    s = S.Settings(language="fr", theme="neon", gemini_provider="x", gemini_model="  ").normalized()
    assert (s.language, s.theme, s.gemini_provider) == ("vi", "system", "off")
    assert s.gemini_model == S.Settings().gemini_model


def test_file_hong_khong_lam_vo(tmp_path):
    p = tmp_path / "s.json"
    p.write_text("{khong phai json", encoding="utf-8")
    assert S.load(p) == S.Settings()
    p.write_text("[1, 2, 3]", encoding="utf-8")
    assert S.load(p) == S.Settings()


def test_khoa_la_bi_bo_qua_va_file_sua_tay_van_duoc_kep(tmp_path):
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"language": "en", "concurrency": 500, "khoa_la": 1}), encoding="utf-8")
    s = S.load(p)
    assert s.language == "en" and s.concurrency == 8


def test_ghi_nguyen_tu_khong_de_lai_file_tam(tmp_path):
    p = tmp_path / "sub" / "s.json"
    S.save(S.Settings(), p)
    assert p.exists() and not list(p.parent.glob("*.tmp"))


def test_khong_bao_gio_luu_khoa_api(tmp_path):
    p = tmp_path / "s.json"
    S.save(S.Settings(gemini_provider="gemini_api"), p)
    txt = p.read_text(encoding="utf-8").lower()
    assert "key" not in txt and "token" not in txt and "sk-" not in txt


# ---- Gemini: tự cập nhật model & hạ bậc khi hết định mức --------------------
def test_gemini_mac_dinh_tu_cap_nhat_va_ha_bac():
    s = S.Settings()
    assert s.gemini_auto_update is True and s.gemini_fallback is True
    assert s.gemini_tier == "pro" and s.gemini_refresh_hours == 24


def test_gemini_bac_ngoai_mien_ve_mac_dinh():
    assert S.Settings(gemini_tier="ultra").normalized().gemini_tier == "pro"
    for t in ("pro", "flash", "flash-lite"):
        assert S.Settings(gemini_tier=t).normalized().gemini_tier == t


def test_gemini_gio_lam_moi_duoc_kep():
    assert S.Settings(gemini_refresh_hours=0).normalized().gemini_refresh_hours == 1
    assert S.Settings(gemini_refresh_hours=9999).normalized().gemini_refresh_hours == 168
    assert S.Settings(gemini_refresh_hours="x").normalized().gemini_refresh_hours == 24


def test_gemini_cong_tac_luu_doc_lai(tmp_path):
    p = tmp_path / "s.json"
    S.save(S.Settings(gemini_auto_update=False, gemini_fallback=False, gemini_tier="flash",
                      gemini_refresh_hours=6), p)
    s = S.load(p)
    assert (s.gemini_auto_update, s.gemini_fallback, s.gemini_tier, s.gemini_refresh_hours) == \
        (False, False, "flash", 6)
