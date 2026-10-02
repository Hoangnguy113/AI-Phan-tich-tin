"""Trạng thái đăng nhập Claude cho GUI.

Agnet chạy bằng TÀI KHOẢN Claude đã đăng nhập (`claude auth login`), không cần
ANTHROPIC_API_KEY. Đo thực tế 01/10/2026: nếu có khoá API thì Claude Code ƯU TIÊN khoá
và bỏ qua tài khoản — khoá sai sẽ gây lỗi 401 dù đã đăng nhập. Nên GUI phải cảnh báo
khi phát hiện khoá, và `api_key_in_use()` nói rõ khoá đến từ đâu.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ..env import ROOT

STATUS_CMD = ["claude", "auth", "status", "--json"]
LOGIN_CMD = ["claude", "auth", "login"]
LOGOUT_CMD = ["claude", "auth", "logout"]


@dataclass
class AuthStatus:
    logged_in: bool = False
    email: str = ""
    plan: str = ""
    method: str = ""
    org: str = ""
    reason: str = ""
    raw: str = ""

    @property
    def ready(self) -> bool:
        """Đủ điều kiện để chạy pipeline bằng tài khoản."""
        return self.logged_in

    def mo_ta(self) -> str:
        if self.ready:
            return f"Đã đăng nhập: {self.email} · gói {self.plan or 'không rõ'}"
        return f"Chưa dùng được: {self.reason or 'không rõ nguyên nhân'}"


def has_cli() -> bool:
    return shutil.which("claude") is not None


def _run(cmd: list[str], timeout: float | None = 15) -> tuple[int, str]:
    """Chạy lệnh, không bao giờ ném lỗi ra ngoài."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:                                   # lệnh thiếu, treo, quyền...
        return 1, f"{type(e).__name__}: {e}"


def status() -> AuthStatus:
    if not has_cli():
        return AuthStatus(reason="không tìm thấy lệnh `claude` trong PATH — cài Claude Code trước")
    code, out = _run(STATUS_CMD)
    try:
        d = json.loads(out[out.index("{"):out.rindex("}") + 1])
    except Exception:
        return AuthStatus(reason="không đọc được kết quả `claude auth status`", raw=out.strip())
    if not d.get("loggedIn"):
        return AuthStatus(reason="chưa đăng nhập — bấm Đăng nhập, trình duyệt sẽ mở ra",
                          raw=out.strip())
    return AuthStatus(logged_in=True, email=d.get("email", ""), plan=d.get("subscriptionType", ""),
                      method=d.get("authMethod", ""), org=d.get("orgName", ""), raw=out.strip())


def api_key_in_use(env_file: str | Path | None = None) -> str | None:
    """Khoá API đang hiện diện ở đâu, hay None nếu sạch.

    Có khoá = pipeline tính tiền theo API thay vì dùng gói đăng ký.
    """
    if (os.environ.get("ANTHROPIC_API_KEY") or "").strip():
        return "biến môi trường"
    p = Path(env_file) if env_file else ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            k, _, v = line.strip().partition("=")
            if k.strip() == "ANTHROPIC_API_KEY" and v.strip().strip("\"'"):
                return f".env ({p})"
    return None
