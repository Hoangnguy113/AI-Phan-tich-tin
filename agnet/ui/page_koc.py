"""Trang Nhân vật KOC: xem danh sách/chi tiết, sửa CÁC TRƯỜNG AN TOÀN, xem prompt (chỉ đọc).

Quy tắc cứng (CLAUDE.md số 5, KE_HOACH mục 17.8/17.11):
- KHÓA: Lớp B (realism_engine.json), `negative`, `consistency_lock` — trang không có đường nào ghi vào đó;
  `save_character` ném KocLocked nếu đường dẫn không nằm trong EDITABLE.
- Tuổi < 22 bị từ chối; từ cấm / gợi dục / số đo (dùng lại master_prompt._scan_banned) bị từ chối;
  mạo danh bác sĩ/luật sư bị từ chối.
- `ai_disclosure` luôn bật cho mọi nhân vật KOC (chỉ hiển thị, không tắt được).
- status `ready` chỉ khi MỌI ảnh gốc trong identity.reference_images tồn tại trên đĩa. Hiện chưa có ảnh nên
  chưa bật được.
Ghi nguyên tử (tệp tạm + replace).
"""
from __future__ import annotations

import copy
import json
import os
import re
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QPlainTextEdit, QPushButton, QSpinBox, QVBoxLayout, QWidget)

from ..koc import master_prompt as mp

TITLE_VI = "Nhân vật KOC"
TITLE_EN = "KOC characters"
EN: dict[str, str] = {
    "Nhân vật KOC": "KOC characters",
    "Nhân vật:": "Characters:",
    "Thông tin sửa được": "Editable fields",
    "Đã khóa (không sửa được)": "Locked (read-only)",
    "Tuổi (tối thiểu 22):": "Age (minimum 22):",
    "Trạng thái:": "Status:",
    "Nền tảng chính:": "Main platform:",
    "Tên:": "Name:",
    "Khu vực:": "Region:",
    "Lĩnh vực:": "Niche:",
    "Giọng:": "Voice:",
    "Tính cách:": "Persona:",
    "Bối cảnh:": "Setting:",
    "Ánh sáng chính:": "Key light:",
    "Ánh sáng bổ sung:": "Fill light:",
    "Trang phục:": "Wardrobe:",
    "Xem prompt": "View prompt",
    "Bỏ thay đổi": "Discard changes",
    "Lưu": "Save",
    "Luôn bật chú thích nội dung do AI tạo (ai_disclosure): bật.":
        "AI-generated disclosure (ai_disclosure) is always on.",
    "Chưa có ảnh gốc nên chưa bật được trạng thái ready.": "No reference images yet, so ready cannot be set.",
}

EDITABLE = {  # đường dẫn -> nhãn
    "meta.name": "Tên:", "meta.region": "Khu vực:", "meta.niche": "Lĩnh vực:", "meta.voice": "Giọng:",
    "identity.persona": "Tính cách:", "defaults.setting": "Bối cảnh:", "defaults.key_light": "Ánh sáng chính:",
    "defaults.fill": "Ánh sáng bổ sung:", "defaults.wardrobe_palette": "Trang phục:",
}
LOCKED_KEYS = ("realism_engine", "negative", "consistency_lock", "negative_video")
AGE_PATH = "age"
_AGE_RE = re.compile(r"\b(\d{1,3})(\s*years?\s*old)")
_IMPERSONATE = re.compile(
    r"(?<!không )(?<!không phải )(?<!chẳng phải )(?<!not a )(?<!not )(?<!no )\b(bác sĩ|bac si|luật sư|luat su|dược sĩ|doctor|physician|lawyer|attorney|surgeon)\b",
    re.I)
STATUSES = ("draft", "ready")


class KocError(ValueError):
    """Thay đổi bị từ chối — không có gì được ghi."""


class KocLocked(KocError):
    """Cố sửa phần bị khóa (Lớp B / negative / consistency_lock) hoặc trường ngoài danh sách cho phép."""


# ---- đọc -------------------------------------------------------------------
def _read_status(yaml_path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        for line in yaml_path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s*-\s*\{id:\s*([\w-]+),.*?status:\s*(\w+)", line)
            if m:
                out[m.group(1)] = m.group(2)
    except OSError:
        pass
    return out


def get_age(char: dict) -> int | None:
    m = _AGE_RE.search(char.get("identity", {}).get("demographics", ""))
    return int(m.group(1)) if m else None


def list_characters(char_dir: Path, yaml_path: Path) -> list[dict]:
    st = _read_status(yaml_path)
    out = []
    for p in sorted(Path(char_dir).glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            cid = d["identity"]["character_id"]
        except (OSError, ValueError, KeyError):
            continue
        out.append({"id": cid, "file": p.name, "name": d.get("meta", {}).get("name", cid), "age": get_age(d),
                    "status": st.get(cid, "draft"), "summary": d["identity"].get("persona", ""), "data": d})
    return out


def missing_reference_images(char: dict, refs_root: Path) -> list[str]:
    return [r for r in char.get("identity", {}).get("reference_images", []) if not (Path(refs_root) / r).is_file()]


# ---- kiểm tra --------------------------------------------------------------
def check_text(label: str, value: str) -> None:
    try:
        mp._scan_banned(label, value)
    except mp.PromptError as e:
        raise KocError(str(e)) from e
    if _IMPERSONATE.search(value):
        raise KocError(f"{label}: không được mạo danh bác sĩ/luật sư (mục 17.11)")


def _get(d: dict, path: str):
    for k in path.split("."):
        d = d.get(k, {}) if isinstance(d, dict) else {}
    return d


def _set(d: dict, path: str, v) -> None:
    *ks, last = path.split(".")
    for k in ks:
        d = d.setdefault(k, {})
    d[last] = v


def apply_changes(char: dict, changes: dict) -> dict:
    """Trả bản mới đã kiểm tra; ném KocLocked/KocError. Không đụng bản gốc."""
    new = copy.deepcopy(char)
    for path, value in changes.items():
        if path.split(".")[0] in LOCKED_KEYS or (path != AGE_PATH and path not in EDITABLE):
            raise KocLocked(f"'{path}' bị khóa — chỉ sửa được: {', '.join(EDITABLE)} và tuổi")
        if path == AGE_PATH:
            age = int(value)
            if age < mp.MIN_AGE:
                raise KocError(f"Tuổi {age} < {mp.MIN_AGE}: nhân vật phải từ {mp.MIN_AGE} tuổi (mục 17.11)")
            demo = new["identity"]["demographics"]
            new["identity"]["demographics"] = _AGE_RE.sub(lambda m: f"{age}{m.group(2)}", demo, count=1)
            continue
        if not isinstance(value, str) or not value.strip():
            raise KocError(f"'{path}' không được để trống")
        check_text(path, value)
        _set(new, path, value.strip())
    try:
        mp.validate_identity(new["identity"])
    except mp.PromptError as e:
        raise KocError(str(e)) from e
    if any(k in new for k in LOCKED_KEYS):
        raise KocLocked("tệp nhân vật không được chứa Lớp B/negative/consistency_lock")
    return new


def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def set_status(yaml_path: Path, char: dict, status: str, refs_root: Path) -> None:
    if status not in STATUSES:
        raise KocError(f"status không hợp lệ: {status}")
    if status == "ready":
        miss = missing_reference_images(char, refs_root)
        if miss:
            raise KocError("Chưa có ảnh gốc nên chưa bật được 'ready' (thiếu: " + ", ".join(miss) + ")")
    cid = char["identity"]["character_id"]
    text = Path(yaml_path).read_text(encoding="utf-8")
    pat = re.compile(rf"(\{{id:\s*{re.escape(cid)},.*?status:\s*)\w+")
    new, n = pat.subn(rf"\g<1>{status}", text, count=1)
    if n != 1:
        raise KocError(f"không thấy {cid} trong characters.yaml")
    _atomic_write(Path(yaml_path), new)


def save_character(char_dir: Path, yaml_path: Path, char_id: str, changes: dict, *,
                   status: str | None = None, refs_root: Path | None = None) -> dict:
    """Kiểm tra TOÀN BỘ trước, rồi mới ghi (JSON trước, status sau). Trả nhân vật mới."""
    p = Path(char_dir) / f"{char_id.lower()}.json"
    old = json.loads(p.read_text(encoding="utf-8"))
    new = apply_changes(old, changes)
    cur_status = _read_status(Path(yaml_path)).get(char_id, "draft")
    want = status or cur_status
    if want == "ready" and missing_reference_images(new, refs_root or mp.ROOT):
        raise KocError("Chưa có ảnh gốc nên chưa bật được 'ready'")
    if new != old:
        _atomic_write(p, json.dumps(new, ensure_ascii=False, indent=2) + "\n")
    if want != cur_status:
        set_status(Path(yaml_path), new, want, refs_root or mp.ROOT)
    return new


def preview_prompt(char: dict) -> dict:
    """Chỉ đọc: dựng prompt mẫu bằng build_prompt từ mặc định của nhân vật."""
    d = char.get("defaults", {})
    plat = char.get("meta", {}).get("main_platform", "tiktok").split("/")[0].strip()
    shot = {"scene_id": "preview", "setting": d.get("setting", "plain room"),
            "time_and_light": "daylight", "key_light": d.get("key_light", "window light"),
            "wardrobe": {"top": d.get("wardrobe_palette", "plain top")},
            "pose_action": "facing camera, relaxed", "expression": "neutral, slight smile",
            "framing": "medium close-up, eye level"}
    return mp.build_prompt(char, shot, platform=plat if plat in mp.PLATFORM_RATIO else "tiktok")


# ---- giao diện -------------------------------------------------------------
class KocPage(QWidget):
    saved = Signal(str)

    def __init__(self, char_dir: str | Path | None = None, yaml_path: str | Path | None = None,
                 refs_root: str | Path | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.char_dir = Path(char_dir) if char_dir else mp.CHAR_DIR
        self.yaml_path = Path(yaml_path) if yaml_path else mp.ROOT / "config" / "characters.yaml"
        self.refs_root = Path(refs_root) if refs_root else mp.ROOT
        self._chars: list[dict] = []
        self._loading = False
        self._build()
        self.reload()

    def _build(self) -> None:
        self.list = QListWidget()
        self.list.setMaximumWidth(260)
        self.list.currentRowChanged.connect(self._show)
        self.header = QLabel()
        self.header.setWordWrap(True)
        self.edits: dict[str, QLineEdit] = {}
        box = QGroupBox("Thông tin sửa được")
        form = QFormLayout(box)
        for path, label in EDITABLE.items():
            e = QLineEdit()
            self.edits[path] = e
            form.addRow(label, e)
        self.age = QSpinBox()
        self.age.setRange(0, 99)
        form.addRow("Tuổi (tối thiểu 22):", self.age)
        self.status = QComboBox()
        self.status.addItems(STATUSES)
        form.addRow("Trạng thái:", self.status)
        self.status_note = QLabel("Chưa có ảnh gốc nên chưa bật được trạng thái ready.")
        self.status_note.setWordWrap(True)
        form.addRow(self.status_note)

        self.disclosure = QLabel("Luôn bật chú thích nội dung do AI tạo (ai_disclosure): bật.")
        self.locked = QPlainTextEdit()
        self.locked.setReadOnly(True)
        self.locked.setMaximumHeight(110)
        lbox = QGroupBox("Đã khóa (không sửa được)")
        ll = QVBoxLayout(lbox)
        ll.addWidget(self.locked)

        self.btn_save = QPushButton("Lưu")
        self.btn_save.clicked.connect(self.save)
        self.btn_reset = QPushButton("Bỏ thay đổi")
        self.btn_reset.clicked.connect(lambda: self._show(self.list.currentRow()))
        self.btn_prompt = QPushButton("Xem prompt")
        self.btn_prompt.clicked.connect(self.show_prompt)
        self.msg = QLabel()
        self.msg.setWordWrap(True)
        self.prompt_view = QPlainTextEdit()
        self.prompt_view.setReadOnly(True)

        row = QHBoxLayout()
        for b in (self.btn_save, self.btn_reset, self.btn_prompt):
            row.addWidget(b)
        row.addStretch(1)
        right = QVBoxLayout()
        for w in (self.header, self.disclosure, box, lbox):
            right.addWidget(w)
        right.addLayout(row)
        right.addWidget(self.msg)
        right.addWidget(self.prompt_view, 1)
        root = QHBoxLayout(self)
        left = QVBoxLayout()
        left.addWidget(QLabel("Nhân vật:"))
        left.addWidget(self.list, 1)
        root.addLayout(left)
        root.addLayout(right, 1)

    def _say(self, text: str, bad: bool = False) -> None:
        self.msg.setText(text)
        self.msg.setStyleSheet("color: #c5221f;" if bad else "color: #137333;")

    def current(self) -> dict | None:
        r = self.list.currentRow()
        return self._chars[r] if 0 <= r < len(self._chars) else None

    def reload(self) -> None:
        keep = (self.current() or {}).get("id")
        self._chars = list_characters(self.char_dir, self.yaml_path)
        self._loading = True
        self.list.clear()
        for c in self._chars:
            self.list.addItem(f"{c['name']} — {c['age'] if c['age'] is not None else '?'} tuổi — {c['status']}")
        self._loading = False
        idx = next((i for i, c in enumerate(self._chars) if c["id"] == keep), 0 if self._chars else -1)
        self.list.setCurrentRow(idx)
        self._show(idx)

    def _show(self, row: int) -> None:
        if not (0 <= row < len(self._chars)) or self._loading:
            return
        c = self._chars[row]
        d = c["data"]
        self.header.setText(f"<b>{c['name']}</b> ({c['id']}) — {c['summary']}")
        for path, e in self.edits.items():
            e.setText(str(_get(d, path) or ""))
        self.age.setValue(c["age"] or 0)
        self.status.setCurrentText(c["status"])
        eng = mp.load_engine()
        self.locked.setPlainText(
            "Lớp B (realism_engine.json): " + ", ".join(eng["realism_engine"]) + "\n"
            f"negative: cố định, lấy từ realism_engine.json ({len(eng['negative'])} ký tự/mục)\n"
            "consistency_lock: sinh tự động từ identity khi dựng prompt\n"
            "Ảnh gốc: " + ("đủ" if not missing_reference_images(d, self.refs_root)
                           else "chưa có (" + str(len(d["identity"].get("reference_images", []))) + " tệp thiếu)"))
        self.prompt_view.clear()
        self.msg.clear()

    def save(self) -> None:
        c = self.current()
        if not c:
            return
        changes = {p: e.text() for p, e in self.edits.items()}
        changes[AGE_PATH] = self.age.value()
        try:
            save_character(self.char_dir, self.yaml_path, c["id"], changes,
                           status=self.status.currentText(), refs_root=self.refs_root)
        except KocError as e:
            self._say(f"Chưa lưu: {e}", bad=True)
            return
        except (OSError, ValueError) as e:
            self._say(f"Lỗi ghi tệp: {e}", bad=True)
            return
        self.reload()
        self._say("Đã lưu.")
        self.saved.emit(c["id"])

    def show_prompt(self) -> None:
        c = self.current()
        if not c:
            return
        try:
            p = preview_prompt(c["data"])
        except mp.PromptError as e:
            self._say(f"Không dựng được prompt: {e}", bad=True)
            return
        self.prompt_view.setPlainText(json.dumps(p, ensure_ascii=False, indent=2))
