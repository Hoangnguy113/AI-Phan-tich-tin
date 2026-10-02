import pytest
from agnet.core import scoring as sc


def _inp(vals, sid="s1"):
    return sc.ScoreInput(story_id=sid, components={k: sc.Component(value=v, evidence=f"nguồn {k}") for k, v in vals.items()})


ALL100 = {k: 100 for k in sc.COMPONENTS}


def test_weights_file_sums_to_one():
    w = sc.load_weights("config/scoring.yaml")
    assert abs(sum(w.values()) - 1) < 1e-9
    assert abs(sum(sc.load_weights("config/scoring.yaml", breaking=True).values()) - 1) < 1e-9


def test_perfect_and_zero():
    w = sc.load_weights("config/scoring.yaml")
    assert sc.trend_score(_inp(ALL100), w) == 100
    assert sc.trend_score(_inp({k: 0 for k in sc.COMPONENTS}), w) == 0


def test_missing_component_refuses_not_guesses():
    w = sc.load_weights("config/scoring.yaml")
    partial = {k: 80 for k in sc.COMPONENTS if k != "velocity"}
    with pytest.raises(sc.MissingEvidence):
        sc.trend_score(_inp(partial), w)


def test_empty_evidence_rejected():
    with pytest.raises(ValueError):
        sc.Component(value=50, evidence="   ")


def test_rank_drops_unscorable_and_sorts():
    w = sc.load_weights("config/scoring.yaml")
    low = _inp({k: 30 for k in sc.COMPONENTS}, "low")
    high = _inp({k: 90 for k in sc.COMPONENTS}, "high")
    bad = _inp({"velocity": 99}, "bad")
    assert [s for s, _ in sc.rank([low, bad, high], w, 5)] == ["high", "low"]


def test_bad_weights_rejected(tmp_path):
    w = sc.load_weights("config/scoring.yaml")
    w["velocity"] += 0.1
    with pytest.raises(ValueError):
        sc.save_weights(w, tmp_path / "x.yaml")
