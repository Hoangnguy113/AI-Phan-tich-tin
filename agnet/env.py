"""Nạp .env vào môi trường. Không ghi đè biến đã có, không bao giờ in giá trị."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_env(path: Path | str | None = None) -> list[str]:
    """Trả về TÊN các khoá đã nạp (không có giá trị) để log được an toàn."""
    p = Path(path or ROOT / ".env")
    loaded: list[str] = []
    if not p.exists():
        return loaded
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and v and k not in os.environ:
            os.environ[k] = v
            loaded.append(k)
    return loaded
