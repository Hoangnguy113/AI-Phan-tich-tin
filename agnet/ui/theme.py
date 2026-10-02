"""Chủ đề sáng / tối / theo hệ thống cho toàn ứng dụng.

Dùng kiểu Fusion + bảng màu tường minh để "sáng" và "tối" giống nhau trên mọi máy,
không phụ thuộc cách Windows tô cửa sổ.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


def _palette(dark: bool) -> QPalette:
    p = QPalette()
    if dark:
        c = dict(window="#202124", base="#17181a", alt="#2a2b2e", text="#e8eaed", button="#2d2e31",
                 hi="#3b78e7", dis="#80868b", tip="#2d2e31")
    else:
        c = dict(window="#f6f7f9", base="#ffffff", alt="#eef0f3", text="#202124", button="#e8eaed",
                 hi="#1a73e8", dis="#9aa0a6", tip="#ffffe1")
    q = {k: QColor(v) for k, v in c.items()}
    for role, key in ((QPalette.Window, "window"), (QPalette.Base, "base"), (QPalette.AlternateBase, "alt"),
                      (QPalette.WindowText, "text"), (QPalette.Text, "text"), (QPalette.ButtonText, "text"),
                      (QPalette.Button, "button"), (QPalette.Highlight, "hi"), (QPalette.ToolTipBase, "tip"),
                      (QPalette.ToolTipText, "text")):
        p.setColor(role, q[key])
    p.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    p.setColor(QPalette.PlaceholderText, q["dis"])
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        p.setColor(QPalette.Disabled, role, q["dis"])
    return p


def system_is_dark(app: QApplication) -> bool:
    try:
        return app.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except AttributeError:                      # Qt cũ không có colorScheme
        return False


def apply_theme(app: QApplication, mode: str) -> str:
    """Áp chủ đề; trả về 'light' hoặc 'dark' thực tế đã dùng."""
    dark = system_is_dark(app) if mode not in ("light", "dark") else mode == "dark"
    app.setStyle("Fusion")
    app.setPalette(_palette(dark))
    return "dark" if dark else "light"
