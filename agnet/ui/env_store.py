"""Ghi/đọc khoá API trong .env — không bao giờ in giá trị, không bao giờ đưa vào settings hay log.

Chỉ thay đúng dòng cần sửa để giữ comment và các khoá khác (ANTHROPIC_API_KEY, TELEGRAM_*...).
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from ..env import ROOT

DEFAULT_PATH = ROOT / ".env"
_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")


def _check(name: str, value: str | None = None) -> None:
    if not _NAME.match(name):
        raise ValueError(f"tên khoá không hợp lệ: {name!r}")
    if value is not None and (not value or any(c.isspace() for c in value) or "#" in value):
        # khoảng trắng, xuống dòng, '#' làm hỏng cách load_env đọc dòng KEY=VALUE
        raise ValueError("giá trị rỗng, hoặc chứa khoảng trắng / xuống dòng / '#'")


def _lines(p: Path) -> list[str]:
    return p.read_text(encoding="utf-8").splitlines() if p.exists() else []


def _write(p: Path, lines: list[str]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        os.chmod(tmp, 0o600)                       # chứa khoá: chỉ chủ sở hữu đọc được
    except OSError:
        pass
    os.replace(tmp, p)                             # nguyên tử: lỗi giữa chừng không làm cụt .env


def _set(p: Path, name: str, value: str) -> None:
    lines, done = _lines(p), False
    for i, line in enumerate(lines):
        if line.partition("=")[0].strip() == name and "=" in line and not line.lstrip().startswith("#"):
            lines[i], done = f"{name}={value}", True
            break
    if not done:
        lines.append(f"{name}={value}")
    _write(p, lines)


def set_key(path: str | Path | None, name: str, value: str) -> None:
    _check(name, value)
    _set(Path(path or DEFAULT_PATH), name, value)


def clear_key(path: str | Path | None, name: str) -> None:
    """Xoá giá trị nhưng giữ tên biến, đúng kiểu .env hiện có (xem load_env: giá trị rỗng bị bỏ qua)."""
    _check(name)
    p = Path(path or DEFAULT_PATH)
    if p.exists():
        _set(p, name, "")


def has_key(path: str | Path | None, name: str) -> bool:
    for line in _lines(Path(path or DEFAULT_PATH)):
        k, _, v = line.strip().partition("=")
        if k.strip() == name and v.strip().strip("\"'"):
            return True
    return False


def mask(value: str) -> str:
    """Che khoá để hiển thị: giữ 4 ký tự đầu và 4 ký tự cuối khi đủ dài, còn lại là chấm."""
    if not value:
        return ""
    if len(value) <= 8:
        return "•" * len(value)
    return value[:4] + "•" * (len(value) - 8) + value[-4:]
