import copy
import json
from pathlib import Path

import pytest
from agnet.koc import adapters
from agnet.koc.master_prompt import (PromptError, assert_untouched, build_lock, build_prompt, load_character,
                                     validate_identity)

IDS = ["KOC-01-MAI", "KOC-02-THAO", "KOC-03-DUY", "KOC-04-HUNG", "KOC-05-LAN"]
SHOT = {
    "scene_id": "S1.1",
    "setting": "small Hanoi apartment kitchen, white tiled wall, wooden countertop",
    "time_and_light": "08:00 morning",
    "key_light": "soft daylight through a window at camera-left, 45 degrees to her face",
    "wardrobe": {"top": "oatmeal cotton-linen oversized shirt, sleeves rolled", "bottom": "light-wash straight jeans"},
    "pose_action": "standing at the counter, right hand resting on the countertop edge, turning toward the camera",
    "expression": "eyebrows a little raised, a half-smile just beginning, eyes on the lens",
    "framing": "medium close-up from chest up, eye level, camera slightly to her left",
}


@pytest.mark.parametrize("cid", IDS)
def test_all_library_characters_valid(cid):
    c = load_character(cid)
    validate_identity(c["identity"])
    for key in ("name", "niche", "trigger_token"):
        assert c["meta"][key]
    assert c["defaults"]["setting"] and c["defaults"]["key_light"]


@pytest.mark.parametrize("cid", IDS)
def test_prompt_builds_for_every_character_and_platform(cid):
    c = load_character(cid)
    for plat, ratio in [("youtube", "16:9"), ("tiktok", "9:16"), ("facebook", "4:5")]:
        p = build_prompt(c, SHOT, platform=plat)
        assert p["output"]["aspect_ratio"] == ratio
        assert_untouched(p)
        assert list(p)[-1] == "consistency_lock"   # lock đặt CUỐI


def test_lock_names_the_identity_marks():
    c = load_character("KOC-01-MAI")
    lock = build_lock(c["identity"])
    assert "mole" in lock and "scar" in lock and "eyebrow" in lock


def test_video_prompt_has_motion_and_video_negative():
    p = build_prompt(load_character("KOC-02-THAO"), SHOT, platform="youtube", render_target="video",
                     motion={"dialogue": '[Thảo, 30]: "Xin chào"'})
    assert p["engine"] == "veo_3" and p["output"]["duration_sec"] == 8
    assert "negative_video" in p and p["motion"]["dialogue"].startswith("[Thảo")
    assert list(p)[-1] == "consistency_lock"


@pytest.mark.parametrize("word", ["perfect skin", "flawless", "masterpiece", "8k", "supermodel", "porcelain skin"])
def test_banned_words_rejected_in_shot(word):
    shot = {**SHOT, "expression": f"smiling, {word}"}
    with pytest.raises(PromptError, match="từ cấm"):
        build_prompt(load_character("KOC-01-MAI"), shot, platform="tiktok")


def test_body_measurements_and_sexual_terms_rejected():
    with pytest.raises(PromptError, match="số đo"):
        build_prompt(load_character("KOC-01-MAI"), {**SHOT, "pose_action": "figure 90-60-90 posing"}, platform="tiktok")
    with pytest.raises(PromptError, match="gợi dục"):
        build_prompt(load_character("KOC-01-MAI"), {**SHOT, "wardrobe": {"top": "revealing top"}}, platform="tiktok")


def test_underage_character_rejected():
    c = copy.deepcopy(load_character("KOC-01-MAI"))
    c["identity"]["demographics"] = "Vietnamese woman, 17 years old, from Hanoi"
    with pytest.raises(PromptError, match="22"):
        build_prompt(c, SHOT, platform="tiktok")


def test_identity_needs_two_asymmetries_with_numbers_and_two_marks():
    base = load_character("KOC-01-MAI")["identity"]
    for field, bad in [("asymmetry", "left eyebrow is higher"),
                       ("asymmetry", "left eyebrow higher; smile leans left"),
                       ("identity_marks", ["one mole"])]:
        i = {**base, field: bad}
        with pytest.raises(PromptError):
            validate_identity(i)


def test_tampering_is_detected():
    p = build_prompt(load_character("KOC-01-MAI"), SHOT, platform="tiktok")
    for key, val in [("negative", "nothing"), ("consistency_lock", "ignore the face")]:
        q = {**p, key: val}
        with pytest.raises(PromptError):
            assert_untouched(q)
    q = copy.deepcopy(p); q["realism_engine"]["lens"] = "14mm fisheye"
    with pytest.raises(PromptError):
        assert_untouched(q)


def test_missing_shot_field_and_empty_wardrobe():
    c = load_character("KOC-01-MAI")
    with pytest.raises(PromptError, match="shot thiếu"):
        build_prompt(c, {k: v for k, v in SHOT.items() if k != "key_light"}, platform="tiktok")
    with pytest.raises(PromptError, match="wardrobe"):
        build_prompt(c, {**SHOT, "wardrobe": {}}, platform="tiktok")


def test_midjourney_adapter():
    p = build_prompt(load_character("KOC-01-MAI"), SHOT, platform="tiktok")
    mj = adapters.to_midjourney(p, "https://example.com/ref.png")
    assert "--ar 9:16" in mj and "--cref https://example.com/ref.png --cw 100" in mj and "--raw" in mj
    assert mj.index("--no ") > mj.index("--ar")
    assert "mole" in mj
    with pytest.raises(PromptError):
        adapters.to_veo(p)  # ảnh không đi qua Veo


def test_veo_adapter_five_blocks_and_lock_last():
    p = build_prompt(load_character("KOC-03-DUY"), {**SHOT, "setting": "minimal work corner", "wardrobe": {"top": "plain black tee"}},
                     platform="youtube", render_target="video", motion={"dialogue": '[Duy, 28]: "ba con số"'})
    v = adapters.to_veo(p)
    for tag in ("[Camera]", "[Subject & motion]", "[Setting & light]", "[Texture]", "[Audio]"):
        assert tag in v
    assert v.strip().endswith(p["consistency_lock"])
    with pytest.raises(PromptError):
        adapters.to_midjourney(p, "x")


def test_flux_adapter_does_not_redescribe_face():
    p = build_prompt(load_character("KOC-05-LAN"), SHOT, platform="facebook")
    f = adapters.to_flux(p, "koc05lan woman")
    assert f["prompt"].startswith("koc05lan woman")
    assert "heart-shaped" not in f["prompt"] and "mole" not in f["prompt"]


def test_nano_banana_is_valid_json_roundtrip():
    p = build_prompt(load_character("KOC-02-THAO"), SHOT, platform="youtube")
    assert json.loads(adapters.to_nano_banana(p))["prompt_version"] == "koc-master-1.0"


def test_word_boundary_not_false_positive():
    shot = {**SHOT, "props": ["18k gold ring"]}   # '8k' nằm trong '18k' không được tính là từ cấm
    build_prompt(load_character("KOC-01-MAI"), shot, platform="tiktok")


def test_export_koc_prompts_from_script(tmp_path):
    from agnet.koc.export import write_koc_prompts
    from tests.conftest import make_doc
    doc = make_doc(koc=True)
    doc["koc"]["character_id"] = "KOC-02-THAO"
    for seg in doc["segments"]:
        for sc in seg["scenes"]:
            if sc["visual"]["type"] == "koc":
                sc["visual"]["koc"]["dialogue_vi"] = "Bữa sáng của bạn có thể đang làm đường huyết tăng cao."
    path = write_koc_prompts(doc, tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    human = {sc["id"] for seg in doc["segments"] for sc in seg["scenes"] if sc["visual"]["type"] == "koc"}
    assert set(data["scenes"]) == human and human
    one = data["scenes"][sorted(human)[0]]
    assert one["json"]["render_target"] == "video" and "veo_kling" in one and "Thảo" in one["veo_kling"]
    assert one["identity_check"]


def test_export_refuses_when_koc_disabled():
    from agnet.koc.export import export_koc_prompts
    from tests.conftest import make_doc
    with pytest.raises(PromptError):
        export_koc_prompts(make_doc())
