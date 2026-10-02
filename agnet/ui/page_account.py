"""Trang Tài khoản Claude — chạy bằng tài khoản đã đăng nhập, không cần API key."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QProcess
from PySide6.QtWidgets import (QGroupBox, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton,
                               QVBoxLayout, QWidget)

from . import auth, procs


class AccountPage(QWidget):
    def __init__(self, flows_path: str | Path, db_path: str | Path, parent: QWidget | None = None):
        super().__init__(parent)
        self.flows_path, self.db_path = Path(flows_path), Path(db_path)
        self._proc: QProcess | None = None
        self._build()
        self.refresh()

    def _build(self) -> None:
        self.state = QLabel()
        self.state.setWordWrap(True)
        self.state.setStyleSheet("font-size: 15px;")
        self.warn = QLabel()
        self.warn.setWordWrap(True)

        btn_login = QPushButton("Đăng nhập")
        btn_login.clicked.connect(lambda: self._spawn(auth.LOGIN_CMD))
        btn_logout = QPushButton("Đăng xuất")
        btn_logout.clicked.connect(lambda: self._spawn(auth.LOGOUT_CMD))
        btn_check = QPushButton("Kiểm tra lại")
        btn_check.clicked.connect(self.refresh)
        self.btn_doctor = QPushButton("Kiểm tra hệ thống (doctor)")
        self.btn_doctor.clicked.connect(self._doctor)

        row = QHBoxLayout()
        for b in (btn_login, btn_logout, btn_check, self.btn_doctor):
            row.addWidget(b)
        row.addStretch(1)

        box = QGroupBox("Tài khoản Claude")
        lay = QVBoxLayout(box)
        lay.addWidget(self.state)
        lay.addWidget(self.warn)
        lay.addLayout(row)

        self.out = QPlainTextEdit()
        self.out.setReadOnly(True)
        self.out.setPlaceholderText("Kết quả kiểm tra hệ thống hiện ở đây.")

        root = QVBoxLayout(self)
        root.addWidget(box)
        root.addWidget(self.out, 1)

    def refresh(self) -> None:
        s = auth.status()
        self.state.setText(s.mo_ta() + (f"<br><small>{s.org}</small>" if s.org else ""))
        self.state.setStyleSheet("font-size: 15px; color: %s;" %
                                 ("#137333" if s.ready else "#c5221f"))
        where = auth.api_key_in_use()
        if where:
            self.warn.setText(
                f"<b>Cảnh báo:</b> phát hiện ANTHROPIC_API_KEY ở {where}. "
                "Claude Code ưu tiên khoá API hơn tài khoản, nên lần chạy sẽ bị tính tiền theo API. "
                "Khi GUI khởi chạy pipeline thì khoá này đã được bỏ ra khỏi tiến trình con."
            )
            self.warn.setStyleSheet("color: #b06000; background: #fef7e0; padding: 6px;")
        else:
            self.warn.setText("Không có khoá API — pipeline sẽ dùng gói đăng ký của tài khoản trên.")
            self.warn.setStyleSheet("color: #137333;")

    def _spawn(self, cmd: list[str]) -> None:
        """Mở lệnh claude trong cửa sổ riêng; đăng nhập cần trình duyệt nên không bắt output."""
        QProcess.startDetached(cmd[0], cmd[1:])
        self.out.appendPlainText(f"Đã chạy: {' '.join(cmd)}\n"
                                 "Làm xong trong cửa sổ vừa mở, rồi bấm 'Kiểm tra lại'.")

    def _doctor(self) -> None:
        if self._proc is not None:
            return
        self.out.clear()
        self.btn_doctor.setEnabled(False)
        cmd = procs.doctor_cmd(self.flows_path, self.db_path)
        p = QProcess(self)
        p.setProcessChannelMode(QProcess.MergedChannels)
        p.readyReadStandardOutput.connect(
            lambda: self.out.appendPlainText(
                bytes(p.readAllStandardOutput()).decode("utf-8", "replace").rstrip()))
        p.finished.connect(self._doctor_done)
        self._proc = p
        p.start(cmd[0], cmd[1:])

    def _doctor_done(self) -> None:
        self.btn_doctor.setEnabled(True)
        self._proc = None
        self.refresh()
