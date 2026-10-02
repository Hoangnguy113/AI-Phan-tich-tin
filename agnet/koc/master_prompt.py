"""koc-master-1.0 (mục 17.3): ghép LỚP A (identity) + B (realism) + C (shot) + negative + consistency lock.

Code này là chỗ DUY NHẤT sinh prompt nhân vật. Agent không viết prompt tay, nên không thể
vô tình sửa Lớp B, negative hay consistency_lock.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENGINE_FILE = Path(__file__).with_name("realism_engine.json")
CHAR_DIR = ROOT / "config" / "characters"
VERSION = "koc-master-1.0"

PLATFORM_RATIO = {"youtube": "16:9", "tiktok": "9:16", "facebook": "4:5"}
MIN_AGE = 22  # mục 17.11

# Token "trung bình hoá" — cấm trong identity/shot (vẫn xuất hiện hợp lệ trong `negative`)
BANNED = [
    "perfect", "flawless", "masterpiece", "8k", "ultra detailed", "ultra-detailed", "hyper detailed",
    "hyperdetailed", "ultra realistic", "beautiful woman", "supermodel", "doll-like", "doll like",
    "porcelain skin", "symmetrical face", "instagram filter",
]
_MEASURE_RE = re.compile(r"\b\d{2,3}\s*[-–/]\s*\d{2,3}\s*[-–/]\s*\d{2,3}\b")
_SEXUAL = ["sexy", "seductive", "lingerie", "cleavage", "busty", "revealing", "provocative", "bikini"]

REQUIRED_IDENTITY = ["character_id", "reference_images", "demographics", "face_structure", "asymmetry",
                     "identity_marks", "eyes", "nose", "lips", "hair", "skin", "build", "hands",
                     "signature_items", "persona"]
REQUIRED_SHOT = ["scene_id", "setting", "time_and_light", "key_light", "wardrobe", "pose_action",
                 "expression", "framing"]


class PromptError(ValueError):
    pass


def load_engine() -> dict:
    return json.loads(ENGINE_FILE.read_text(encoding="utf-8"))


def load_character(character_id: str, directory: Path | str = CHAR_DIR) -> dict:
    p = Path(directory) / f"{character_id.lower()}.json"
    if not p.exists():
        raise PromptError(f"không có nhân vật {character_id!r} ({p})")
    data = json.loads(p.read_text(encoding="utf-8"))
    if data["identity"]["character_id"] != character_id:
        raise PromptError(f"{p.name}: character_id không khớp tên file")
    return data


def _scan_banned(label: str, obj) -> None:
    text = json.dumps(obj, ensure_ascii=False).lower()
    for w in BANNED:
        if re.search(rf"(?<![\w]){re.escape(w)}(?![\w])", text):
            raise PromptError(f"{label} chứa từ cấm '{w}' (mục 17.4) — tả ánh sáng/ống kính thay vì tả 'đẹp'")
    for w in _SEXUAL:
        if re.search(rf"\b{w}\b", text):
            raise PromptError(f"{label} chứa mô tả gợi dục '{w}' (mục 17.11)")
    if _MEASURE_RE.search(text):
        raise PromptError(f"{label} chứa số đo cơ thể (mục 17.11)")


def validate_identity(identity: dict) -> None:
    missing = [k for k in REQUIRED_IDENTITY if not identity.get(k)]
    if missing:
        raise PromptError(f"identity thiếu: {missing}")
    if len([s for s in re.split(r"[;\n]", identity["asymmetry"]) if s.strip()]) < 2:
        raise PromptError("identity.asymmetry cần ≥ 2 điểm bất đối xứng, ngăn bằng ';' (mục 17.7)")
    if not any(ch.isdigit() for ch in identity["asymmetry"]):
        raise PromptError("identity.asymmetry phải có số đo cụ thể (vd 2mm) (mục 17.4 #1)")
    marks = identity["identity_marks"]
    if not isinstance(marks, list) or len(marks) < 2:
        raise PromptError("identity.identity_marks cần ≥ 2 dấu hiệu riêng (mục 17.7)")
    m = re.search(r"(\d{2})\s*years?\s*old", identity["demographics"])
    if not m or int(m.group(1)) < MIN_AGE:
        raise PromptError(f"demographics phải ghi 'NN years old' với NN ≥ {MIN_AGE} (mục 17.11)")
    _scan_banned("identity", {k: v for k, v in identity.items() if k != "reference_images"})


def build_lock(identity: dict) -> str:
    """Consistency lock sinh từ chính identity → luôn khớp nhân vật; đặt CUỐI prompt (mục 17.2)."""
    marks = "; ".join(identity["identity_marks"])
    asym = "; ".join(s.strip() for s in re.split(r"[;\n]", identity["asymmetry"]) if s.strip())
    items = ", ".join(identity["signature_items"])
    return (
        "The face must stay exactly as in the reference images: identical bone structure, eye shape and "
        "spacing, nose, lips, teeth, and these identity marks — " + marks + ". Keep the natural asymmetry — "
        + asym + ". Do not beautify, slim, smooth, re-age or re-ethnicise the face. Keep the hair length and "
        "these signature items: " + items + ". Only the pose, wardrobe, background and lighting described in "
        "`shot` may change."
    )


def build_prompt(character: dict, shot: dict, *, platform: str, render_target: str = "image",
                 engine: str | None = None, motion: dict | None = None,
                 duration_sec: float = 8, fps: int = 24) -> dict:
    if render_target not in ("image", "video"):
        raise PromptError("render_target phải là 'image' hoặc 'video'")
    if platform not in PLATFORM_RATIO:
        raise PromptError(f"nền tảng không hỗ trợ: {platform}")
    identity = copy.deepcopy(character["identity"])
    validate_identity(identity)
    missing = [k for k in REQUIRED_SHOT if not shot.get(k)]
    if missing:
        raise PromptError(f"shot thiếu: {missing}")
    wardrobe = shot["wardrobe"]
    if not isinstance(wardrobe, dict) or not any(wardrobe.values()):
        raise PromptError("shot.wardrobe phải là dict có ít nhất một món")
    _scan_banned("shot", shot)

    eng = load_engine()
    ratio = PLATFORM_RATIO[platform]
    default_engine = "veo_3" if render_target == "video" else "nano_banana_pro"
    out_block = {"aspect_ratio": ratio, "resolution": "2K", "count": 1} if render_target == "image" \
        else {"aspect_ratio": ratio, "duration_sec": duration_sec, "fps": fps}

    prompt = {
        "prompt_version": VERSION,
        "render_target": render_target,
        "engine": engine or default_engine,
        "output": out_block,
        "identity": identity,
        "realism_engine": eng["realism_engine"],
        "shot": copy.deepcopy(shot),
    }
    if render_target == "video":
        m = {**eng["video_motion_defaults"], **(motion or {})}
        _scan_banned("motion", m)
        prompt["motion"] = m
    prompt["negative"] = eng["negative"]
    if render_target == "video":
        prompt["negative_video"] = eng["negative_video"]
    prompt["consistency_lock"] = build_lock(identity)  # luôn là khoá CUỐI
    return prompt


def assert_untouched(prompt: dict) -> None:
    """Kiểm tra Lớp B/negative/lock chưa bị sửa — dùng trong QA và test."""
    eng = load_engine()
    if prompt["realism_engine"] != eng["realism_engine"]:
        raise PromptError("realism_engine đã bị sửa (mục 17.8: cấm)")
    if prompt["negative"] != eng["negative"]:
        raise PromptError("negative đã bị sửa (mục 17.8: cấm)")
    if prompt["consistency_lock"] != build_lock(prompt["identity"]):
        raise PromptError("consistency_lock đã bị sửa (mục 17.8: cấm)")
    if list(prompt)[-1] != "consistency_lock":
        raise PromptError("consistency_lock phải nằm CUỐI prompt (mục 17.2)")
