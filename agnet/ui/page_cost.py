"""Trang Chi phí & hạn mức: chi hôm nay/trần theo luồng, tổng 7 ngày, lần chạy dừng vì trần, model Gemini đang nghỉ.

Chỉ đọc dữ liệu có thật (cost_ledger, runs, config/gemini_models.json); không có thì hiện "chưa có", không
ước lượng. Không gọi mạng. Chỉ sửa MỘT trường: max_cost_usd_per_day, qua flows_store.set_fields (giữ
nguyên comment và các trường khác).
"""
from __future__ import annotations

import json
import time
from datetime import date, timedelta
from pathlib import Path

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
                               QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from ..core.models import load_flows
from ..gemini.client import DEFAULT_CACHE
from ..storage.db import Store
from . import flows_store as fs

TITLE_VI = "Chi phí & hạn mức"
TITLE_EN = "Cost & limits"
EN: dict[str, str] = {
    "Chi phí & hạn mức": "Cost & limits",
    "Luồng": "Flow",
    "Đã chi hôm nay": "Spent today",
    "Trần/ngày": "Daily cap",
    "% trần": "% of cap",
    "Tổng 7 ngày": "7-day total",
    "Chi phí theo luồng": "Cost by flow",
    "Sửa trần chi phí": "Edit daily cap",
    "Trần chi phí/ngày (USD):": "Daily cost cap (USD):",
    "Lưu trần": "Save cap",
    "Model Gemini đang nghỉ": "Gemini models cooling down",
    "Làm mới": "Refresh",
    "Model": "Model",
    "Nghỉ đến": "Resting until",
    "Còn lại": "Remaining",
}
COLS = ["Luồng", "Đã chi hôm nay", "Trần/ngày", "% trần", "Tổng 7 ngày"]
CAPPED_PREFIX = "dừng vì hết ngân sách"
NONE = "chưa có"


def usd(v: float | None) -> str:
    return NONE if v is None else f"${v:,.2f}"


def read_cooldowns(cache_path: Path, now: float | None = None) -> list[tuple[str, float]]:
    """[(khóa model, giây còn lại)] của model đang nghỉ; [] nếu không có/hỏng tệp."""
    now = time.time() if now is None else now
    try:
        d = json.loads(Path(cache_path).read_text(encoding="utf-8"))
        cool = d.get("cooldowns") or {}
        out = [(k, float(v) - now) for k, v in cool.items() if float(v) > now]
    except (OSError, ValueError, AttributeError, TypeError):
        return []
    return sorted(out, key=lambda t: t[1])


class CostPage(QWidget):
    changed = Signal()

    def __init__(self, flows_path: str | Path, db_path: str | Path, gemini_cache: str | Path | None = None,
                 today: date | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.flows_path, self.db_path = Path(flows_path), Path(db_path)
        self.gemini_cache = Path(gemini_cache) if gemini_cache else DEFAULT_CACHE
        self._today = today
        self._build()
        self.refresh()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(10000)

    def today(self) -> date:
        return self._today or date.today()

    def _build(self) -> None:
        self.table = QTableWidget(0, len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.itemSelectionChanged.connect(self._selected)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.note = QLabel()
        self.note.setWordWrap(True)

        self.cap = QDoubleSpinBox()
        self.cap.setRange(0.01, 1000)
        self.cap.setDecimals(2)
        self.cap.setPrefix("$")
        self.btn_cap = QPushButton("Lưu trần")
        self.btn_cap.setEnabled(False)
        self.btn_cap.clicked.connect(self.save_cap)
        self.msg = QLabel()
        self.msg.setWordWrap(True)
        box = QGroupBox("Sửa trần chi phí")
        f = QFormLayout(box)
        f.addRow("Trần chi phí/ngày (USD):", self.cap)
        f.addRow(self.btn_cap)
        f.addRow(self.msg)

        self.cool = QTableWidget(0, 3)
        self.cool.setHorizontalHeaderLabels(["Model", "Nghỉ đến", "Còn lại"])
        self.cool.setEditTriggers(QTableWidget.NoEditTriggers)
        self.cool.horizontalHeader().setStretchLastSection(True)
        self.cool.setMaximumHeight(150)
        self.cool_note = QLabel()
        btn = QPushButton("Làm mới")
        btn.clicked.connect(self.refresh)

        root = QVBoxLayout(self)
        root.addWidget(QLabel("<b>Chi phí theo luồng</b>"))
        root.addWidget(self.table, 1)
        root.addWidget(self.summary)
        root.addWidget(self.note)
        root.addWidget(box)
        root.addWidget(QLabel("<b>Model Gemini đang nghỉ</b>"))
        root.addWidget(self.cool)
        root.addWidget(self.cool_note)
        row = QHBoxLayout()
        row.addWidget(btn)
        row.addStretch(1)
        root.addLayout(row)

    # ---- dữ liệu --------------------------------------------------------
    def current_id(self) -> str:
        r = self.table.currentRow()
        it = self.table.item(r, 0) if r >= 0 else None
        return it.text() if it else ""

    def refresh(self) -> None:
        keep = self.current_id()
        try:
            flows = load_flows(self.flows_path)
        except Exception as e:                                 # noqa: BLE001
            self.note.setText(f"flows.yaml đang có lỗi: {e}")
            self.note.setStyleSheet("color: #c5221f;")
            return
        self.note.clear()
        has_db = self.db_path.is_file()
        store = Store(self.db_path) if has_db else None
        today = self.today()
        week: dict[str, float] = {}
        capped = 0
        if store:
            cut = (today - timedelta(days=6)).isoformat()        # 7 ngày lịch gồm cả hôm nay
            with store._conn() as c:                           # đọc tổng, đúng mốc 'today' của trang
                for r in c.execute("SELECT flow_id, SUM(usd) s FROM cost_ledger WHERE day >= ? GROUP BY flow_id", (cut,)):
                    week[r["flow_id"]] = float(r["s"])
                capped = c.execute("SELECT COUNT(*) n FROM runs WHERE day >= ? AND status LIKE ?",
                                   (cut, CAPPED_PREFIX + "%")).fetchone()["n"]
        self.table.setRowCount(len(flows))
        total_week = 0.0
        for i, f in enumerate(flows):
            spent = store.spent_today(f.id, today) if store else None
            pct = (spent / f.max_cost_usd_per_day * 100) if spent is not None else None
            w = week.get(f.id, 0.0) if store else None
            total_week += w or 0.0
            cells = [f.id, usd(spent), usd(f.max_cost_usd_per_day), NONE if pct is None else f"{pct:.0f}%",
                     usd(w)]
            for j, t in enumerate(cells):
                self.table.setItem(i, j, QTableWidgetItem(t))
        if keep:
            for i in range(self.table.rowCount()):
                if self.table.item(i, 0).text() == keep:
                    self.table.selectRow(i)
        if not store:
            self.summary.setText("Tổng 7 ngày: chưa có dữ liệu (chưa có cơ sở dữ liệu chạy). "
                                 "Lần chạy dừng vì trần: chưa có.")
        else:
            self.summary.setText(f"Tổng 7 ngày: {usd(total_week)} · lần chạy dừng vì hết ngân sách (7 ngày): {capped}")
        self._refresh_cooldowns()

    def _refresh_cooldowns(self) -> None:
        if not self.gemini_cache.is_file():
            self.cool.setRowCount(0)
            self.cool_note.setText("Chưa có dữ liệu model Gemini (chưa có config/gemini_models.json).")
            return
        rows = read_cooldowns(self.gemini_cache)
        self.cool.setRowCount(len(rows))
        now = time.time()
        for i, (k, left) in enumerate(rows):
            until = time.strftime("%Y-%m-%d %H:%M", time.localtime(now + left))
            for j, t in enumerate((k, until, f"{int(left // 60)} phút")):
                self.cool.setItem(i, j, QTableWidgetItem(t))
        self.cool_note.setText("" if rows else "Không có model nào đang nghỉ.")

    def _selected(self) -> None:
        fid = self.current_id()
        self.btn_cap.setEnabled(bool(fid))
        if not fid:
            return
        try:
            f = next(x for x in load_flows(self.flows_path) if x.id == fid)
        except Exception:                                      # noqa: BLE001
            return
        self.cap.setValue(f.max_cost_usd_per_day)

    def _say(self, text: str, bad: bool = False) -> None:
        self.msg.setText(text)
        self.msg.setStyleSheet("color: #c5221f;" if bad else "color: #137333;")

    def save_cap(self) -> None:
        fid = self.current_id()
        if not fid:
            return
        try:
            fs.set_fields(self.flows_path, fid, {"max_cost_usd_per_day": round(self.cap.value(), 2)})
        except (fs.InvalidFlows, OSError, KeyError) as e:
            self._say(f"Chưa lưu: {e}", bad=True)
            return
        self._say(f"Đã lưu trần ${self.cap.value():.2f}/ngày cho '{fid}'. Bản cũ ở flows.yaml.bak")
        self.refresh()
        self.changed.emit()
