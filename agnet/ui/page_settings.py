"""Trang Cài đặt chung: ngôn ngữ, chủ đề, số agent chạy song song, Gemini.

Cài đặt THEO LUỒNG (số tin/ngày, giờ chạy, trần chi phí) ở trang "Cài đặt luồng".
Khoá Gemini lưu vào .env (không vào app_settings.json), ô nhập luôn che và được xoá sau khi lưu.
"""
from __future__ import annotations

import shutil
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QSpinBox, QVBoxLayout, QWidget)

from ..core import settings as S
from . import env_store

KEY_NAME = "GEMINI_API_KEY"


class SettingsPage(QWidget):
    changed = Signal(object)                     # Settings vừa lưu → cửa sổ chính áp dụng ngay

    def __init__(self, settings_path: str | Path | None = None, env_path: str | Path | None = None,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.settings_path = Path(settings_path) if settings_path else S.DEFAULT_PATH
        self.env_path = Path(env_path) if env_path else env_store.DEFAULT_PATH
        self._build()
        self.reload()

    # ---- dựng giao diện -------------------------------------------------
    def _combo(self, items: list[tuple[str, str]]) -> QComboBox:
        c = QComboBox()
        for label, data in items:
            c.addItem(label, data)
        return c

    def _build(self) -> None:
        self.language = self._combo([("Tiếng Việt", "vi"), ("English", "en")])
        self.theme = self._combo([("Theo hệ thống", "system"), ("Sáng", "light"), ("Tối", "dark")])

        self.concurrency = QSpinBox()
        self.concurrency.setRange(*S.CONCURRENCY_RANGE)
        self.concurrency.setSuffix("  agent")
        self.conc_note = QLabel(
            "Nhiều agent cùng dùng một lần đăng nhập Claude có thể đua nhau làm mới token "
            "(đã gặp khi chạy thật 02/10/2026). Mặc định 3 là mức thận trọng.")
        self.conc_note.setWordWrap(True)
        self.conc_note.setStyleSheet("color: gray;")

        self.provider = self._combo([("Tắt (chỉ dùng Claude)", "off"),
                                     ("Gemini API (khóa Google AI Studio)", "gemini_api"),
                                     ("Gemini CLI (đăng nhập Google)", "gemini_cli")])
        self.provider.currentIndexChanged.connect(self._provider_changed)
        self.model = QLineEdit()
        self.gemini_key = QLineEdit()
        self.gemini_key.setEchoMode(QLineEdit.Password)
        self.gemini_key.setPlaceholderText("Dán khóa mới (để trống = giữ khóa hiện tại)")
        self.btn_clear_key = QPushButton("Xóa khóa")
        self.btn_clear_key.clicked.connect(self._clear_key)
        self.key_state = QLabel()
        self.key_state.setWordWrap(True)

        box_ui = QGroupBox("Giao diện")
        f1 = QFormLayout(box_ui)
        f1.addRow("Ngôn ngữ giao diện:", self.language)
        f1.addRow("Chủ đề:", self.theme)

        box_run = QGroupBox("Chạy song song")
        f2 = QFormLayout(box_run)
        f2.addRow("Số agent chạy song song:", self.concurrency)
        f2.addRow(self.conc_note)

        box_gem = QGroupBox("Khảo sát thị trường & tìm kiếm mạng (Gemini)")
        f3 = QFormLayout(box_gem)
        f3.addRow("Nhà cung cấp:", self.provider)
        f3.addRow("Model:", self.model)
        keyrow = QHBoxLayout()
        keyrow.addWidget(self.gemini_key, 1)
        keyrow.addWidget(self.btn_clear_key)
        f3.addRow("Khóa Gemini API:", keyrow)
        f3.addRow(self.key_state)

        self.btn_save = QPushButton("Lưu")
        self.btn_save.clicked.connect(self.save)
        self.msg = QLabel()
        self.msg.setWordWrap(True)

        root = QVBoxLayout(self)
        for b in (box_ui, box_run, box_gem):
            root.addWidget(b)
        row = QHBoxLayout()
        row.addWidget(self.btn_save)
        row.addStretch(1)
        root.addLayout(row)
        root.addWidget(self.msg)
        root.addStretch(1)

    # ---- dữ liệu --------------------------------------------------------
    def reload(self) -> None:
        s = S.load(self.settings_path)
        self.language.setCurrentIndex(max(0, self.language.findData(s.language)))
        self.theme.setCurrentIndex(max(0, self.theme.findData(s.theme)))
        self.concurrency.setValue(s.concurrency)
        self.provider.setCurrentIndex(max(0, self.provider.findData(s.gemini_provider)))
        self.model.setText(s.gemini_model)
        self.gemini_key.clear()
        self._provider_changed()

    def current(self) -> S.Settings:
        # Bắt đầu từ cài đặt đã lưu để KHÔNG đè các trường do trang khác sở hữu (chính sách Gemini ở trang Gemini).
        return replace(S.load(self.settings_path), language=self.language.currentData(),
                       theme=self.theme.currentData(), concurrency=self.concurrency.value(),
                       gemini_provider=self.provider.currentData(), gemini_model=self.model.text()).normalized()

    def _provider_changed(self) -> None:
        p = self.provider.currentData()
        api = p == "gemini_api"
        for w in (self.gemini_key, self.btn_clear_key):
            w.setEnabled(api)
        self.model.setEnabled(p != "off")
        if p == "gemini_api":
            have = env_store.has_key(self.env_path, KEY_NAME)
            self.key_state.setText("Đã có khóa Gemini trong .env." if have else
                                   "Chưa có khóa Gemini — dán khóa vào ô trên rồi bấm Lưu.")
            self.key_state.setStyleSheet("color: #137333;" if have else "color: #c5221f;")
        elif p == "gemini_cli":
            ok = shutil.which("gemini") is not None
            self.key_state.setText("Đã tìm thấy lệnh `gemini`. Cần đã đăng nhập Google trong Gemini CLI."
                                   if ok else "Chưa cài Gemini CLI (không thấy lệnh `gemini` trong PATH).")
            self.key_state.setStyleSheet("color: #137333;" if ok else "color: #c5221f;")
        else:
            self.key_state.setText("Gemini đang tắt — các agent khảo sát sẽ dùng Claude như cũ.")
            self.key_state.setStyleSheet("color: gray;")

    def _say(self, text: str, bad: bool = False) -> None:
        self.msg.setText(text)
        self.msg.setStyleSheet("color: #c5221f;" if bad else "color: #137333;")

    # ---- thao tác -------------------------------------------------------
    def _clear_key(self) -> None:
        env_store.clear_key(self.env_path, KEY_NAME)
        self.gemini_key.clear()
        self._provider_changed()
        self._say("Đã xóa khóa Gemini khỏi .env.")

    def save(self) -> None:
        new_key = self.gemini_key.text().strip()
        if new_key:
            try:
                env_store.set_key(self.env_path, KEY_NAME, new_key)
            except ValueError:
                # không lặp lại giá trị người dùng nhập ở bất cứ đâu
                self._say("Khóa không hợp lệ (không được rỗng, có khoảng trắng hoặc ký tự '#'). Chưa lưu gì.", bad=True)
                return
        try:
            saved = S.save(self.current(), self.settings_path)
        except OSError as e:
            self._say(f"Không ghi được cài đặt: {e}", bad=True)
            return
        self.gemini_key.clear()                    # không để khóa nằm trong ô sau khi đã lưu
        self._provider_changed()
        self._say("Đã lưu cài đặt." + (" Đã ghi khóa Gemini vào .env." if new_key else ""))
        self.changed.emit(saved)
