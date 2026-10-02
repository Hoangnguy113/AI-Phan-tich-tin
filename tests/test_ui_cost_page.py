"""Trang Chi phí: số liệu từ cost_ledger, lần chạy dừng vì trần, model nghỉ, sửa trần giữ nguyên trường khác."""
from __future__ import annotations

import json
import os
import shutil
import time
from datetime import date

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6", reason="chưa cài PySide6")
from PySide6.QtWidgets import QApplication  # noqa: E402

from agnet.core.models import load_flows  # noqa: E402
from agnet.koc.master_prompt import ROOT  # noqa: E402
from agnet.storage.db import Store  # noqa: E402
from agnet.ui import page_cost as C  # noqa: E402

TODAY = date(2026, 10, 2)


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def env(tmp_path):
    f = tmp_path / "flows.yaml"
    shutil.copy(ROOT / "config" / "flows.yaml", f)
    return f, tmp_path / "t.db", tmp_path / "gem.json"


def test_no_data_shows_chua_co(qapp, env):
    f, db, g = env
    pg = C.CostPage(f, db, g, today=TODAY)
    assert pg.table.item(0, 1).text() == "chưa có" and "chưa có" in pg.summary.text()
    assert "Chưa có dữ liệu model" in pg.cool_note.text()
    assert not db.exists()                                   # không tự tạo DB


def test_numbers_capped_and_cooldowns(qapp, env):
    f, db, g = env
    fid = load_flows(f)[0].id
    cap = load_flows(f)[0].max_cost_usd_per_day
    s = Store(db)
    s.start_run("r1", fid, TODAY)
    s.charge(fid, 0.25, cap=cap, today=TODAY, run_id="r1")
    s.finish_run("r1", "dừng vì hết ngân sách: x")
    g.write_text(json.dumps({"cooldowns": {"gemini-2.5-pro": time.time() + 600, "old": time.time() - 5}}))
    pg = C.CostPage(f, db, g, today=TODAY)
    assert pg.table.item(0, 1).text() == "$0.25"
    assert pg.table.item(0, 3).text() == f"{0.25 / cap * 100:.0f}%"
    assert "$0.25" in pg.summary.text() and "(7 ngày): 1" in pg.summary.text()
    assert pg.cool.rowCount() == 1 and pg.cool.item(0, 0).text() == "gemini-2.5-pro"


def test_edit_cap_only_that_field(qapp, env):
    f, db, g = env
    before = load_flows(f)[0]
    pg = C.CostPage(f, db, g, today=TODAY)
    pg.table.selectRow(0)
    pg.cap.setValue(2.5)
    pg.save_cap()
    after = load_flows(f)[0]
    assert after.max_cost_usd_per_day == 2.5
    assert after.model_dump() == {**before.model_dump(), "max_cost_usd_per_day": 2.5}
    assert "max_cost_usd_per_day: 2.5" in f.read_text(encoding="utf-8")


def test_corrupt_cache_ignored(tmp_path):
    p = tmp_path / "g.json"
    p.write_text("{not json")
    assert C.read_cooldowns(p) == []
