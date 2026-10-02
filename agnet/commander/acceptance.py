"""Nghiệm thu BẰNG CODE (mục 18.3). Không gọi LLM, không ước lượng: mục thiếu bằng chứng bị LOẠI."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

from .contract import RAW_ITEM_FIELDS, TaskContract

MAX_FUTURE = timedelta(hours=1)           # lệch đồng hồ nhỏ thì bỏ qua; tương lai xa là bịa


@dataclass
class Rejection:
    item: object
    reason: str            # mã ngắn: schema | url | not_grounded | too_old | bad_date | future | duplicate
    detail: str = ""


@dataclass
class AcceptReport:
    accepted: list[dict] = field(default_factory=list)
    rejected: list[Rejection] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)     # lỗi cấp hợp đồng + tóm tắt lỗi từng mục, đủ cụ thể để gửi lại

    @property
    def passed(self) -> bool:
        return not self.errors


def parse_iso(s: str) -> datetime | None:
    if not isinstance(s, str) or not s.strip():
        return None
    t = s.strip()
    if t.endswith(("Z", "z")):
        t = t[:-1] + "+00:00"
    try:
        d = datetime.fromisoformat(t)
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _host(url: str) -> str:
    try:
        h = (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""
    return h[4:] if h.startswith("www.") else h


def _valid_url(url) -> bool:
    if not isinstance(url, str):
        return False
    try:
        p = urlsplit(url.strip())
    except ValueError:
        return False
    return p.scheme in ("http", "https") and bool(p.hostname) and "." in p.hostname and " " not in url.strip()


def _canon_url(url: str) -> str:
    p = urlsplit(url.strip())
    return f"{(p.hostname or '').lower().removeprefix('www.')}{p.path.rstrip('/')}" + (f"?{p.query}" if p.query else "")


def _norm_title(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower().replace("đ", "d"))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return " ".join(re.findall(r"[a-z0-9]+", t))


def _grounding_index(result) -> tuple[set[str], set[str]]:
    """(url chuẩn hoá, tên miền) từ nguồn bám. Tiêu đề nguồn dạng tên miền (cách Gemini hay trả) cũng được tính là miền."""
    urls, hosts = set(), set()
    for s in (getattr(result, "sources", None) or []):
        u = (s or {}).get("url", "")
        if _valid_url(u):
            urls.add(_canon_url(u))
            hosts.add(_host(u))
        t = ((s or {}).get("title") or "").strip().lower()
        if re.fullmatch(r"(www\.)?[a-z0-9-]+(\.[a-z0-9-]+)+", t):
            hosts.add(t.removeprefix("www."))
    return urls, hosts


def _is_grounded(url: str, urls: set[str], hosts: set[str]) -> bool:
    # Khớp URL đầy đủ, hoặc miền trùng một nguồn bám (Gemini hay trả URL chuyển hướng + tên miền làm title).
    return _canon_url(url) in urls or _host(url) in hosts


def _items_from(raw):
    if isinstance(raw, dict):
        raw = raw.get("items", raw.get("results"))
    return raw if isinstance(raw, list) else None


def accept(items, contract: TaskContract, result, now: datetime) -> AcceptReport:
    """`items`: giá trị JSON đã bóc (list, hoặc dict có khoá items). `result`: GeminiResult (cần .sources)."""
    rep = AcceptReport()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    lst = _items_from(items)
    if lst is None:
        rep.errors.append("đầu ra không phải mảng JSON các mục")
        return rep

    g_urls, g_hosts = _grounding_index(result)
    if not contract.allow_ungrounded and not (g_urls or g_hosts):
        rep.errors.append("không có nguồn bám Google Search (grounding) đi kèm — mọi mục bị loại vì không có bằng chứng")

    seen_url: set[str] = set()
    seen_title: set[str] = set()
    oldest = now - timedelta(hours=contract.max_age_hours)
    for it in lst:
        def rej(reason, detail=""):
            rep.rejected.append(Rejection(it, reason, detail))

        if not isinstance(it, dict):
            rej("schema", "mục không phải đối tượng JSON")
            continue
        bad = [k for k in RAW_ITEM_FIELDS if not isinstance(it.get(k), str) or not it[k].strip()]
        if bad:
            rej("schema", "thiếu/rỗng: " + ", ".join(bad))
            continue
        if not _valid_url(it["url"]):
            rej("url", f"url không hợp lệ (cần http/https): {it['url'][:80]}")
            continue
        if not contract.allow_ungrounded and not _is_grounded(it["url"], g_urls, g_hosts):
            rej("not_grounded", f"url không có trong nguồn bám của Gemini: {it['url'][:80]}")
            continue
        d = parse_iso(it["published_at"])
        if d is None:
            rej("bad_date", f"published_at không phải ISO 8601: {it['published_at'][:40]}")
            continue
        if d > now + MAX_FUTURE:
            rej("future", f"published_at ở tương lai: {it['published_at']}")
            continue
        if d < oldest:
            rej("too_old", f"đăng {it['published_at']}, quá cửa sổ {contract.max_age_hours:g} giờ")
            continue
        cu, nt = _canon_url(it["url"]), _norm_title(it["title"])
        if cu in seen_url or (nt and nt in seen_title):
            rej("duplicate", f"trùng url/tiêu đề: {it['title'][:60]}")
            continue
        seen_url.add(cu)
        seen_title.add(nt)
        rep.accepted.append({k: it[k].strip() for k in RAW_ITEM_FIELDS})

    if rep.rejected:
        counts: dict[str, int] = {}
        for r in rep.rejected:
            counts[r.reason] = counts.get(r.reason, 0) + 1
        for reason, n in counts.items():
            ex = next(r.detail for r in rep.rejected if r.reason == reason)
            rep.errors.append(f"{n} mục bị loại ({reason}), ví dụ: {ex}")
    if len(rep.accepted) < contract.min_items:
        rep.errors.append(f"chỉ có {len(rep.accepted)} mục hợp lệ, hợp đồng đòi tối thiểu {contract.min_items}")
    # Mục bị loại KHÔNG tự làm rớt nếu vẫn đủ số lượng: chỉ giữ lỗi cấp hợp đồng khi chưa đủ.
    if len(rep.accepted) >= contract.min_items and (g_urls or g_hosts or contract.allow_ungrounded):
        rep.errors = []
    return rep
