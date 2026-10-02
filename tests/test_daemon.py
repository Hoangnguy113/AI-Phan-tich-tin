"""Kiểm phần vận hành: quyết định chạy bù, khoá một bản chạy, trần thời gian, thông báo."""
import asyncio
from datetime import date, datetime

import pytest
from zoneinfo import ZoneInfo

from agnet import daemon
from agnet.core.models import Flow
from agnet.notify import Notifier, format_run
from agnet.storage.db import Store

TZ = ZoneInfo("Asia/Bangkok")
B = dict(name="n", topic="t", timezone="Asia/Bangkok")


def mk(**kw):
    return Flow(id=kw.pop("id", "f1"), schedule=kw.pop("schedule", ["30 5 * * *"]), **B, **kw)


def at(h, m=0):
    return datetime(2026, 10, 1, h, m, tzinfo=TZ)


# ---- chạy bù -------------------------------------------------------------
def test_schedule_passed_today():
    f = mk()
    assert daemon.schedule_passed_today(f, at(9)) is True
    assert daemon.schedule_passed_today(f, at(4)) is False


def test_catchup_khi_may_tung_tat(tmp_path):
    st = Store(tmp_path / "a.db")
    assert daemon.catchup_reason(mk(), st, at(9)) is None          # 9h sáng, đã qua 5h30, chưa chạy → bù


def test_khong_bu_khi_da_chay_hom_nay(tmp_path):
    st = Store(tmp_path / "a.db")
    st.start_run("r1", "f1", date(2026, 10, 1))
    st.finish_run("r1", "thiếu sản lượng: 7/10")
    assert daemon.catchup_reason(mk(), st, at(9)) == "hôm nay đã chạy"


def test_lan_chay_bo_do_khong_tinh_la_da_chay(tmp_path):
    st = Store(tmp_path / "a.db")
    st.start_run("r1", "f1", date(2026, 10, 1))
    assert daemon.catchup_reason(mk(), st, at(9)) == "đang có lần chạy khác"
    st.mark_stale_running(0)                                        # máy tắt giữa chừng
    assert daemon.catchup_reason(mk(), st, at(9)) is None


def test_qua_moc_bu_thi_cho_ngay_mai(tmp_path):
    st = Store(tmp_path / "a.db")
    assert daemon.catchup_reason(mk(catchup_until="12:00"), st, at(15)) == "quá mốc bù 12:00"
    assert daemon.catchup_reason(mk(catchup_until="22:00"), st, at(15)) is None   # mốc bù tuỳ chọn


def test_cac_truong_hop_khong_bu(tmp_path):
    st = Store(tmp_path / "a.db")
    assert daemon.catchup_reason(mk(catchup=False), st, at(9)) == "catchup=false"
    assert daemon.catchup_reason(mk(enabled=False), st, at(9)) == "luồng đang tắt"
    assert daemon.catchup_reason(mk(), st, at(4)) == "chưa tới giờ hôm nay"
    brk = Flow(id="b", mode="breaking", interval_hours=3, **B)
    assert "breaking" in daemon.catchup_reason(brk, st, at(9))


# ---- khoá một bản chạy ---------------------------------------------------
def test_chi_mot_daemon_duoc_chay(tmp_path):
    a, b = daemon.SingleInstance(tmp_path / "x.lock"), daemon.SingleInstance(tmp_path / "x.lock")
    assert a.acquire() is True
    assert b.acquire() is False          # bản thứ hai bị chặn → không trả tiền API hai lần
    a.release()
    assert b.acquire() is True
    b.release()


def test_serve_thoat_khi_da_co_daemon(tmp_path):
    lock = daemon.SingleInstance(tmp_path / "y.lock")
    assert lock.acquire()
    (tmp_path / "flows.yaml").write_text("flows: []", encoding="utf-8")
    rc = asyncio.run(daemon.serve(tmp_path / "flows.yaml", str(tmp_path / "a.db"),
                                  log_dir=tmp_path / "logs", lock_path=tmp_path / "y.lock"))
    lock.release()
    assert rc == 3


# ---- trần thời gian & lỗi không được giết daemon -------------------------
class FakeNotifier(Notifier):
    def __init__(self):
        super().__init__()
        self.sent = []

    def run_finished(self, flow, day, result, error=None):
        self.sent.append((flow.id, result, error))


def test_qua_tran_thoi_gian_thi_dung_va_bao(tmp_path, monkeypatch):
    st = Store(tmp_path / "a.db")

    async def hang(flow, **kw):
        st.start_run("r9", flow.id, date.today())
        await asyncio.sleep(5)

    monkeypatch.setattr(daemon, "run_flow", hang)
    n = FakeNotifier()
    f = mk(run_timeout_min=0.01)          # 0,6 giây
    out = asyncio.run(daemon.run_guarded(f, db=str(tmp_path / "a.db"), notifier=n, store=st))
    assert out is None
    assert "quá trần thời gian" in n.sent[0][2]
    assert st.recent_runs(1)[0]["status"].startswith("quá trần thời gian")
    assert not st.is_running("f1")        # không để lại lần chạy treo


def test_loi_khi_chay_duoc_bao_va_khong_nem_ra_ngoai(tmp_path, monkeypatch):
    st = Store(tmp_path / "a.db")

    async def boom(flow, **kw):
        raise RuntimeError("API sập")

    monkeypatch.setattr(daemon, "run_flow", boom)
    n = FakeNotifier()
    assert asyncio.run(daemon.run_guarded(mk(), db=str(tmp_path / "a.db"), notifier=n, store=st)) is None
    assert "API sập" in n.sent[0][2]


def test_chay_xong_bao_du_so_lieu(tmp_path, monkeypatch):
    st = Store(tmp_path / "a.db")

    async def ok(flow, **kw):
        return {"status": "ok", "passed": 10, "spent": 3.21, "outcomes": [], "errors": []}

    monkeypatch.setattr(daemon, "run_flow", ok)
    n = FakeNotifier()
    out = asyncio.run(daemon.run_guarded(mk(sensitive=True, human_review=True),
                                         db=str(tmp_path / "a.db"), notifier=n, store=st))
    assert out["passed"] == 10 and out["quota"] == 10 and out["human_review"] is True
    txt = format_run("f1", "2026-10-01", out)
    assert "10/10" in txt and "$3.21" in txt and "kiểm duyệt" in txt


# ---- thông báo -----------------------------------------------------------
class FakeTx:
    def __init__(self, fail=False):
        self.calls, self.fail = [], fail

    def post(self, url, payload):
        if self.fail:
            raise OSError("mạng lỗi")
        self.calls.append((url, payload))
        return 200


def test_telegram_gui_va_khong_lam_lo_token():
    tx = FakeTx()
    n = Notifier(transport=tx, env={"TELEGRAM_BOT_TOKEN": "123:abc", "TELEGRAM_CHAT_ID": "77"})
    assert n.telegram("xin chào") is True
    url, payload = tx.calls[0]
    assert url.endswith("/sendMessage") and payload["chat_id"] == "77" and payload["text"] == "xin chào"


def test_thieu_token_thi_bo_qua_chu_khong_loi():
    n = Notifier(transport=FakeTx(), env={})
    assert n.telegram("x") is False


def test_gui_that_bai_khong_nem_loi():
    n = Notifier(transport=FakeTx(fail=True), env={"TELEGRAM_BOT_TOKEN": "t", "TELEGRAM_CHAT_ID": "c"})
    assert n.telegram("x") is False
    n.run_finished(mk(), "2026-10-01", {"passed": 1, "spent": 0.1, "status": "ok", "quota": 10})


def test_webhook_theo_cau_hinh_luong():
    tx = FakeTx()
    n = Notifier(transport=tx, env={})
    f = mk(webhook_url="https://hook.test/x", notify=["webhook"])
    n.run_finished(f, "2026-10-01", {"passed": 2, "spent": 0.5, "status": "ok", "quota": 10})
    assert tx.calls[0][0] == "https://hook.test/x" and tx.calls[0][1]["flow_id"] == "f1"


def test_bao_loi_co_icon_do():
    assert format_run("f1", "2026-10-01", None, "mất mạng").startswith("❌")


# ---- nạp lại flows.yaml khi đang chạy -----------------------------------
def test_serve_nap_lai_flows_khi_file_doi(tmp_path, monkeypatch):
    fp = tmp_path / "flows.yaml"
    base = ('flows:\n  - id: {id}\n    name: n\n    topic: t\n    catchup: false\n'
            '    schedule: ["{cron}"]\n')
    fp.write_text(base.format(id="a1", cron="30 5 * * *"), encoding="utf-8")
    seen = {}

    async def go():
        task = asyncio.create_task(daemon.serve(fp, str(tmp_path / "a.db"), log_dir=tmp_path / "logs",
                                                notifier=FakeNotifier(), lock_path=tmp_path / "z.lock",
                                                stop_after_sec=1.2))
        await asyncio.sleep(0.3)
        monkeypatch.setattr(daemon, "RELOAD_EVERY_SEC", 1)
        fp.write_text(base.format(id="a2", cron="0 7 * * *"), encoding="utf-8")
        await task

    monkeypatch.setattr(daemon, "RELOAD_EVERY_SEC", 1)
    asyncio.run(go())
    # log ghi lại cả hai lần nạp: luồng a1 rồi a2
    txt = (tmp_path / "logs" / "agnet.log").read_text(encoding="utf-8")
    assert "a1" in txt and "a2" in txt
