"""Trang Gemini: khóa & trạng thái, thang model, chính sách (bậc ưu tiên, tự cập nhật, hạ bậc, chu kỳ tải lại).

Mọi lệnh gọi mạng (probe, tải danh sách, đọc thang) chạy trong QThreadPool; kết quả về qua tín hiệu nên UI
không treo. Khóa chỉ hiện dạng che (env_store.mask) và không bao giờ vào nhãn/log. Chính sách lưu bằng
S.load rồi chỉ đổi 4 trường của trang này, để không đè lên cài đặt của trang Cài đặt chung.
"""
from __future__ import annotations

import dataclasses
import os
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QFormLayout, QGroupBox, QHBoxLayout,
                               QHeaderView, QLabel, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from ..core import settings as S
from ..gemini.client import GeminiClient
from . import env_store

KEY_NAME = "GEMINI_API_KEY"
POLICY_FIELDS = ("gemini_tier", "gemini_auto_update", "gemini_fallback", "gemini_refresh_hours")

ClientFactory = Callable[[S.Settings], GeminiClient]


def read_key(env_path: str | Path | None) -> str:
    """Biến môi trường trước, rồi tới dòng GEMINI_API_KEY trong .env. Chỉ để che/đưa cho client."""
    v = os.environ.get(KEY_NAME, "").strip()
    if v:
        return v
    p = Path(env_path or env_store.DEFAULT_PATH)
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            k, _, val = line.strip().partition("=")
            if k.strip() == KEY_NAME and val.strip().strip("\"'"):
                return val.strip().strip("\"'")
    except OSError:
        pass
    return ""


class _Signals(QObject):
    done = Signal(str, object)           # (loại việc, kết quả)
    failed = Signal(str, str)            # (loại việc, thông báo đã che khóa)


class _Task(QRunnable):
    def __init__(self, kind: str, fn: Callable[[], object], redact: str = ""):
        super().__init__()
        self.kind, self.fn, self.redact = kind, fn, redact
        self.signals = _Signals()

    def run(self) -> None:
        try:
            out = self.fn()
        except Exception as e:                      # noqa: BLE001 — không để luồng nền chết âm thầm
            msg = f"{type(e).__name__}: {e}"
            if self.redact:
                msg = msg.replace(self.redact, "***")
            self.signals.failed.emit(self.kind, msg)
            return
        self.signals.done.emit(self.kind, out)


class GeminiPage(QWidget):
    changed = Signal(object)                 # Settings vừa lưu
    probe_finished = Signal(dict)            # báo cáo probe (để test/nơi khác theo dõi)
    table_updated = Signal(int)              # số dòng của bảng thang model

    def __init__(self, settings_path: str | Path | None = None, env_path: str | Path | None = None,
                 client_factory: ClientFactory | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.settings_path = Path(settings_path) if settings_path else S.DEFAULT_PATH
        self.env_path = Path(env_path) if env_path else env_store.DEFAULT_PATH
        self._factory = client_factory or self._default_factory
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)       # tuần tự: client dùng chung file cache
        self._tasks: set[_Task] = set()
        self._first_show = True
        self._build()
        self.reload()

    # ---- client ---------------------------------------------------------
    def _default_factory(self, s: S.Settings) -> GeminiClient:
        return GeminiClient(read_key(self.env_path), settings=s)

    # ---- giao diện ------------------------------------------------------
    def _build(self) -> None:
        self.key_label = QLabel()
        self.btn_probe = QPushButton("Kiểm tra khóa")
        self.btn_probe.clicked.connect(self.check_key)
        self.probe_out = QLabel("Bấm “Kiểm tra khóa” để thử khóa Gemini.")
        self.probe_out.setWordWrap(True)
        box_key = QGroupBox("Khóa và trạng thái")
        f1 = QFormLayout(box_key)
        f1.addRow("Khóa Gemini API:", self.key_label)
        f1.addRow(self.btn_probe)
        f1.addRow(self.probe_out)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Thứ tự", "Model", "Bậc", "Phiên bản", "Preview", "Trạng thái"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.btn_models = QPushButton("Tải lại danh sách model")
        self.btn_models.clicked.connect(self.reload_models)
        self.models_msg = QLabel()
        self.models_msg.setWordWrap(True)
        box_lad = QGroupBox("Thang model")
        l2 = QVBoxLayout(box_lad)
        l2.addWidget(self.table)
        r2 = QHBoxLayout()
        r2.addWidget(self.btn_models)
        r2.addStretch(1)
        l2.addLayout(r2)
        l2.addWidget(self.models_msg)

        self.tier = QComboBox()
        for label, data in (("Pro (mạnh nhất)", "pro"), ("Flash (cân bằng)", "flash"),
                            ("Flash-Lite (rẻ, nhanh)", "flash-lite")):
            self.tier.addItem(label, data)
        self.auto_update = QCheckBox("Tự cập nhật danh sách model từ Google")
        self.fallback = QCheckBox("Hạ xuống model thấp hơn khi hết định mức")
        self.refresh_hours = QSpinBox()
        self.refresh_hours.setRange(*S.REFRESH_HOURS_RANGE)
        self.refresh_hours.setSuffix("  giờ")
        self.btn_save = QPushButton("Lưu chính sách")
        self.btn_save.clicked.connect(self.save)
        self.msg = QLabel()
        self.msg.setWordWrap(True)
        box_pol = QGroupBox("Chính sách")
        f3 = QFormLayout(box_pol)
        f3.addRow("Bậc ưu tiên:", self.tier)
        f3.addRow(self.auto_update)
        f3.addRow(self.fallback)
        f3.addRow("Tải lại danh sách mỗi:", self.refresh_hours)
        f3.addRow(self.btn_save)
        f3.addRow(self.msg)

        root = QVBoxLayout(self)
        root.addWidget(box_key)
        root.addWidget(box_lad, 1)
        root.addWidget(box_pol)

    def showEvent(self, e) -> None:                 # noqa: N802
        super().showEvent(e)
        if self._first_show:
            self._first_show = False
            if read_key(self.env_path):
                self.refresh_table()

    # ---- dữ liệu --------------------------------------------------------
    def reload(self) -> None:
        s = S.load(self.settings_path)
        self.tier.setCurrentIndex(max(0, self.tier.findData(s.gemini_tier)))
        self.auto_update.setChecked(s.gemini_auto_update)
        self.fallback.setChecked(s.gemini_fallback)
        self.refresh_hours.setValue(s.gemini_refresh_hours)
        key = read_key(self.env_path)
        if key:
            self.key_label.setText(env_store.mask(key))
            self.key_label.setStyleSheet("")
        else:
            self.key_label.setText("Chưa có khóa — nhập ở trang Cài đặt chung.")
            self.key_label.setStyleSheet("color: #c5221f;")
        self.btn_probe.setEnabled(bool(key))
        self.btn_models.setEnabled(bool(key))

    def current_policy(self) -> dict:
        return {"gemini_tier": self.tier.currentData(), "gemini_auto_update": self.auto_update.isChecked(),
                "gemini_fallback": self.fallback.isChecked(), "gemini_refresh_hours": self.refresh_hours.value()}

    def save(self) -> None:
        try:
            cur = S.load(self.settings_path)                # đọc lại: giữ nguyên các trường của trang khác
            saved = S.save(dataclasses.replace(cur, **self.current_policy()), self.settings_path)
        except OSError as e:
            self._say(f"Không ghi được cài đặt: {e}", bad=True)
            return
        self._say("Đã lưu chính sách Gemini.")
        self.changed.emit(saved)

    def _say(self, text: str, bad: bool = False) -> None:
        self.msg.setText(text)
        self.msg.setStyleSheet("color: #c5221f;" if bad else "color: #137333;")

    # ---- việc nền -------------------------------------------------------
    def _busy(self, on: bool) -> None:
        have = bool(read_key(self.env_path))
        self.btn_probe.setEnabled(have and not on)
        self.btn_models.setEnabled(have and not on)

    def _submit(self, kind: str, fn: Callable[[GeminiClient], object]) -> None:
        s = S.load(self.settings_path)
        key = read_key(self.env_path)
        task = _Task(kind, lambda: fn(self._factory(s)), redact=key)
        task.setAutoDelete(False)
        self._tasks.add(task)
        task.signals.done.connect(self._on_done)
        task.signals.failed.connect(self._on_failed)
        self._busy(True)
        self.pool.start(task)

    def check_key(self) -> None:
        self.probe_out.setText("Đang kiểm tra khóa…")
        self.probe_out.setStyleSheet("color: gray;")
        self._submit("probe", lambda c: c.probe())

    def reload_models(self) -> None:
        self.models_msg.setText("Đang tải lại danh sách model…")
        self.models_msg.setStyleSheet("color: gray;")

        def job(c: GeminiClient):
            c.refresh_models(force=True)
            c._ladder = None                               # dựng lại thang từ danh sách mới
            return c.status()
        self._submit("models", job)

    def refresh_table(self) -> None:
        self._submit("status", lambda c: c.status())

    def _finish(self) -> None:
        self._tasks = {t for t in self._tasks if t.signals is not self.sender()}
        self._busy(False)

    def _on_done(self, kind: str, out) -> None:
        if kind == "probe":
            self._show_probe(out)
            self.probe_finished.emit(out)
        else:
            self._fill_table(out)
            if kind == "models":
                self.models_msg.setText(f"Đã tải lại: {len(out)} model trong thang.")
                self.models_msg.setStyleSheet("color: #137333;")
        self._finish()

    def _on_failed(self, kind: str, msg: str) -> None:
        if kind == "probe":
            self.probe_out.setText(f"Không kiểm tra được: {msg}")
            self.probe_out.setStyleSheet("color: #c5221f;")
        else:
            self.models_msg.setText(f"Không tải được danh sách model: {msg}")
            self.models_msg.setStyleSheet("color: #c5221f;")
        self._finish()

    # ---- hiển thị -------------------------------------------------------
    def _show_probe(self, rep: dict) -> None:
        key = {"ok": "hợp lệ", "bad": "bị từ chối (sai/bị khóa)", "error": "lỗi khi liệt kê model"}.get(
            rep.get("key"), "chưa rõ")
        plain = {"ok": "được", "fail": "lỗi"}.get(rep.get("plain"), "chưa thử")
        search = {"ok": "được (có nguồn)", "no_sources": "gọi được nhưng không trả nguồn",
                  "blocked": "BỊ CHẶN (429)", "fail": "lỗi"}.get(rep.get("search"), "chưa thử")
        lines = [f"Khóa: {key}", f"Số model: {rep.get('models', 0)}",
                 f"Gọi thường: {plain}" + (f" (model {rep['model']})" if rep.get("model") else ""),
                 f"Bám nguồn Google Search: {search}"]
        if rep.get("search") == "blocked":
            lines.append("Giải thích: bám nguồn bị 429 thường do khóa thuộc gói miễn phí — cần bật thanh toán "
                         "(billing) cho dự án Google AI Studio. Gọi thường vẫn dùng được; khảo sát có nguồn thì chưa.")
        elif rep.get("note"):
            lines.append(f"Ghi chú: {rep['note']}")
        good = rep.get("key") == "ok" and rep.get("plain") == "ok" and rep.get("search") == "ok"
        self.probe_out.setText("\n".join(lines))
        self.probe_out.setStyleSheet("color: #137333;" if good else "color: #c5221f;")

    def _fill_table(self, rows: list[dict]) -> None:
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            cd = int(r.get("cooldown_s", 0))
            vals = [str(i + 1), r["name"], r["tier"], r["version"], "có" if r["preview"] else "không",
                    f"nghỉ còn {cd} giây" if cd > 0 else "sẵn sàng"]
            for c, v in enumerate(vals):
                self.table.setItem(i, c, QTableWidgetItem(v))
        self.table_updated.emit(len(rows))
