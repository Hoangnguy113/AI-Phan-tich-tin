"""Số agent chạy song song đặt trong giao diện phải thật sự đến được Pipeline."""
from __future__ import annotations

import asyncio

from agnet import runner
from agnet.core import settings as S
from agnet.core.models import Flow


class _FakePipeline:
    seen: dict = {}

    def __init__(self, *args, **kw):
        _FakePipeline.seen = dict(kw)

    async def run(self):
        return {"status": "ok", "passed": 0, "spent": 0.0}


def _flow():
    return Flow(id="x", name="X", topic="t", schedule=["0 5 * * *"])


def test_concurrency_lay_tu_cai_dat(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "Pipeline", _FakePipeline)
    monkeypatch.setattr(runner, "load_agents", lambda: {})
    monkeypatch.setattr(runner.settings, "load", lambda *a, **k: S.Settings(concurrency=6))
    asyncio.run(runner.run_flow(_flow(), db=str(tmp_path / "a.db"), runner=object(), root=tmp_path))
    assert _FakePipeline.seen["concurrency"] == 6


def test_concurrency_mac_dinh_la_3(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "Pipeline", _FakePipeline)
    monkeypatch.setattr(runner, "load_agents", lambda: {})
    monkeypatch.setattr(runner.settings, "load", lambda *a, **k: S.Settings())
    asyncio.run(runner.run_flow(_flow(), db=str(tmp_path / "a.db"), runner=object(), root=tmp_path))
    assert _FakePipeline.seen["concurrency"] == 3
