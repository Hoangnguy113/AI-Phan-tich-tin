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


# ---- engine (v1.2: Gemini khảo sát, Claude phán đoán) ----
GEMINI_AGENTS = {"trend-scout", "video-platform-scout", "news-scout", "community-scout",
                 "domain-internal-scout", "keyword-miner", "competitor-gap-analyst"}


def _frontmatters():
    import re
    out = {}
    for f in sorted(Path(AGENT_DIR).glob("*.md")):
        text = f.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
        assert m, f.name
        out[f.stem] = (yaml.safe_load(m.group(1)), m.group(2))
    return out


def test_all_seventeen_declare_valid_engine_and_name_matches_file():
    fm = _frontmatters()
    assert len(fm) == 17
    for stem, (meta, _) in fm.items():
        assert meta.get("engine") in {"claude", "gemini"}, stem
        assert stem.split("-", 1)[1] == meta["name"], stem


def test_exactly_seven_gemini_agents():
    fm = _frontmatters()
    assert {m["name"] for m, _ in fm.values() if m["engine"] == "gemini"} == GEMINI_AGENTS


def test_gemini_prompts_carry_contract_and_forbid_fabrication():
    for stem, (meta, body) in _frontmatters().items():
        if meta["engine"] != "gemini":
            continue
        low = body.lower()
        assert "RawItem" in body and "url" in low, stem
        assert "TaskContract" in body, stem
        assert "cấm bịa" in low, stem
        assert "no_search_tool" in body and "trí nhớ" in low, stem


def test_fact_checker_and_deep_researcher_stay_claude_with_note():
    fm = _frontmatters()
    for stem in ("11-deep-researcher", "12-fact-checker"):
        meta, body = fm[stem]
        assert meta["engine"] == "claude" and "MANG NGUỒN VỀ" in body


def test_ngay_dang_bat_buoc_o_agent_04_08_09_va_enrich_bat_mac_dinh():
    from pathlib import Path
    from agnet.pipeline.pipeline import Pipeline
    d = Path(__file__).resolve().parents[1] / ".claude" / "agents"
    for f in ("04-community-scout", "08-keyword-miner", "09-competitor-gap-analyst"):
        t = (d / f"{f}.md").read_text(encoding="utf-8")
        assert "YYYY-MM-DD hoặc null" not in t and "BẮT BUỘC" in t, f
    assert Pipeline.__dataclass_fields__["enrich_agents"].default == ("keyword-miner", "competitor-gap-analyst")


def test_agent_doc_web_khong_co_bash_va_khong_co_cong_cu_ghi():
    from agnet.pipeline.agents import AgentError, load_agents
    specs = load_agents()
    for n, s in specs.items():
        assert not ({"Write", "Edit", "MultiEdit", "NotebookEdit"} & set(s.tools)), n
        assert not ("Bash" in s.tools and {"WebFetch", "WebSearch"} & set(s.tools)), n
    for f in ("01-trend-scout", "02-video-platform-scout", "03-news-scout", "05-domain-internal-scout"):
        from pathlib import Path
        t = (Path(__file__).resolve().parents[1] / ".claude" / "agents" / f"{f}.md").read_text(encoding="utf-8")
        assert "YYYY-MM-DD hoặc null" not in t and "BẮT BUỘC" in t, f


def test_load_agents_tu_choi_agent_co_quyen_ghi_hoac_web_cung_bash(tmp_path):
    import pytest
    from agnet.pipeline.agents import AgentError, load_agents
    for tools in ("Read, Write", "WebFetch, Bash", "Read, Edit, Bash"):
        (tmp_path / "x.md").write_text(f"---\nname: x\ndescription: d\ntools: {tools}\n---\nbody", encoding="utf-8")
        with pytest.raises(AgentError):
            load_agents(tmp_path)
