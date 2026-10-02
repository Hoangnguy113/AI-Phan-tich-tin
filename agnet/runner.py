"""Chạy một luồng ngay (không cần APScheduler)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from .core import settings
from .core.models import Flow
from .pipeline.agents import SdkRunner, load_agents
from .pipeline.pipeline import Pipeline
from .storage.db import Store


async def run_flow(flow: Flow, *, db: str = "agnet.db", runner=None, root: Path | str | None = None) -> dict:
    root = Path(root or Path(__file__).resolve().parents[1])
    # số agent chạy song song do người dùng đặt trong giao diện (core/settings.py)
    p = Pipeline(flow, load_agents(), runner or SdkRunner(), Store(db), date.today(), root / flow.output_dir,
                 concurrency=settings.load().concurrency)
    return await p.run()
