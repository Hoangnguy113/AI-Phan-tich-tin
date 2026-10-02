"""Trang "Đội agent": bảng 17 agent đọc từ .claude/agents/*.md, cho sửa có kiểm soát engine và model.

Ràng buộc cứng (CLAUDE.md, KE_HOACH 18.10): giao diện KHÔNG đổi `tools` và không bao giờ cho agent có Write/Edit.
Ghi bằng cách thay đúng dòng `model:`/`engine:` trong frontmatter, phần còn lại của tệp giữ nguyên từng byte,
ghi nguyên tử (tệp tạm + os.replace). Sau khi lưu chạy lại load_agents; lỗi thì tự hoàn tác.
"""
from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QHBoxLayout, QHeaderView, QLabel, QPushButton,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from ..pipeline.agents import AGENT_DIR, load_agents

MODELS = ("haiku", "sonnet", "opus")
ENGINES = ("claude", "gemini")
# Chỉ 7 agent khảo sát (mang nguồn về) được chạy bằng Gemini; còn lại khoá ở claude (quy tắc cứng số 1, 4).
GEMINI_ELIGIBLE = frozenset({"trend-scout", "video-platform-scout", "news-scout", "community-scout",
                             "domain-internal-scout", "keyword-miner", "competitor-gap-analyst"})
FORBIDDEN_TOOLS = frozenset({"write", "edit", "multiedit", "notebookedit"})
QA_AGENT = "editor-in-chief"

_FM = re.compile(r"^(---\n)(.*?)(\n---\n)(.*)$", re.S)


@dataclass
class Row:
    path: Path
    name: str
    tier: str
    engine: str
    model: str
    tools: list[str]


def _meta(text: str) -> dict[str, str]:
    m = _FM.match(text)
    out: dict[str, str] = {}
    if m:
        for line in m.group(2).split("\n"):
            k, sep, v = line.partition(":")
            if sep and not line.startswith((" ", "-")):
                out[k.strip()] = v.strip().strip("\"'")
    return out


def read_rows(directory: Path | str) -> list[Row]:
    rows = []
    for f in sorted(Path(directory).glob("*.md")):
        meta = _meta(f.read_text(encoding="utf-8"))
        t = re.search(r"Tầng\s*(\d+)", meta.get("description", ""))
        tools = [x.strip() for x in meta.get("tools", "").split(",") if x.strip()]
        rows.append(Row(f, meta.get("name", f.stem), f"Tầng {t.group(1)}" if t else "—",
                        meta.get("engine", "claude"), meta.get("model", "sonnet"), tools))
    return rows


def set_field(text: str, key: str, value: str) -> str:
    """Thay ĐÚNG dòng `key:` trong frontmatter (chưa có `engine` thì chèn ngay sau `model`). Giữ nguyên phần còn lại."""
    if any(c in str(value) for c in "\r\n") or "\n" in key:
        raise ValueError("giá trị không được chứa xuống dòng")
    m = _FM.match(text)
    if not m:
        raise ValueError("thiếu frontmatter")
    lines = m.group(2).split("\n")
    for i, ln in enumerate(lines):
        if re.match(rf"^{re.escape(key)}\s*:", ln):
            lines[i] = f"{key}: {value}"
            break
    else:
        at = next((i + 1 for i, ln in enumerate(lines) if ln.startswith("model:")), len(lines))
        lines.insert(at, f"{key}: {value}")
    return m.group(1) + "\n".join(lines) + m.group(3) + m.group(4)


def atomic_write(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".agent-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def warnings_for(rows: list[Row]) -> list[str]:
    """Cảnh báo cấu hình: thiếu bước QA ở cuối pipeline, hoặc agent nào có quyền ghi."""
    out = []
    qa = next((r for r in rows if r.name == QA_AGENT), None)
    if qa is None:
        out.append(f"Thiếu bước QA: không có agent “{QA_AGENT}” trong đội.")
    elif qa.engine != "claude":
        out.append(f"Bước QA “{QA_AGENT}” phải chạy bằng claude.")
    for r in rows:
        bad = [t for t in r.tools if t.lower() in FORBIDDEN_TOOLS]
        if bad:
            out.append(f"{r.name}: có công cụ ghi ({', '.join(bad)}) — agent không được có quyền Write/Edit.")
    return out


class AgentsPage(QWidget):
    saved = Signal(int)                      # số tệp vừa ghi

    def __init__(self, directory: Path | str | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.dir = Path(directory) if directory else AGENT_DIR
        self._undo: dict[Path, str] = {}     # nội dung trước lần lưu gần nhất
        self._rows: list[Row] = []
        self._build()
        self.reload()

    def _build(self) -> None:
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Số", "Tên", "Tầng", "Engine", "Model", "Công cụ"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.warn = QLabel()
        self.warn.setWordWrap(True)
        self.msg = QLabel()
        self.msg.setWordWrap(True)
        self.btn_save = QPushButton("Lưu thay đổi")
        self.btn_save.clicked.connect(self.save)
        self.btn_undo = QPushButton("Hoàn tác")
        self.btn_undo.clicked.connect(self.undo)
        self.btn_undo.setEnabled(False)
        self.btn_reload = QPushButton("Làm mới")
        self.btn_reload.clicked.connect(self.reload)
        note = QLabel("Chỉ đổi được engine và model. Công cụ (tools) chỉ đọc; agent không có quyền Write/Edit. "
                      "Chỉ 7 agent khảo sát mới được chọn gemini.")
        note.setWordWrap(True)
        note.setStyleSheet("color: gray;")
        bar = QHBoxLayout()
        for b in (self.btn_save, self.btn_undo, self.btn_reload):
            bar.addWidget(b)
        bar.addStretch(1)
        root = QVBoxLayout(self)
        root.addWidget(note)
        root.addWidget(self.warn)
        root.addWidget(self.table, 1)
        root.addLayout(bar)
        root.addWidget(self.msg)

    # ---- dữ liệu --------------------------------------------------------
    def reload(self) -> None:
        self._rows = read_rows(self.dir)
        self.table.setRowCount(len(self._rows))
        for i, r in enumerate(self._rows):
            num = re.match(r"(\d+)", r.path.name)
            for c, v in ((0, num.group(1) if num else str(i + 1)), (1, r.name), (2, r.tier),
                         (5, ", ".join(r.tools))):
                self.table.setItem(i, c, QTableWidgetItem(v))
            eng = QComboBox()
            for e in ENGINES:
                eng.addItem(e, e)
            if r.name not in GEMINI_ELIGIBLE:
                eng.model().item(1).setEnabled(False)          # khoá ở claude
            eng.setCurrentIndex(max(0, eng.findData(r.engine)))
            mod = QComboBox()
            for m in MODELS:
                mod.addItem(m, m)
            mod.setCurrentIndex(max(0, mod.findData(r.model)))
            self.table.setCellWidget(i, 3, eng)
            self.table.setCellWidget(i, 4, mod)
        w = warnings_for(self._rows)
        self.warn.setText("\n".join("⚠ " + x for x in w))
        self.warn.setStyleSheet("color: #c5221f;")
        self.warn.setVisible(bool(w))

    def _say(self, text: str, bad: bool = False) -> None:
        self.msg.setText(text)
        self.msg.setStyleSheet("color: #c5221f;" if bad else "color: #137333;")

    def _chosen(self, i: int) -> tuple[str, str]:
        return self.table.cellWidget(i, 3).currentData(), self.table.cellWidget(i, 4).currentData()

    def save(self) -> None:
        changes: list[tuple[Row, str, str]] = []
        for i, r in enumerate(self._rows):
            eng, mod = self._chosen(i)
            if eng not in ENGINES or mod not in MODELS:
                continue
            if eng == "gemini" and r.name not in GEMINI_ELIGIBLE:
                self._say(f"{r.name}: chỉ agent khảo sát mới được chạy bằng gemini.", bad=True)
                return
            if (eng, mod) != (r.engine, r.model):
                changes.append((r, eng, mod))
        if not changes:
            self._say("Không có thay đổi để lưu.")
            return
        before: dict[Path, str] = {}
        try:
            for r, eng, mod in changes:
                old = r.path.read_text(encoding="utf-8")
                new = set_field(set_field(old, "model", mod), "engine", eng)
                before[r.path] = old
                atomic_write(r.path, new)
            load_agents(self.dir)                              # kiểm tra còn nạp được
        except Exception as e:                                 # noqa: BLE001 — lỗi gì cũng phải hoàn tác
            for p, txt in before.items():
                atomic_write(p, txt)
            self.reload()
            self._say(f"Không lưu được, đã tự hoàn tác: {type(e).__name__}: {e}", bad=True)
            return
        self._undo = before
        self.btn_undo.setEnabled(True)
        self.reload()
        self._say(f"Đã lưu {len(changes)} agent. Bấm “Hoàn tác” để quay về bản trước.")
        self.saved.emit(len(changes))

    def undo(self) -> None:
        if not self._undo:
            return
        try:
            for p, txt in self._undo.items():
                atomic_write(p, txt)
            load_agents(self.dir)
        except Exception as e:                                 # noqa: BLE001
            self._say(f"Không hoàn tác được: {type(e).__name__}: {e}", bad=True)
            return
        n = len(self._undo)
        self._undo = {}
        self.btn_undo.setEnabled(False)
        self.reload()
        self._say(f"Đã hoàn tác {n} agent về bản trước.")
        self.saved.emit(n)
