"""Báo kết quả mỗi lần chạy: Telegram + webhook của luồng (mục 11.3).

Thiết kế: KHÔNG BAO GIỜ ném lỗi ra ngoài — gửi tin thất bại không được làm sập lịch chạy.
Token lấy từ môi trường, không nằm trong code và không vào log.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol

log = logging.getLogger("agnet.notify")
TIMEOUT = 20


class Transport(Protocol):
    def post(self, url: str, payload: dict) -> int: ...


class HttpTransport:
    def post(self, url: str, payload: dict) -> int:
        req = urllib.request.Request(
            url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:   # nosec - URL do người dùng tự cấu hình
            return int(r.status)


def _fmt_usd(x: float) -> str:
    return f"${x:.2f}"


def format_run(flow_id: str, day: str, result: dict | None, error: str | None = None) -> str:
    """Tóm tắt một lần chạy, đủ đọc trên điện thoại."""
    if error:
        return f"❌ Agnet · {flow_id} · {day}\nLỗi: {error[:400]}"
    passed = int(result.get("passed", 0))
    quota = int(result.get("quota", 0) or 0)
    spent = float(result.get("spent", 0.0))
    status = str(result.get("status", "")) or "ok"
    icon = "✅" if quota and passed >= quota else ("⚠️" if passed else "❌")
    lines = [f"{icon} Agnet · {flow_id} · {day}",
             f"Kịch bản đạt: {passed}" + (f"/{quota}" if quota else ""),
             f"Chi phí: {_fmt_usd(spent)}",
             f"Trạng thái: {status}"]
    if result.get("folder"):
        lines.append(f"Thư mục: {result['folder']}")
    if result.get("human_review"):
        lines.append("⚠️ Cần người kiểm duyệt trước khi dùng (luồng sensitive/human_review).")
    errs = result.get("errors") or []
    if errs:
        lines.append("Nguồn lỗi: " + "; ".join(str(e)[:80] for e in errs[:4]))
    return "\n".join(lines)


@dataclass
class Notifier:
    transport: Transport | None = None
    env: dict | None = None

    def _env(self, key: str) -> str | None:
        src = self.env if self.env is not None else os.environ
        v = (src.get(key) or "").strip()
        return v or None

    def _tx(self) -> Transport:
        return self.transport or HttpTransport()

    def telegram(self, text: str) -> bool:
        token, chat = self._env("TELEGRAM_BOT_TOKEN"), self._env("TELEGRAM_CHAT_ID")
        if not token or not chat:
            log.warning("bỏ qua Telegram: chưa đặt %s",
                        ", ".join(k for k, v in (("TELEGRAM_BOT_TOKEN", token), ("TELEGRAM_CHAT_ID", chat)) if not v))
            return False
        try:
            st = self._tx().post(f"https://api.telegram.org/bot{token}/sendMessage",
                                 {"chat_id": chat, "text": text, "disable_web_page_preview": True})
            log.info("Telegram: đã gửi (HTTP %s)", st)
            return True
        except (urllib.error.URLError, OSError, ValueError) as e:
            log.warning("Telegram thất bại: %s", type(e).__name__)
            return False

    def webhook(self, url: str, payload: dict) -> bool:
        try:
            st = self._tx().post(url, payload)
            log.info("Webhook: đã gửi (HTTP %s)", st)
            return True
        except (urllib.error.URLError, OSError, ValueError) as e:
            log.warning("Webhook thất bại: %s", type(e).__name__)
            return False

    def run_finished(self, flow, day: str, result: dict | None, error: str | None = None) -> None:
        """Gửi theo cấu hình luồng: notify chứa 'telegram' và/hoặc webhook_url. Không ném lỗi."""
        channels = [c.lower() for c in (getattr(flow, "notify", None) or ["telegram"])]
        text = format_run(flow.id, day, result, error)
        try:
            if "telegram" in channels:
                self.telegram(text)
            url = getattr(flow, "webhook_url", None)
            if url and ("webhook" in channels or not channels):
                self.webhook(url, {"flow_id": flow.id, "day": day, "error": error,
                                   "text": text, "result": _safe(result)})
        except Exception as e:                                    # chốt cuối: tuyệt đối không sập lịch
            log.warning("gửi thông báo thất bại: %s", type(e).__name__)


def _safe(result: dict | None) -> dict:
    if not result:
        return {}
    return {k: v for k, v in result.items() if isinstance(v, (str, int, float, bool, list, dict)) or v is None}
