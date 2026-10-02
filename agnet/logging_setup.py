"""Ghi log cho lần chạy không người trông (mục 11/14).

Một file mỗi ngày trong `logs/`, cộng thêm ra màn hình. Không bao giờ in giá trị biến môi
trường: thông báo lỗi chỉ nói TÊN khoá bị thiếu.
"""
from __future__ import annotations

import logging
import os
import re
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

FMT = "%(asctime)s %(levelname)-7s %(name)-18s %(message)s"
SECRET_KEYS = ("ANTHROPIC_API_KEY", "YOUTUBE_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")


class RedactSecrets(logging.Filter):
    """Chốt an toàn cuối: nếu một khoá lọt vào log, thay bằng ***."""

    def filter(self, record: logging.LogRecord) -> bool:
        vals = [v for k in SECRET_KEYS if (v := os.environ.get(k)) and len(v) >= 8]
        if vals:
            msg = record.getMessage()
            new = re.sub("|".join(re.escape(v) for v in vals), "***", msg)
            if new != msg:
                record.msg, record.args = new, ()
        return True


def setup(log_dir: Path | str = "logs", level: int = logging.INFO, keep_days: int = 30) -> Path:
    d = Path(log_dir)
    d.mkdir(parents=True, exist_ok=True)
    path = d / "agnet.log"
    root = logging.getLogger()
    root.setLevel(level)
    for h in list(root.handlers):
        root.removeHandler(h)
    fh = TimedRotatingFileHandler(path, when="midnight", backupCount=keep_days, encoding="utf-8")
    fh.suffix = "%Y-%m-%d"
    sh = logging.StreamHandler()
    for h in (fh, sh):
        h.setFormatter(logging.Formatter(FMT))
        h.addFilter(RedactSecrets())
        root.addHandler(h)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    return path
