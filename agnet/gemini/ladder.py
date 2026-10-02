"""Phân tích tên model Gemini và xếp "thang" từ cao xuống thấp.

KHÔNG gõ cứng tên model. Từ tên (vd `gemini-2.5-pro`) rút ra: phiên bản (2.5), bậc (pro > flash > flash-lite),
có phải bản preview/exp không. Model mới của Google xuất hiện là tự vào thang.

Thứ tự hạ bậc (theo yêu cầu): hết phiên bản này sang phiên bản thấp hơn CÙNG bậc, rồi mới xuống bậc thấp hơn:
  3.8-pro → 3.7-pro → … → 3.8-flash → 3.7-flash → … → 3.8-flash-lite → …
Bản preview/exp chỉ nằm SAU toàn bộ bản ổn định.

Chưa kiểm chứng: danh sách tên model thật của Google; bộ phân tích chịu được tên lạ (bỏ qua, không vỡ).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

TIER_RANK = {"pro": 0, "flash": 1, "flash-lite": 2}       # số nhỏ = cao hơn
_NAME = re.compile(r"^gemini-(\d+(?:\.\d+)*)-(pro|flash-lite|flash)(?:-(.+))?$")
# phần đuôi cho biết model không dùng để sinh văn bản thường / hoặc chỉ là bí danh trùng lặp
_SKIP_TAGS = ("image", "tts", "live", "audio", "embedding", "aqa", "robotics", "computer-use",
              "vision", "native", "customtools", "latest", "thinking")
_PREVIEW_TAGS = ("preview", "exp")


@dataclass(frozen=True)
class ModelInfo:
    name: str                 # tên rút gọn, vd "gemini-2.5-pro" (không có tiền tố "models/")
    version: tuple[int, ...]
    tier: str
    preview: bool
    suffix: str = ""

    def to_json(self) -> dict:
        return {"name": self.name, "version": list(self.version), "tier": self.tier,
                "preview": self.preview, "suffix": self.suffix}

    @staticmethod
    def from_json(d: dict) -> "ModelInfo":
        return ModelInfo(d["name"], tuple(d["version"]), d["tier"], bool(d["preview"]), d.get("suffix", ""))


def parse_model(name: str) -> ModelInfo | None:
    """Tên → ModelInfo; None nếu không phải model văn bản họ gemini mà ta hiểu được."""
    n = (name or "").strip()
    if n.startswith("models/"):
        n = n[len("models/"):]
    m = _NAME.match(n.lower())
    if not m:
        return None
    ver, tier, suffix = m.group(1), m.group(2), m.group(3) or ""
    parts = suffix.split("-") if suffix else []
    if any(t in parts for t in _SKIP_TAGS):
        return None
    preview = any(t in parts for t in _PREVIEW_TAGS)
    return ModelInfo(n.lower(), tuple(int(x) for x in ver.split(".")), tier, preview, suffix)


def _rank_variant(m: ModelInfo) -> tuple:
    """Cùng (phiên bản, bậc, preview) mà nhiều biến thể: chuộng tên trơn, rồi hậu tố lớn nhất."""
    return (m.suffix == "" or m.suffix in _PREVIEW_TAGS, m.suffix)


def build_ladder(names, start_tier: str = "pro") -> list[ModelInfo]:
    """Danh sách tên → thang đi XUỐNG, bắt đầu từ bậc `start_tier`."""
    best: dict[tuple, ModelInfo] = {}
    for raw in names:
        m = parse_model(raw)
        if m is None:
            continue
        key = (m.version, m.tier, m.preview)
        if key not in best or _rank_variant(m) > _rank_variant(best[key]):
            best[key] = m
    start = TIER_RANK.get(start_tier, 0)
    pool = [m for m in best.values() if TIER_RANK[m.tier] >= start]

    def order(m: ModelInfo):
        neg_version = tuple(-x for x in m.version)
        return (m.preview, TIER_RANK[m.tier], neg_version)

    return sorted(pool, key=order)
