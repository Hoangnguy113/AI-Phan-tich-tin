"""Toán thời lượng (mục 8). Đây là phép tính, KHÔNG giao cho LLM."""
from __future__ import annotations

import re

# Bảng mục 8: thời lượng (phút) -> (từ tối thiểu, từ tối đa) ở ~150–170 từ/phút
WORD_TABLE_MIN = {3: 450, 5: 750, 10: 1500, 15: 2250, 20: 3000}

TOLERANCE = 0.10  # KPI mục 1: sai lệch thời lượng <= ±10%
SCENE_PAUSE_SEC = 0.4  # khoảng nghỉ tối thiểu giữa các câu trong một cảnh

_WORD_RE = re.compile(r"[^\W_]+(?:['’\-][^\W_]+)*", re.UNICODE)


def count_words(text: str) -> int:
    """Đếm từ theo khoảng trắng/ký tự chữ — dùng chung cho vi/de/en."""
    return len(_WORD_RE.findall(text or ""))


def speech_seconds(text: str, wpm: float) -> float:
    if wpm <= 0:
        raise ValueError("wpm phải > 0")
    return count_words(text) / (wpm / 60.0)


def scene_duration(text: str, wpm: float, pause_sec: float = SCENE_PAUSE_SEC) -> float:
    """duration_sec = số từ / (wpm/60) + khoảng nghỉ (mục 8)."""
    return round(speech_seconds(text, wpm) + pause_sec, 2)


def word_budget(target_minutes: float, wpm: float, *, intro_outro_share: float = 0.0) -> int:
    """Ngân sách số từ cho cả video; trừ phần dành cho cảnh không lời (nếu có)."""
    total = target_minutes * wpm * (1 - intro_outro_share)
    return int(round(total))


def split_budget(total_words: int, weights: list[float]) -> list[int]:
    """Chia ngân sách từ cho các phân đoạn theo trọng số, tổng khớp tuyệt đối."""
    s = sum(weights)
    if s <= 0:
        raise ValueError("tổng trọng số phải > 0")
    raw = [total_words * w / s for w in weights]
    out = [int(x) for x in raw]
    # phân phối phần dư theo phần thập phân lớn nhất
    for i in sorted(range(len(raw)), key=lambda i: raw[i] - out[i], reverse=True)[: total_words - sum(out)]:
        out[i] += 1
    return out


def within_tolerance(actual_sec: float, target_sec: float, tol: float = TOLERANCE) -> bool:
    return abs(actual_sec - target_sec) <= target_sec * tol


def deviation(actual_sec: float, target_sec: float) -> float:
    return (actual_sec - target_sec) / target_sec


def pick_duration_bucket(mix: dict[str, int], produced: dict[str, int]) -> str | None:
    """Trả về khoảng thời lượng còn thiếu nhiều nhất so với duration_mix; None nếu đủ."""
    missing = {k: need - produced.get(k, 0) for k, need in mix.items()}
    key = max(missing, key=lambda k: missing[k]) if missing else None
    return key if key and missing[key] > 0 else None
