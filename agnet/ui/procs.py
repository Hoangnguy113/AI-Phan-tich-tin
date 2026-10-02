"""Dựng lệnh cho tiến trình con của GUI.

Việc tốn tiền hoặc chạy lâu (run, serve, catchup) luôn chạy ở TIẾN TRÌNH RIÊNG, không
chạy trong tiến trình GUI: giữ cửa sổ không treo và tái dùng đúng phần đã có test
(khoá một bản chạy, bù lịch, log, trần thời gian).

Phần này thuần dữ liệu để kiểm được bằng test; QProcess nằm ở lớp widget.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from ..env import ROOT


def _base(flows: str | Path, db: str | Path) -> list[str]:
    return [sys.executable, "-m", "agnet", "--flows", str(flows), "--db", str(db)]


def run_flow_cmd(flow_id: str, flows: str | Path, db: str | Path) -> list[str]:
    return _base(flows, db) + ["run", flow_id]


def catchup_cmd(flows: str | Path, db: str | Path, flow_id: str | None = None,
                force: bool = False) -> list[str]:
    cmd = _base(flows, db) + ["catchup"]
    if flow_id:
        cmd.append(flow_id)
    if force:
        cmd.append("--force")
    return cmd


def serve_cmd(flows: str | Path, db: str | Path) -> list[str]:
    return _base(flows, db) + ["serve"]


def doctor_cmd(flows: str | Path, db: str | Path) -> list[str]:
    return _base(flows, db) + ["doctor"]


def child_env(drop_api_key: bool = True) -> dict[str, str]:
    """Môi trường cho tiến trình con.

    Bỏ ANTHROPIC_API_KEY để pipeline dùng TÀI KHOẢN Claude đã đăng nhập. Đo 01/10/2026:
    có khoá thì Claude Code ưu tiên khoá và bỏ qua tài khoản.
    """
    env = dict(os.environ)
    if drop_api_key:
        env.pop("ANTHROPIC_API_KEY", None)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"
    return env


def log_file(log_dir: str | Path | None = None) -> Path:
    return Path(log_dir or ROOT / "logs") / "agnet.log"
