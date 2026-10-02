"""Trang Bảng điều khiển — hôm nay chạy chưa, chi phí, và nút chạy ngay.

Mọi lần chạy đều ở tiến trình riêng (xem procs.py) để cửa sổ không treo.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from PySide6.QtCore import QProcess, QTimer
from PySide6.QtWidgets import (QHBoxLayout, QHeaderView, QLabel, QMessageBox, QPlainTextEdit,
                               QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from ..core.models import load_flows
from ..storage.db import Store
from . import auth, procs

COLS = ["Luồng", "Số tin/ngày", "Hôm nay", "Đã chi hôm nay", "Trần/ngày", "Lịch"]


class RunsPage(QWidget):
    def __init__(self, flows_path: str | Path, db_path: str | Path, parent: QWidget | None = None):
        super().__init__(parent)
        self.flows_path, self.db_path = Path(flows_path), Path(db_path)
        self._proc: QProcess | None = None
        self._build()
        self.refresh()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(5000)

    def _build(self) -> None:
        self.table = QTableWidget(0, len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)

        self.btn_run = QPushButton("Chạy ngay luồng đang chọn")
        self.btn_run.clicked.connect(self._run)
        self.btn_stop = QPushButton("Dừng")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop)
        btn_refresh = QPushButton("Làm mới")
        btn_refresh.clicked.connect(self.refresh)

        self.note = QLabel()
        self.note.setWordWrap(True)

        row = QHBoxLayout()
        row.addWidget(self.btn_run)
        row.addWidget(self.btn_stop)
        row.addWidget(btn_refresh)
        row.addStretch(1)

        self.runs = QTableWidget(0, 4)
        self.runs.setHorizontalHeaderLabels(["Luồng", "Ngày", "Trạng thái", "Chi phí"])
        self.runs.horizontalHeader().setStretchLastSection(True)
        self.runs.setMaximumHeight(170)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Kết quả lần chạy hiện ở đây.")

        root = QVBoxLayout(self)
        root.addWidget(QLabel("<b>Các luồng</b>"))
        root.addWidget(self.table)
        root.addLayout(row)
        root.addWidget(self.note)
        root.addWidget(QLabel("<b>Lần chạy gần đây</b>"))
        root.addWidget(self.runs)
        root.addWidget(self.log, 1)

    # ---- làm mới --------------------------------------------------------
    def refresh(self) -> None:
        try:
            flows = load_flows(self.flows_path)
        except Exception as e:
            self.note.setText(f"flows.yaml đang có lỗi: {e}")
            self.note.setStyleSheet("color: #c5221f;")
            return
        st = Store(self.db_path)
        today = date.today()
        self.table.setRowCount(len(flows))
        for r, f in enumerate(flows):
            ran = st.ran_today(f.id, today)
            vals = [f.id, str(f.daily_quota), "đã chạy" if ran else "chưa chạy",
                    f"${st.spent_today(f.id, today):.2f}", f"${f.max_cost_usd_per_day:g}",
                    ", ".join(f.schedule) or (f"mỗi {f.interval_hours:g} giờ" if f.interval_hours else "—")]
            for c, v in enumerate(vals):
                self.table.setItem(r, c, QTableWidgetItem(v))
            if not f.enabled:
                self.table.item(r, 0).setText(f.id + "  (tắt)")
        if self.table.currentRow() < 0 and flows:
            self.table.selectRow(0)

        recent = st.recent_runs(8)
        self.runs.setRowCount(len(recent))
        for r, x in enumerate(recent):
            for c, v in enumerate([x["flow_id"], x["day"], str(x["status"]),
                                   f"${x['usd'] or 0:.2f}"]):
                self.runs.setItem(r, c, QTableWidgetItem(v))

        s = auth.status()
        busy = self._proc is not None
        self.btn_run.setEnabled(s.ready and not busy)
        if not s.ready:
            self.note.setText(f"Chưa chạy được: {s.reason} — xem tab Tài khoản Claude.")
            self.note.setStyleSheet("color: #c5221f;")
        elif busy:
            self.note.setText("Đang chạy… cửa sổ vẫn dùng được bình thường.")
            self.note.setStyleSheet("color: #b06000;")
        else:
            self.note.setText(f"Sẵn sàng — chạy bằng tài khoản {s.email} (gói {s.plan}).")
            self.note.setStyleSheet("color: #137333;")

    def _selected_flow(self) -> str:
        r = self.table.currentRow()
        it = self.table.item(r, 0) if r >= 0 else None
        return it.text().replace("  (tắt)", "") if it else ""

    # ---- chạy -----------------------------------------------------------
    def _run(self) -> None:
        flow_id = self._selected_flow()
        if not flow_id or self._proc is not None:
            return
        if QMessageBox.question(
                self, "Chạy ngay?",
                f"Chạy luồng '{flow_id}' bây giờ.\n\n"
                "Việc này gọi Claude thật và tiêu hạn mức gói đăng ký của bạn. Tiếp tục?"
        ) != QMessageBox.Yes:
            return
        self.log.clear()
        cmd = procs.run_flow_cmd(flow_id, self.flows_path, self.db_path)
        p = QProcess(self)
        p.setProcessChannelMode(QProcess.MergedChannels)
        p.setProcessEnvironment(self._env())
        p.readyReadStandardOutput.connect(
            lambda: self.log.appendPlainText(
                bytes(p.readAllStandardOutput()).decode("utf-8", "replace").rstrip()))
        p.finished.connect(self._done)
        self._proc = p
        self.btn_stop.setEnabled(True)
        self.log.appendPlainText("$ " + " ".join(cmd))
        p.start(cmd[0], cmd[1:])
        self.refresh()

    @staticmethod
    def _env():
        from PySide6.QtCore import QProcessEnvironment
        env = QProcessEnvironment()
        for k, v in procs.child_env().items():
            env.insert(k, v)
        return env

    def _stop(self) -> None:
        if self._proc:
            self._proc.kill()

    def _done(self, code: int, _status) -> None:
        self.log.appendPlainText(f"\n[kết thúc, mã {code}]")
        self._proc = None
        self.btn_stop.setEnabled(False)
        self.refresh()
