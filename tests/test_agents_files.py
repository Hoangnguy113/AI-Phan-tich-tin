import yaml
from pathlib import Path

from agnet.pipeline.agents import AGENT_DIR, SKILL_DIR, extract_json, load_agents, skill_text, AgentError
import pytest

EXPECTED = {"trend-scout", "video-platform-scout", "news-scout", "community-scout", "domain-internal-scout",
            "dedup-cluster", "trend-scorer", "keyword-miner", "competitor-gap-analyst", "content-strategist",
            "deep-researcher", "fact-checker", "script-writer", "director", "hook-packaging",
            "editor-in-chief", "koc-character-director"}


def test_seventeen_agents_with_valid_frontmatter():
    agents = load_agents()
    assert set(agents) == EXPECTED and len(agents) == 17
    for a in agents.values():
        assert a.model in {"haiku", "sonnet", "opus"} and a.description and a.prompt and a.tools


def test_model_tiers_match_plan_section_13():
    a = load_agents()
    assert {n for n, x in a.items() if x.model == "opus"} == {"content-strategist", "editor-in-chief"}
    scouts = {"trend-scout", "video-platform-scout", "news-scout", "community-scout", "domain-internal-scout"}
    assert all(a[n].model == "haiku" for n in scouts)


def test_every_referenced_skill_exists_and_has_valid_frontmatter():
    used = {s for a in load_agents().values() for s in a.skills}
    assert len(used) == 6
    for s in used:
        assert skill_text(s)
        raw = (SKILL_DIR / s / "SKILL.md").read_text(encoding="utf-8")
        meta = yaml.safe_load(raw.split("---")[1])
        assert meta["name"] == s and len(meta["description"]) > 40


def test_no_agent_can_write_files_except_none():
    # file đầu ra do code ghi (pipeline.export), agent không được Write/Edit
    for a in load_agents().values():
        assert "Write" not in a.tools and "Edit" not in a.tools, a.name


def test_extract_json_variants():
    assert extract_json('{"a":1}') == {"a": 1}
    assert extract_json('Đây là kết quả:\n```json\n{"a": [1,2]}\n```\nxong') == {"a": [1, 2]}
    assert extract_json('lời dẫn {"x": {"y": 2}} đuôi') == {"x": {"y": 2}}
    with pytest.raises(AgentError):
        extract_json("không có json")
