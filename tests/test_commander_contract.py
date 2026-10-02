import json
from datetime import datetime, timedelta, timezone

import pytest

from agnet.commander import ComplianceStore, TaskContract, accept, build_prompt, run_contract
from agnet.gemini.client import AllModelsExhausted, GeminiResult, GroundingUnavailable

NOW = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)


def iso(h):
    return (NOW - timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%SZ")


def item(n, url=None, hours=2, **kw):
    d = {"title": f"Tin số {n} về chip", "url": url or f"https://news.example.com/a{n}", "source": "Example",
         "published_at": iso(hours), "snippet": f"Tóm tắt {n}"}
    d.update(kw)
    return d


def res(items, urls=None, text=None):
    srcs = [{"url": u, "title": "x"} for u in (urls if urls is not None else [i["url"] for i in items if isinstance(i, dict)])]
    return GeminiResult(text=text if text is not None else json.dumps(items), model="m", sources=srcs)


def C(**kw):
    d = dict(agent="scout", flow_id="f", goal="tìm tin", min_items=2, max_age_hours=24)
    d.update(kw)
    return TaskContract(**d)


class Fake:
    def __init__(self, *outs):
        self.outs, self.prompts, self.kw = list(outs), [], []

    def generate(self, prompt, **kw):
        self.prompts.append(prompt)
        self.kw.append(kw)
        o = self.outs.pop(0)
        if isinstance(o, Exception):
            raise o
        return o


def test_prompt_nêu_cấm_bịa_và_nguồn():
    p = build_prompt(C(required_sources=["Reuters", "HN"], min_items=5))
    for s in ("TỐI THIỂU 5", "Reuters", "Bịa URL", "published_at", "24 giờ"):
        assert s in p
    assert "LẦN NỘP TRƯỚC" not in p
    assert "* lỗi A" in build_prompt(C(), ["lỗi A"])


def test_contract_validate():
    with pytest.raises(ValueError):
        C(min_items=0)


def test_accept_ca_tốt():
    its = [item(1), item(2)]
    r = accept(its, C(), res(its), NOW)
    assert r.passed and len(r.accepted) == 2 and not r.rejected


def test_url_bịa_không_có_trong_grounding():
    its = [item(1), item(2), item(3, url="https://fake.invalid-site.org/zzz")]
    r = accept(its, C(), res(its, urls=[its[0]["url"], its[1]["url"]]), NOW)
    assert r.passed and [x.reason for x in r.rejected] == ["not_grounded"]


def test_khớp_theo_miền_và_title_miền():
    its = [item(1, url="https://www.news.example.com/x"), item(2, url="https://other.org/y")]
    g = GeminiResult(text="", model="m", sources=[{"url": "https://vertex.redirect/abc", "title": "other.org"},
                                                  {"url": "https://news.example.com/zz", "title": "t"}])
    assert len(accept(its, C(), g, NOW).accepted) == 2


def test_không_grounding_thì_loại_hết():
    its = [item(1), item(2)]
    r = accept(its, C(), res(its, urls=[]), NOW)
    assert not r.passed and not r.accepted and any("grounding" in e for e in r.errors)


def test_allow_ungrounded():
    its = [item(1), item(2)]
    assert accept(its, C(allow_ungrounded=True), res(its, urls=[]), NOW).passed


def test_quá_cũ_tương_lai_ngày_hỏng_url_hỏng():
    its = [item(1), item(2, hours=100), item(3, hours=-5), item(4, published_at="hôm qua"),
           item(5, url="ftp://a.b/c"), item(6, url="not a url"), item(7)]
    its[6]["url"] = its[0]["url"]
    r = accept(its, C(min_items=1), res(its), NOW)
    assert [x.reason for x in r.rejected] == ["too_old", "future", "bad_date", "url", "url", "duplicate"]
    assert len(r.accepted) == 1 and r.passed


def test_trùng_tiêu_đề_chuẩn_hoá():
    a, b = item(1), item(2, title="TIN SỐ 1 VỀ CHIP!!")
    r = accept([a, b], C(min_items=1), res([a, b]), NOW)
    assert len(r.accepted) == 1 and r.rejected[0].reason == "duplicate"


def test_thiếu_số_lượng_không_ước_lượng():
    its = [item(1)]
    r = accept(its, C(min_items=3), res(its), NOW)
    assert not r.passed and len(r.accepted) == 1 and any("tối thiểu 3" in e for e in r.errors)


def test_schema_thiếu_trường_và_không_phải_mảng():
    r = accept([{"title": "a"}, "x", item(1)], C(min_items=1), res([item(1)]), NOW)
    assert [x.reason for x in r.rejected] == ["schema", "schema"] and r.passed
    assert not accept({"foo": 1}, C(), res([]), NOW).passed
    assert accept({"items": [item(1), item(2)]}, C(), res([item(1), item(2)]), NOW).passed


def test_runner_đạt_ngay():
    its = [item(1), item(2)]
    f = Fake(res(its))
    o = run_contract(f, C(), NOW, sleep=lambda s: None)
    assert o.passed and o.attempts == 1 and len(o.items) == 2 and len(f.prompts) == 1
    assert f.kw[0]["search"] is True


def test_runner_retry_một_lần_rồi_đạt():
    its = [item(1), item(2)]
    f = Fake(res([], text="không phải json"), res(its))
    o = run_contract(f, C(), NOW, sleep=lambda s: None)
    assert o.passed and o.attempts == 2
    assert "JSON hỏng" in f.prompts[1] and "LẦN NỘP TRƯỚC" in f.prompts[1]


def test_runner_retry_một_lần_rồi_fail_không_bịa():
    its = [item(1)]
    f = Fake(res(its), res(its))
    o = run_contract(f, C(min_items=3), NOW, sleep=lambda s: None)
    assert o.compliance == "fail" and o.attempts == 2 and len(f.prompts) == 2
    assert o.items == [] and len(o.salvaged) == 1 and "tối thiểu 3" in f.prompts[1]


def test_runner_lỗi_gemini_fail_không_retry():
    for exc in (GroundingUnavailable("chặn"), AllModelsExhausted("hết", [])):
        f = Fake(exc)
        o = run_contract(f, C(), NOW, sleep=lambda s: None)
        assert o.compliance == "fail" and o.attempts == 1 and len(f.prompts) == 1 and not o.items


def test_metrics(tmp_path):
    st = ComplianceStore(tmp_path / "t.db")
    its = [item(1), item(2)]
    ok = run_contract(Fake(res(its)), C(), NOW, sleep=lambda s: None)
    ok2 = run_contract(Fake(res([], text="x"), res(its)), C(), NOW, sleep=lambda s: None)
    bad = run_contract(Fake(res([], text="x"), res([], text="y")), C(agent="trend"), NOW, sleep=lambda s: None)
    for c, o in ((C(), ok), (C(), ok2), (C(agent="trend"), bad)):
        st.record(c, o, now=NOW)
    r = st.rates()
    assert r["scout"]["runs"] == 2 and r["scout"]["rate"] == 1.0 and r["scout"]["first_try"] == 1
    assert st.rate("trend") == 0.0 and st.rate("none") is None
    assert ComplianceStore(tmp_path / "t.db").rate("scout", last_n=1) == 1.0
