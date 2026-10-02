"""Trend Score 0–100 (mục 5). Từ chối chấm nếu thiếu dữ liệu/nguồn — không bịa số."""
from __future__ import annotations

import shutil
import time
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator

COMPONENTS = ["velocity", "volume", "engagement", "gap", "audience_fit", "evergreen", "impact", "source_trust"]


class Component(BaseModel):
    value: float = Field(ge=0, le=100)
    evidence: str  # nguồn số liệu/URL/ghi chú — BẮT BUỘC (chống bịa số, mục 1)

    @field_validator("evidence")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("thành phần điểm phải có evidence (nguồn số liệu)")
        return v


class ScoreInput(BaseModel):
    story_id: str
    components: dict[str, Component]


class MissingEvidence(ValueError):
    pass


def load_weights(path: str | Path = "config/scoring.yaml", *, breaking: bool = False) -> dict[str, float]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    w = data["breaking_overrides"] if breaking else data["weights"]
    _check_weights(w)
    return {k: float(v) for k, v in w.items()}


def _check_weights(w: dict[str, float]) -> None:
    if set(w) != set(COMPONENTS):
        raise ValueError(f"trọng số phải đủ đúng {COMPONENTS}")
    if abs(sum(w.values()) - 1.0) > 1e-6:
        raise ValueError(f"tổng trọng số phải = 1.0, hiện {sum(w.values()):.4f}")


def trend_score(inp: ScoreInput, weights: dict[str, float]) -> float:
    _check_weights(weights)
    missing = [c for c in COMPONENTS if c not in inp.components]
    if missing:
        raise MissingEvidence(f"{inp.story_id}: thiếu thành phần {missing} — không chấm khi thiếu dữ liệu")
    return round(sum(weights[c] * inp.components[c].value for c in COMPONENTS), 1)


def rank(items: list[ScoreInput], weights: dict[str, float], top_n: int) -> list[tuple[str, float]]:
    scored = []
    for it in items:
        try:
            scored.append((it.story_id, trend_score(it, weights)))
        except MissingEvidence:
            continue  # loại, không đoán
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_n]


def save_weights(new: dict[str, float], path: str | Path = "config/scoring.yaml") -> Path:
    """Analytics Learner ghi trọng số mới; luôn lưu bản cũ để quay lại."""
    _check_weights(new)
    p = Path(path)
    backup = p.with_suffix(f".{int(time.time())}.bak.yaml")
    shutil.copy2(p, backup)
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    data["weights"] = {k: round(float(v), 4) for k, v in new.items()}
    p.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return backup
