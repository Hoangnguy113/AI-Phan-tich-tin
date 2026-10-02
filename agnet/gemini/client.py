"""Client Gemini REST (khoá Google AI Studio) — chỉ dùng thư viện chuẩn.

Việc làm: (1) tự tải danh sách model và cache; (2) gọi generateContent có bám nguồn Google Search;
(3) lỗi 429 thì model đó "nghỉ" rồi thử model kế trong thang; (4) trả nguồn bám (grounding) để code nghiệm thu.

KHÔNG ép schema JSON (responseSchema) vì chưa kiểm chứng được nó dùng chung với bám nguồn tìm kiếm;
chỉ yêu cầu JSON trong prompt và dùng `extract_json` để bóc.

Chưa kiểm chứng với Google thật (chưa có khoá): định dạng lỗi 429 (retryDelay, PerDay), thời điểm đặt lại
hạn mức ngày (giả định nửa đêm giờ Los Angeles), tên model thật. Mọi thứ được kiểm bằng transport giả.
Khoá chỉ đi qua header, không bao giờ vào URL, log hay thông báo lỗi.
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from ..core.settings import Settings
from .ladder import ModelInfo, build_ladder, parse_model

BASE = "https://generativelanguage.googleapis.com/v1beta"
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE = ROOT / "config" / "gemini_models.json"

# transport(method, url, headers, body|None, timeout) -> (status, body_bytes)
Transport = Callable[[str, str, dict, "bytes | None", float], "tuple[int, bytes]"]


class GeminiError(Exception):
    pass


class GeminiAuthError(GeminiError):
    """Khoá sai/thiếu/bị khoá — hạ model không giải quyết được."""


class AllModelsExhausted(GeminiError):
    """Hết cả thang (hết định mức hoặc lỗi máy chủ). Người gọi nên chuyển sang Claude và ghi cảnh báo."""

    def __init__(self, msg: str, attempts: list[dict]):
        super().__init__(msg)
        self.attempts = attempts


@dataclass
class GeminiResult:
    text: str
    model: str
    sources: list[dict] = field(default_factory=list)     # [{"url", "title"}] từ groundingMetadata
    queries: list[str] = field(default_factory=list)      # các truy vấn tìm kiếm Gemini đã dùng
    attempts: list[dict] = field(default_factory=list)    # [{"model", "outcome"}] — để thấy đã hạ bậc ở đâu
    fell_back: bool = False                               # True nếu không phải model đầu thang


def urllib_transport(method: str, url: str, headers: dict, body: bytes | None, timeout: float):
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read() or b""
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return 0, str(type(e).__name__).encode()          # 0 = lỗi mạng; không kèm URL/khoá


def _redact(s: str, key: str) -> str:
    return s.replace(key, "***") if key else s


def _next_daily_reset(now: float) -> float:
    """Giả định (chưa kiểm chứng): hạn mức ngày đặt lại lúc nửa đêm giờ Los Angeles."""
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("America/Los_Angeles")
    except Exception:
        tz = timezone(timedelta(hours=-8))
    local = datetime.fromtimestamp(now, tz)
    nxt = (local + timedelta(days=1)).replace(hour=0, minute=0, second=5, microsecond=0)
    return nxt.timestamp()


def parse_quota_error(body: bytes, now: float) -> tuple[float, bool]:
    """Từ thân lỗi 429 → (thời điểm model được dùng lại, là hạn mức ngày?). Chịu được thân lạ."""
    text = body.decode("utf-8", "replace")
    daily = bool(re.search(r"PerDay|per day|daily", text, re.I))
    delay = None
    m = re.search(r'"retryDelay"\s*:\s*"([\d.]+)s"', text)
    if m:
        delay = float(m.group(1))
    if daily:
        return _next_daily_reset(now), True
    return now + (delay if delay is not None else 60.0), False


def extract_json(text: str):
    """Bóc JSON từ đầu ra model (có thể bọc ```json ... ```). Không đọc được thì ném ValueError."""
    t = (text or "").strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", t, re.S)
    if m:
        t = m.group(1).strip()
    try:
        return json.loads(t)
    except ValueError:
        pass
    pairs = sorted((("{", "}"), ("[", "]")), key=lambda p: (t.find(p[0]) if p[0] in t else len(t) + 1))
    for open_, close in pairs:
        i, j = t.find(open_), t.rfind(close)
        if i != -1 and j > i:
            try:
                return json.loads(t[i:j + 1])
            except ValueError:
                continue
    raise ValueError("không bóc được JSON từ đầu ra của Gemini")


class GeminiClient:
    def __init__(self, api_key: str, *, settings: Settings | None = None, cache_path: str | Path | None = None,
                 transport: Transport | None = None, clock: Callable[[], float] = time.time,
                 sleep: Callable[[float], None] = time.sleep, timeout: float = 120.0, server_retries: int = 2):
        if not api_key:
            raise GeminiAuthError("thiếu GEMINI_API_KEY")
        self._key = api_key
        self.s = (settings or Settings()).normalized()
        self.cache_path = Path(cache_path or DEFAULT_CACHE)
        self._tx = transport or urllib_transport
        self._now, self._sleep = clock, sleep
        self.timeout, self.server_retries = timeout, server_retries
        self._ladder: list[ModelInfo] | None = None
        self._cool: dict[str, float] = {}                  # model -> thời điểm được dùng lại
        self._load_cache()

    # ---- cache -------------------------------------------------------------------------------------
    def _load_cache(self) -> None:
        self._cache: dict = {}
        try:
            d = json.loads(self.cache_path.read_text(encoding="utf-8"))
            if isinstance(d, dict):
                self._cache = d
                self._cool = {k: float(v) for k, v in (d.get("cooldowns") or {}).items()}
        except (OSError, ValueError, TypeError):
            pass

    def _save_cache(self) -> None:
        d = dict(self._cache)
        d["cooldowns"] = {k: v for k, v in self._cool.items() if v > self._now()}
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.cache_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            tmp.replace(self.cache_path)
        except OSError:
            pass                                           # cache hỏng không được làm sập lượt gọi

    # ---- danh sách model & thang ---------------------------------------------------------------------
    def _headers(self) -> dict:
        return {"x-goog-api-key": self._key, "Content-Type": "application/json"}

    def list_models(self) -> list[str]:
        names, token = [], ""
        for _ in range(20):
            url = f"{BASE}/models?pageSize=200" + (f"&pageToken={token}" if token else "")
            status, body = self._tx("GET", url, self._headers(), None, self.timeout)
            self._raise_auth(status, body)
            if status != 200:
                raise GeminiError(f"liệt kê model lỗi HTTP {status}")
            d = json.loads(body.decode("utf-8"))
            for m in d.get("models", []):
                if "generateContent" in (m.get("supportedGenerationMethods") or ["generateContent"]):
                    names.append(m.get("name", ""))
            token = d.get("nextPageToken") or ""
            if not token:
                break
        return names

    def refresh_models(self, force: bool = False) -> list[ModelInfo]:
        """Tải lại danh sách khi quá hạn (hoặc force). Lỗi mạng thì dùng bản cache cũ — không làm sập."""
        age_ok = (self._now() - float(self._cache.get("fetched_at", 0))) < self.s.gemini_refresh_hours * 3600
        if self._cache.get("models") and age_ok and not force:
            return self._ladder_from(self._cache["models"])
        try:
            names = self.list_models()
        except GeminiAuthError:
            raise
        except (GeminiError, ValueError):
            return self._ladder_from(self._cache.get("models", []))
        self._cache["fetched_at"] = self._now()
        self._cache["models"] = names
        self._save_cache()
        return self._ladder_from(names)

    def _ladder_from(self, names) -> list[ModelInfo]:
        return build_ladder(names, self.s.gemini_tier)

    def ladder(self) -> list[ModelInfo]:
        if self._ladder is None:
            if self.s.gemini_auto_update:
                lad = self.refresh_models()
            else:
                lad = self._ladder_from(self._cache.get("models", []))
            if not self.s.gemini_auto_update or not lad:
                lad = self._pinned_ladder(lad)
            if not self.s.gemini_fallback:
                lad = lad[:1]
            self._ladder = lad
        return self._ladder

    def _pinned_ladder(self, lad: list[ModelInfo]) -> list[ModelInfo]:
        """Ghim tay: model ghim đứng đầu, sau đó là các model đứng SAU nó trong thang (nếu biết thang)."""
        p = parse_model(self.s.gemini_model) or ModelInfo(self.s.gemini_model, (0,), "flash", False)
        names = [m.name for m in lad]
        rest = lad[names.index(p.name) + 1:] if p.name in names else []
        return [p] + rest

    # ---- gọi model ------------------------------------------------------------------------------------
    def _raise_auth(self, status: int, body: bytes) -> None:
        if status in (401, 403) or (status == 400 and b"API key" in body):
            raise GeminiAuthError(f"khoá Gemini bị từ chối (HTTP {status})")

    def generate(self, prompt: str, *, system: str | None = None, search: bool = True,
                 temperature: float | None = None) -> GeminiResult:
        payload: dict = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        if search:
            payload["tools"] = [{"google_search": {}}]
        if temperature is not None:
            payload["generationConfig"] = {"temperature": temperature}
        body = json.dumps(payload).encode("utf-8")

        attempts: list[dict] = []
        lad = self.ladder()
        for idx, m in enumerate(lad):
            if self._cool.get(m.name, 0) > self._now():
                attempts.append({"model": m.name, "outcome": "cooling"})
                continue
            res = self._try_model(m, body, attempts)
            if res is not None:
                res.attempts = attempts
                res.fell_back = idx > 0 or any(a["outcome"] != "ok" for a in attempts)
                return res
        raise AllModelsExhausted("hết thang model Gemini (định mức hoặc lỗi máy chủ)", attempts)

    def _try_model(self, m: ModelInfo, body: bytes, attempts: list[dict]) -> GeminiResult | None:
        url = f"{BASE}/models/{m.name}:generateContent"
        for n in range(self.server_retries + 1):
            status, raw = self._tx("POST", url, self._headers(), body, self.timeout)
            if status == 200:
                try:
                    res = self._parse(m.name, raw)
                except (ValueError, KeyError):
                    attempts.append({"model": m.name, "outcome": "bad_response"})
                    return None
                attempts.append({"model": m.name, "outcome": "ok"})
                return res
            self._raise_auth(status, raw)
            if status == 429:
                until, daily = parse_quota_error(raw, self._now())
                self._cool[m.name] = until
                self._save_cache()
                attempts.append({"model": m.name, "outcome": "quota_daily" if daily else "quota_minute"})
                return None
            if status == 404:
                self._cool[m.name] = self._now() + 24 * 3600
                self._save_cache()
                attempts.append({"model": m.name, "outcome": "not_found"})
                return None
            if status == 0 or status >= 500:                # lỗi mạng/máy chủ: thử lại lùi dần rồi bỏ model
                if n < self.server_retries:
                    self._sleep(2 ** n)
                    continue
                attempts.append({"model": m.name, "outcome": f"server_{status}"})
                return None
            attempts.append({"model": m.name, "outcome": f"http_{status}"})
            return None
        return None

    def _parse(self, model: str, raw: bytes) -> GeminiResult:
        d = json.loads(raw.decode("utf-8"))
        cand = d["candidates"][0]
        text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
        if not text.strip():
            raise ValueError("trả lời rỗng")
        gm = cand.get("groundingMetadata") or {}
        seen, sources = set(), []
        for ch in gm.get("groundingChunks", []):
            web = ch.get("web") or {}
            u = web.get("uri")
            if u and u not in seen:
                seen.add(u)
                sources.append({"url": u, "title": web.get("title", "")})
        return GeminiResult(text=text, model=model, sources=sources, queries=list(gm.get("webSearchQueries", [])))
