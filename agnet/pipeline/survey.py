"""Bộ đọc đầu ra khảo sát (scout 01-05, keyword-miner 08, competitor-gap 09).

Chấp nhận cả hai dạng: mảng RawItem thuần, hoặc {"items":[...],"reason":"..."}. RawItem có thể mở rộng
(signal/answered, kind/intent, covered/missed/gap_hint) — các khoá thêm được GIỮ NGUYÊN cho hạ nguồn.
Không bao giờ bịa: thiếu/hỏng thì trả rỗng kèm lý do.
"""
from __future__ import annotations

from dataclasses import dataclass, field

MAX_GAP_HINTS = 3          # 09: tối đa 3 gợi ý khoảng trống toàn lượt


@dataclass
class SurveyResult:
    items: list[dict] = field(default_factory=list)
    reason: str = ""
    dropped: int = 0                     # mục không phải đối tượng JSON

    @property
    def no_search_tool(self) -> bool:
        return self.reason.startswith("no_search_tool")

    def as_dict(self, source: str = "") -> dict:
        d = {"items": self.items, "reason": self.reason}
        return {"scout": source, **d} if source else d


def read_survey(raw) -> SurveyResult:
    reason = ""
    if isinstance(raw, dict):
        reason = str(raw.get("reason") or "").strip()
        lst = None
        for key in ("items", "questions", "results"):      # "questions": dạng cũ của community-scout
            if isinstance(raw.get(key), list):
                lst = raw[key]
                break
    elif isinstance(raw, list):
        lst = raw
    else:
        return SurveyResult(reason="đầu ra khảo sát không phải mảng/đối tượng JSON")
    if lst is None:
        return SurveyResult(reason=reason or "đầu ra khảo sát không có khoá items")
    items = [i for i in lst if isinstance(i, dict)]
    return SurveyResult(items=items, reason=reason, dropped=len(lst) - len(items))


def gap_hints(items: list[dict], limit: int = MAX_GAP_HINTS) -> list[str]:
    """Gợi ý khoảng trống từ competitor-gap-analyst (trường gap_hint), không trùng, tối đa `limit`."""
    out: list[str] = []
    for it in items:
        h = it.get("gap_hint")
        for x in (h if isinstance(h, list) else [h]):
            if isinstance(x, str) and x.strip() and x.strip() not in out:
                out.append(x.strip())
    return out[:limit]
