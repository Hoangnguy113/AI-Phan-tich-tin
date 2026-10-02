"""Thanh điều hướng bên trái: danh sách mục + vùng nội dung xếp chồng (thay cho tab ngang)."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QStackedWidget,
                               QVBoxLayout, QWidget)

STYLE = """
#Sidebar { background: palette(alternate-base); border-right: 1px solid palette(mid); }
#Brand { font-size: 17px; font-weight: 700; padding: 14px 16px 2px 16px; }
#BrandSub { color: palette(placeholder-text); padding: 0 16px 10px 16px; }
#Nav { background: transparent; border: none; outline: 0; }
#Nav::item { padding: 9px 14px; margin: 1px 8px; border-radius: 6px; }
#Nav::item:hover:!selected { background: palette(midlight); }
#Nav::item:selected { background: palette(highlight); color: palette(highlighted-text); }
#SideFoot { color: palette(placeholder-text); padding: 8px 16px 12px 16px; }
"""


class SidebarShell(QWidget):
    """Điều hướng trái + trang phải. `add_page` thêm mục; Ctrl+1…9 nhảy nhanh tới từng mục."""
    page_changed = Signal(int)

    def __init__(self, brand: str = "Agnet", subtitle: str = "", footer: str = "", parent=None):
        super().__init__(parent)
        self.setStyleSheet(STYLE)
        self.nav = QListWidget(objectName="Nav")
        self.nav.setIconSize(QSize(18, 18))
        self.nav.setFocusPolicy(Qt.NoFocus)
        self.stack = QStackedWidget()

        side = QFrame(objectName="Sidebar")
        side.setFixedWidth(210)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(0)
        sl.addWidget(QLabel(brand, objectName="Brand"))
        if subtitle:
            sl.addWidget(QLabel(subtitle, objectName="BrandSub"))
        sl.addWidget(self.nav, 1)
        self.footer = QLabel(footer, objectName="SideFoot")
        self.footer.setWordWrap(True)
        sl.addWidget(self.footer)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(side)
        lay.addWidget(self.stack, 1)
        self.nav.currentRowChanged.connect(self._on_row)

    def add_page(self, title: str, page: QWidget) -> int:
        idx = self.stack.addWidget(page)
        self.nav.addItem(QListWidgetItem(title))
        if idx < 9:
            QShortcut(QKeySequence(f"Ctrl+{idx + 1}"), self, activated=lambda i=idx: self.set_current(i))
        if self.nav.currentRow() < 0:
            self.nav.setCurrentRow(0)
        return idx

    def set_current(self, idx: int) -> None:
        self.nav.setCurrentRow(idx)

    def current(self) -> int:
        return self.stack.currentIndex()

    def _on_row(self, row: int) -> None:
        if 0 <= row < self.stack.count():
            self.stack.setCurrentIndex(row)
            self.page_changed.emit(row)
