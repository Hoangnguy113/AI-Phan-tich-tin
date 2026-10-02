"""Cài đặt chung của ứng dụng (không thuộc về một luồng): ngôn ngữ, chủ đề, số agent song song, Gemini.

Lưu ở config/app_settings.json. Cài đặt THEO LUỒNG (số tin/ngày, giờ chạy, trần chi phí) vẫn ở
flows.yaml. Khoá API KHÔNG bao giờ nằm ở đây — chúng ở .env (xem ui/env_store.py).

File hỏng hoặc thiếu thì dùng mặc định; không bao giờ làm ứng dụng không mở được.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PATH = ROOT / "config" / "app_settings.json"

LANGUAGES = ("vi", "en")
THEMES = ("system", "light", "dark")
GEMINI_PROVIDERS = ("off", "gemini_api", "gemini_cli")
GEMINI_TIERS = ("pro", "flash", "flash-lite")      # bậc ưu tiên; hết định mức thì hạ dần
REFRESH_HOURS_RANGE = (1, 168)
CONCURRENCY_RANGE = (1, 8)


@dataclass
class Settings:
    language: str = "vi"
    theme: str = "system"
    concurrency: int = 3                    # số agent chạy song song (Pipeline.concurrency)
    gemini_provider: str = "off"            # off | gemini_api | gemini_cli
    gemini_model: str = "gemini-2.5-flash"  # model ghim tay; chỉ dùng khi tắt tự cập nhật (chưa kiểm chứng trên máy này)
    gemini_auto_update: bool = True         # tự tải lại danh sách model từ Google để thấy model mới
    gemini_fallback: bool = True            # hết định mức (429) thì xuống model thấp hơn
    gemini_tier: str = "pro"                # bậc muốn dùng trước: pro > flash > flash-lite
    gemini_refresh_hours: int = 24          # bao lâu tải lại danh sách model một lần
    gemini_require_grounding: bool = True   # BẮT BUỘC bám nguồn Google Search cho khảo sát; không bám được thì KHÔNG chuyển sang Claude làm thay

    def normalized(self) -> "Settings":
        """Đưa mọi giá trị về miền hợp lệ — tin tưởng file sửa tay hay giá trị rác đều không vỡ."""
        lo, hi = CONCURRENCY_RANGE
        try:
            conc = int(self.concurrency)
        except (TypeError, ValueError):
            conc = Settings.concurrency
        model = str(self.gemini_model or "").strip() or Settings.gemini_model
        try:
            hrs = int(self.gemini_refresh_hours)
        except (TypeError, ValueError):
            hrs = Settings.gemini_refresh_hours
        rlo, rhi = REFRESH_HOURS_RANGE
        return Settings(
            language=self.language if self.language in LANGUAGES else "vi",
            theme=self.theme if self.theme in THEMES else "system",
            concurrency=max(lo, min(hi, conc)),
            gemini_provider=self.gemini_provider if self.gemini_provider in GEMINI_PROVIDERS else "off",
            gemini_model=model,
            gemini_auto_update=bool(self.gemini_auto_update),
            gemini_fallback=bool(self.gemini_fallback),
            gemini_tier=self.gemini_tier if self.gemini_tier in GEMINI_TIERS else "pro",
            gemini_refresh_hours=max(rlo, min(rhi, hrs)),
            gemini_require_grounding=bool(self.gemini_require_grounding),
        )


def load(path: str | Path | None = None) -> Settings:
    p = Path(path or DEFAULT_PATH)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return Settings()
    if not isinstance(data, dict):
        return Settings()
    known = {f.name for f in fields(Settings)}
    return Settings(**{k: v for k, v in data.items() if k in known}).normalized()


def save(s: Settings, path: str | Path | None = None) -> Settings:
    """Ghi nguyên tử (file tạm → thay thế) để mất điện giữa chừng không để lại file cụt."""
    p = Path(path or DEFAULT_PATH)
    s = s.normalized()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(asdict(s), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(p)
    return s
