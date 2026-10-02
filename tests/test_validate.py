import pytest
from agnet.core.models import Flow
from agnet.core.validate import has_errors, validate_script

FLOW = Flow(id="suckhoe-yt-sang", name="x", topic="t", schedule=["0 5 * * *"], duration_min=3, duration_max=20,
            strict_factcheck=True, sensitive=True, human_review=True)


def errs(issues):
    return [str(i) for i in issues if i.severity == "error"]


def test_valid_doc_passes(doc):
    assert not has_errors(validate_script(doc, FLOW)), errs(validate_script(doc, FLOW))


def test_valid_koc_doc_passes(koc_doc):
    assert not has_errors(validate_script(koc_doc)), errs(validate_script(koc_doc))


def test_missing_required_field(doc):
    del doc["narrator"]
    assert any("narrator" in e for e in errs(validate_script(doc)))


def test_gap_between_scenes_detected(doc):
    doc["segments"][0]["scenes"][2]["start_sec"] += 3
    assert any("hở/chồng" in e for e in errs(validate_script(doc)))


def test_total_duration_outside_tolerance(doc):
    doc["target_duration_sec"] = doc["target_duration_sec"] * 1.3
    assert any("lệch" in e for e in errs(validate_script(doc)))


def test_voiceover_too_long_for_scene(doc):
    doc["segments"][0]["scenes"][0]["voiceover"] = " ".join(["từ"] * 60)
    assert any("lời thoại" in e for e in errs(validate_script(doc)))


def test_platform_ratio_mismatch(doc):
    doc["aspect_ratio"] = "9:16"
    assert any("không dùng" in e for e in errs(validate_script(doc)))


def test_unverified_source_blocks(doc):
    doc["sources"][0]["verified"] = False
    assert any("chưa xác minh" in e for e in errs(validate_script(doc)))


def test_dangling_source_id(doc):
    doc["segments"][0]["scenes"][0]["source_ids"] = ["src_99"]
    assert any("src_99" in e for e in errs(validate_script(doc)))


def test_low_qa_blocks(doc):
    doc["qa"]["score"] = 7.9
    assert any("QA" in e for e in errs(validate_script(doc)))


def test_sensitive_flow_requires_human_review(doc):
    doc["qa"]["human_review_required"] = False
    assert any("human_review" in e for e in errs(validate_script(doc, FLOW)))


def test_title_without_truth_check_rejected(doc):
    del doc["packaging"]["titles"][0]["truth_check"]
    assert has_errors(validate_script(doc))


def test_rumor_check_title_must_be_question(doc):
    doc["packaging"]["titles"][0]["technique"] = "rumor_check"
    assert any("câu hỏi" in e for e in errs(validate_script(doc)))
    doc["packaging"]["titles"][0]["text"] = "5 sai lầm khi ăn sáng – tin đồn hay sự thật?"
    doc["title"] = doc["packaging"]["titles"][0]["text"]
    assert not any("câu hỏi" in e for e in errs(validate_script(doc)))


def test_flow_mismatch(doc):
    doc["platform"] = "tiktok"
    doc["aspect_ratio"] = "9:16"
    assert any("nền tảng của luồng" in e for e in errs(validate_script(doc, FLOW)))


def test_koc_ratio_out_of_range(koc_doc):
    for _, sc in [(0, s) for seg in koc_doc["segments"] for s in seg["scenes"]]:
        if sc["visual"]["type"] == "koc":
            sc["visual"] = {"type": "broll", "description": "cảnh b-roll"}
    assert any("25–40%" in e for e in errs(validate_script(koc_doc)))


def test_koc_requires_ai_disclosure(koc_doc):
    koc_doc["packaging"]["ai_disclosure"] = False
    assert any("ai_disclosure" in e for e in errs(validate_script(koc_doc)))


def test_koc_scene_when_disabled(koc_doc):
    koc_doc["koc"]["enabled"] = False
    assert any("koc.enabled=false" in e for e in errs(validate_script(koc_doc)))


def test_koc_prompt_ref_must_point_to_own_scene(koc_doc):
    for seg in koc_doc["segments"]:
        for sc in seg["scenes"]:
            if sc["visual"]["type"] == "koc":
                sc["visual"]["koc"]["prompt_ref"] = "koc_prompts.json#S9.9"
                break
    assert any("không trỏ về chính cảnh này" in e for e in errs(validate_script(koc_doc)))


def test_koc_wardrobe_required(koc_doc):
    del koc_doc["koc"]["wardrobe_set"]
    assert any("wardrobe_set" in e for e in errs(validate_script(koc_doc)))


def test_flow_requires_koc_but_script_has_none(doc):
    f = Flow(id="suckhoe-yt-sang", name="x", topic="t", schedule=["0 5 * * *"],
             koc={"enabled": True, "character_id": "KOC-02-THAO"})
    assert any("luồng bật KOC" in e for e in errs(validate_script(doc, f)))
