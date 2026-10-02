"""Trang Gemini: lưu chính sách, probe ca blocked, không treo UI, không lộ khóa. Transport giả, không mạng."""
from __future__ import annotations

import json
import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6", reason="chưa cài PySide6")

from PySide6.QtWidgets import QApplication, QLabel     # noqa: E402

from agnet.core import settings as S                   # noqa: E402
from agnet.gemini.client import GeminiClient           # noqa: E402
from agnet.ui import i18n                              # noqa: E402
from agnet.ui.page_gemini import GeminiPage            # noqa: E402
from agnet.ui.page_settings import SettingsPage        # noqa: E402

KEY = "AIza" + "x" * 35
MODELS = {"models": [{"name": "models/gemini-2.5-pro", "supportedGenerationMethods": ["generateContent"]},
                     {"name": "models/gemini-2.5-flash", "supportedGenerationMethods": ["generateContent"]}]}
OK_BODY = json.dumps({"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}).encode()
QUOTA = b'{"error": {"message": "Quota exceeded, limit: 0"}}'


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def transport(blocked_search=True):
    calls = []

    def tx(method, url, headers, body, timeout):
        calls.append((method, url))
        if method == "GET":
            return 200, json.dumps(MODELS).encode()
        if body and b"google_search" in body and blocked_search:
            return 429, QUOTA
        return 200, OK_BODY
    tx.calls = calls
    return tx


def make(tmp_path, tx, key=KEY, monkeypatch=None):
    env = tmp_path / ".env"
    env.write_text(f"GEMINI_API_KEY={key}\n" if key else "", encoding="utf-8")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    def factory(s):
        return GeminiClient(key, settings=s, cache_path=tmp_path / "cache.json", transport=tx,
                            sleep=lambda _s: None)
    return GeminiPage(tmp_path / "s.json", env, client_factory=factory)


def wait(signal, trigger, ms=5000):
    """Chạy vòng sự kiện tới khi tín hiệu về — chứng tỏ kết quả đến qua tín hiệu chứ không chặn UI."""
    from PySide6.QtCore import QEventLoop, QTimer
    got, loop = [], QEventLoop()
    signal.connect(lambda *a: (got.append(a), loop.quit()))
    QTimer.singleShot(ms, loop.quit)
    trigger()
    returned_immediately = not got            # trigger() trả về trước khi có kết quả
    if not got:
        loop.exec()
    assert got, "quá hạn: tín hiệu không về"
    return got[0], returned_immediately


def all_text(w):
    return " ".join(l.text() for l in w.findChildren(QLabel))


def test_khoa_hien_da_che(qapp, tmp_path, monkeypatch):
    p = make(tmp_path, transport(), monkeypatch=monkeypatch)
    assert KEY not in all_text(p) and p.key_label.text().startswith("AIza") and "•" in p.key_label.text()


def test_khong_co_khoa_khoa_nut(qapp, tmp_path, monkeypatch):
    p = make(tmp_path, transport(), key="", monkeypatch=monkeypatch)
    assert not p.btn_probe.isEnabled() and "Chưa có khóa" in p.key_label.text()


def test_probe_blocked_hien_dung_va_khong_treo(qapp, tmp_path, monkeypatch):
    p = make(tmp_path, transport(True), monkeypatch=monkeypatch)
    (rep,), immediate = wait(p.probe_finished, p.btn_probe.click)
    assert immediate and rep["search"] == "blocked" and rep["plain"] == "ok"
    t = p.probe_out.text()
    assert "BỊ CHẶN" in t and "gói miễn phí" in t and "thanh toán" in t and "Số model: 2" in t
    assert KEY not in t and KEY not in all_text(p)
    assert p.btn_probe.isEnabled()


def test_probe_ok(qapp, tmp_path, monkeypatch):
    p = make(tmp_path, transport(False), monkeypatch=monkeypatch)
    # transport không trả nguồn bám → "no_sources", không được báo là ok
    (rep,), _ = wait(p.probe_finished, p.btn_probe.click)
    assert rep["search"] == "no_sources" and "không trả nguồn" in p.probe_out.text()


def test_tai_lai_model_do_bang_va_nghi(qapp, tmp_path, monkeypatch):
    tx = transport()
    p = make(tmp_path, tx, monkeypatch=monkeypatch)
    (n,), imm = wait(p.table_updated, p.btn_models.click)
    assert imm and n == 2 and p.table.rowCount() == 2
    assert p.table.item(0, 1).text() == "gemini-2.5-pro" and p.table.item(0, 0).text() == "1"
    assert p.table.item(0, 5).text() == "sẵn sàng"
    assert any(m == "GET" for m, _ in tx.calls)


def test_loi_nen_khong_lo_khoa(qapp, tmp_path, monkeypatch):
    def bad(method, url, headers, body, timeout):
        raise RuntimeError(f"hỏng {KEY}")
    p = make(tmp_path, bad, monkeypatch=monkeypatch)
    p.btn_models.setEnabled(True)
    p.reload_models()
    t0 = time.time()
    while p.models_msg.text().startswith("Đang") and time.time() - t0 < 5:
        QApplication.processEvents()
        time.sleep(0.01)
    assert "Không tải được" in p.models_msg.text() and KEY not in p.models_msg.text()


def test_luu_chinh_sach_va_giu_truong_khac(qapp, tmp_path, monkeypatch):
    p = make(tmp_path, transport(), monkeypatch=monkeypatch)
    S.save(S.Settings(language="en", concurrency=5, gemini_provider="gemini_api"), tmp_path / "s.json")
    got = []
    p.changed.connect(got.append)
    p.tier.setCurrentIndex(p.tier.findData("flash-lite"))
    p.auto_update.setChecked(False)
    p.fallback.setChecked(False)
    p.refresh_hours.setValue(500)                     # vượt miền → spinbox chặn ở 168
    p.save()
    s = S.load(tmp_path / "s.json")
    assert (s.gemini_tier, s.gemini_auto_update, s.gemini_fallback, s.gemini_refresh_hours) == \
        ("flash-lite", False, False, 168)
    assert s.language == "en" and s.concurrency == 5 and s.gemini_provider == "gemini_api"
    assert got and got[0].gemini_tier == "flash-lite"


def test_trang_cai_dat_chung_khong_de_chinh_sach_gemini(qapp, tmp_path, monkeypatch):
    from agnet.ui.app import MainWindow
    flows = tmp_path / "flows.yaml"
    flows.write_text('flows:\n  - id: a\n    name: "A"\n    topic: "t"\n    daily_quota: 1\n    schedule: ["0 5 * * *"]\n', encoding="utf-8")
    sp = tmp_path / "s.json"
    S.save(S.Settings(gemini_tier="flash", gemini_fallback=False, gemini_refresh_hours=48), sp)
    w = MainWindow(flows, tmp_path / "a.db", sp, tmp_path / ".env", tmp_path / "out")
    w.general.save()
    s = S.load(sp)
    assert (s.gemini_tier, s.gemini_fallback, s.gemini_refresh_hours) == ("flash", False, 48)
    nav = w.shell.nav
    assert nav.item(3).text() == "Gemini"


def test_dich_tieng_anh(qapp, tmp_path, monkeypatch):
    p = make(tmp_path, transport(), monkeypatch=monkeypatch)
    i18n.apply(p, "en")
    assert p.btn_probe.text() == "Check key" and p.btn_models.text() == "Reload model list"
    assert p.table.horizontalHeaderItem(0).text() == "Order"
    assert p.tier.itemText(0) == "Pro (most capable)" and p.btn_save.text() == "Save policy"
    assert p.refresh_hours.suffix() == "  hours"
