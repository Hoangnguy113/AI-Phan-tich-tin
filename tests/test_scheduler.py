from apscheduler.schedulers.asyncio import AsyncIOScheduler
from agnet.core.models import Flow
from agnet.scheduler import sync, triggers_for

B = dict(topic="t", name="n")


def mk(i, **kw):
    return Flow(id=i, schedule=["30 5 * * *", "0 17 * * *"], **B, **{**kw})


async def _noop(f): ...


def _sched():
    return AsyncIOScheduler(timezone="Asia/Bangkok")   # không start: job nằm ở trạng thái chờ, đủ để kiểm đăng ký


def test_two_crons_two_jobs_and_timezone():
    f = mk("a")
    s = _sched()
    assert sync(s, [f], _noop) == {"a#0", "a#1"}
    nxt = s.get_job("a#0").trigger
    assert str(nxt.timezone) == "Asia/Bangkok" and "hour='5'" in str(nxt)


def test_disabled_and_removed_flows_are_unscheduled():
    s = _sched()
    sync(s, [mk("a"), mk("b")], _noop)
    assert {j.id for j in s.get_jobs()} == {"a#0", "a#1", "b#0", "b#1"}
    sync(s, [mk("a", enabled=False)], _noop)
    assert s.get_jobs() == []


def test_changing_time_replaces_job_without_restart():
    # cần scheduler ĐANG CHẠY: ở trạng thái chờ APScheduler không loại job trùng id
    import asyncio

    async def go():
        s = _sched()
        s.start(paused=True)
        sync(s, [mk("a")], _noop)
        f2 = Flow(id="a", schedule=["15 6 * * *"], **B)
        sync(s, [f2], _noop)
        out = ({j.id for j in s.get_jobs()}, str(s.get_job("a#0").trigger))
        s.shutdown(wait=False)
        return out

    ids, trig = asyncio.run(go())
    assert ids == {"a#0"} and "hour='6'" in trig and "minute='15'" in trig


def test_breaking_flow_uses_interval():
    f = Flow(id="b", mode="breaking", interval_hours=3, **B)
    t = triggers_for(f)[0]
    assert t.interval.total_seconds() == 3 * 3600
