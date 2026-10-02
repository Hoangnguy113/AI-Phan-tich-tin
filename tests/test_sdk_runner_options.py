"""Kiểm SdkRunner chỉ gửi đúng ngữ cảnh cần thiết cho mỗi lượt gọi agent.

Đo thực tế 01/10/2026: không đặt `setting_sources` và `tools` làm mỗi lượt gọi tốn
61.517 token đầu vào (plugin của máy có 1005 SKILL.md + định nghĩa mọi công cụ
tích hợp). Đặt đủ ba tham số còn 6.831 token. Test này giữ không cho tái phát.
Dùng SDK giả — không gọi API thật.
"""
from __future__ import annotations

import asyncio
import sys
import types
from dataclasses import dataclass

from agnet.pipeline.agents import AgentSpec, SdkRunner


@dataclass
class _FakeResult:
    result: str = "xong"
    total_cost_usd: float = 0.0
    is_error: bool = False
    subtype: str = "success"


def _fake_sdk(captured: dict) -> types.ModuleType:
    """Module claude_agent_sdk giả, ghi lại tham số đã truyền."""
    mod = types.ModuleType("claude_agent_sdk")

    class ClaudeAgentOptions:
        def __init__(self, **kw):
            captured.update(kw)

    async def query(*, prompt, options):
        captured["prompt"] = prompt
        yield _FakeResult()

    mod.ClaudeAgentOptions = ClaudeAgentOptions
    mod.ResultMessage = _FakeResult
    mod.query = query
    return mod


SPEC = AgentSpec(name="director", description="đạo diễn", model="sonnet",
                 tools=["Read", "Bash"], skills=[], prompt="HƯỚNG DẪN ĐẠO DIỄN")


def _run(captured: dict, monkeypatch, spec: AgentSpec = SPEC):
    monkeypatch.setitem(sys.modules, "claude_agent_sdk", _fake_sdk(captured))
    return asyncio.run(SdkRunner().run(spec, "việc cần làm", max_budget_usd=1.0))


def test_khong_nap_settings_plugin_mcp_cua_may(monkeypatch):
    captured: dict = {}
    res = _run(captured, monkeypatch)
    assert res.text == "xong"
    assert captured["setting_sources"] == []
    assert captured["strict_mcp_config"] is True


def test_chi_gui_dinh_nghia_cong_cu_agent_can(monkeypatch):
    captured: dict = {}
    _run(captured, monkeypatch)
    assert captured["tools"] == ["Read", "Bash"]
    assert captured["allowed_tools"] == ["Read", "Bash"]


def test_tools_theo_tung_agent(monkeypatch):
    scout = AgentSpec(name="trend-scout", description="scout", model="haiku",
                      tools=["WebSearch", "WebFetch", "Read", "Bash"], skills=[], prompt="P")
    captured: dict = {}
    _run(captured, monkeypatch, scout)
    assert captured["tools"] == ["WebSearch", "WebFetch", "Read", "Bash"]


def test_khong_tu_tat_thinking_va_chan_subagent(monkeypatch):
    """Thinking là nơi ra chất lượng viết/QA — không được tự tắt để tiết kiệm."""
    captured: dict = {}
    _run(captured, monkeypatch)
    assert "thinking" not in captured
    assert captured["env"]["CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"] == "0"
