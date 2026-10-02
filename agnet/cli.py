"""Dòng lệnh Agnet. Agent (Claude) gọi các lệnh này qua Bash để lấy kết quả TÍNH TOÁN chính xác."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from .core import timing
from .env import load_env
from .core.models import load_flows
from .core.validate import has_errors, validate_file
from .storage.db import Store


def _flow(flows_path: str, flow_id: str | None):
    flows = load_flows(flows_path)
    if not flow_id:
        return None
    for f in flows:
        if f.id == flow_id:
            return f
    sys.exit(f"Không có luồng '{flow_id}' trong {flows_path}")


def cmd_flows(a) -> int:
    for f in load_flows(a.flows):
        state = "BẬT" if f.enabled else "tắt"
        print(f"{f.id:24} {state:4} {f.platform:9} {f.aspect_ratio:5} {f.duration_min:g}-{f.duration_max:g}p "
              f"quota={f.daily_quota} wpm={f.wpm:g} lang={f.output_language} ${f.max_cost_usd_per_day:g}/ngày")
    return 0


def cmd_validate(a) -> int:
    issues = validate_file(a.script, _flow(a.flows, a.flow))
    for i in issues:
        print(i)
    if not issues:
        print("OK — script.json hợp lệ")
    return 1 if has_errors(issues) else 0


def cmd_budget(a) -> int:
    total = timing.word_budget(a.minutes, a.wpm)
    weights = [float(x) for x in a.weights.split(",")] if a.weights else [1.0]
    parts = timing.split_budget(total, weights)
    print(json.dumps({"minutes": a.minutes, "wpm": a.wpm, "total_words": total, "target_sec": a.minutes * 60,
                      "segment_words": parts}, ensure_ascii=False))
    return 0


def cmd_count(a) -> int:
    text = Path(a.file).read_text(encoding="utf-8") if a.file else sys.stdin.read()
    w = timing.count_words(text)
    print(json.dumps({"words": w, "seconds": round(timing.speech_seconds(text, a.wpm), 1), "wpm": a.wpm}))
    return 0


def cmd_dedup(a) -> int:
    hit = Store(a.db).find_duplicate(a.title, today=date.today())
    if hit:
        print(json.dumps({"duplicate": True, "of": hit[0], "similarity": hit[1]}, ensure_ascii=False))
        return 1
    print(json.dumps({"duplicate": False}))
    return 0


def cmd_claim(a) -> int:
    ok = Store(a.db).claim_topic(a.flow_id, a.title, today=date.today())
    print(json.dumps({"claimed": ok}))
    return 0 if ok else 1


def cmd_run(a) -> int:
    import asyncio
    from .runner import run_flow
    flow = _flow(a.flows, a.flow_id)
    res = asyncio.run(run_flow(flow, db=a.db))
    print(json.dumps({"status": res["status"], "passed": res["passed"], "spent_usd": round(res["spent"], 2)}, ensure_ascii=False))
    return 0 if res["passed"] >= flow.daily_quota else 2


def cmd_gui(a) -> int:
    """Mở phần mềm quản lý (cửa sổ desktop)."""
    try:
        from .ui.app import run
    except ImportError as e:
        sys.exit(f"Thiếu PySide6 — cài bằng: pip install PySide6\n({e})")
    return run(a.flows, a.db)


def cmd_serve(a) -> int:
    import asyncio
    from .daemon import serve
    return asyncio.run(serve(a.flows, a.db))


def cmd_doctor(a) -> int:
    """Kiểm tra mọi điều kiện để chạy tự động, KHÔNG gọi API tốn tiền."""
    import os, shutil
    from .pipeline.agents import load_agents
    ok = True
    def line(good: bool, label: str, note: str = "") -> None:
        nonlocal ok
        ok = ok and good
        print(("  OK   " if good else "  THIEU") + f" {label}" + (f" — {note}" if note else ""))

    print("1) Cấu hình luồng")
    try:
        flows = load_flows(a.flows)
        on = [f for f in flows if f.enabled]
        line(bool(on), f"{len(flows)} luồng, {len(on)} đang bật", ", ".join(f.id for f in on))
        for f in on:
            line(bool(f.schedule) or f.mode == "breaking", f"{f.id}: lịch {f.schedule or f.interval_hours}",
                 f"tz={f.timezone} quota={f.daily_quota} trần ${f.max_cost_usd_per_day:g}/ngày "
                 f"bù={'có' if f.catchup else 'không'} tới {f.catchup_until}")
    except Exception as e:
        line(False, "flows.yaml", str(e)[:160])

    print("2) Xác thực & phụ thuộc")
    key = bool((os.environ.get("ANTHROPIC_API_KEY") or "").strip())
    cli_login = shutil.which("claude") is not None
    line(key or cli_login, "ANTHROPIC_API_KEY hoặc đã đăng nhập Claude Code",
         "có khoá trong môi trường" if key else ("có lệnh `claude` — cần đã /login" if cli_login else "đặt khoá trong .env"))
    try:
        import claude_agent_sdk  # noqa: F401
        line(True, "claude-agent-sdk đã cài")
    except Exception as e:
        line(False, "claude-agent-sdk", str(e)[:120])
    try:
        line(len(load_agents()) == 17, f"nạp được {len(load_agents())}/17 agent")
    except Exception as e:
        line(False, "agent .claude/agents", str(e)[:120])

    print("3) Thông báo")
    tele = all((os.environ.get(k) or "").strip() for k in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"))
    line(tele, "Telegram", "đã có token & chat id" if tele else
         "điền TELEGRAM_BOT_TOKEN và TELEGRAM_CHAT_ID trong .env (không bắt buộc)")

    print("4) Ghi file & dữ liệu")
    root = Path(__file__).resolve().parents[1]
    try:
        (root / "logs").mkdir(exist_ok=True)
        (root / "logs" / ".write_probe").write_text("ok", encoding="utf-8")
        line(True, "ghi được logs/")
    except Exception as e:
        line(False, "ghi logs/", str(e)[:120])
    try:
        st = Store(a.db)
        st.mark_stale_running(99999)
        line(True, f"SQLite {a.db} dùng được", f"{len(st.recent_runs(5))} lần chạy gần đây")
    except Exception as e:
        line(False, f"SQLite {a.db}", str(e)[:120])
    print("\n=> " + ("SẴN SÀNG chạy tự động: `python -m agnet serve`" if ok else
                     "CÒN THIẾU — xem các dòng 'THIEU' ở trên (dòng Telegram không bắt buộc)"))
    return 0 if ok else 1


def cmd_status(a) -> int:
    st = Store(a.db)
    runs = st.recent_runs(a.limit, a.flow)
    print(f"{'luồng':24} {'ngày':11} {'trạng thái':34} {'chi phí':>8}  bắt đầu")
    for r in runs:
        print(f"{r['flow_id'][:24]:24} {r['day']:11} {str(r['status'])[:34]:34} ${r['usd'] or 0:7.2f}  {r['started_at']}")
    if not runs:
        print("  (chưa có lần chạy nào)")
    print("\nChi phí theo ngày:")
    for c in st.cost_by_day(a.days):
        print(f"  {c['day']}  {c['flow_id'][:24]:24} ${c['usd']:7.3f}  {c['calls']} lượt gọi agent")
    today = date.today()
    for f in load_flows(a.flows):
        if f.enabled:
            print(f"  hôm nay {f.id}: {'đã chạy' if st.ran_today(f.id, today) else 'CHƯA chạy'}"
                  f" · đã chi ${st.spent_today(f.id, today):.2f}/{f.max_cost_usd_per_day:g}")
    return 0


def cmd_catchup(a) -> int:
    """Chạy bù thủ công những luồng hôm nay chưa chạy (tốn chi phí API)."""
    import asyncio
    from .daemon import catchup_reason, now_local, run_guarded
    from .notify import Notifier
    st = Store(a.db)
    flows = load_flows(a.flows)
    if a.flow_id:
        flows = [f for f in flows if f.id == a.flow_id] or sys.exit(f"Không có luồng '{a.flow_id}'")
    todo = []
    for f in flows:
        why = None if a.force else catchup_reason(f, st, now_local(f))
        print(f"{f.id}: {'CHẠY BÙ' if why is None else 'bỏ qua — ' + why}")
        if why is None:
            todo.append(f)
    if not todo:
        return 0
    from .logging_setup import setup as setup_logging
    setup_logging()
    n = Notifier()
    async def go():
        for f in todo:
            await run_guarded(f, db=a.db, notifier=n, store=st, trigger="bù thủ công")
    asyncio.run(go())
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="agnet")
    p.add_argument("--flows", default="config/flows.yaml")
    p.add_argument("--db", default="agnet.db")
    sp = p.add_subparsers(dest="cmd", required=True)
    sp.add_parser("flows", help="liệt kê & kiểm tra cấu hình luồng").set_defaults(fn=cmd_flows)
    v = sp.add_parser("validate", help="kiểm tra script.json"); v.add_argument("script"); v.add_argument("--flow"); v.set_defaults(fn=cmd_validate)
    b = sp.add_parser("budget", help="ngân sách từ theo thời lượng"); b.add_argument("--minutes", type=float, required=True)
    b.add_argument("--wpm", type=float, required=True); b.add_argument("--weights", help="vd 1,3,3,3,2,1"); b.set_defaults(fn=cmd_budget)
    c = sp.add_parser("count", help="đếm từ & ước thời lượng"); c.add_argument("--wpm", type=float, required=True); c.add_argument("--file"); c.set_defaults(fn=cmd_count)
    d = sp.add_parser("dedup", help="kiểm tra trùng đề tài 30 ngày"); d.add_argument("title"); d.set_defaults(fn=cmd_dedup)
    k = sp.add_parser("claim", help="khoá đề tài"); k.add_argument("flow_id"); k.add_argument("title"); k.set_defaults(fn=cmd_claim)
    r = sp.add_parser("run", help="chạy ngay một luồng (tốn chi phí API)"); r.add_argument("flow_id"); r.set_defaults(fn=cmd_run)
    sp.add_parser("serve", help="chạy nền theo lịch mọi luồng đang bật (log + bù lịch + thông báo)").set_defaults(fn=cmd_serve)
    sp.add_parser("doctor", help="kiểm tra điều kiện chạy tự động (không tốn API)").set_defaults(fn=cmd_doctor)
    sp.add_parser("gui", help="mở phần mềm quản lý (cửa sổ desktop)").set_defaults(fn=cmd_gui)
    st = sp.add_parser("status", help="lịch sử chạy & chi phí"); st.add_argument("--limit", type=int, default=12)
    st.add_argument("--days", type=int, default=7); st.add_argument("--flow"); st.set_defaults(fn=cmd_status)
    cu = sp.add_parser("catchup", help="chạy bù luồng hôm nay chưa chạy (tốn chi phí API)")
    cu.add_argument("flow_id", nargs="?"); cu.add_argument("--force", action="store_true"); cu.set_defaults(fn=cmd_catchup)
    a = p.parse_args(argv)
    load_env()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
