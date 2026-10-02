from agnet.core import timing


def test_count_words_vi_de():
    assert timing.count_words("Bữa sáng của bạn có thể đang làm đường huyết tăng gấp đôi.") == 13
    assert timing.count_words("Zwanzig Jahre auf der Bühne.") == 5
    assert timing.count_words("") == 0


def test_duration_formula():
    # 160 wpm = 2.667 từ/giây; 16 từ = 6s, +0.4s nghỉ
    assert timing.scene_duration(" ".join(["a"] * 16), 160) == 6.4


def test_split_budget_exact_sum():
    parts = timing.split_budget(1601, [1, 3, 3, 3, 2, 1])
    assert sum(parts) == 1601 and len(parts) == 6


def test_tolerance_boundaries():
    assert timing.within_tolerance(660, 600)       # đúng +10%
    assert not timing.within_tolerance(661, 600)


def test_duration_mix_picks_most_missing():
    mix = {"3-5": 3, "8-12": 5, "15-20": 2}
    assert timing.pick_duration_bucket(mix, {"8-12": 1}) == "8-12"  # thiếu 4 > thiếu 3 > thiếu 2
    assert timing.pick_duration_bucket(mix, {"3-5": 3, "8-12": 5, "15-20": 2}) is None
