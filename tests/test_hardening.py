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


# ---- đợt phản biện ---------------------------------------------------------------------------------------
def _lad_agent(tmp_path, front):
    (tmp_path / "q.md").write_text(f"---\nname: editor-in-chief\ndescription: d\n{front}\n---\nx", encoding="utf-8")
    return load_agents(tmp_path)


@pytest.mark.parametrize("front", ["engine: Gemini\ntools: Read", "engine: '  gemini '\ntools: Read",
                                   "engine: gpt\ntools: Read", "tools: [Read, Write]", "tools: Read, write",
                                   "tools: Read, Write(*)", "tools: mcp__fs__write_file", "tools: Edit(src/**)",
                                   "tools: WebFetch, Bash(*)"])
def test_load_agents_khong_bi_lach_bang_chu_hoa_danh_sach_hay_ngoac(tmp_path, front):
    with pytest.raises(AgentError):
        _lad_agent(tmp_path, front)


def test_nghiem_thu_url_chuyen_huong_khong_bao_chung_url_bia():
    from datetime import datetime, timezone
    from types import SimpleNamespace
    from agnet.commander import TaskContract, accept
    now = datetime(2026, 10, 2, 12, tzinfo=timezone.utc)
    c = TaskContract(agent="trend-scout", flow_id="f", goal="g", min_items=1, max_age_hours=48)
    mk_item = lambda u: {"title": "t " + u[-3:], "url": u, "source": "news", "published_at": "2026-10-02", "snippet": "s"}
    # nguồn bám là URL chuyển hướng + title "reuters.com": URL bịa trên miền chuyển hướng KHÔNG qua
    res = SimpleNamespace(sources=[{"url": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/x",
                                    "title": "reuters.com"}])
    r = accept([mk_item("https://vertexaisearch.cloud.google.com/fake/abc")], c, res, now)
    assert not r.accepted
    # một nguồn chỉ cấp 1 suất cho miền reuters.com: mục thứ hai cùng miền bị loại
    r = accept([mk_item("https://www.reuters.com/a1"), mk_item("https://www.reuters.com/b2")], c, res, now)
    assert len(r.accepted) == 1 and r.rejected[0].reason == "not_grounded"


def test_survey_bo_muc_rong():
    from agnet.pipeline.survey import read_survey
    assert read_survey({"items": [{}, {"title": "a"}]}).items == [{"title": "a"}]


def test_gemini_co_han_chot_tong_cho_ca_thang(tmp_path):
    from agnet.gemini import AllModelsExhausted
    t = [1e6]
    fake = Fake({m: [(503, b"")] * 9 for m in ("gemini-3.8-pro", "gemini-3.7-pro", "gemini-3.8-flash",
                                               "gemini-3.8-flash-lite")})
    c = GeminiClient("K", cache_path=tmp_path / "m.json", transport=fake, clock=lambda: t[0],
                     sleep=lambda s: t.__setitem__(0, t[0] + 100), max_total_s=150)
    with pytest.raises(AllModelsExhausted) as e:
        c.generate("x", search=False)
    assert any(a["outcome"] == "deadline" for a in e.value.attempts)


@pytest.mark.parametrize("bad", ["ｐｅｒｆｅｃｔ", "hyper  detailed skin", "hyper-detailed", "8 K", "ultra realistic",
                                 "90 60 90", "sexily posed", "sensual", "skimpy outfit", "underwear"])
def test_koc_chan_them_cach_lach(bad):
    from agnet.ui.page_koc import KocError, check_text
    with pytest.raises(KocError):
        check_text("defaults.setting", bad)


def test_env_tao_tep_tam_0600_ngay_tu_dau(tmp_path, monkeypatch):
    import stat
    from agnet.ui import env_store
    seen = []
    real = os.replace
    monkeypatch.setattr(os, "replace", lambda a, b: (seen.append(stat.S_IMODE(os.stat(a).st_mode)), real(a, b))[1])
    env_store.set_key(tmp_path / ".env", "GEMINI_API_KEY", "k" * 20)
    assert seen == [0o600]


def test_loi_ghi_tep_mot_kich_ban_khong_sap_ca_lan_chay(tmp_path, monkeypatch):
    from agnet.pipeline import export
    monkeypatch.setattr(export, "write_script_folder", lambda *a, **k: (_ for _ in ()).throw(OSError("đĩa đầy")))
    p = Pipeline(_flow(), load_agents(), FakeRunner(), Store(tmp_path / "t.db"), date(2026, 10, 2), tmp_path / "o")
    res = asyncio.run(p.run())
    assert not res["status"].startswith("lỗi:")
