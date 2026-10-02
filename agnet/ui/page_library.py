"""Trang Kho kịch bản — xem kịch bản/bài viết ngay trong phần mềm, cùng nguồn với thư mục output/.

Pipeline ghi vào output/<ngày>/<luồng>/<nn_slug>/; trang này đọc lại đúng thư mục đó và tự làm mới khi có
kịch bản mới (hoặc khi duyệt), nên "vừa ở thư mục vừa trong phần mềm" luôn khớp nhau.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QHBoxLayout, QInputDialog, QLabel, QPushButton, QSplitter, QTabWidget,
                               QTextBrowser, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from . import library as L

STATUS_LABEL = {"pending": "chưa duyệt", "approved": "ĐÃ DUYỆT", "rewrite": "CẦN VIẾT LẠI", "rejected": "ĐÃ LOẠI"}
STATUS_COLOR = {"pending": None, "approved": "#137333", "rewrite": "#b06000", "rejected": "#c5221f"}
# (nhãn tab, loại tệp, dạng hiển thị)
TABS = [("Kịch bản", "script", "md"), ("Lời thoại", "voiceover", "text"), ("Đóng gói", "packaging", "md"),
        ("Nguồn", "sources", "md"), ("Nhân vật KOC", "koc", "text"), ("JSON", "json", "text")]
ROLE = Qt.UserRole


class LibraryPage(QWidget):
    def __init__(self, output_root: str | Path | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.root = Path(output_root) if output_root else L.DEFAULT_ROOT
        self._sig: tuple = ()
        self._entries: dict[str, L.Entry] = {}
        self._build()
        self.reload()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(4000)

    # ---- dựng giao diện -------------------------------------------------
    def _build(self) -> None:
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.currentItemChanged.connect(lambda cur, _prev: self._show(cur))

        self.count = QLabel()
        self.head = QLabel()
        self.head.setWordWrap(True)
        self.head.setTextFormat(Qt.RichText)
        self.flags = QLabel()
        self.flags.setWordWrap(True)

        self.tabs = QTabWidget()
        self.views: dict[str, QTextBrowser] = {}
        for label, kind, _fmt in TABS:
            v = QTextBrowser()
            v.setOpenExternalLinks(True)
            self.views[kind] = v
            self.tabs.addTab(v, label)
        self.report = QTextBrowser()
        self.tabs.addTab(self.report, "Báo cáo ngày")

        self.btn_ok = QPushButton("Duyệt")
        self.btn_ok.clicked.connect(lambda: self.set_status("approved"))
        self.btn_rw = QPushButton("Cần viết lại…")
        self.btn_rw.clicked.connect(self._ask_rewrite)
        self.btn_no = QPushButton("Loại")
        self.btn_no.clicked.connect(lambda: self.set_status("rejected"))
        self.btn_open = QPushButton("Mở thư mục")
        self.btn_open.clicked.connect(self._open_folder)
        self.btn_refresh = QPushButton("Làm mới")
        self.btn_refresh.clicked.connect(self.reload)
        self.msg = QLabel()
        self.msg.setWordWrap(True)

        bar = QHBoxLayout()
        for b in (self.btn_ok, self.btn_rw, self.btn_no, self.btn_open, self.btn_refresh):
            bar.addWidget(b)
        bar.addStretch(1)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.addWidget(self.head)
        rl.addWidget(self.flags)
        rl.addLayout(bar)
        rl.addWidget(self.msg)
        rl.addWidget(self.tabs, 1)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.addWidget(self.count)
        ll.addWidget(self.tree, 1)

        split = QSplitter()
        split.addWidget(left)
        split.addWidget(right)
        split.setStretchFactor(1, 1)
        split.setSizes([330, 700])
        QHBoxLayout(self).addWidget(split)
        self._enable(False)

    def _enable(self, on: bool) -> None:
        for b in (self.btn_ok, self.btn_rw, self.btn_no, self.btn_open):
            b.setEnabled(on)

    # ---- dữ liệu --------------------------------------------------------
    def current_entry(self) -> L.Entry | None:
        it = self.tree.currentItem()
        key = it.data(0, ROLE) if it else None
        return self._entries.get(key) if key else None

    def _poll(self) -> None:
        sig = L.signature(self.root)
        if sig != self._sig:
            self.reload()

    def reload(self) -> None:
        keep = self.current_entry()
        keep_key = str(keep.folder) if keep else None
        self._sig = L.signature(self.root)
        entries = L.scan(self.root)
        self._entries = {str(e.folder): e for e in entries}

        self.tree.blockSignals(True)
        self.tree.clear()
        days: dict[str, QTreeWidgetItem] = {}
        flows: dict[tuple, QTreeWidgetItem] = {}
        target = None
        for e in entries:
            d = days.get(e.day)
            if d is None:
                d = days[e.day] = QTreeWidgetItem(self.tree, [e.day])
            f = flows.get((e.day, e.flow_id))
            if f is None:
                f = flows[(e.day, e.flow_id)] = QTreeWidgetItem(d, [e.flow_id])
                f.setData(0, ROLE, None)
            score = f"{e.qa_score:g}" if e.qa_score is not None else "–"
            it = QTreeWidgetItem(f, [f"{e.slug}  ·  QA {score}  ·  {STATUS_LABEL[e.status]}"])
            it.setData(0, ROLE, str(e.folder))
            it.setToolTip(0, e.title)
            if STATUS_COLOR[e.status]:
                from PySide6.QtGui import QColor
                it.setForeground(0, QColor(STATUS_COLOR[e.status]))
            if str(e.folder) == keep_key:
                target = it
        self.tree.expandAll()
        self.tree.blockSignals(False)

        self.count.setText(f"<b>{len(entries)}</b> kịch bản trong {self.root}")
        if target is None and entries:
            target = self.tree.topLevelItem(0).child(0).child(0)      # kịch bản đầu tiên
        if target is not None:
            self.tree.setCurrentItem(target)
        self._show(self.tree.currentItem())

    # ---- hiển thị ---------------------------------------------------------
    def _show(self, item: QTreeWidgetItem | None) -> None:
        e = self.current_entry()
        if e is None:
            self._enable(False)
            self.head.setText("")
            self.flags.setText("")
            for v in self.views.values():
                v.clear()
            self.report.clear()
            # chọn nút luồng: hiện báo cáo ngày nếu có
            if item is not None and item.parent() is not None and item.parent().parent() is None:
                day, flow = item.parent().text(0), item.text(0)
                self.report.setMarkdown(L.day_report(self.root, day, flow) or "_Chưa có báo cáo ngày._")
                self.tabs.setCurrentWidget(self.report)
            return
        self._enable(True)
        mins = f"{e.duration_sec / 60:.1f} phút" if e.duration_sec else "–"
        color = STATUS_COLOR[e.status] or "gray"
        self.head.setText(
            f"<h3>{e.title}</h3>{e.day} · {e.flow_id} · QA "
            f"{('%g' % e.qa_score) if e.qa_score is not None else '–'} · {mins} · {e.language or '–'} · "
            f"<span style='color:{color}'><b>{STATUS_LABEL[e.status]}</b></span>"
            + (f"<br><i>Góp ý: {e.note}</i>" if e.note else ""))
        extra = ("Cần người duyệt trước khi đăng. " if e.human_review_required else "")
        self.flags.setText((extra + " · ".join(e.flags)) if (extra or e.flags) else "")
        self.flags.setStyleSheet("color: #b06000;")
        for _label, kind, fmt in TABS:
            text = L.read_text(e, kind)
            v = self.views[kind]
            if text is None:
                v.setPlainText("(không có tệp này)")
            elif fmt == "md":
                v.setMarkdown(text)
            else:
                v.setPlainText(text)
        self.report.setMarkdown(L.day_report(self.root, e.day, e.flow_id) or "_Chưa có báo cáo ngày._")
        self.msg.setText("")

    # ---- thao tác -------------------------------------------------------
    def set_status(self, status: str, note: str = "") -> None:
        e = self.current_entry()
        if e is None:
            return
        try:
            L.set_review(e.folder, status, note)
        except (ValueError, OSError) as err:
            self.msg.setText(f"Chưa lưu: {err}")
            self.msg.setStyleSheet("color: #c5221f;")
            return
        self.reload()
        self.msg.setText(f"Đã đánh dấu: {STATUS_LABEL[status]}.")
        self.msg.setStyleSheet("color: #137333;")

    def _ask_rewrite(self) -> None:
        note, ok = QInputDialog.getMultiLineText(self, "Cần viết lại", "Góp ý cụ thể cho lần viết lại:")
        if ok:
            self.set_status("rewrite", note)

    def _open_folder(self) -> None:
        e = self.current_entry()
        if e is not None:
            L.open_folder(e.folder)
