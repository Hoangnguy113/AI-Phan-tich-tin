"""Chạy nền hằng ngày: lịch cron, chạy bù khi máy từng tắt, tự nạp lại flows.yaml, báo Telegram.

Nguyên tắc: một lần chạy lỗi KHÔNG được làm chết tiến trình nền; mọi lỗi được log + gửi thông báo
rồi chờ lần kế tiếp. Chỉ cho phép một bản daemon duy nhất (khoá file) để không trả tiền API hai lần.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import date, datetime, time, timedelta
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .core.models import Flow, load_flows
from .env import ROOT, load_env
from .logging_setup import setup as setup_logging
from .notify import Notifier
from .runner import run_flow
from .scheduler import sync
from .storage.db import Store

log = logging.getLogger("agnet.daemon")
RELOAD_EVERY_SEC = 30
STALE_RUN_HOURS = 6.0


# ---- khoá một bản chạy ---------------------------------------------------
class SingleInstance:
    """Khoá file theo kiểu hệ điều hành: tiến trình chết bất ngờ thì khoá tự nhả."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self._fh = None

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # KHÔNG dùng chế độ "a+": trong chế độ nối thêm, con trỏ nằm ở cuối file nên
        # msvcrt.locking khoá một byte KHÁC nhau tuỳ nội dung sẵn có — hai bản chạy
        # khoá hai byte khác nhau và cả hai đều tưởng mình giành được khoá.
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o644)
        self._fh = os.fdopen(fd, "r+", encoding="utf-8")
        self._fh.seek(0)                                         # mọi bản chạy phải khoá CÙNG byte 0
        try:
            try:
                import msvcrt                                    # Windows
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_NBLCK, 1)
            except ImportError:
                import fcntl                                     # Linux/macOS
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self._fh.close()
            self._fh = None
            return False
        self._fh.seek(0)
        self._fh.truncate()
        self._fh.write(f"{os.getpid()} {datetime.now().isoformat(timespec='seconds')}\n")
        self._fh.flush()
        return True

    def release(self) -> None:
        if self._fh:
            try:
                self._fh.close()
            finally:
                self._fh = None


# ---- quyết định chạy bù (thuần, kiểm được bằng test) ---------------------
def parse_hhmm(s: str) -> time:
    hh, _, mm = s.partition(":")
    return time(int(hh), int(mm))


def _tz(flow: Flow):
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(flow.timezone)
    except Exception:                                            # múi giờ lạ → dùng giờ máy
        return None


def now_local(flow: Flow) -> datetime:
    tz = _tz(flow)
    return datetime.now(tz) if tz else datetime.now()


def schedule_passed_today(flow: Flow, now: datetime) -> bool:
    """Hôm nay đã qua ít nhất một mốc cron của luồng chưa?"""
    from apscheduler.triggers.cron import CronTrigger
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    for c in flow.schedule:
        trig = CronTrigger.from_crontab(c, timezone=now.tzinfo) if now.tzinfo else CronTrigger.from_crontab(c)
        nxt = trig.get_next_fire_time(None, midnight)
        if nxt and nxt <= now:
            return True
    return False


def catchup_reason(flow: Flow, store: Store, now: datetime) -> str | None:
    """Trả lý do BỎ QUA chạy bù, hoặc None nếu nên chạy bù ngay."""
    if not flow.enabled:
        return "luồng đang tắt"
    if flow.mode != "scheduled":
        return "luồng breaking chạy theo chu kỳ, không cần bù"
    if not flow.catchup:
        return "catchup=false"
    if store.ran_today(flow.id, now.date()):
        return "hôm nay đã chạy"
    if store.is_running(flow.id):
        return "đang có lần chạy khác"
    if not schedule_passed_today(flow, now):
        return "chưa tới giờ hôm nay"
    if now.timetz().replace(tzinfo=None) > parse_hhmm(flow.catchup_until):
        return f"quá mốc bù {flow.catchup_until}"
    return None


# ---- chạy một luồng an toàn ---------------------------------------------
async def run_guarded(flow: Flow, *, db: str, notifier: Notifier, store: Store, trigger: str = "lịch") -> dict | None:
    day = now_local(flow).date().isoformat()
    if store.is_running(flow.id):
        log.warning("%s: bỏ qua (%s) vì đang có lần chạy chưa kết thúc", flow.id, trigger)
        return None
    log.info("%s: bắt đầu (%s), quota=%s, trần $%.2f/ngày, trần thời gian %g phút",
             flow.id, trigger, flow.daily_quota, flow.max_cost_usd_per_day, flow.run_timeout_min)
    try:
        res = await asyncio.wait_for(run_flow(flow, db=db), timeout=flow.run_timeout_min * 60)
    except asyncio.TimeoutError:
        store.finish_running(flow.id, f"quá trần thời gian {flow.run_timeout_min:g} phút")
        log.error("%s: quá trần thời gian %g phút — đã dừng", flow.id, flow.run_timeout_min)
        notifier.run_finished(flow, day, None, f"quá trần thời gian {flow.run_timeout_min:g} phút")
        return None
    except Exception as e:                                       # lỗi gì cũng không được giết daemon
        store.finish_running(flow.id, f"lỗi: {type(e).__name__}")
        log.exception("%s: lỗi khi chạy", flow.id)
        notifier.run_finished(flow, day, None, f"{type(e).__name__}: {e}")
        return None
    out = {"passed": res.get("passed", 0), "spent": res.get("spent", 0.0), "status": res.get("status", ""),
           "quota": flow.daily_quota, "human_review": bool(flow.sensitive or flow.human_review),
           "folder": str(Path(flow.output_dir) / day / flow.id),
           "errors": [str(x) for x in (res.get("errors") or [])]}
    log.info("%s: xong — đạt %s/%s, chi $%.2f, %s", flow.id, out["passed"], flow.daily_quota, out["spent"], out["status"])
    notifier.run_finished(flow, day, out)
    return out


# ---- vòng đời daemon -----------------------------------------------------
async def serve(flows_path: str | Path = "config/flows.yaml", db: str = "agnet.db", *,
                log_dir: str | Path = "logs", notifier: Notifier | None = None,
                lock_path: str | Path | None = None, stop_after_sec: float | None = None) -> int:
    setup_logging(log_dir)
    names = load_env()
    log.info("Agnet daemon khởi động · nạp .env: %s", ", ".join(names) or "không có khoá mới")
    lock = SingleInstance(lock_path or Path(db).with_suffix(".lock"))
    if not lock.acquire():
        log.error("Đã có một Agnet daemon đang chạy (khoá %s) — thoát để không chạy trùng.", lock.path)
        return 3
    notifier = notifier or Notifier()
    store = Store(db)
    n = store.mark_stale_running(STALE_RUN_HOURS)
    if n:
        log.warning("Đánh dấu %d lần chạy bỏ dở (máy tắt giữa chừng) là 'interrupted'", n)

    flows_path = Path(flows_path)
    state: dict = {"mtime": None, "flows": []}
    sched = AsyncIOScheduler()

    async def job(flow: Flow):
        current = next((f for f in state["flows"] if f.id == flow.id), flow)   # luôn dùng cấu hình mới nhất
        await run_guarded(current, db=db, notifier=notifier, store=store, trigger="lịch")

    def reload_flows(first: bool = False) -> None:
        try:
            mtime = flows_path.stat().st_mtime
        except OSError as e:
            log.error("không đọc được %s: %s", flows_path, e)
            return
        if not first and mtime == state["mtime"]:
            return
        try:
            flows = load_flows(flows_path)
        except Exception as e:
            log.error("flows.yaml sai cấu hình, giữ nguyên lịch cũ: %s", e)
            state["mtime"] = mtime
            return
        state["mtime"], state["flows"] = mtime, flows
        ids = sync(sched, flows, job)
        log.info("Đã nạp %d luồng (%d đang bật, %d job): %s", len(flows),
                 sum(f.enabled for f in flows), len(ids), ", ".join(f.id for f in flows if f.enabled) or "—")
        if sched.running:
            log_next()

    def log_next() -> None:
        for j in sched.get_jobs():
            if j.id != "_reload" and getattr(j, "next_run_time", None):
                log.info("  %s → lần chạy kế tiếp %s", j.id, j.next_run_time)

    reload_flows(first=True)
    sched.add_job(reload_flows, IntervalTrigger(seconds=RELOAD_EVERY_SEC), id="_reload", replace_existing=True)
    sched.start()
    log_next()

    # chạy bù: máy từng tắt đúng giờ cron mà hôm nay chưa chạy
    for f in list(state["flows"]):
        why = catchup_reason(f, store, now_local(f))
        if why is None:
            log.warning("%s: chạy bù vì hôm nay chưa chạy (mốc bù %s)", f.id, f.catchup_until)
            asyncio.create_task(run_guarded(f, db=db, notifier=notifier, store=store, trigger="bù lịch"))
        else:
            log.info("%s: không chạy bù (%s)", f.id, why)

    try:
        if stop_after_sec:
            await asyncio.sleep(stop_after_sec)
        else:
            await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        log.info("Nhận tín hiệu dừng.")
    finally:
        sched.shutdown(wait=False)
        lock.release()
        log.info("Agnet daemon đã dừng.")
    return 0
