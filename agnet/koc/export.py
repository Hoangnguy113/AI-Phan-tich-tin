"""Từ script.json → koc_prompts.json (mục 10.1 / 17.9): ba bản cho mỗi cảnh có người."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from . import adapters
from .master_prompt import PromptError, assert_untouched, build_prompt, load_character


def export_koc_prompts(doc: dict, *, character_dir: Path | str | None = None, cref_url: str = "<URL_ANH_GOC>") -> dict:
    koc = doc.get("koc") or {}
    if not koc.get("enabled"):
        raise PromptError("kịch bản không bật KOC")
    kwargs = {"directory": character_dir} if character_dir else {}
    char = load_character(koc["character_id"], **kwargs)
    d = char["defaults"]
    trigger = char["meta"]["trigger_token"]
    out: dict = {"character_id": koc["character_id"], "prompt_version": "koc-master-1.0",
                 "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "scenes": {}}
    for seg in doc["segments"]:
        for sc in seg["scenes"]:
            if sc["visual"]["type"] != "koc":
                continue
            k = sc["visual"]["koc"]
            shot = {
                "scene_id": sc["id"],
                "setting": d["setting"],
                "time_and_light": k.get("time_and_light", "daytime"),
                "key_light": d["key_light"],
                "fill": d.get("fill", ""),
                "wardrobe": {"outfit": koc["wardrobe_set"]},
                "pose_action": k.get("pose_action") or sc["visual"]["description"],
                "expression": k.get("expression") or sc.get("emotion") or "natural, attentive",
                "framing": k.get("framing") or "medium close-up, eye level",
            }
            motion = {"dialogue": f'[{char["meta"]["name"]}]: "{k["dialogue_vi"]}"'} if k.get("dialogue_vi") else None
            p = build_prompt(char, shot, platform=doc["platform"], render_target=k["render_target"],
                             engine=koc.get("engines", {}).get(k["render_target"]), motion=motion,
                             duration_sec=k["duration_sec"])
            assert_untouched(p)
            entry = {"json": p, "nano_banana": adapters.to_nano_banana(p), "flux": adapters.to_flux(p, trigger)}
            if k["render_target"] == "image":
                entry["midjourney"] = adapters.to_midjourney(p, cref_url)
            else:
                entry["veo_kling"] = adapters.to_veo(p)
            entry["identity_check"] = k["identity_check"]
            out["scenes"][sc["id"]] = entry
    return out


def write_koc_prompts(doc: dict, out_dir: Path | str, **kw) -> Path:
    data = export_koc_prompts(doc, **kw)
    path = Path(out_dir) / "koc_prompts.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
