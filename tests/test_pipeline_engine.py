"""Chọn engine, fallback Gemini -> Claude, retry OAuth, song song, bộ đọc khảo sát. Toàn đồ giả — không gọi API."""
from __future__ import annotations

import asyncio
import json
from datetime import date, datetime, timedelta, timezone

import pytest
from agnet.commander import ComplianceStore
from agnet.core import settings as S
from agnet.core.models import Flow
from agnet.gemini.client import AllModelsExhausted, GeminiAuthError, GeminiResult, GroundingUnavailable
from agnet.pipeline.agents import AgentError, AgentResult, AgentSpec, load_agents
from agnet.pipeline.engine import GeminiRunner, RetryingRunner, RoutingRunner, build_runner, is_transient
from agnet.pipeline.pipeline import SCOUTS, Pipeline
from agnet.pipeline.survey import gap_hints, read_survey
from agnet.storage.db import Store
from tests.test_pipeline import FakeRunner

NOW = datetime.now(timezone.utc)      # build_runner dùng đồng hồ thật nên tin mẫu phải mới
URL = "https://vnexpress.net/bai-1"


def spec(name="trend-scout", engine="gemini"):
    return AgentSpec(name, "d", "haiku", [], [], "NHIỆM VỤ SCOUT", engine)


def prompt():
    return json.dumps({"flow": {"id": "f1", "topic": "sức khoẻ"}, "task": "scout"})


class ClaudeStub:
    def __init__(self, text='{"items": []}'):
        self.calls, self.text = [], text

    async def run(self, agent, prompt, *, max_budget_usd):
        self.calls.append(agent.name)
        return AgentResult(self.text, cost_usd=0.1)


class FakeGemini:
    def __init__(self, text=None, exc=None, sources=None):
        self.text, self.exc, self.calls = text, exc, 0
        self.sources = sources if sources is not None else [{"url": URL, "title": "vnexpress.net"}]

    def generate(self, prompt, **kw):
        self.calls += 1
        if self.exc:
            raise self.exc
        return GeminiResult(self.text, "gemini-3.8-flash", sources=self.sources)


GOOD = json.dumps([{"title": "T", "url": URL, "source": "VnExpress", "published_at": (NOW - timedelta(hours=1)).isoformat(),
                    "snippet": "s", "signal": 12, "answered": False}])


def gem(client, tmp_path, claude=None):
    claude = claude or ClaudeStub()
    return GeminiRunner(client, claude, store=ComplianceStore(tmp_path / "c.db"), now=lambda: NOW), claude


# ---- AgentSpec.engine --------------------------------------------------------------------------------
def test_agent_files_doc_engine():
    ag = load_agents()
    assert ag["trend-scout"].engine == "gemini" and ag["director"].engine == "claude"


# ---- chọn runner -------------------------------------------------------------------------------------
def run(coro):
    return asyncio.run(coro)


def test_provider_off_moi_agent_chay_claude(tmp_path):
    claude = ClaudeStub()
    r = build_runner(S.Settings(gemini_provider="off"), claude=claude, db=str(tmp_path / "a.db"), api_key="k",
                     client_factory=lambda k, s: pytest.fail("không được tạo client"))
    assert r.gemini is None
    run(r.run(spec(), prompt(), max_budget_usd=1))
    assert claude.calls == ["trend-scout"]


def test_provider_bat_dinh_tuyen_theo_engine(tmp_path):
    claude, g = ClaudeStub(), FakeGemini(GOOD)
    r = build_runner(S.Settings(gemini_provider="gemini_api"), claude=claude, db=str(tmp_path / "a.db"),
                     api_key="k", client_factory=lambda k, s: g)
    res = run(r.run(spec(engine="gemini"), prompt(), max_budget_usd=1))
    assert g.calls == 1 and claude.calls == []
    data = json.loads(res.text)
    assert data["items"][0]["url"] == URL and data["items"][0]["signal"] == 12      # khoá mở rộng được giữ
    run(r.run(spec("director", "claude"), "{}", max_budget_usd=1))
    assert claude.calls == ["director"] and g.calls == 1


def test_thieu_khoa_chay_claude_va_canh_bao(tmp_path):
    claude = ClaudeStub()

    def factory(k, s):
        raise GeminiAuthError("thiếu GEMINI_API_KEY")
    r = build_runner(S.Settings(gemini_provider="gemini_api"), claude=claude, db=str(tmp_path / "a.db"),
                     api_key="", client_factory=factory)
    assert r.gemini is None and any("khoá" in w for w in r.warnings)
    run(r.run(spec(), prompt(), max_budget_usd=1))
    assert claude.calls == ["trend-scout"]


def test_provider_cli_chua_ho_tro_chay_claude(tmp_path):
    r = build_runner(S.Settings(gemini_provider="gemini_cli"), claude=ClaudeStub(), db=str(tmp_path / "a.db"))
    assert r.gemini is None and r.warnings


# ---- fallback ----------------------------------------------------------------------------------------
@pytest.mark.parametrize("exc", [GroundingUnavailable("429 search"), AllModelsExhausted("hết", []),
                                 GeminiAuthError("khoá sai")])
def test_gemini_loi_thi_chuyen_sang_claude(tmp_path, exc):
    runner, claude = gem(FakeGemini(exc=exc), tmp_path)
    res = run(runner.run(spec(), prompt(), max_budget_usd=1))
    assert claude.calls == ["trend-scout"] and res.cost_usd == 0.1
    assert any("chuyển sang Claude" in w for w in runner.warnings)


def test_sai_hop_dong_khong_bia_thay(tmp_path):
    runner, claude = gem(FakeGemini('[{"title":"x"}]'), tmp_path)
    res = run(runner.run(spec(), prompt(), max_budget_usd=1))
    data = json.loads(res.text)
    assert data["items"] == [] and data["reason"].startswith("compliance_fail")
    assert claude.calls == []


def test_ghi_compliance_store(tmp_path):
    runner, _ = gem(FakeGemini(GOOD), tmp_path)
    run(runner.run(spec(), prompt(), max_budget_usd=1))
    runner2, _ = gem(FakeGemini('[{"title":"x"}]'), tmp_path)
    run(runner2.run(spec(), prompt(), max_budget_usd=1))
    rates = ComplianceStore(tmp_path / "c.db").rates()["trend-scout"]
    assert rates["runs"] == 2 and rates["passed"] == 1 and rates["failed"] == 1


def test_loi_goi_khong_ghi_compliance(tmp_path):
    runner, _ = gem(FakeGemini(exc=GroundingUnavailable("x")), tmp_path)
    run(runner.run(spec(), prompt(), max_budget_usd=1))
    assert ComplianceStore(tmp_path / "c.db").rates() == {}


# ---- retry -------------------------------------------------------------------------------------------
class Flaky:
    def __init__(self, fails, msg):
        self.fails, self.msg, self.n = fails, msg, 0

    async def run(self, agent, prompt, *, max_budget_usd):
        self.n += 1
        if self.n <= self.fails:
            raise AgentError(self.msg)
        return AgentResult("{}")


OAUTH = "Failed to refresh OAuth token: another Claude Code process is refreshing it"


def test_retry_oauth_lui_dan():
    sleeps = []

    async def fake_sleep(d):
        sleeps.append(d)
    f = Flaky(2, OAUTH)
    r = RetryingRunner(f, attempts=4, base_delay=1, sleep=fake_sleep)
    assert run(r.run(spec(), "{}", max_budget_usd=1)).text == "{}"
    assert f.n == 3 and len(sleeps) == 2 and sleeps[1] > sleeps[0] * 1.2 - 1e-9 and r.warnings


def test_retry_het_luot_thi_bao_loi():
    async def nosleep(d):
        pass
    f = Flaky(99, OAUTH)
    with pytest.raises(AgentError, match="hết 3 lần"):
        run(RetryingRunner(f, attempts=3, sleep=nosleep).run(spec(), "{}", max_budget_usd=1))
    assert f.n == 3


def test_loi_khong_tam_thoi_khong_thu_lai():
    f = Flaky(99, "agent trả JSON sai")
    with pytest.raises(AgentError):
        run(RetryingRunner(f, sleep=lambda d: None).run(spec(), "{}", max_budget_usd=1))
    assert f.n == 1 and not is_transient(AgentError("x"))


# ---- pipeline: khởi động ấm + song song --------------------------------------------------------------
def _flow():
    return Flow(id="f1", name="t", topic="t", schedule=["0 5 * * *"], daily_quota=1, sensitive=False,
                max_cost_usd_per_day=100)


class Tracking(FakeRunner):
    def __init__(self):
        super().__init__()
        self.live = self.peak = 0
        self.order = []

    async def run(self, agent, prompt, *, max_budget_usd):
        if agent.name in SCOUTS:
            self.order.append(("start", agent.name, self.live))
            self.live += 1
            self.peak = max(self.peak, self.live)
            await asyncio.sleep(0.02)
            self.live -= 1
        return await super().run(agent, prompt, max_budget_usd=max_budget_usd)


def test_khoi_dong_am_scout_dau_chay_don_le(tmp_path):
    r = Tracking()
    p = Pipeline(_flow(), load_agents(), r, Store(tmp_path / "t.db"), date(2026, 10, 2), tmp_path / "o", concurrency=8)
    asyncio.run(p.survey())
    assert r.order[0][2] == 0 and r.order[1][2] == 0 and r.peak >= 2      # đơn lẻ trước, rồi mới song song


def test_scout_ton_trong_concurrency(tmp_path):
    r = Tracking()
    p = Pipeline(_flow(), load_agents(), r, Store(tmp_path / "t.db"), date(2026, 10, 2), tmp_path / "o", concurrency=2)
    asyncio.run(p.survey())
    assert r.peak <= 2


def test_canh_bao_runner_vao_bao_cao(tmp_path):
    r = Tracking()
    r.warnings = ["cảnh báo thử"]
    p = Pipeline(_flow(), load_agents(), r, Store(tmp_path / "t.db"), date(2026, 10, 2), tmp_path / "o")
    asyncio.run(p.run())
    assert "cảnh báo thử" in p.errors


# ---- bộ đọc khảo sát ---------------------------------------------------------------------------------
def test_doc_mang_thuan_va_dang_boc():
    item = {"title": "a", "signal": 3}
    assert read_survey([item]).items == [item]
    r = read_survey({"items": [item, "rác"], "reason": "thiếu nguồn X"})
    assert r.items == [item] and r.reason == "thiếu nguồn X" and r.dropped == 1
    assert read_survey({"questions": [item]}).items == [item]          # dạng cũ
    assert read_survey({"items": [], "reason": "no_search_tool: 429"}).no_search_tool
    assert read_survey("rác").items == [] and read_survey({"x": 1}).reason


def test_gap_hints_toi_da_3():
    items = [{"gap_hint": f"h{i}"} for i in range(5)] + [{"gap_hint": "h0"}, {"gap_hint": ["z"]}]
    assert gap_hints(items) == ["h0", "h1", "h2"]


def test_pipeline_nhan_scout_mang_thuan_va_ghi_reason(tmp_path):
    class R(FakeRunner):
        async def run(self, agent, prompt, *, max_budget_usd):
            if agent.name == "news-scout":
                return AgentResult(json.dumps({"items": [], "reason": "no_search_tool: 429"}))
            if agent.name == "trend-scout":
                return AgentResult(json.dumps([{"title": "a", "signal": 1}]))
            return await super().run(agent, prompt, max_budget_usd=max_budget_usd)
    p = Pipeline(_flow(), load_agents(), R(), Store(tmp_path / "t.db"), date(2026, 10, 2), tmp_path / "o")
    out = asyncio.run(p.survey())
    assert out[0]["items"] == [{"title": "a", "signal": 1}]
    assert any("news-scout" in e and "no_search_tool" in e for e in p.errors)
