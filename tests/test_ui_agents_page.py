"""Trang Đội agent: dùng bản sao thư mục agent trong thư mục tạm, KHÔNG đụng .claude/agents thật."""
from __future__ import annotations

import os
import shutil

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6", reason="chưa cài PySide6")

from PySide6.QtWidgets import QApplication      # noqa: E402

from agnet.pipeline.agents import AGENT_DIR, load_agents     # noqa: E402
from agnet.ui import i18n                       # noqa: E402
from agnet.ui import page_agents as PA          # noqa: E402

app = QApplication.instance() or QApplication([])


@pytest.fixture
def page(tmp_path):
    d = tmp_path / "agents"
    shutil.copytree(AGENT_DIR, d)
    return PA.AgentsPage(d), d


def row_of(p, name):
    return next(i for i, r in enumerate(p._rows) if r.name == name)


def test_hien_17_agent_va_khong_canh_bao(page):
    p, _ = page
    assert p.table.rowCount() == 17 and p.table.item(0, 1).text() == "trend-scout"
    assert p.table.item(0, 2).text() == "Tầng 1" and "WebSearch" in p.table.item(0, 5).text()
    assert not p.warn.isVisible() and not p.warn.text()


def test_agent_khong_khao_sat_khoa_gemini(page):
    p, _ = page
    eng = p.table.cellWidget(row_of(p, "script-writer"), 3)
    assert not eng.model().item(1).isEnabled()
    eng2 = p.table.cellWidget(row_of(p, "news-scout"), 3)
    assert eng2.model().item(1).isEnabled()


def test_sua_model_chi_doi_dung_dong_va_hoan_tac(page):
    p, d = page
    f = next(d.glob("13-*.md"))
    before = f.read_text(encoding="utf-8")
    p.table.cellWidget(row_of(p, "script-writer"), 4).setCurrentIndex(PA.MODELS.index("opus"))
    p.save()
    after = f.read_text(encoding="utf-8")
    assert "model: opus" in after and "model: sonnet" not in after
    diff = [(a, b) for a, b in zip(before.split("\n"), after.split("\n")) if a != b]
    assert len(diff) == 1 and diff[0] == ("model: sonnet", "model: opus")
    assert load_agents(d)["script-writer"].model == "opus"
    assert p.btn_undo.isEnabled()
    p.undo()
    assert f.read_text(encoding="utf-8") == before and not p.btn_undo.isEnabled()
    assert not list(d.glob(".agent-*"))


def test_doi_engine_gemini_cho_agent_khao_sat(page):
    p, d = page
    i = row_of(p, "keyword-miner")
    p.table.cellWidget(i, 3).setCurrentIndex(0)           # claude
    p.save()
    assert "engine: claude" in next(d.glob("08-*.md")).read_text(encoding="utf-8")


def test_chan_gemini_cho_agent_khong_khao_sat(page):
    p, d = page
    f = next(d.glob("13-*.md"))
    before = f.read_text(encoding="utf-8")
    p.table.cellWidget(row_of(p, "script-writer"), 3).model().item(1).setEnabled(True)   # giả lập ép
    p.table.cellWidget(row_of(p, "script-writer"), 3).setCurrentIndex(1)
    p.save()
    assert f.read_text(encoding="utf-8") == before and "chỉ agent khảo sát" in p.msg.text()


def test_khong_doi_tools_va_set_field_khong_cham_tools():
    text = "---\nname: x\nmodel: haiku\ntools: Read\n---\nthân\n"
    out = PA.set_field(PA.set_field(text, "model", "opus"), "engine", "claude")
    assert "tools: Read" in out and out.endswith("---\nthân\n") and "engine: claude" in out


def test_tu_hoan_tac_khi_load_agents_loi(page, monkeypatch):
    p, d = page
    f = next(d.glob("13-*.md"))
    before = f.read_text(encoding="utf-8")

    def boom(_d):
        raise PA.AgentError("hỏng") if hasattr(PA, "AgentError") else RuntimeError("hỏng")
    monkeypatch.setattr(PA, "load_agents", boom)
    p.table.cellWidget(row_of(p, "script-writer"), 4).setCurrentIndex(2)
    p.save()
    assert f.read_text(encoding="utf-8") == before and "tự hoàn tác" in p.msg.text()


def test_canh_bao_thieu_qa_va_quyen_ghi(tmp_path):
    d = tmp_path / "a"
    shutil.copytree(AGENT_DIR, d)
    next(d.glob("16-*.md")).unlink()
    f = next(d.glob("13-*.md"))
    f.write_text(f.read_text(encoding="utf-8").replace("tools: Read, Bash", "tools: Read, Write"), encoding="utf-8")
    p = PA.AgentsPage(d)
    t = p.warn.text()
    assert "Thiếu bước QA" in t and "Write" in t


def test_dich_tieng_anh(page):
    p, _ = page
    i18n.apply(p, "en")
    assert p.btn_undo.text() == "Undo" and p.table.horizontalHeaderItem(1).text() == "Name"
