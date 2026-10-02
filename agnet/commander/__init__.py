"""Chỉ huy (mục 18.3): hợp đồng giao việc cho Gemini + nghiệm thu BẰNG CODE + đo tỉ lệ đạt hợp đồng."""
from .acceptance import AcceptReport, Rejection, accept
from .contract import TaskContract, build_prompt
from .metrics import ComplianceStore
from .runner import RunOutcome, run_contract

__all__ = ["TaskContract", "build_prompt", "accept", "AcceptReport", "Rejection",
           "run_contract", "RunOutcome", "ComplianceStore"]
