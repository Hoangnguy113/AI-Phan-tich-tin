from agnet.gemini.ladder import build_ladder, parse_model


def names(lad):
    return [m.name for m in lad]


def test_parse_ten_la_va_ten_hop_le():
    m = parse_model("models/gemini-3.8-pro")
    assert (m.version, m.tier, m.preview) == ((3, 8), "pro", False)
    assert parse_model("gemini-2.5-flash-lite").tier == "flash-lite"
    assert parse_model("gemini-3-pro-preview").preview is True
    for bad in ("", "gpt-4", "gemma-3-27b", "gemini-2.5-flash-image", "gemini-2.5-flash-tts",
                "gemini-2.0-flash-live", "gemini-pro-latest", "text-embedding-004", "gemini-exp-1206"):
        assert parse_model(bad) is None, bad


def test_thang_ha_phien_ban_truoc_roi_ha_bac():
    lad = build_ladder(["models/gemini-3.7-flash", "models/gemini-3.8-pro", "models/gemini-3.7-pro",
                        "models/gemini-3.8-flash", "models/gemini-3.8-flash-lite", "models/gemini-3.7-flash-lite"])
    assert names(lad) == ["gemini-3.8-pro", "gemini-3.7-pro", "gemini-3.8-flash", "gemini-3.7-flash",
                          "gemini-3.8-flash-lite", "gemini-3.7-flash-lite"]


def test_model_moi_tu_vao_thang_va_so_phien_ban_khong_theo_chu():
    lad = build_ladder(["gemini-2.5-pro", "gemini-2.10-pro", "gemini-9.0-pro"])
    assert names(lad) == ["gemini-9.0-pro", "gemini-2.10-pro", "gemini-2.5-pro"]


def test_preview_chi_sau_ban_on_dinh():
    lad = build_ladder(["gemini-4.0-pro-preview", "gemini-2.5-pro", "gemini-2.5-flash"])
    assert names(lad) == ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-4.0-pro-preview"]


def test_bat_dau_tu_bac_chon():
    lad = build_ladder(["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite"], start_tier="flash")
    assert names(lad) == ["gemini-2.5-flash", "gemini-2.5-flash-lite"]


def test_gop_bien_the_cung_phien_ban():
    lad = build_ladder(["gemini-2.0-flash-001", "gemini-2.0-flash", "gemini-2.0-flash-002"])
    assert names(lad) == ["gemini-2.0-flash"]
