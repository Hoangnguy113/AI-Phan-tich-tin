"""Dòng lệnh phải import được và khai báo đủ lệnh.

Lý do có file này: 01/10/2026 một lỗi cú pháp trong cli.py lọt qua toàn bộ 150 test
vì không test nào import module đó. Chỉ phát hiện khi chạy thật.
"""
from __future__ import annotations

import pytest

from agnet import cli


def test_import_duoc_va_co_du_lenh():
    p = cli.main.__globals__["argparse"].ArgumentParser  # chắc chắn module nạp được
    assert p is not None
    for name in ("flows", "validate", "budget", "count", "dedup", "claim",
                 "run", "serve", "doctor", "gui", "status", "catchup"):
        assert hasattr(cli, f"cmd_{name}"), name


def test_lenh_gui_bao_ro_khi_thieu_pyside(monkeypatch):
    """Thiếu PySide6 thì phải thoát kèm hướng dẫn, không được ném lỗi khó hiểu."""
    import builtins
    real = builtins.__import__

    def no_pyside(name, *a, **kw):
        if name.startswith("PySide6") or name.endswith("ui.app"):
            raise ImportError("No module named 'PySide6'")
        return real(name, *a, **kw)

    monkeypatch.setattr(builtins, "__import__", no_pyside)
    with pytest.raises(SystemExit) as e:
        cli.cmd_gui(type("A", (), {"flows": "f.yaml", "db": "d.db"})())
    assert "PySide6" in str(e.value)
