"""Mô hình cấu hình Luồng (mục 3.1 KE_HOACH_AGNET.md)."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

Platform = Literal["youtube", "tiktok", "facebook"]
TitleStyle = Literal["curiosity", "rumor_check", "neutral"]
Mode = Literal["scheduled", "breaking"]

# Tốc độ đọc mặc định (từ/phút) theo ngôn ngữ — mục 3.1
DEFAULT_WPM = {"vi": 160, "de": 140, "en": 150}
DEFAULT_RATIO = {"youtube": "16:9", "tiktok": "9:16", "facebook": "4:5"}


class KocConfig(BaseModel):
    enabled: bool = False
    character_id: str | None = None
    human_scene_ratio: float = Field(0.33, ge=0.25, le=0.40)  # mục 4: 25–40% số cảnh
    image_engine: str = "nano_banana_pro"
    video_engine: str = "veo_3"

    @model_validator(mode="after")
    def _need_character(self) -> "KocConfig":
        if self.enabled and not self.character_id:
            raise ValueError("koc.enabled=true cần koc.character_id")
        return self


class Flow(BaseModel):
    id: str
    name: str
    enabled: bool = True
    topic: str
    seed_keywords: list[str] = []
    exclude_keywords: list[str] = []
    audience: str = ""
    region: str = "VN"
    language: str = "vi"
    output_language: str | None = None
    source_languages: list[str] = []
    review_translation: str | None = None
    platform: Platform = "youtube"
    aspect_ratio: str | None = None
    duration_min: float = Field(3, ge=3)
    duration_max: float = Field(20, le=20)
    duration_mix: dict[str, int] = {}
    daily_quota: int = Field(10, ge=1)
    schedule: list[str] = []
    timezone: str = "Asia/Bangkok"
    mode: Mode = "scheduled"
    interval_hours: float | None = None
    min_trend_score: float = 0
    sources: list[str] = []
    tone: str = ""
    narrator_persona: str = ""
    cta_style: str = ""
    brand_rules: list[str] = []
    title_style: TitleStyle = "curiosity"
    strict_factcheck: bool = True
    sensitive: bool = False
    human_review: bool = False
    entity_type: str | None = None
    privacy_guard: bool = True
    wpm: float | None = None
    max_tokens_per_run: int | None = None
    max_cost_usd_per_day: float = Field(8.0, gt=0)
    output_dir: str = "output"
    # --- chạy tự động hằng ngày (mục 11.1) ---
    catchup: bool = True            # máy tắt đúng giờ cron → chạy bù khi bật lại
    catchup_until: str = "12:00"    # chỉ bù nếu giờ địa phương của luồng còn trước mốc này (HH:MM)
    run_timeout_min: float = Field(180, gt=0)   # trần thời gian một lần chạy, tránh treo vô hạn
    webhook_url: str | None = None
    notify: list[str] = []
    koc: KocConfig = KocConfig()

    @field_validator("id")
    @classmethod
    def _slug(cls, v: str) -> str:
        if not v or not all(c.isalnum() or c in "-_" for c in v):
            raise ValueError("id chỉ gồm chữ, số, '-' và '_'")
        return v

    @model_validator(mode="after")
    def _defaults_and_checks(self) -> "Flow":
        if self.duration_min > self.duration_max:
            raise ValueError("duration_min > duration_max")
        if self.output_language is None:
            self.output_language = self.language
        if self.aspect_ratio is None:
            self.aspect_ratio = DEFAULT_RATIO[self.platform]
        if self.wpm is None:
            self.wpm = DEFAULT_WPM.get(self.output_language, 150)
        if self.mode == "breaking" and not self.interval_hours:
            raise ValueError("mode=breaking cần interval_hours")
        if self.mode == "scheduled" and self.enabled and not self.schedule:
            raise ValueError("luồng scheduled đang bật cần ít nhất một cron trong schedule")
        if self.duration_mix:
            for key in self.duration_mix:
                lo, _, hi = key.partition("-")
                if not (lo.isdigit() and hi.isdigit()):
                    raise ValueError(f"duration_mix khoá sai định dạng: {key!r}")
                if float(lo) < self.duration_min or float(hi) > self.duration_max:
                    raise ValueError(f"duration_mix {key!r} vượt khoảng thời lượng của luồng")
            if sum(self.duration_mix.values()) != self.daily_quota:
                raise ValueError("tổng duration_mix phải bằng daily_quota")
        hh, _, mm = self.catchup_until.partition(":")
        if not (hh.isdigit() and mm.isdigit() and 0 <= int(hh) <= 23 and 0 <= int(mm) <= 59):
            raise ValueError("catchup_until phải dạng HH:MM (24 giờ)")
        if self.sensitive and not self.human_review:
            raise ValueError("luồng sensitive=true bắt buộc human_review=true (mục 14)")
        return self


class FlowFile(BaseModel):
    flows: list[Flow]

    @model_validator(mode="after")
    def _unique_ids(self) -> "FlowFile":
        ids = [f.id for f in self.flows]
        dup = {i for i in ids if ids.count(i) > 1}
        if dup:
            raise ValueError(f"id luồng trùng: {sorted(dup)}")
        return self


def load_flows(path: str | Path = "config/flows.yaml") -> list[Flow]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return FlowFile.model_validate(data).flows
