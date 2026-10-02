import pytest
from pydantic import ValidationError
from agnet.core.models import Flow, load_flows

BASE = dict(id="a", name="A", topic="t", schedule=["0 5 * * *"])


def test_sample_flows_load():
    f = load_flows("config/flows.yaml")[0]
    assert f.wpm == 160 and f.aspect_ratio == "16:9" and f.output_language == "vi"


def test_german_defaults_wpm_140():
    f = Flow(**BASE, language="vi", output_language="de", platform="youtube")
    assert f.wpm == 140


def test_tiktok_ratio():
    assert Flow(**BASE, platform="tiktok").aspect_ratio == "9:16"


@pytest.mark.parametrize("bad", [
    dict(duration_min=2), dict(duration_max=25), dict(id="a b"),
    dict(sensitive=True, human_review=False),
    dict(mode="breaking"),
    dict(duration_mix={"3-5": 1}, daily_quota=10),
    dict(koc={"enabled": True}),
    dict(schedule=[]),
])
def test_invalid_flows_rejected(bad):
    with pytest.raises(ValidationError):
        Flow(**{**BASE, **bad})
