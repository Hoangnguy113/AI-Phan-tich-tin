"""Một schema, bốn công cụ (mục 17.6). Chuyển prompt JSON koc-master-1.0 sang văn bản từng công cụ."""
from __future__ import annotations

import json

from .master_prompt import PromptError


def _wardrobe(w: dict) -> str:
    return ", ".join(str(v) for v in w.values() if v)


def to_nano_banana(p: dict) -> str:
    """Nano Banana Pro / Gemini nhận JSON có cấu trúc — dán nguyên."""
    return json.dumps(p, ensure_ascii=False, indent=2)


def to_midjourney(p: dict, cref_url: str) -> str:
    """Thứ tự theo mục 17.6: identity → shot → wardrobe → setting/light → lens/exposure/film → tham số."""
    if p["render_target"] != "image":
        raise PromptError("Midjourney chỉ cho ảnh")
    i, r, s = p["identity"], p["realism_engine"], p["shot"]
    parts = [
        i["demographics"], i["face_structure"], i["asymmetry"], "; ".join(i["identity_marks"]), i["skin"],
        s["framing"], s["pose_action"], s["expression"],
        _wardrobe(s["wardrobe"]),
        s["setting"], s["time_and_light"], s["key_light"],
        r["camera_body"], r["lens"], r["exposure"], r["film_emulation"], r["grain"],
    ]
    body = ", ".join(x.strip().rstrip(".") for x in parts if x)
    return f"{body} --ar {p['output']['aspect_ratio']} --stylize 50 --raw --cref {cref_url} --cw 100 --no {p['negative']}"


def to_flux(p: dict, trigger_token: str) -> dict:
    """Flux/SDXL + LoRA: trigger token + chỉ tả phần THAY ĐỔI (không tả lại mặt, mục 17.5 B3)."""
    s, r = p["shot"], p["realism_engine"]
    text = ", ".join([trigger_token, s["framing"], s["pose_action"], s["expression"], _wardrobe(s["wardrobe"]),
                      s["setting"], s["key_light"], r["camera_body"], r["lens"], r["film_emulation"]])
    return {"prompt": text, "negative_prompt": p["negative"], "lora_weight": 0.9, "cfg": 3.5}


def to_veo(p: dict) -> str:
    """Công thức 5 khối: Camera + Chủ thể/vật lý + Bối cảnh/ánh sáng + Texture + Âm thanh/thoại."""
    if p["render_target"] != "video":
        raise PromptError("Veo/Kling chỉ cho video")
    i, r, s, m, o = p["identity"], p["realism_engine"], p["shot"], p["motion"], p["output"]
    blocks = [
        f"[Camera] {s['framing']}; {m['camera_move']}. Duration {o['duration_sec']}s, {o['fps']}fps, {o['aspect_ratio']}.",
        f"[Subject & motion] {i['demographics']}; {i['face_structure']}; {i['asymmetry']}. {s['pose_action']}. "
        f"Expression: {s['expression']}. {m.get('subject_motion', '')} {m.get('physics_notes', '')}".strip(),
        f"[Setting & light] {s['setting']}, {s['time_and_light']}. {s['key_light']}.",
        f"[Texture] Wearing {_wardrobe(s['wardrobe'])}. Skin: {i['skin']}. {r['lighting_rule']}.",
        f"[Audio] {m.get('dialogue', 'no dialogue')} {m.get('ambience', '')} {m['lip_sync']}. {m['no_cut']}.".strip(),
        f"AVOID: {p['negative_video']}.",
        p["consistency_lock"],
    ]
    return "\n".join(b for b in blocks if b)
