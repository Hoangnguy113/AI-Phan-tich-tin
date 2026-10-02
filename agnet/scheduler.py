"""Đăng ký lịch chạy từ bảng luồng (mục 3, 11.1). Đổi giờ trong flows.yaml → gọi sync() là xong, không cần khởi động lại."""
from __future__ import annotations

import asyncio
from typing import Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from .core.models import Flow, load_flows
from .runner import run_flow


def job_id(flow: Flow, n: int) -> str:
    return f"{flow.id}#{n}"


def triggers_for(flow: Flow) -> list:
    if flow.mode == "breaking":
        return [IntervalTrigger(hours=flow.interval_hours, timezone=flow.timezone)]
    return [CronTrigger.from_crontab(c, timezone=flow.timezone) for c in flow.schedule]


def sync(scheduler: AsyncIOScheduler, flows: list[Flow], job: Callable) -> set[str]:
    """Đồng bộ job với cấu hình: thêm/sửa luồng bật, gỡ luồng tắt hoặc đã xoá."""
    wanted: set[str] = set()
    for f in flows:
        if not f.enabled:
            continue
        for n, trig in enumerate(triggers_for(f)):
            jid = job_id(f, n)
            wanted.add(jid)
            scheduler.add_job(job, trig, args=[f], id=jid, replace_existing=True, max_instances=1,
                              coalesce=True, misfire_grace_time=3600)
    for j in scheduler.get_jobs():
        if j.id not in wanted:
            scheduler.remove_job(j.id)
    return wanted


async def serve(flows_path: str = "config/flows.yaml", db: str = "agnet.db") -> int:
    """Chạy nền theo lịch. Phần vận hành (log, khoá, chạy bù, thông báo) nằm ở agnet/daemon.py."""
    from .daemon import serve as _serve          # nạp muộn: tránh vòng import
    return await _serve(flows_path, db)
