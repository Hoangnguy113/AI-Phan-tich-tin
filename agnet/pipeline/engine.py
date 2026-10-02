"""Chọn engine cho từng agent (mục 18): Claude (mặc định) hoặc Gemini qua hợp đồng nhiệm vụ.

- `RetryingRunner`: thử lại lùi dần cho lỗi tạm của Claude (đặc biệt đua làm mới OAuth token).
- `GeminiRunner`: agent engine=gemini chạy qua GeminiClient + run_contract; Gemini hỏng thì CHUYỂN SANG Claude
  (ghi cảnh báo, không dừng pipeline). Gemini trả sai hợp đồng thì KHÔNG bịa thay: trả rỗng kèm lý do.
- `RoutingRunner`/`build_runner`: provider "off" (mặc định) => mọi agent chạy Claude như trước.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
from datetime import datetime, timezone
from typing import Callable

from ..commander import ComplianceStore, TaskContract, run_contract
from ..core import settings as app_settings
from ..gemini.client import GeminiAuthError, GeminiError, extract_json
from .agents import AgentError, AgentResult, AgentRunner, AgentSpec, SdkRunner

log = logging.getLogger("agnet.engine")

TRANSIENT_MARKERS = (
    "failed to refresh oauth token", "another claude code process", "refreshing it",
    "overloaded", "rate limit", "rate_limit", "429", "529", "503", "502", "temporarily",
    "connection reset", "connection error", "econnreset", "timed out", "timeout", "try again",
)


def is_transient(exc: BaseException) -> bool:
    msg = f"{type(exc).__name__}: {exc}".lower()
    return any(m in msg for m in TRANSIENT_MARKERS)


class RetryingRunner:
    """Bọc một runner: lỗi tạm thì chờ lùi dần (có nhiễu ngẫu nhiên để các tiến trình song song không va nhau lần nữa)."""

    def __init__(self, inner: AgentRunner, *, attempts: int = 4, base_delay: float = 5.0, max_delay: float = 60.0,
                 sleep: Callable[[float], "asyncio.Future"] = asyncio.sleep, rng: random.Random | None = None):
        self.inner, self.attempts = inner, max(1, attempts)
        self.base_delay, self.max_delay, self._sleep = base_delay, max_delay, sleep
        self._rng = rng or random.Random()
        self.warnings: list[str] = []

    async def run(self, agent: AgentSpec, prompt: str, *, max_budget_usd: float) -> AgentResult:
        last: Exception | None = None
        for n in range(self.attempts):
            try:
                return await self.inner.run(agent, prompt, max_budget_usd=max_budget_usd)
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001 — chỉ thử lại lỗi tạm, còn lại ném nguyên
                if not is_transient(e):
                    raise
                last = e
                if n == self.attempts - 1:
                    break
                delay = min(self.max_delay, self.base_delay * (2 ** n)) * (1 + self._rng.random() * 0.5)
                msg = f"{agent.name}: lỗi tạm ({str(e)[:120]}), thử lại sau {delay:.1f}s ({n + 1}/{self.attempts - 1})"
                log.warning(msg)
                self.warnings.append(msg)
                await self._sleep(delay)
        raise AgentError(f"{agent.name}: hết {self.attempts} lần thử, lỗi tạm vẫn còn — {last}") from last


class _Recorder:
    """Bọc GeminiClient để biết lượt gọi có THẬT SỰ lỗi (khác với trả lời sai hợp đồng) và lấy văn bản thô."""

    def __init__(self, client):
        self._c, self.exc, self.text = client, None, ""

    def generate(self, *a, **kw):
        try:
            res = self._c.generate(*a, **kw)
        except GeminiError as e:
            self.exc = e
            raise
        self.exc = None
        self.text = getattr(res, "text", "") or ""
        return res


class GeminiRunner:
    """Cùng giao diện AgentRunner. `fallback` là runner Claude."""

    def __init__(self, client, fallback: AgentRunner, *, store: ComplianceStore | None = None,
                 min_items: dict[str, int] | None = None, max_age_hours: float = 48.0,
                 require_grounding: bool = True,
                 now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        self.client, self.fallback, self.store = client, fallback, store
        self.min_items, self.max_age_hours, self._now = min_items or {}, max_age_hours, now
        self.require_grounding = require_grounding
        self.warnings: list[str] = []

    def _warn(self, msg: str) -> None:
        log.warning(msg)
        self.warnings.append(msg)

    async def _fallback(self, agent, prompt, budget, why: str) -> AgentResult:
        if self.require_grounding:
            # BẮT BUỘC bám nguồn: Gemini không bám được thì nguồn này bị LOẠI, không để Claude làm thay.
            reason = f"grounding_required: Gemini không bám nguồn được ({why})"
            self._warn(f"{agent.name}: {reason} — bỏ nguồn này, KHÔNG chuyển sang Claude")
            return AgentResult(json.dumps({"items": [], "reason": reason}, ensure_ascii=False))
        self._warn(f"{agent.name}: Gemini không dùng được ({why}) — chuyển sang Claude")
        return await self.fallback.run(agent, prompt, max_budget_usd=budget)

    @staticmethod
    def _contract(agent: AgentSpec, prompt: str, min_items: int, max_age: float) -> TaskContract:
        try:
            ctx = json.loads(prompt)
        except ValueError:
            ctx = {}
        flow = ctx.get("flow") if isinstance(ctx, dict) and isinstance(ctx.get("flow"), dict) else {}
        extra = {k: v for k, v in ctx.items() if k != "flow"} if isinstance(ctx, dict) else {}
        brief = {k: flow[k] for k in ("topic", "language", "seed_keywords", "exclude_keywords") if k in flow}
        goal = (agent.prompt + "\n\nNGỮ CẢNH LUỒNG: " + json.dumps(brief, ensure_ascii=False)
                + ("\nĐẦU VÀO: " + json.dumps(extra, ensure_ascii=False) if extra else ""))
        return TaskContract(agent=agent.name, flow_id=str(flow.get("id") or "?"), goal=goal,
                            min_items=min_items, max_age_hours=max_age)

    async def run(self, agent: AgentSpec, prompt: str, *, max_budget_usd: float) -> AgentResult:
        contract = self._contract(agent, prompt, self.min_items.get(agent.name, 1), self.max_age_hours)
        rec = _Recorder(self.client)
        try:
            outcome = await asyncio.to_thread(run_contract, rec, contract, self._now())
        except GeminiError as e:                                   # phòng khi run_contract ném thay vì gói
            return await self._fallback(agent, prompt, max_budget_usd, f"{type(e).__name__}: {e}")
        if rec.exc is not None and not outcome.passed:
            return await self._fallback(agent, prompt, max_budget_usd, f"{type(rec.exc).__name__}: {rec.exc}")
        self._record(contract, outcome)
        if not outcome.passed:
            # Gemini trả lời nhưng sai hợp đồng: loại nguồn này, KHÔNG bịa/thay bằng dữ liệu khác (18.5 điểm 4).
            reason = "compliance_fail: " + "; ".join(outcome.errors)[:300]
            self._warn(f"{agent.name}: {reason}")
            return AgentResult(json.dumps({"items": [], "reason": reason}, ensure_ascii=False))
        items = self._restore_extras(outcome.items, rec.text)
        return AgentResult(json.dumps({"items": items, "reason": ""}, ensure_ascii=False))

    def _record(self, contract, outcome) -> None:
        if self.store is None:
            return
        try:
            self.store.record(contract, outcome)
        except Exception as e:  # noqa: BLE001 — đo đạc không được làm hỏng pipeline
            log.warning("không ghi được ComplianceStore: %s", type(e).__name__)

    @staticmethod
    def _restore_extras(accepted: list[dict], text: str) -> list[dict]:
        """Nghiệm thu chỉ giữ 5 khoá RawItem; trả lại các khoá mở rộng (signal, covered...) từ bản gốc theo url."""
        try:
            raw = extract_json(text)
        except ValueError:
            return accepted
        lst = raw.get("items", raw.get("results")) if isinstance(raw, dict) else raw
        by_url = {str(i.get("url", "")).strip(): i for i in (lst or []) if isinstance(i, dict)}
        out = []
        for it in accepted:
            orig = by_url.get(it["url"], {})
            out.append({**{k: v for k, v in orig.items() if k not in it}, **it})
        return out


class RoutingRunner:
    """Agent engine=gemini -> GeminiRunner (nếu có); còn lại -> Claude."""

    def __init__(self, claude: AgentRunner, gemini: GeminiRunner | None = None):
        self.claude, self.gemini = claude, gemini
        self.notes: list[str] = []          # cảnh báo lúc dựng (thiếu khoá, provider chưa hỗ trợ)

    @property
    def warnings(self) -> list[str]:
        return [*self.notes, *getattr(self.claude, "warnings", []), *(self.gemini.warnings if self.gemini else [])]

    async def run(self, agent: AgentSpec, prompt: str, *, max_budget_usd: float) -> AgentResult:
        if self.gemini is not None and agent.engine == "gemini":
            return await self.gemini.run(agent, prompt, max_budget_usd=max_budget_usd)
        return await self.claude.run(agent, prompt, max_budget_usd=max_budget_usd)


def build_runner(settings: app_settings.Settings | None = None, *, claude: AgentRunner | None = None,
                 db: str = "agnet.db", api_key: str | None = None, client_factory=None,
                 retry: bool = True, store: ComplianceStore | None = None) -> RoutingRunner:
    """Provider "off" (mặc định an toàn) => không có GeminiRunner, mọi agent chạy Claude như cũ.
    Thiếu khoá / provider chưa hỗ trợ => cũng chạy Claude, kèm cảnh báo."""
    s = (settings or app_settings.load()).normalized()
    base = claude or SdkRunner()
    if retry and not isinstance(base, RetryingRunner):
        base = RetryingRunner(base)
    router = RoutingRunner(base)
    if s.gemini_provider == "off":
        return router
    if s.gemini_provider != "gemini_api":
        router.notes.append(f"gemini_provider={s.gemini_provider} chưa được hỗ trợ trong pipeline — mọi agent chạy Claude")
        log.warning(router.notes[-1])
        return router
    key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY", "")
    try:
        if client_factory is not None:
            client = client_factory(key, s)
        else:
            from ..gemini.client import GeminiClient
            client = GeminiClient(key, settings=s)
    except GeminiAuthError as e:
        router.notes.append(f"thiếu khoá Gemini ({e}) — mọi agent chạy Claude")
        log.warning(router.notes[-1])
        return router
    router.gemini = GeminiRunner(client, base, store=store or ComplianceStore(db),
                                 require_grounding=s.gemini_require_grounding)
    return router
