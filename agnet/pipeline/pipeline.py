"""Bộ điều phối (bộ xương, bằng Python): lịch trình, hạn mức, kiểm tra cứng, vòng QA ≤ 2.

Phán đoán (chiến lược, viết, đạo diễn, QA) do agent Claude làm; mọi thứ có thể kiểm bằng code
(thời lượng, schema, trùng đề tài, ngân sách, hợp đồng KOC) đều do code chặn ở đây.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from ..core.models import Flow
from ..core.validate import Issue, has_errors, validate_script
from ..koc.export import write_koc_prompts
from ..storage.db import BudgetExceeded, Store
from .agents import AgentError, AgentResult, AgentRunner, AgentSpec, extract_json
from . import export
from .survey import SurveyResult, gap_hints, read_survey

MAX_QA_ROUNDS = 2          # mục 4 / 9
QA_PASS = 8.0
OVERSAMPLE = 1.5           # mục 6: viết dư để QA loại bớt
# Trần thời gian mỗi lần gọi agent (giây). Scout bị treo không được chặn cả pipeline (mục 14: lỗi một nguồn không dừng).
TIMEOUT_SEC = {"scout": 420, "default": 1200}
SCOUTS = ["trend-scout", "video-platform-scout", "news-scout", "community-scout", "domain-internal-scout"]


@dataclass
class StoryOutcome:
    title: str
    verdict: str            # pass | reject | error
    score: float | None = None
    note: str = ""
    folder: str | None = None


class SurveyEmpty(RuntimeError):
    """Mọi nguồn khảo sát đều rỗng (vd. Gemini không bám nguồn được) — không được bịa thay."""


@dataclass
class Pipeline:
    flow: Flow
    agents: dict[str, AgentSpec]
    runner: AgentRunner
    store: Store
    today: date
    out_root: Path
    concurrency: int = 3
    warm_start: bool = True        # 18.7: một lượt gọi đơn lẻ trước khi bung song song (tránh đua làm mới OAuth token)
    enrich_agents: tuple = ("keyword-miner", "competitor-gap-analyst")   # chạy theo từng đề tài (bật mặc định theo quyết định người dùng)
    timeout_sec: dict = field(default_factory=lambda: dict(TIMEOUT_SEC))
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    errors: list[str] = field(default_factory=list)
    _budget_hit: bool = False

    # ---- gọi agent: trừ ngân sách, dừng cứng khi chạm trần -------------------
    async def call(self, name: str, payload: dict) -> dict | list:
        if self._budget_hit:
            raise BudgetExceeded(self.flow.id, self.store.spent_today(self.flow.id, self.today), self.flow.max_cost_usd_per_day)
        remaining = self.store.remaining(self.flow.id, self.flow.max_cost_usd_per_day, self.today)
        if remaining <= 0:
            self._budget_hit = True
            raise BudgetExceeded(self.flow.id, self.store.spent_today(self.flow.id, self.today), self.flow.max_cost_usd_per_day)
        prompt = json.dumps({"flow": self.flow.model_dump(mode="json"), **payload}, ensure_ascii=False)
        limit = self.timeout_sec["scout" if name in SCOUTS else "default"]
        share = len(SCOUTS) if name in SCOUTS else max(self.concurrency, 1)
        remaining = remaining / share      # các agent song song cùng chia phần còn lại, tránh vượt trần
        try:
            res: AgentResult = await asyncio.wait_for(
                self.runner.run(self.agents[name], prompt, max_budget_usd=remaining), timeout=limit)
        except asyncio.TimeoutError:
            raise AgentError(f"{name}: quá {limit}s không trả kết quả — bỏ qua") from None
        try:
            self.store.charge(self.flow.id, res.cost_usd, cap=self.flow.max_cost_usd_per_day, today=self.today,
                              run_id=self.run_id, tokens=res.tokens, note=name)
        except BudgetExceeded:
            self._budget_hit = True
            raise
        return extract_json(res.text)

    async def enrich(self, story: dict) -> dict:
        """keyword-miner (08) / competitor-gap-analyst (09), tuỳ chọn. Lỗi một agent không dừng kịch bản."""
        out: dict = {}
        for name in self.enrich_agents:
            if name not in self.agents:
                continue
            try:
                res = read_survey(await self.call(name, {"task": "enrich", "story": story}))
            except BudgetExceeded:
                raise
            except (AgentError, ValueError) as e:
                self.errors.append(f"{name}: {e}")
                continue
            out[name] = res.as_dict()
            hints = gap_hints(res.items)
            if hints:
                out["gap_hints"] = hints
        return out

    async def survey(self) -> list[dict]:
        """Chạy các scout (song song tối đa `concurrency`), đọc cả hai dạng đầu ra; lỗi một nguồn không dừng pipeline."""
        sem = asyncio.Semaphore(max(self.concurrency, 1))

        async def one(n):
            async with sem:
                return await self.call(n, {"task": "scout"})

        results: list = []
        names = list(SCOUTS)
        if self.warm_start and names:
            first = names.pop(0)                       # lượt đơn lẻ đầu tiên: làm ấm đăng nhập trước khi song song
            results.append((first, (await asyncio.gather(one(first), return_exceptions=True))[0]))
        rest = await asyncio.gather(*[one(n) for n in names], return_exceptions=True)
        results += list(zip(names, rest))
        out = []
        for n, r in results:
            if isinstance(r, BudgetExceeded):
                raise r
            if isinstance(r, Exception):
                self.errors.append(f"{n}: {r}")          # lỗi một nguồn không dừng pipeline (mục 14)
                continue
            sv: SurveyResult = read_survey(r)
            if not sv.items and sv.reason:
                self.errors.append(f"{n}: {sv.reason}")
            if sv.dropped:
                self.errors.append(f"{n}: bỏ {sv.dropped} mục không phải đối tượng JSON")
            out.append(sv.as_dict(n))
        if not any(o.get("items") for o in out):
            raise SurveyEmpty("khảo sát không thu được mục nào có nguồn — dừng, không viết kịch bản từ dữ liệu trống")
        return out

    # ---- một kịch bản ---------------------------------------------------------
    async def make_script(self, story: dict) -> tuple[StoryOutcome, dict | None, str]:
        title = story["title"]
        try:
            insights = await self.enrich(story)
            plan = await self.call("content-strategist", {"story": story, **({"insights": insights} if insights else {})})
            dossier = await self.call("deep-researcher", {"plan": plan})
            facts = await self.call("fact-checker", {"dossier": dossier})

            summary, written = "", []
            for seg in plan["outline"]:
                part = await self.call("script-writer", {"plan": plan, "segment": seg, "facts": facts,
                                                          "running_summary": summary, "written_so_far": written})
                written.append(part)
                summary = part.get("running_summary", summary)

            direction = await self.call("director", {"plan": plan, "written": written, "facts": facts})
            doc, script_md = direction["script"], direction.get("script_md", "")

            if self.flow.koc.enabled:
                doc = (await self.call("koc-character-director", {"script": doc}))["script"]
            pack = await self.call("hook-packaging", {"plan": plan, "script": doc, "facts": facts})
            doc["packaging"] = {**pack.get("packaging", pack), "ai_disclosure": bool(
                doc.get("koc", {}).get("enabled") or pack.get("packaging", pack).get("ai_disclosure"))}
            if "hook_variants" in pack:
                doc["hook_variants"] = pack["hook_variants"]

            for round_no in range(MAX_QA_ROUNDS + 1):
                issues = validate_script(doc, self.flow)
                if has_errors(issues):
                    verdict = {"verdict": "revise", "score": 0, "fixes": [{"scene": i.path, "issue": i.message, "fix": ""} for i in issues if i.severity == "error"]}
                else:
                    verdict = await self.call("editor-in-chief", {"script": doc, "plan": plan, "facts": facts})
                    doc["qa"] = {"score": float(verdict["score"]), "flags": verdict.get("flags", []),
                                 "human_review_required": bool(self.flow.sensitive or self.flow.human_review or verdict.get("flags"))}
                    issues = validate_script(doc, self.flow)
                    if verdict["verdict"] == "pass" and not has_errors(issues):
                        return StoryOutcome(title, "pass", doc["qa"]["score"]), doc, script_md
                    if verdict["verdict"] == "reject":
                        return StoryOutcome(title, "reject", float(verdict["score"]), "QA loại"), None, ""
                if round_no == MAX_QA_ROUNDS:
                    break
                revised = await self.call("director", {"plan": plan, "script": doc, "fixes": verdict.get("fixes", []), "facts": facts})
                doc, script_md = revised["script"], revised.get("script_md", script_md)
                doc["packaging"] = doc.get("packaging") or {**pack.get("packaging", pack), "ai_disclosure": bool(doc.get("koc", {}).get("enabled"))}
            note = "; ".join(str(i) for i in issues if i.severity == "error")[:200] or "không đạt QA sau 2 vòng"
            return StoryOutcome(title, "reject", None, note), None, ""
        except BudgetExceeded:
            raise
        except (AgentError, KeyError, TypeError, ValueError) as e:
            return StoryOutcome(title, "error", None, f"{type(e).__name__}: {e}"[:200]), None, ""

    # ---- cả luồng -------------------------------------------------------------
    async def run(self) -> dict:
        day = self.today.isoformat()
        self.store.start_run(self.run_id, self.flow.id, self.today)
        outcomes: list[StoryOutcome] = []
        status = "ok"
        try:
            items = await self.survey()
            clusters = await self.call("dedup-cluster", {"scouts": items})
            ranked = await self.call("trend-scorer", {"stories": clusters["stories"],
                                                       "take": int(self.flow.daily_quota * OVERSAMPLE + 0.999)})
            queue = list(ranked["ranked"])
            passed = 0
            index = 0

            async def work(story):
                nonlocal passed, index
                outcome, doc, md = await self.make_script(story)
                if outcome.verdict == "pass" and passed < self.flow.daily_quota:
                    passed += 1
                    index += 1
                    outcome.folder = str(export.write_script_folder(doc, md, self.out_root, day, index))
                    if doc.get("koc", {}).get("enabled"):
                        write_koc_prompts(doc, outcome.folder)
                else:
                    if outcome.verdict == "pass":
                        outcome.verdict, outcome.note = "reject", "vượt quota"
                    self.store.release_topic(self.flow.id, story["title"], today=self.today)
                outcomes.append(outcome)

            running: set[asyncio.Task] = set()
            try:
                while (queue or running) and not self._budget_hit:
                    # chỉ khởi động thêm khi còn thiếu: đã đạt + đang chạy < quota (không viết dư tốn tiền)
                    while queue and passed + len(running) < self.flow.daily_quota and len(running) < self.concurrency:
                        running.add(asyncio.create_task(work(queue.pop(0))))
                    if not running:
                        break
                    done, running = await asyncio.wait(running, return_when=asyncio.FIRST_COMPLETED)
                    for t in done:
                        if t.exception():
                            raise t.exception()
                    if passed >= self.flow.daily_quota:
                        break
            finally:
                for t in running:
                    t.cancel()
                if running:
                    await asyncio.gather(*running, return_exceptions=True)
            if passed < self.flow.daily_quota:
                status = f"thiếu sản lượng: {passed}/{self.flow.daily_quota} (không hạ ngưỡng QA)"
        except BudgetExceeded as e:
            status = f"dừng vì hết ngân sách: {e}"
        except SurveyEmpty as e:
            status = f"dừng: {e}"
        self.errors.extend(w for w in getattr(self.runner, "warnings", []) if w not in self.errors)
        spent = self.store.spent_today(self.flow.id, self.today)
        report = export.daily_report(self.flow.id, day, [o.__dict__ for o in outcomes], spent, status, self.errors)
        rdir = Path(self.out_root) / day / self.flow.id
        rdir.mkdir(parents=True, exist_ok=True)
        (rdir / "_BAO_CAO_NGAY.md").write_text(report, encoding="utf-8")
        self.store.finish_run(self.run_id, status)
        return {"status": status, "passed": sum(o.verdict == "pass" for o in outcomes), "outcomes": outcomes, "spent": spent}
