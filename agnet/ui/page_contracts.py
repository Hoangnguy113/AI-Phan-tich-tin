"""Trang "Hợp đồng & tỉ lệ đạt": đọc ComplianceStore, chỉ hiện số đo thật; chưa có lượt nào thì nói rõ, không bịa."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (QAbstractItemView, QHBoxLayout, QHeaderView, QLabel, QPushButton, QSpinBox,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from ..commander.metrics import ComplianceStore

EMPTY = "Chưa có lượt chạy Gemini nào."


class ContractsPage(QWidget):
    def __init__(self, db_path: str | Path = "agnet.db", parent: QWidget | None = None):
        super().__init__(parent)
        self.db_path = str(db_path)
        self.last_n = QSpinBox()
        self.last_n.setRange(0, 1000)
        self.last_n.setSpecialValueText("tất cả")
        self.last_n.setPrefix("N lượt gần nhất: ")
        self.last_n.setValue(0)
        self.btn = QPushButton("Làm mới")
        self.btn.clicked.connect(self.refresh)
        self.info = QLabel()
        self.info.setWordWrap(True)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Agent", "Số lượt", "Đạt", "Không đạt", "Đạt ngay lần 1", "Tỉ lệ đạt"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        bar = QHBoxLayout()
        bar.addWidget(self.last_n)
        bar.addWidget(self.btn)
        bar.addStretch(1)
        root = QVBoxLayout(self)
        root.addLayout(bar)
        root.addWidget(self.info)
        root.addWidget(self.table, 1)
        self.refresh()

    def refresh(self) -> None:
        try:
            rates = ComplianceStore(self.db_path).rates(last_n=self.last_n.value() or None)
        except Exception as e:                                  # noqa: BLE001
            rates = {}
            self.info.setText(f"Không đọc được số đo: {type(e).__name__}: {e}")
            self.info.setStyleSheet("color: #c5221f;")
            self.table.setRowCount(0)
            return
        self.table.setRowCount(len(rates))
        for i, (agent, r) in enumerate(sorted(rates.items())):
            vals = [agent, str(r["runs"]), str(r["passed"]), str(r["failed"]), str(r["first_try"]),
                    f"{r['rate'] * 100:.0f}%"]
            for c, v in enumerate(vals):
                self.table.setItem(i, c, QTableWidgetItem(v))
        if rates:
            self.info.setText(f"{len(rates)} agent có số đo.")
            self.info.setStyleSheet("color: gray;")
        else:
            self.info.setText(EMPTY)
            self.info.setStyleSheet("color: #b06000;")
