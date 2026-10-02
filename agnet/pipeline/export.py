"""Ghi file đầu ra cho một kịch bản (mục 10.1). Mọi file ghi bằng code, không để LLM ghi."""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path


def slugify(text: str, max_len: int = 48) -> str:
    t = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:max_len] or "kich-ban"


def voiceover_txt(doc: dict) -> str:
    out = []
    for seg in doc["segments"]:
        out.append(f"## {seg['id']} — {seg['name']}")
        out += [sc["voiceover"] for sc in seg["scenes"]]
        out.append("")
    return "\n".join(out).strip() + "\n"


def sources_md(doc: dict) -> str:
    lines = ["# Nguồn tham khảo đã kiểm chứng", ""]
    for s in doc["sources"]:
        mark = "✅" if s["verified"] else "⚠️ chưa xác minh"
        lines.append(f"- **{s['id']}** {mark} — {s['title']}" + (f" — {s['url']}" if s.get("url") else ""))
    return "\n".join(lines) + "\n"


def packaging_md(doc: dict) -> str:
    p = doc["packaging"]
    lines = ["# Đóng gói", "", "## Tiêu đề", ""]
    for t in p["titles"]:
        lines.append(f"- {t['text']}  \n  _{t.get('technique', 'plain')}_ — kiểm chứng: {t['truth_check']}")
    if doc.get("hook_variants"):
        lines += ["", "## Hook thay thế", ""] + [f"{i}. {h}" for i, h in enumerate(doc["hook_variants"], 1)]
    for key, label in [("description", "Mô tả"), ("tags", "Tag"), ("hashtags", "Hashtag"), ("thumbnail_ideas", "Thumbnail")]:
        v = p.get(key)
        if v:
            lines += ["", f"## {label}", "", v if isinstance(v, str) else "\n".join(f"- {x}" for x in v)]
    if doc.get("chapters"):
        lines += ["", "## Chapter", ""] + [f"- {int(c['at_sec']//60):02d}:{int(c['at_sec']%60):02d} {c['title']}" for c in doc["chapters"]]
    return "\n".join(lines) + "\n"


def write_script_folder(doc: dict, script_md: str, out_root: Path | str, day: str, index: int) -> Path:
    folder = Path(out_root) / day / doc["flow_id"] / f"{index:02d}_{slugify(doc['title'])}"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "script.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    (folder / "script.md").write_text(script_md, encoding="utf-8")
    (folder / "voiceover.txt").write_text(voiceover_txt(doc), encoding="utf-8")
    (folder / "sources.md").write_text(sources_md(doc), encoding="utf-8")
    (folder / "packaging.md").write_text(packaging_md(doc), encoding="utf-8")
    return folder


def daily_report(flow_id: str, day: str, results: list[dict], spent: float, status: str, errors: list[str]) -> str:
    passed = [r for r in results if r["verdict"] == "pass"]
    lines = [f"# Báo cáo ngày {day} — luồng {flow_id}", "",
             f"- Trạng thái: **{status}**", f"- Đạt QA: **{len(passed)}** / {len(results)} kịch bản đã viết",
             f"- Chi phí: **${spent:.2f}**", ""]
    lines += ["## Kịch bản", "", "| # | Đề tài | Kết quả | Điểm QA | Ghi chú |", "|---|---|---|---|---|"]
    for i, r in enumerate(results, 1):
        lines.append(f"| {i} | {r['title']} | {r['verdict']} | {r.get('score', '—')} | {r.get('note', '')} |")
    if errors:
        lines += ["", "## Lỗi", ""] + [f"- {e}" for e in errors]
    return "\n".join(lines) + "\n"
