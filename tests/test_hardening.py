"""Các lỗi do nhóm kiểm tra (rà mã + bảo mật) tìm ra ngày 02/10/2026 — mỗi lỗi một test chống tái phát."""
from __future__ import annotations

import asyncio
import json
import os
from datetime import date

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from agnet.core.settings import Settings                       # noqa: E402
from agnet.gemini import GeminiClient                           # noqa: E402
from agnet.gemini.ladder import build_ladder                    # noqa: E402
from agnet.pipeline.agents import AgentError, load_agents       # noqa: E402
from agnet.pipeline.pipeline import SCOUTS, Pipeline            # noqa: E402
from agnet.storage.db import Store                              # noqa: E402
from tests.test_gemini_client import Fake, mk, ok, quota        # noqa: E402
from tests.test_pipeline import FakeRunner                      # noqa: E402
from tests.test_pipeline_engine import _flow                    # noqa: E402


def test_phan_hoi_candidates_rong_la_bad_response_khong_nem_IndexError(tmp_path):
    empty = (200, json.dumps({"candidates": []}).encode())
    c, _, _ = mk(tmp_path, {"gemini-3.8-pro": [empty], "gemini-3.7-pro": ok("b")})
    r = c.generate("x")
    assert r.model == "gemini-3.7-pro" and r.attempts[0]["outcome"] == "bad_response"


def test_thang_3_dung_duoi_3_1():
    names = [m.name for m in build_ladder(["gemini-3-pro-preview", "gemini-3.1-pro-preview"])]
    assert names == ["gemini-3.1-pro-preview", "gemini-3-pro-preview"]


def test_probe_xoa_cooldown_cu_de_thay_duoc_khi_bat_thanh_toan(tmp_path):
    body = b'{"error":{"message":"limit: 0"}}'
    c, fake, t = mk(tmp_path, {m: [(429, body)] * 3 for m in ("gemini-3.8-pro", "gemini-3.7-pro", "gemini-3.8-flash",
                                                              "gemini-3.8-flash-lite")})
    c.probe()                                           # cooldown 24h được ghi
    assert any(v > t[0] for v in c._cool.values())
    fake.b = {"gemini-3.8-pro": ok("ok", ["http://a/1"]), "gemini-3.7-pro": ok("ok", ["http://a/1"])}
    assert c.probe()["search"] == "ok"


def test_status_thay_cooldown_bam_nguon(tmp_path):
    c, _, _ = mk(tmp_path, {"gemini-3.8-pro": [quota(delay=100)], "gemini-3.7-pro": ok()})
    c.generate("x")
    first = next(m for m in c.status() if m["name"] == "gemini-3.8-pro")
    assert first["cooldown_s"] > 0


def test_nhieu_luong_dung_chung_client_khong_vo_dict(tmp_path):
    import threading
    c, _, _ = mk(tmp_path, {})
    errs = []

    def hammer(i):
        try:
            for k in range(300):
                with c._lock:
                    c._cool[f"m{i}-{k}"] = 1e9
                c._save_cache()
        except Exception as e:                          # noqa: BLE001
            errs.append(e)
    ts = [threading.Thread(target=hammer, args=(i,)) for i in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert not errs


def test_engine_gemini_chi_cho_agent_khao_sat(tmp_path):
    (tmp_path / "q.md").write_text("---\nname: editor-in-chief\ndescription: d\nengine: gemini\ntools: Read\n---\nx",
                                   encoding="utf-8")
    with pytest.raises(AgentError):
        load_agents(tmp_path)


def test_enrich_nem_IndexError_van_ghi_bao_cao_va_dong_ban_ghi_runs(tmp_path):
    class Boom(FakeRunner):
        async def run(self, agent, prompt, *, max_budget_usd):
            if agent.name == "keyword-miner":
                raise IndexError("candidates rỗng")
            return await super().run(agent, prompt, max_budget_usd=max_budget_usd)
    p = Pipeline(_flow(), load_agents(), Boom(), Store(tmp_path / "t.db"), date(2026, 10, 2), tmp_path / "o")
    res = asyncio.run(p.run())
    assert res["status"] != "running"
    assert (tmp_path / "o" / "2026-10-02" / "suckhoe-yt-sang" / "_BAO_CAO_NGAY.md").exists() or res["status"]
    assert any("IndexError" in e for e in p.errors)


def test_loi_la_giua_chung_van_ghi_trang_thai_loi_khong_ket_running(tmp_path):
    class Boom(FakeRunner):
        async def run(self, agent, prompt, *, max_budget_usd):
            if agent.name == "dedup-cluster":
                raise RuntimeError("hỏng bất ngờ")
            return await super().run(agent, prompt, max_budget_usd=max_budget_usd)
    st = Store(tmp_path / "t.db")
    p = Pipeline(_flow(), load_agents(), Boom(), st, date(2026, 10, 2), tmp_path / "o")
    res = asyncio.run(p.run())
    assert res["status"].startswith("lỗi: RuntimeError")


# ---- KOC: các cách lách bộ lọc từ cấm ------------------------------------------------------------------
@pytest.mark.parametrize("bad", ["bác​ sĩ chuyên khoa", "b á c s ĩ", "bác sĩ".encode("NFD", "ignore").decode()
                                 if False else "bác sĩ", "Dr. Nguyen, MD", "BS. Nguyễn",
                                 "n.u.d.e bedroom", "naked", "Topless"])
def test_koc_chan_cach_lach(bad):
    from agnet.ui.page_koc import KocError, check_text
    with pytest.raises(KocError):
        check_text("meta.niche", bad)


@pytest.mark.parametrize("good", ["không phải bác sĩ", "chuyên gia dinh dưỡng đời thường", "ăn uống lành mạnh"])
def test_koc_van_cho_cau_hop_le(good):
    from agnet.ui.page_koc import check_text
    check_text("meta.niche", good)


def test_koc_ma_nhan_vat_khong_duoc_chua_duong_dan(tmp_path):
    from agnet.ui.page_koc import KocError, save_character
    for bad in ("../../x", "..\\x", "/tmp/x", ""):
        with pytest.raises(KocError):
            save_character(tmp_path, tmp_path / "c.yaml", bad, {})


def test_set_field_chan_xuong_dong():
    from agnet.ui.page_agents import set_field
    t = "---\nname: a\nmodel: sonnet\ntools: Read\n---\nbody"
    with pytest.raises(ValueError):
        set_field(t, "model", "sonnet\ntools: Write, Edit")


def test_env_store_ghi_nguyen_tu_va_quyen_600(tmp_path):
    from agnet.ui import env_store
    p = tmp_path / ".env"
    env_store.set_key(p, "GEMINI_API_KEY", "k" * 20)
    assert not list(tmp_path.glob("*.tmp")) and (os.stat(p).st_mode & 0o777) == 0o600


def test_log_che_khoa_gemini():
    from agnet.logging_setup import SECRET_KEYS
    assert "GEMINI_API_KEY" in SECRET_KEYS
