"""Nạp 17 agent từ .claude/agents/*.md và cung cấp bộ chạy agent (Claude Agent SDK hoặc giả lập cho test)."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import yaml

ROOT = Path(__file__).resolve().parents[2]
AGENT_DIR = ROOT / ".claude" / "agents"
SKILL_DIR = ROOT / ".claude" / "skills"
GEMINI_AGENTS = frozenset({"trend-scout", "video-platform-scout", "news-scout", "community-scout",
                           "domain-internal-scout", "keyword-miner", "competitor-gap-analyst"})
WRITE_TOOLS = frozenset({"Write", "Edit", "MultiEdit", "NotebookEdit"})
WRITE_TOOLS_L = frozenset(t.lower() for t in WRITE_TOOLS)


@dataclass
class AgentSpec:
    name: str
    description: str
    model: str
    tools: list[str]
    skills: list[str]
    prompt: str
    engine: str = "claude"       # claude | gemini (mục 18); gemini chỉ có hiệu lực khi cài đặt bật provider


@dataclass
class AgentResult:
    text: str
    cost_usd: float = 0.0
    tokens: int = 0


class AgentError(RuntimeError):
    pass


def load_agents(directory: Path | str = AGENT_DIR) -> dict[str, AgentSpec]:
    specs: dict[str, AgentSpec] = {}
    for f in sorted(Path(directory).glob("*.md")):
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", f.read_text(encoding="utf-8"), re.S)
        if not m:
            raise AgentError(f"{f.name}: thiếu frontmatter")
        meta = yaml.safe_load(m.group(1))
        raw_tools = meta.get("tools", "")
        if isinstance(raw_tools, (list, tuple)):
            raw_tools = ",".join(str(t) for t in raw_tools)
        tools = [t.strip() for t in str(raw_tools).split(",") if t.strip()]
        base = {re.sub(r"\(.*$", "", t).strip().lower() for t in tools}      # "Write(*)" → "write", chữ thường
        writers = sorted(t for t in tools if re.sub(r"\(.*$", "", t).strip().lower() in WRITE_TOOLS_L
                         or re.search(r"write|edit", t, re.I))
        if writers:                                   # quy tắc cứng: agent không có quyền ghi (file do code xuất)
            raise AgentError(f"{f.name}: agent không được có công cụ ghi {writers}")
        engine = str(meta.get("engine", "claude")).strip().lower()
        if engine not in ("claude", "gemini"):
            raise AgentError(f"{f.name}: engine không hợp lệ {engine!r}")
        if engine == "gemini" and meta["name"] not in GEMINI_AGENTS:
            raise AgentError(f"{f.name}: engine gemini chỉ dành cho agent khảo sát (QA/viết/đạo diễn luôn là Claude)")
        if "bash" in base and {"webfetch", "websearch"} & base:
            raise AgentError(f"{f.name}: agent đọc web không được có Bash (prompt-injection → chạy lệnh)")
        spec = AgentSpec(meta["name"], meta["description"], meta.get("model", "sonnet"), tools,
                         meta.get("skills") or [], m.group(2).strip(),
                         str(meta.get("engine", "claude")).strip().lower() or "claude")
        if spec.name in specs:
            raise AgentError(f"trùng tên agent {spec.name}")
        specs[spec.name] = spec
    return specs


def skill_text(name: str) -> str:
    p = SKILL_DIR / name / "SKILL.md"
    if not p.exists():
        raise AgentError(f"skill {name!r} không tồn tại")
    body = re.sub(r"^---\n.*?\n---\n", "", p.read_text(encoding="utf-8"), flags=re.S)
    return body.strip()


def extract_json(text: str) -> dict | list:
    """Lấy JSON từ câu trả lời của agent (có thể bọc ```json ... ``` hoặc kèm lời dẫn)."""
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    candidates = [fence.group(1)] if fence else []
    candidates.append(text)
    for c in candidates:
        c = c.strip()
        for start in (m.start() for m in re.finditer(r"[\[{]", c)):
            try:
                return json.JSONDecoder().raw_decode(c[start:])[0]
            except json.JSONDecodeError:
                continue
    raise AgentError("agent không trả JSON hợp lệ")


class AgentRunner(Protocol):
    async def run(self, agent: AgentSpec, prompt: str, *, max_budget_usd: float) -> AgentResult: ...


class SdkRunner:
    """Chạy một agent bằng Claude Agent SDK. Chưa được kiểm thử với API thật trong repo này."""

    def __init__(self, cwd: Path | str = ROOT, max_turns: int = 30):
        self.cwd, self.max_turns = str(cwd), max_turns

    async def run(self, agent: AgentSpec, prompt: str, *, max_budget_usd: float) -> AgentResult:
        from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query  # nạp muộn: chỉ cần khi chạy thật

        system = agent.prompt + "\n\n" + "\n\n".join(f"# Skill: {s}\n{skill_text(s)}" for s in agent.skills)
        opts = ClaudeAgentOptions(
            system_prompt=system, model=agent.model, allowed_tools=agent.tools, cwd=self.cwd,
            max_turns=self.max_turns, max_budget_usd=max_budget_usd, permission_mode="dontAsk",
            env={"CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "0"},  # agent này không được tự đẻ subagent
            # Ba tham số dưới cắt chi phí cố định mỗi lượt gọi từ 61.517 còn 6.831 token (đo 01/10/2026).
            # Agnet tự dựng system prompt và tự đọc .claude/agents, .claude/skills bằng Python,
            # nên không cần Claude Code nạp settings/plugin/hook/CLAUDE.md của máy.
            setting_sources=[],
            strict_mcp_config=True,
            tools=list(agent.tools),  # allowed_tools là QUYỀN; tools quyết định gửi định nghĩa nào
        )
        text, cost = "", 0.0
        async for msg in query(prompt=prompt, options=opts):
            if isinstance(msg, ResultMessage):
                text = msg.result or ""
                cost = float(msg.total_cost_usd or 0.0)
                if msg.is_error:
                    raise AgentError(f"{agent.name}: {msg.subtype} — {(msg.result or '')[:200]}")
        return AgentResult(text=text, cost_usd=cost)
