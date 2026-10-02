"""Giao -> nghiệm thu -> (rớt) gửi lại ĐÚNG MỘT LẦN -> vẫn rớt thì compliance="fail". Không bao giờ bịa dữ liệu thay Gemini."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from ..gemini.client import GeminiError, extract_json
from .acceptance import AcceptReport, accept
from .contract import TaskContract, build_prompt

RETRY_PAUSE_S = 0.0


@dataclass
class RunOutcome:
    compliance: str                                   # "pass" | "fail"
    items: list[dict] = field(default_factory=list)   # CHỈ khi pass; fail thì rỗng (nguồn bị loại khỏi lượt chạy)
    report: AcceptReport | None = None                # báo cáo lần nộp cuối
    attempts: int = 0                                 # số lần giao (1 hoặc 2)
    errors: list[str] = field(default_factory=list)
    model: str = ""
    salvaged: list[dict] = field(default_factory=list)  # mục hợp lệ của lần cuối khi fail — chỉ để hiển thị, không dùng chạy tiếp

    @property
    def passed(self) -> bool:
        return self.compliance == "pass"


def _submit(client, contract: TaskContract, prompt: str):
    """Trả (result, report, errors). Lỗi Gemini -> errors, không ném."""
    try:
        res = client.generate(prompt, search=True, allow_ungrounded=contract.allow_ungrounded)
    except GeminiError as e:
        return None, None, [f"{type(e).__name__}: {e}"]
    return res, None, []


def run_contract(client, contract: TaskContract, now: datetime | None = None,
                 sleep: Callable[[float], None] = time.sleep) -> RunOutcome:
    now = now or datetime.now(timezone.utc)
    errors: list[str] = []
    last_report: AcceptReport | None = None
    model = ""
    for attempt in (1, 2):
        prompt = build_prompt(contract, errors if attempt == 2 else None)
        res, _, call_err = _submit(client, contract, prompt)
        if res is None:
            # Gemini không trả lời được (hết thang, khoá, grounding chặn): gửi lại cũng không sửa được bằng lời nhắc.
            return RunOutcome("fail", report=last_report, attempts=attempt, errors=call_err, model=model)
        model = getattr(res, "model", "") or model
        try:
            data = extract_json(res.text)
            rep = accept(data, contract, res, now)
        except ValueError as e:
            rep = AcceptReport(errors=[f"JSON hỏng: {e}"])
        last_report = rep
        if rep.passed:
            return RunOutcome("pass", items=rep.accepted, report=rep, attempts=attempt, model=model)
        errors = list(rep.errors)
        if attempt == 1:
            sleep(RETRY_PAUSE_S)
    return RunOutcome("fail", report=last_report, attempts=2, errors=errors, model=model,
                      salvaged=list(last_report.accepted) if last_report else [])
