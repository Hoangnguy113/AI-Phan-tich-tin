"""Đọc trạng thái đăng nhập Claude cho GUI — không gọi mạng, không gọi API."""
from __future__ import annotations

import json

from agnet.ui import auth

MAU = {
    "loggedIn": True, "authMethod": "claude.ai", "apiProvider": "firstParty",
    "email": "ai@example.com", "orgName": "Tổ chức của ai@example.com",
    "subscriptionType": "pro",
}


def _fake_run(out: str, code: int = 0):
    def run(cmd, timeout=None):
        return code, out
    return run


def test_doc_duoc_tai_khoan_va_goi(monkeypatch):
    monkeypatch.setattr(auth, "_run", _fake_run(json.dumps(MAU)))
    monkeypatch.setattr(auth, "has_cli", lambda: True)
    s = auth.status()
    assert s.logged_in and s.email == "ai@example.com" and s.plan == "pro"
    assert s.method == "claude.ai" and s.ready


def test_chua_dang_nhap(monkeypatch):
    monkeypatch.setattr(auth, "_run", _fake_run(json.dumps({"loggedIn": False})))
    monkeypatch.setattr(auth, "has_cli", lambda: True)
    s = auth.status()
    assert not s.logged_in and not s.ready and s.reason


def test_thieu_lenh_claude(monkeypatch):
    monkeypatch.setattr(auth, "has_cli", lambda: False)
    s = auth.status()
    assert not s.ready and "claude" in s.reason.lower()


def test_json_rac_khong_lam_vo(monkeypatch):
    monkeypatch.setattr(auth, "_run", _fake_run("không phải json"))
    monkeypatch.setattr(auth, "has_cli", lambda: True)
    s = auth.status()
    assert not s.ready and s.raw == "không phải json"


def test_canh_bao_khi_co_api_key(monkeypatch):
    """Khoá API được ưu tiên hơn tài khoản — GUI phải cảnh báo (đo 01/10/2026)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-abc")
    assert auth.api_key_in_use() == "biến môi trường"
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    assert auth.api_key_in_use() is None


def test_canh_bao_khi_env_file_co_key(monkeypatch, tmp_path):
    f = tmp_path / ".env"
    f.write_text("ANTHROPIC_API_KEY=sk-ant-xyz\n", encoding="utf-8")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert auth.api_key_in_use(env_file=f) == f".env ({f})"
    f.write_text("ANTHROPIC_API_KEY=\n", encoding="utf-8")
    assert auth.api_key_in_use(env_file=f) is None
