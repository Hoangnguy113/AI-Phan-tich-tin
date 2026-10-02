"""Kiểm tra script.json: schema (mục 10.3) + quy tắc ngữ nghĩa (mục 8, 9, 7A, 17).

Đây là cổng chặn cuối cùng TRƯỚC khi file được xuất cho phần mềm dựng.
Lỗi `error` = không xuất. Lỗi `warn` = xuất nhưng báo cáo.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from . import timing
from .models import Flow

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "script.schema.json"
EPS = 0.06  # sai số làm tròn giây cho phép giữa các cảnh

# Nhịp đổi cảnh trung bình hợp lý theo nền tảng (mục 10.4), giây
CADENCE = {"youtube": (2.0, 9.0), "tiktok": (1.0, 5.0), "facebook": (2.0, 8.0)}
RATIO_BY_PLATFORM = {
    "youtube": {"16:9"},
    "tiktok": {"9:16"},
    "facebook": {"4:5", "1:1", "9:16"},
}


@dataclass
class Issue:
    severity: str  # "error" | "warn"
    path: str
    message: str

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.path}: {self.message}"


def _schema_issues(doc: dict[str, Any]) -> list[Issue]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    v = Draft202012Validator(schema)
    out = []
    for e in sorted(v.iter_errors(doc), key=lambda e: list(e.absolute_path)):
        path = "/".join(str(p) for p in e.absolute_path) or "(root)"
        out.append(Issue("error", path, e.message))
    return out


def validate_script(doc: dict[str, Any], flow: Flow | None = None) -> list[Issue]:
    issues = _schema_issues(doc)
    if issues:  # schema hỏng thì các kiểm tra sau không còn tin cậy
        return issues

    wpm = float(doc["wpm"])
    target = float(doc["target_duration_sec"])
    segs = doc["segments"]

    # --- 1. Tính liên tục thời gian: segment và scene -----------------------
    ids_seen: set[str] = set()
    cursor = 0.0
    all_scenes: list[tuple[dict, dict]] = []
    for si, seg in enumerate(segs):
        if abs(seg["start_sec"] - cursor) > EPS:
            issues.append(Issue("error", f"segments/{si}", f"{seg['id']} bắt đầu {seg['start_sec']}s, đúng ra phải {cursor:.2f}s (hở/chồng thời gian)"))
        scene_cursor = seg["start_sec"]
        for sc in seg["scenes"]:
            if sc["id"] in ids_seen:
                issues.append(Issue("error", sc["id"], "id cảnh trùng"))
            ids_seen.add(sc["id"])
            if not sc["id"].startswith(seg["id"] + "."):
                issues.append(Issue("error", sc["id"], f"cảnh không thuộc phân đoạn {seg['id']}"))
            if abs(sc["start_sec"] - scene_cursor) > EPS:
                issues.append(Issue("error", sc["id"], f"start_sec {sc['start_sec']} ≠ {scene_cursor:.2f} (hở/chồng cảnh)"))
            scene_cursor = sc["start_sec"] + sc["duration_sec"]
            all_scenes.append((seg, sc))
        if abs(seg["end_sec"] - scene_cursor) > EPS:
            issues.append(Issue("error", seg["id"], f"end_sec {seg['end_sec']} ≠ tổng các cảnh {scene_cursor:.2f}"))
        cursor = seg["end_sec"]

    # --- 2. Tổng thời lượng so với mục tiêu (KPI ±10%) ----------------------
    if not timing.within_tolerance(cursor, target):
        dev = timing.deviation(cursor, target) * 100
        issues.append(Issue("error", "target_duration_sec", f"tổng {cursor:.0f}s lệch {dev:+.1f}% so với mục tiêu {target:.0f}s (cho phép ±10%)"))
    if flow and not (flow.duration_min * 60 <= cursor <= flow.duration_max * 60):
        issues.append(Issue("error", "segments", f"tổng {cursor/60:.1f} phút ngoài khoảng {flow.duration_min}-{flow.duration_max} phút của luồng"))

    # --- 3. Lời thoại có kịp trong thời lượng cảnh không --------------------
    total_words = 0
    for seg, sc in all_scenes:
        words = timing.count_words(sc["voiceover"])
        total_words += words
        need = timing.speech_seconds(sc["voiceover"], wpm)
        if need > sc["duration_sec"] + 0.5:
            issues.append(Issue("error", sc["id"], f"lời thoại {words} từ cần ~{need:.1f}s nhưng cảnh chỉ {sc['duration_sec']}s @ {wpm:g} wpm"))
        elif words and need < sc["duration_sec"] * 0.35 and sc["duration_sec"] > 6:
            issues.append(Issue("warn", sc["id"], f"cảnh {sc['duration_sec']}s mà lời thoại chỉ ~{need:.1f}s (khoảng lặng dài?)"))
    expected_words = target / 60 * wpm
    if total_words < expected_words * 0.80 or total_words > expected_words * 1.10:
        issues.append(Issue("warn", "voiceover", f"tổng {total_words} từ, kỳ vọng ~{expected_words:.0f} từ cho {target/60:.1f} phút @ {wpm:g} wpm"))

    # --- 4. Nền tảng: tỉ lệ khung hình & nhịp cảnh --------------------------
    plat = doc["platform"]
    if doc["aspect_ratio"] not in RATIO_BY_PLATFORM[plat]:
        issues.append(Issue("error", "aspect_ratio", f"{plat} không dùng {doc['aspect_ratio']} (cho phép {sorted(RATIO_BY_PLATFORM[plat])})"))
    avg = cursor / max(len(all_scenes), 1)
    lo, hi = CADENCE[plat]
    if not lo <= avg <= hi:
        issues.append(Issue("warn", "segments", f"nhịp trung bình {avg:.1f}s/cảnh ngoài khoảng {lo}-{hi}s của {plat}"))
    if flow:
        if doc["flow_id"] != flow.id:
            issues.append(Issue("error", "flow_id", f"{doc['flow_id']} ≠ luồng {flow.id}"))
        if doc["platform"] != flow.platform:
            issues.append(Issue("error", "platform", f"{doc['platform']} ≠ nền tảng của luồng ({flow.platform})"))
        if doc["language"] != flow.output_language:
            issues.append(Issue("error", "language", f"{doc['language']} ≠ output_language của luồng ({flow.output_language})"))

    # --- 5. Nguồn: tham chiếu hợp lệ, chưa xác minh không được dùng ---------
    sources = {s["id"]: s for s in doc["sources"]}
    for _, sc in all_scenes:
        for sid in sc.get("source_ids", []):
            if sid not in sources:
                issues.append(Issue("error", sc["id"], f"source_id {sid!r} không có trong sources"))
            elif not sources[sid]["verified"]:
                issues.append(Issue("error", sc["id"], f"dùng nguồn chưa xác minh {sid!r} (mục 4 — Fact-checker)"))
    if flow and flow.strict_factcheck and not any(sc.get("source_ids") for _, sc in all_scenes):
        issues.append(Issue("error", "sources", "luồng strict_factcheck nhưng không cảnh nào gắn source_ids"))

    # --- 6. Tiêu đề: truth_check bắt buộc (mục 7A) --------------------------
    for i, t in enumerate(doc["packaging"]["titles"]):
        if t.get("technique") == "rumor_check" and "?" not in t["text"]:
            issues.append(Issue("error", f"packaging/titles/{i}", "tiêu đề 'tin đồn – kiểm chứng' phải ở dạng câu hỏi (mục 7A)"))
    if doc["title"] not in {t["text"] for t in doc["packaging"]["titles"]}:
        issues.append(Issue("warn", "title", "title chính không nằm trong packaging.titles nên chưa có truth_check"))

    # --- 7. QA & kiểm duyệt tay ---------------------------------------------
    qa = doc["qa"]
    if qa["score"] < 8:
        issues.append(Issue("error", "qa/score", f"điểm QA {qa['score']} < 8 (mục 9) — không được xuất"))
    if flow and (flow.sensitive or flow.human_review) and not qa["human_review_required"]:
        issues.append(Issue("error", "qa/human_review_required", "luồng nhạy cảm/human_review phải gắn human_review_required=true"))

    # --- 8. KOC (mục 17) -----------------------------------------------------
    issues += _koc_issues(doc, all_scenes, flow)
    return issues


def _koc_issues(doc: dict, all_scenes: list[tuple[dict, dict]], flow: Flow | None) -> list[Issue]:
    out: list[Issue] = []
    koc = doc.get("koc") or {"enabled": False}
    human = [sc for _, sc in all_scenes if sc["visual"]["type"] == "koc"]
    if flow and flow.koc.enabled and not koc["enabled"]:
        out.append(Issue("error", "koc", f"luồng bật KOC ({flow.koc.character_id}) nhưng kịch bản không có koc.enabled=true"))
        return out
    if not koc["enabled"]:
        for sc in human:
            out.append(Issue("error", sc["id"], "cảnh visual.type='koc' nhưng koc.enabled=false"))
        return out
    if not koc.get("character_id"):
        out.append(Issue("error", "koc/character_id", "koc.enabled=true cần character_id"))
    if flow and flow.koc.enabled and koc.get("character_id") != flow.koc.character_id:
        out.append(Issue("error", "koc/character_id", f"{koc.get('character_id')} ≠ nhân vật của luồng ({flow.koc.character_id})"))
    if not koc.get("wardrobe_set"):
        out.append(Issue("error", "koc/wardrobe_set", "một kịch bản = một bộ phục trang (mục 17.8) — thiếu wardrobe_set"))
    ratio = len(human) / max(len(all_scenes), 1)
    if not 0.25 <= ratio <= 0.40:
        out.append(Issue("error", "koc", f"{ratio:.0%} cảnh có mặt người, phải trong 25–40% (mục 17.8)"))
    for sc in human:
        k = sc["visual"].get("koc")
        if not k:
            out.append(Issue("error", sc["id"], "visual.type='koc' thiếu khối visual.koc"))
            continue
        if k["prompt_ref"] != f"koc_prompts.json#{sc['id']}":
            out.append(Issue("error", sc["id"], f"prompt_ref {k['prompt_ref']!r} không trỏ về chính cảnh này"))
    if not doc["packaging"].get("ai_disclosure"):
        out.append(Issue("error", "packaging/ai_disclosure", "có người dẫn do AI tạo nhưng chưa bật ai_disclosure (mục 17.11)"))
    return out


def has_errors(issues: list[Issue]) -> bool:
    return any(i.severity == "error" for i in issues)


def validate_file(path: str | Path, flow: Flow | None = None) -> list[Issue]:
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_script(doc, flow)
