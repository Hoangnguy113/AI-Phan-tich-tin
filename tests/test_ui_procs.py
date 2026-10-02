"""Lệnh tiến trình con của GUI — không chạy lệnh thật."""
from __future__ import annotations

import sys

from agnet.ui import procs


def test_lenh_chay_mot_luong():
    cmd = procs.run_flow_cmd("luong-a", "config/flows.yaml", "agnet.db")
    assert cmd[:2] == [sys.executable, "-m"] and cmd[2] == "agnet"
    assert cmd[-2:] == ["run", "luong-a"]
    assert "--flows" in cmd and "config/flows.yaml" in cmd


def test_lenh_bu_lich():
    assert procs.catchup_cmd("f.yaml", "d.db")[-1] == "catchup"
    assert procs.catchup_cmd("f.yaml", "d.db", "luong-a")[-1] == "luong-a"
    assert procs.catchup_cmd("f.yaml", "d.db", "luong-a", force=True)[-1] == "--force"


def test_lenh_serve_va_doctor():
    assert procs.serve_cmd("f.yaml", "d.db")[-1] == "serve"
    assert procs.doctor_cmd("f.yaml", "d.db")[-1] == "doctor"


def test_tien_trinh_con_khong_mang_api_key(monkeypatch):
    """Chốt chặn: GUI phải chạy pipeline bằng tài khoản, không bằng khoá API."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-abc")
    assert "ANTHROPIC_API_KEY" not in procs.child_env()
    assert procs.child_env(drop_api_key=False)["ANTHROPIC_API_KEY"] == "sk-ant-abc"


def test_moi_truong_con_doc_duoc_tieng_viet():
    assert procs.child_env()["PYTHONIOENCODING"] == "utf-8"
