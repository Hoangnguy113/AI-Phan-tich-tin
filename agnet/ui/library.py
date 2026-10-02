"""Kho kịch bản: đọc đúng thư mục pipeline đã ghi (output/<ngày>/<luồng>/<nn_slug>/).

Kịch bản vừa nằm trong thư mục vừa hiện trong phần mềm vì cả hai là CÙNG MỘT nguồn: phần mềm không sao chép
gì, chỉ đọc và tự làm mới khi thư mục đổi (xem signature()).

Duyệt / Cần viết lại / Loại lưu ở review.json CẠNH script.json. KHÔNG sửa script.json (đổi schema là việc
của schemas/script.schema.json — quy tắc 7 trong CLAUDE.md).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ..env import ROOT

DEFAULT_ROOT = ROOT / "output"
STATUSES = ("pending", "approved", "rewrite", "rejected")

# nhãn -> mẫu tên tệp (tìm theo thứ tự, lấy tệp đầu tiên có)
_FILES = {
    "script": ("script.md",),
    "voiceover": ("voiceover*.txt",),
    "packaging": ("packaging.md",),
    "sources": ("sources.md",),
    "koc": ("koc_prompts.json",),
    "json": ("script.json",),
}


@dataclass
class Entry:
    day: str
    flow_id: str
    slug: str
    folder: Path
    title: str = ""
    qa_score: float | None = None
    duration_sec: float | None = None
    language: str = ""
    flags: list[str] = field(default_factory=list)
    human_review_required: bool = False
    status: str = "pending"
    note: str = ""


def _json(p: Path) -> dict:
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _md_title(p: Path) -> str:
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                return line[2:].strip()
    except OSError:
        pass
    return ""


def get_review(folder: Path) -> tuple[str, str]:
    d = _json(Path(folder) / "review.json")
    st = d.get("status")
    return (st if st in STATUSES else "pending"), str(d.get("note") or "")


def set_review(folder: str | Path, status: str, note: str = "") -> None:
    if status not in STATUSES:
        raise ValueError(f"trạng thái không hợp lệ: {status!r}")
    note = (note or "").strip()
    if status == "rewrite" and not note:
        raise ValueError("'cần viết lại' phải kèm góp ý cụ thể")
    p = Path(folder) / "review.json"
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"status": status, "note": note,
                               "at": datetime.now().isoformat(timespec="seconds")},
                              ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(p)


def _entry(day: str, flow: str, d: Path) -> Entry | None:
    js, md = d / "script.json", d / "script.md"
    if not js.exists() and not md.exists():
        return None
    meta = _json(js)
    qa = meta.get("qa") if isinstance(meta.get("qa"), dict) else {}
    status, note = get_review(d)
    score = qa.get("score")
    return Entry(
        day=day, flow_id=flow, slug=d.name, folder=d,
        title=str(meta.get("title") or "") or _md_title(md) or d.name,
        qa_score=float(score) if isinstance(score, (int, float)) else None,
        duration_sec=meta.get("target_duration_sec") if isinstance(meta.get("target_duration_sec"), (int, float)) else None,
        language=str(meta.get("language") or ""),
        flags=[str(x) for x in qa.get("flags", [])] if isinstance(qa.get("flags"), list) else [],
        human_review_required=bool(qa.get("human_review_required")),
        status=status, note=note,
    )


def _dirs(p: Path) -> list[Path]:
    try:
        return sorted(x for x in p.iterdir() if x.is_dir() and not x.name.startswith("."))
    except OSError:
        return []


def scan(root: str | Path | None = None) -> list[Entry]:
    """Mọi kịch bản, ngày mới nhất trước, rồi theo luồng, rồi theo số thứ tự."""
    base = Path(root or DEFAULT_ROOT)
    out: list[Entry] = []
    for day in _dirs(base):
        for flow in _dirs(day):
            for d in _dirs(flow):
                e = _entry(day.name, flow.name, d)
                if e:
                    out.append(e)
    out.sort(key=lambda e: (e.day, e.flow_id, e.slug))
    out.sort(key=lambda e: e.day, reverse=True)
    return out


def read_text(entry: Entry, kind: str) -> str | None:
    """Nội dung một tệp của kịch bản; None nếu không có. Chỉ đọc trong thư mục của kịch bản."""
    if kind not in _FILES:
        raise ValueError(f"loại tệp không hợp lệ: {kind!r}")
    for pat in _FILES[kind]:
        for f in sorted(entry.folder.glob(pat)):
            if f.is_file():
                try:
                    return f.read_text(encoding="utf-8")
                except OSError:
                    return None
    return None


def day_report(root: str | Path | None, day: str, flow_id: str) -> str | None:
    p = Path(root or DEFAULT_ROOT) / day / flow_id / "_BAO_CAO_NGAY.md"
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return None


def signature(root: str | Path | None = None) -> tuple:
    """Dấu vân tay rẻ của kho (tên + thời gian sửa các tệp chính) để biết khi nào cần làm mới."""
    sig = []
    for e in scan(root):
        for name in ("script.json", "script.md", "review.json"):
            f = e.folder / name
            try:
                sig.append((str(f), f.stat().st_mtime_ns))
            except OSError:
                pass
    return tuple(sig)


def open_folder(path: str | Path) -> None:
    if hasattr(os, "startfile"):
        os.startfile(str(path))                      # Windows: mở bằng Explorer
