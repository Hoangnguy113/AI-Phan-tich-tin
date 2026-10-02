import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest


def make_doc(n_scenes_per_seg=8, segs=4, wpm=160, scene_sec=9.0, koc=False):
    """Sinh script.json hợp lệ ~ 4*8*9 = 288s (4,8 phút). Lời thoại vừa khít thời lượng."""
    words_per_scene = int((scene_sec - 0.4) * wpm / 60)
    vo = " ".join(["từ"] * words_per_scene)
    segments, t = [], 0.0
    idx = 0
    for s in range(1, segs + 1):
        scenes, st = [], t
        for k in range(1, n_scenes_per_seg + 1):
            idx += 1
            human = koc and idx % 3 == 0
            visual = {"type": "koc" if human else "broll", "description": f"cảnh {s}.{k}"}
            if human:
                visual["koc"] = {"render_target": "video", "duration_sec": 8,
                                 "prompt_ref": f"koc_prompts.json#S{s}.{k}", "identity_check": ["mole below left eye"]}
            scenes.append({"id": f"S{s}.{k}", "start_sec": round(t, 2), "duration_sec": scene_sec, "voiceover": vo,
                           "visual": visual, "transition_out": "cut", "source_ids": ["src_01"]})
            t += scene_sec
        segments.append({"id": f"S{s}", "name": f"Phân đoạn {s}", "start_sec": st, "end_sec": round(t, 2), "scenes": scenes})
    doc = {
        "schema_version": "1.0", "id": "2026-10-01_suckhoe-yt-sang_01", "flow_id": "suckhoe-yt-sang",
        "platform": "youtube", "aspect_ratio": "16:9", "language": "vi", "target_duration_sec": t, "wpm": wpm,
        "title": "5 sai lầm khi ăn sáng",
        "narrator": {"persona": "Bác sĩ trẻ"},
        "segments": segments,
        "packaging": {"titles": [{"text": "5 sai lầm khi ăn sáng", "technique": "number", "truth_check": "Số liệu có nguồn src_01"}]},
        "sources": [{"id": "src_01", "title": "WHO", "url": "https://who.int", "verified": True}],
        "qa": {"score": 8.6, "flags": [], "human_review_required": True},
        "trend": {"score": 87},
    }
    if koc:
        doc["koc"] = {"enabled": True, "character_id": "KOC-02-THAO", "wardrobe_set": "linen pastel", "human_scene_ratio": 0.33}
        doc["packaging"]["ai_disclosure"] = True
    return doc


@pytest.fixture
def doc():
    return make_doc()


@pytest.fixture
def koc_doc():
    return make_doc(koc=True)


@pytest.fixture
def clone():
    return copy.deepcopy
