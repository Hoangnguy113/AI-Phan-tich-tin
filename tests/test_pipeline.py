import asyncio
import copy
import json
from datetime import date

import pytest
from agnet.core.models import Flow
from agnet.pipeline.agents import AgentError, AgentResult, load_agents
from agnet.pipeline.pipeline import Pipeline
from agnet.storage.db import Store
from tests.conftest import make_doc

TODAY = date(2026, 10, 1)


class FakeRunner:
    """Agent giả: trả JSON dựng sẵn. Kiểm điều phối, KHÔNG kiểm chất lượng LLM."""

    def __init__(self, cost=0.5, qa=None, director_doc=None, fail=()):
        self.cost, self.calls, self.fail = cost, [], set(fail)
        self.qa = list(qa or [])
        self.director_doc = director_doc
        self.n_story = 0

    async def run(self, agent, prompt, *, max_budget_usd):
        name = agent.name
        self.calls.append(name)
        if name in self.fail:
            raise AgentError(f"{name} hỏng")
        r = {
            "trend-scout": {"items": [{"title": "a"}]}, "video-platform-scout": {"items": []},
            "news-scout": {"items": []}, "community-scout": {"questions": []}, "domain-internal-scout": {"items": []},
            "keyword-miner": {"items": []}, "competitor-gap-analyst": {"items": []},
            "dedup-cluster": {"stories": [{"title": f"Đề tài {i}"} for i in range(8)]},
            "trend-scorer": {"ranked": [{"title": f"Đề tài {i}", "score": 90 - i} for i in range(8)]},
            "content-strategist": {"outline": [{"segment": f"S{i}"} for i in range(1, 4)], "target_minutes": 4.8},
            "deep-researcher": {"dossier": []}, "fact-checker": {"claims": [], "sources": []},
            "script-writer": {"segment": "S", "running_summary": "tóm tắt"},
            "director": {"script": self.director_doc or make_doc(), "script_md": "# kịch bản"},
            "hook-packaging": {"packaging": make_doc()["packaging"], "hook_variants": ["h1"]},
        }
        if name == "editor-in-chief":
            r = self.qa.pop(0) if self.qa else {"verdict": "pass", "score": 8.6, "flags": []}
        else:
            r = r[name]
        return AgentResult(json.dumps(r, ensure_ascii=False), cost_usd=min(self.cost, max_budget_usd))


def flow(**kw):
    base = dict(id="suckhoe-yt-sang", name="t", topic="t", schedule=["0 5 * * *"], daily_quota=3,
                strict_factcheck=True, sensitive=True, human_review=True, max_cost_usd_per_day=100)
    return Flow(**{**base, **kw})


def run(tmp_path, runner, f=None, store=None, concurrency=2):
    store = store or Store(tmp_path / "t.db")
    p = Pipeline(f or flow(), load_agents(), runner, store, TODAY, tmp_path / "out", concurrency=concurrency)
    return asyncio.run(p.run()), p, store


def test_happy_path_stops_at_quota_and_writes_files(tmp_path):
    res, p, _ = run(tmp_path, FakeRunner())
    assert res["passed"] == 3 and res["status"] == "ok"
    folders = sorted((tmp_path / "out" / "2026-10-01" / "suckhoe-yt-sang").glob("0*_*"))
    assert len(folders) == 3
    for f in folders:
        for name in ("script.json", "script.md", "voiceover.txt", "sources.md", "packaging.md"):
            assert (f / name).exists()
    assert (tmp_path / "out" / "2026-10-01" / "suckhoe-yt-sang" / "_BAO_CAO_NGAY.md").exists()
    saved = json.loads((folders[0] / "script.json").read_text(encoding="utf-8"))
    assert saved["qa"]["human_review_required"] is True       # luồng sensitive


def test_writer_called_per_segment(tmp_path):
    r = FakeRunner()
    run(tmp_path, r, flow(daily_quota=1))
    assert r.calls.count("script-writer") % 3 == 0 and r.calls.count("script-writer") >= 3


def test_qa_revise_then_pass_calls_director_twice(tmp_path):
    r = FakeRunner(qa=[{"verdict": "revise", "score": 6.5, "fixes": [{"scene": "S1.1", "issue": "hook yếu", "fix": "đổi"}]}])
    res, *_ = run(tmp_path, r, flow(daily_quota=1), concurrency=1)
    assert res["passed"] == 1 and r.calls.count("director") == 2


def test_qa_never_passes_after_two_revisions_is_rejected_not_exported(tmp_path):
    bad = {"verdict": "revise", "score": 6, "fixes": []}
    r = FakeRunner(qa=[bad] * 30)
    res, _, store = run(tmp_path, r, flow(daily_quota=1), concurrency=1)
    assert res["passed"] == 0 and "thiếu sản lượng" in res["status"]
    assert not list((tmp_path / "out").glob("*/*/0*_*"))      # không xuất gì
    assert r.calls.count("director") >= 3                    # 1 lần đầu + 2 vòng sửa


def test_qa_says_pass_but_score_below_8_is_blocked_by_code(tmp_path):
    r = FakeRunner(qa=[{"verdict": "pass", "score": 7.5, "flags": []}] * 30)
    res, *_ = run(tmp_path, r, flow(daily_quota=1), concurrency=1)
    assert res["passed"] == 0 and not list((tmp_path / "out").glob("*/*/0*_*"))


def test_invalid_script_never_exported_even_if_qa_would_pass(tmp_path):
    broken = make_doc(); broken["segments"][0]["scenes"][1]["start_sec"] += 5   # hở thời gian
    r = FakeRunner(director_doc=broken)
    res, *_ = run(tmp_path, r, flow(daily_quota=1), concurrency=1)
    assert res["passed"] == 0 and "editor-in-chief" not in r.calls   # QA còn không được gọi
    assert not list((tmp_path / "out").glob("*/*/0*_*"))


def test_budget_cap_stops_safely_and_still_reports(tmp_path):
    r = FakeRunner(cost=3.0)
    res, p, store = run(tmp_path, r, flow(max_cost_usd_per_day=8), concurrency=1)
    assert "hết ngân sách" in res["status"]
    assert store.spent_today("suckhoe-yt-sang", TODAY) < 8 + 3.0 + 1e-9      # dừng ngay sau khi chạm trần
    assert (tmp_path / "out" / "2026-10-01" / "suckhoe-yt-sang" / "_BAO_CAO_NGAY.md").exists()


def test_one_scout_failing_does_not_stop_pipeline(tmp_path):
    r = FakeRunner(fail={"news-scout"})
    res, p, _ = run(tmp_path, r)
    assert res["passed"] == 3 and any("news-scout" in e for e in p.errors)


def test_failed_story_releases_topic_for_reuse(tmp_path):
    store = Store(tmp_path / "t.db")
    store.claim_topic("suckhoe-yt-sang", "Đề tài 0", today=TODAY)
    r = FakeRunner(qa=[{"verdict": "reject", "score": 4, "flags": []}])
    run(tmp_path, r, flow(daily_quota=1), store=store, concurrency=1)
    assert store.claim_topic("suckhoe-yt-sang", "Đề tài 0", today=TODAY) is True   # đã được nhả khoá


def test_koc_flow_writes_koc_prompts(tmp_path):
    kdoc = make_doc(koc=True)
    kdoc["koc"]["character_id"] = "KOC-02-THAO"
    for seg in kdoc["segments"]:
        for sc in seg["scenes"]:
            if sc["visual"]["type"] == "koc":
                sc["visual"]["koc"]["dialogue_vi"] = "Xin chào các bạn."
    class KocRunner(FakeRunner):
        async def run(self, agent, prompt, **kw):
            if agent.name == "koc-character-director":
                self.calls.append(agent.name)
                return AgentResult(json.dumps({"script": kdoc}, ensure_ascii=False), cost_usd=0.1)
            if agent.name == "director":
                self.calls.append(agent.name)
                return AgentResult(json.dumps({"script": make_doc(), "script_md": "#"}), cost_usd=0.1)
            return await super().run(agent, prompt, **kw)
    f = flow(daily_quota=1, koc={"enabled": True, "character_id": "KOC-02-THAO"})
    res, *_ = run(tmp_path, KocRunner(), f, concurrency=1)
    assert res["passed"] == 1
    folder = next((tmp_path / "out").glob("*/*/01_*"))
    data = json.loads((folder / "koc_prompts.json").read_text(encoding="utf-8"))
    assert data["character_id"] == "KOC-02-THAO" and data["scenes"]


def test_hanging_scout_times_out_and_pipeline_continues(tmp_path):
    class Hang(FakeRunner):
        async def run(self, agent, prompt, **kw):
            if agent.name == "community-scout":
                await asyncio.sleep(30)           # treo
            return await super().run(agent, prompt, **kw)
    store = Store(tmp_path / "t.db")
    p = Pipeline(flow(daily_quota=1), load_agents(), Hang(), store, TODAY, tmp_path / "out", concurrency=1,
                 timeout_sec={"scout": 0.2, "default": 30})
    res = asyncio.run(p.run())
    assert res["passed"] == 1 and any("community-scout" in e and "quá" in e for e in p.errors)
