"""Trang Cài đặt luồng — trọng tâm: SỐ TIN TRONG NGÀY, GIỜ CHẠY, trần chi phí.

Ràng buộc cần biết (core/models.py): nếu luồng có `duration_mix` thì
tổng duration_mix PHẢI bằng daily_quota. Nên khi đổi số tin trong ngày, trang này
tự chia lại bảng thời lượng; người dùng vẫn sửa tay được từng dòng.

Giờ chạy chọn bằng bộ chọn giờ:phút (hằng ngày). Lịch cron phức tạp (theo thứ, theo chu kỳ) KHÔNG bị
ghi đè: bộ chọn bị khoá và lịch giữ nguyên như trong flows.yaml.
"""
from __future__ import annotations

from pathlib import Path
from zoneinfo import ZoneInfo

from PySide6.QtCore import QTime, Qt, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox,
                               QHBoxLayout, QLabel, QListWidget, QMessageBox, QPushButton,
                               QSpinBox, QTableWidget, QTableWidgetItem, QTimeEdit, QVBoxLayout,
                               QWidget)

from ..core.models import load_flows
from . import flows_store as fs

QUOTA_MAX = 50
COMMON_TZ = ["Asia/Bangkok", "Asia/Ho_Chi_Minh", "UTC", "Europe/Berlin", "Europe/London", "America/New_York"]


class FlowsPage(QWidget):
    changed = Signal()                      # luồng vừa được lưu → trang khác làm mới

    def __init__(self, flows_path: str | Path, parent: QWidget | None = None):
        super().__init__(parent)
        self.flows_path = Path(flows_path)
        self._loading = False
        self._custom_schedule = False       # True: cron phức tạp, không được ghi đè
        self._build()
        self.reload()

    # ---- dựng giao diện -------------------------------------------------
    def _build(self) -> None:
        self.list = QListWidget()
        self.list.setMaximumWidth(260)
        self.list.currentTextChanged.connect(self._select)

        self.quota = QSpinBox()
        self.quota.setRange(1, QUOTA_MAX)
        self.quota.setSuffix("  kịch bản/ngày")
        self.quota.setStyleSheet("font-size: 16px; font-weight: bold; padding: 4px;")
        self.quota.valueChanged.connect(self._quota_changed)

        self.mix = QTableWidget(0, 2)
        self.mix.setHorizontalHeaderLabels(["Khoảng thời lượng (phút)", "Số kịch bản"])
        self.mix.horizontalHeader().setStretchLastSection(True)
        self.mix.setMaximumHeight(150)
        self.mix.itemChanged.connect(self._mix_edited)

        self.mix_sum = QLabel()
        self.btn_split = QPushButton("Chia lại tự động theo số tin/ngày")
        self.btn_split.clicked.connect(self._split_now)

        self.enabled = QCheckBox("Bật luồng này")

        self.times = QListWidget()
        self.times.setMaximumHeight(90)
        self.time_edit = QTimeEdit(QTime(5, 30))
        self.time_edit.setDisplayFormat("HH:mm")
        self.btn_add_time = QPushButton("Thêm")
        self.btn_add_time.clicked.connect(self._add_time)
        self.btn_del_time = QPushButton("Xóa")
        self.btn_del_time.clicked.connect(self._remove_time)
        self.times_note = QLabel()
        self.times_note.setWordWrap(True)

        self.tz = QComboBox()
        self.tz.setEditable(True)
        self.tz.addItems(COMMON_TZ)

        self.cost = QDoubleSpinBox()
        self.cost.setRange(0.5, 500)
        self.cost.setPrefix("$ ")
        self.cost.setSuffix(" / ngày")

        self.info = QLabel()
        self.info.setWordWrap(True)
        self.msg = QLabel()
        self.msg.setWordWrap(True)

        self.btn_save = QPushButton("Lưu")
        self.btn_save.clicked.connect(self.save)
        self.btn_reset = QPushButton("Bỏ thay đổi")
        self.btn_reset.clicked.connect(lambda: self._select(self.current_id()))

        box_quota = QGroupBox("Sản lượng mỗi ngày")
        lay_q = QVBoxLayout(box_quota)
        lay_q.addWidget(QLabel("Số tin (kịch bản) hệ thống xử lý trong một ngày:"))
        lay_q.addWidget(self.quota)
        lay_q.addWidget(QLabel("Chia theo thời lượng — tổng phải bằng số trên:"))
        lay_q.addWidget(self.mix)
        row = QHBoxLayout()
        row.addWidget(self.mix_sum)
        row.addStretch(1)
        row.addWidget(self.btn_split)
        lay_q.addLayout(row)

        box_other = QGroupBox("Lịch & ngân sách")
        form = QFormLayout(box_other)
        form.addRow(self.enabled)
        form.addRow("Giờ chạy (hằng ngày):", self.times)
        trow = QHBoxLayout()
        trow.addWidget(self.time_edit)
        trow.addWidget(self.btn_add_time)
        trow.addWidget(self.btn_del_time)
        trow.addStretch(1)
        form.addRow(trow)
        form.addRow(self.times_note)
        form.addRow("Múi giờ:", self.tz)
        form.addRow("Trần chi phí:", self.cost)

        buttons = QHBoxLayout()
        buttons.addWidget(self.btn_save)
        buttons.addWidget(self.btn_reset)
        buttons.addStretch(1)

        right = QVBoxLayout()
        right.addWidget(self.info)
        right.addWidget(box_quota)
        right.addWidget(box_other)
        right.addWidget(self.msg)
        right.addLayout(buttons)
        right.addStretch(1)

        root = QHBoxLayout(self)
        left = QVBoxLayout()
        left.addWidget(QLabel("Luồng:"))
        left.addWidget(self.list)
        root.addLayout(left)
        root.addLayout(right, 1)

    # ---- dữ liệu --------------------------------------------------------
    def current_id(self) -> str:
        it = self.list.currentItem()
        return it.text() if it else ""

    def reload(self) -> None:
        keep = self.current_id()
        self.list.clear()
        try:
            ids = fs.flow_ids(self.flows_path)
        except OSError as e:
            self._say(f"Không đọc được {self.flows_path}: {e}", bad=True)
            return
        self.list.addItems(ids)
        if ids:
            self.list.setCurrentRow(ids.index(keep) if keep in ids else 0)

    def _flow(self, flow_id: str):
        for f in load_flows(self.flows_path):
            if f.id == flow_id:
                return f
        return None

    def _select(self, flow_id: str) -> None:
        if not flow_id:
            return
        try:
            f = self._flow(flow_id)
        except Exception as e:
            self._say(f"flows.yaml đang có lỗi: {e}", bad=True)
            return
        if f is None:
            return
        self._loading = True
        self.info.setText(f"<b>{f.name}</b> — {f.platform} {f.aspect_ratio} · "
                          f"{f.duration_min:g}–{f.duration_max:g} phút · {f.output_language} "
                          f"{f.wpm:g} từ/phút")
        self.quota.setValue(min(f.daily_quota, QUOTA_MAX))
        self._fill_mix(f.duration_mix)
        self.enabled.setChecked(f.enabled)
        self._fill_times(f.schedule)
        self.tz.setCurrentText(f.timezone)
        self.cost.setValue(f.max_cost_usd_per_day)
        self._loading = False
        self._say("")
        self._refresh_sum()

    # ---- giờ chạy ---------------------------------------------------------
    def _fill_times(self, schedule: list[str]) -> None:
        self.times.clear()
        times = fs.cron_to_times(schedule)
        self._custom_schedule = times is None
        if self._custom_schedule:
            self.times.addItems(schedule)                       # hiện nguyên văn cron, chỉ để xem
            self.times_note.setText("Lịch tùy chỉnh (theo thứ hoặc chu kỳ) — chỉnh trong flows.yaml; "
                                    "giao diện sẽ không ghi đè lịch này.")
            self.times_note.setStyleSheet("color: #b06000;")
        else:
            self.times.addItems(times)
            self.times_note.setText("Mỗi giờ trong danh sách là một lần chạy mỗi ngày." if times else
                                    "Chưa có giờ chạy nào — luồng sẽ không tự chạy theo lịch.")
            self.times_note.setStyleSheet("color: gray;")
        for w in (self.time_edit, self.btn_add_time, self.btn_del_time):
            w.setEnabled(not self._custom_schedule)

    def _add_time(self) -> None:
        text = self.time_edit.time().toString("HH:mm")
        if text not in [self.times.item(i).text() for i in range(self.times.count())]:
            self.times.addItem(text)
            self.times.sortItems()

    def _remove_time(self) -> None:
        row = self.times.currentRow()
        if row >= 0:
            self.times.takeItem(row)

    def _read_times(self) -> list[str]:
        return [self.times.item(i).text() for i in range(self.times.count())]

    # ---- bảng thời lượng --------------------------------------------------
    def _fill_mix(self, mix: dict[str, int]) -> None:
        self.mix.blockSignals(True)
        self.mix.setRowCount(len(mix))
        for r, (k, v) in enumerate(mix.items()):
            key = QTableWidgetItem(k)
            key.setFlags(key.flags() & ~Qt.ItemIsEditable)       # khoá do thời lượng luồng quyết định
            self.mix.setItem(r, 0, key)
            self.mix.setItem(r, 1, QTableWidgetItem(str(v)))
        self.mix.blockSignals(False)
        self.mix.setVisible(bool(mix))
        self.btn_split.setVisible(bool(mix))
        self.mix_sum.setVisible(bool(mix))

    def _read_mix(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in range(self.mix.rowCount()):
            k, v = self.mix.item(r, 0), self.mix.item(r, 1)
            if k is None:
                continue
            try:
                out[k.text()] = max(0, int((v.text() if v else "0").strip() or 0))
            except ValueError:
                out[k.text()] = 0
        return out

    # ---- phản ứng -------------------------------------------------------
    def _quota_changed(self) -> None:
        if self._loading or self.mix.rowCount() == 0:
            self._refresh_sum()
            return
        self._fill_mix(fs.rescale_mix(self._read_mix(), self.quota.value()))
        self._refresh_sum()

    def _mix_edited(self) -> None:
        if not self._loading:
            self._refresh_sum()

    def _split_now(self) -> None:
        self._fill_mix(fs.rescale_mix(self._read_mix(), self.quota.value()))
        self._refresh_sum()

    def _refresh_sum(self) -> None:
        if self.mix.rowCount() == 0:
            self.mix_sum.setText("")
            self.btn_save.setEnabled(True)
            return
        s, q = sum(self._read_mix().values()), self.quota.value()
        ok = s == q
        self.mix_sum.setText(f"Tổng bảng: <b>{s}</b> / cần <b>{q}</b>" +
                             ("" if ok else " — chưa khớp, chưa lưu được"))
        self.mix_sum.setStyleSheet("color: #137333;" if ok else "color: #c5221f;")
        self.btn_save.setEnabled(ok)

    def _say(self, text: str, bad: bool = False) -> None:
        self.msg.setText(text)
        self.msg.setStyleSheet("color: #c5221f;" if bad else "color: #137333;")

    # ---- lưu ------------------------------------------------------------
    def save(self) -> None:
        flow_id = self.current_id()
        if not flow_id:
            return
        tz = self.tz.currentText().strip()
        try:
            ZoneInfo(tz)
        except Exception:
            self._say(f"Múi giờ không hợp lệ: {tz!r} (ví dụ Asia/Bangkok). Chưa lưu.", bad=True)
            return
        changes: dict[str, object] = {
            "daily_quota": self.quota.value(),
            "enabled": self.enabled.isChecked(),
            "max_cost_usd_per_day": self.cost.value(),
            "timezone": tz,
        }
        if not self._custom_schedule:                  # cron phức tạp: giữ nguyên, không ghi đè
            changes["schedule"] = fs.times_to_cron(self._read_times())
        if self.mix.rowCount():
            changes["duration_mix"] = self._read_mix()
        try:
            fs.set_fields(self.flows_path, flow_id, changes)
        except fs.InvalidFlows as e:
            QMessageBox.warning(self, "Chưa lưu được",
                                f"Cấu hình không hợp lệ nên file giữ nguyên:\n\n{e}")
            self._say("Chưa lưu — xem thông báo vừa rồi.", bad=True)
            return
        except (OSError, KeyError) as e:
            QMessageBox.critical(self, "Lỗi ghi file", str(e))
            return
        self._say(f"Đã lưu. Luồng '{flow_id}' sẽ xử lý {self.quota.value()} tin mỗi ngày. "
                  f"Bản cũ giữ ở flows.yaml.bak")
        self.changed.emit()
