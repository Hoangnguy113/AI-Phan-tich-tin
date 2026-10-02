import json

import pytest

from agnet.core.settings import Settings
from agnet.gemini import AllModelsExhausted, GeminiAuthError, GeminiClient, extract_json

MODELS = {"models": [{"name": f"models/{n}", "supportedGenerationMethods": ["generateContent"]}
                     for n in ("gemini-3.8-pro", "gemini-3.7-pro", "gemini-3.8-flash", "gemini-3.8-flash-lite")]
          + [{"name": "models/embedding-001", "supportedGenerationMethods": ["embedContent"]}]}


def ok(text="xin chào", chunks=()):
    cand = {"content": {"parts": [{"text": text}]},
            "groundingMetadata": {"groundingChunks": [{"web": {"uri": u, "title": "t"}} for u in chunks],
                                  "webSearchQueries": ["q1"]}}
    return 200, json.dumps({"candidates": [cand]}).encode()


def quota(daily=False, delay=30):
    det = '"quotaId": "GenerateRequestsPerDayPerProject"' if daily else ""
    return 429, ('{"error":{"status":"RESOURCE_EXHAUSTED","message":"x %s","details":[{"retryDelay":"%ds"}]}}'
                 % (det, delay)).encode()


class Fake:
    def __init__(self, behaviors):
        self.b, self.calls, self.headers = behaviors, [], []

    def __call__(self, method, url, headers, body, timeout):
        self.calls.append((method, url))
        self.headers.append(headers)
        if method == "GET":
            return 200, json.dumps(MODELS).encode()
        model = url.split("/models/")[1].split(":")[0]
        r = self.b.get(model)
        r = r.pop(0) if isinstance(r, list) else r
        return r or (404, b"{}")

    def posts(self):
        return [u.split("/models/")[1].split(":")[0] for m, u in self.calls if m == "POST"]


def mk(tmp_path, behaviors, now=None, **kw):
    t = [1_000_000.0 if now is None else now]
    fake = Fake(behaviors)
    c = GeminiClient("KEY123", settings=kw.pop("settings", Settings()), cache_path=tmp_path / "m.json",
                     transport=fake, clock=lambda: t[0], sleep=lambda s: t.__setitem__(0, t[0] + s), **kw)
    return c, fake, t


def test_thieu_khoa():
    with pytest.raises(GeminiAuthError):
        GeminiClient("")


def test_goi_thanh_cong_co_bam_nguon_va_khoa_chi_o_header(tmp_path):
    c, fake, _ = mk(tmp_path, {"gemini-3.8-pro": ok("a", ["http://x/1", "http://x/1", "http://x/2"])})
    r = c.generate("hỏi")
    assert r.model == "gemini-3.8-pro" and not r.fell_back and r.queries == ["q1"]
    assert [s["url"] for s in r.sources] == ["http://x/1", "http://x/2"]
    assert all("KEY123" not in u for _, u in fake.calls)
    assert fake.headers[0]["x-goog-api-key"] == "KEY123"


def test_429_ha_xuong_model_thap_hon_va_model_nghi(tmp_path):
    c, fake, t = mk(tmp_path, {"gemini-3.8-pro": [quota(delay=30)], "gemini-3.7-pro": ok("b")})
    r = c.generate("x")
    assert r.model == "gemini-3.7-pro" and r.fell_back
    assert [a["outcome"] for a in r.attempts] == ["quota_minute", "ok"]
    # lượt sau: 3.8-pro còn nghỉ nên bỏ qua ngay, không gọi lại
    c.generate("y")
    assert fake.posts() == ["gemini-3.8-pro", "gemini-3.7-pro", "gemini-3.7-pro"]
    # hết 30 giây thì được thử lại
    t[0] += 31
    fake.b["gemini-3.8-pro"] = ok("c")
    assert c.generate("z").model == "gemini-3.8-pro"


def test_het_dinh_muc_ngay_nghi_den_nua_dem_LA(tmp_path):
    c, _, _ = mk(tmp_path, {"gemini-3.8-pro": [quota(daily=True)], "gemini-3.7-pro": ok()})
    r = c.generate("x")
    assert r.attempts[0]["outcome"] == "quota_daily"
    assert 0 < c._cool["gemini-3.8-pro#search"] - 1_000_000.0 <= 24 * 3600 + 10


def test_het_ca_thang_nem_loi(tmp_path):
    c, _, _ = mk(tmp_path, {m: quota() for m in ("gemini-3.8-pro", "gemini-3.7-pro", "gemini-3.8-flash",
                                                 "gemini-3.8-flash-lite")})
    with pytest.raises(AllModelsExhausted) as e:
        c.generate("x")
    assert len(e.value.attempts) == 4


def test_tat_ha_bac_chi_dung_model_dau(tmp_path):
    c, fake, _ = mk(tmp_path, {"gemini-3.8-pro": quota(), "gemini-3.7-pro": ok()},
                    settings=Settings(gemini_fallback=False))
    with pytest.raises(AllModelsExhausted):
        c.generate("x")
    assert set(fake.posts()) == {"gemini-3.8-pro"}          # không bao giờ xuống model khác khi tắt hạ bậc


def test_khoa_sai_khong_ha_bac(tmp_path):
    c, fake, _ = mk(tmp_path, {"gemini-3.8-pro": (403, b"denied")})
    with pytest.raises(GeminiAuthError):
        c.generate("x")
    assert fake.posts() == ["gemini-3.8-pro"]


def test_loi_may_chu_thu_lai_roi_ha_bac(tmp_path):
    c, fake, t = mk(tmp_path, {"gemini-3.8-pro": [(503, b""), (503, b""), (503, b"")], "gemini-3.7-pro": ok()})
    r = c.generate("x")
    assert r.model == "gemini-3.7-pro" and fake.posts().count("gemini-3.8-pro") == 3
    assert t[0] == 1_000_000.0 + 1 + 2          # lùi dần 1s, 2s


def test_cache_danh_sach_dung_lai_va_het_han_thi_tai_lai(tmp_path):
    c, fake, t = mk(tmp_path, {"gemini-3.8-pro": ok()})
    c.generate("x")
    assert sum(1 for m, _ in fake.calls if m == "GET") == 1
    c2 = GeminiClient("K", cache_path=tmp_path / "m.json", transport=fake, clock=lambda: t[0] + 3600)
    c2.generate("x")
    assert sum(1 for m, _ in fake.calls if m == "GET") == 1          # còn hạn → không tải lại
    c3 = GeminiClient("K", cache_path=tmp_path / "m.json", transport=fake, clock=lambda: t[0] + 25 * 3600)
    c3.generate("x")
    assert sum(1 for m, _ in fake.calls if m == "GET") == 2
    assert "KEY123" not in (tmp_path / "m.json").read_text()


def test_nghi_duoc_luu_qua_lan_khoi_dong_lai(tmp_path):
    c, fake, t = mk(tmp_path, {"gemini-3.8-pro": [quota()], "gemini-3.7-pro": ok()})
    c.generate("x")
    c2 = GeminiClient("K", cache_path=tmp_path / "m.json", transport=fake, clock=lambda: t[0] + 5)
    assert c2.generate("y").attempts[0]["outcome"] == "cooling"


def test_mang_loi_thi_dung_cache_cu(tmp_path):
    c, fake, t = mk(tmp_path, {"gemini-3.8-pro": ok()})
    c.generate("x")

    def down(method, url, h, b, to):
        return (0, b"URLError") if method == "GET" else ok("z")
    c2 = GeminiClient("K", cache_path=tmp_path / "m.json", transport=down, clock=lambda: t[0] + 99 * 3600)
    assert c2.generate("x").model == "gemini-3.8-pro"


def test_khong_co_cache_va_mang_loi_dung_model_ghim(tmp_path):
    def down(method, url, h, b, to):
        return (0, b"") if method == "GET" else ok("z")
    c = GeminiClient("K", settings=Settings(gemini_model="gemini-2.5-flash"), cache_path=tmp_path / "m.json",
                     transport=down)
    assert c.generate("x").model == "gemini-2.5-flash"


def test_tat_tu_cap_nhat_dung_model_ghim_roi_xuong_theo_cache(tmp_path):
    c, fake, _ = mk(tmp_path, {"gemini-3.7-pro": ok()})
    c.refresh_models(force=True)
    c2, fake2, _ = mk(tmp_path, {"gemini-3.8-flash": ok()},
                      settings=Settings(gemini_auto_update=False, gemini_model="gemini-3.8-flash"))
    assert [m.name for m in c2.ladder()] == ["gemini-3.8-flash", "gemini-3.8-flash-lite"]
    assert not any(m == "GET" for m, _ in fake2.calls)


def test_tra_loi_rong_la_loi_va_ha_bac(tmp_path):
    c, _, _ = mk(tmp_path, {"gemini-3.8-pro": ok("  "), "gemini-3.7-pro": ok("b")})
    r = c.generate("x")
    assert r.model == "gemini-3.7-pro" and r.attempts[0]["outcome"] == "bad_response"


def test_extract_json():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Đây là kết quả: [{"x": 2}] hết') == [{"x": 2}]
    with pytest.raises(ValueError):
        extract_json("không có json")


# ---- bám nguồn bị chặn (đo thật 02/10/2026: gọi thường 200, google_search 429 trên mọi model) -------------
def _search_blocked_fake(models=("gemini-3.8-pro", "gemini-3.7-pro", "gemini-3.8-flash", "gemini-3.8-flash-lite")):
    class F(Fake):
        def __call__(self, method, url, headers, body, timeout):
            if method == "POST":
                self.calls.append((method, url))
                return quota() if b"google_search" in body else ok("thường")
            return super().__call__(method, url, headers, body, timeout)
    return F({})


def test_bam_nguon_429_ha_het_thang_roi_moi_ket_luan(tmp_path):
    from agnet.gemini import GroundingUnavailable
    fake = _search_blocked_fake()
    c = GeminiClient("K", cache_path=tmp_path / "m.json", transport=fake, clock=lambda: 1e6)
    with pytest.raises(GroundingUnavailable):
        c.generate("x")
    assert len(fake.posts()) == 5                    # hạ hết 4 model (đều 429 khi bám nguồn) + 1 lần gọi thường để phân biệt
    with pytest.raises(GroundingUnavailable):        # lần sau: biết rồi, không gọi mạng nữa
        c.generate("y")
    assert len(fake.posts()) == 5


def test_cho_phep_khong_bam_nguon_thi_tra_ket_qua_danh_dau(tmp_path):
    fake = _search_blocked_fake()
    c = GeminiClient("K", cache_path=tmp_path / "m.json", transport=fake, clock=lambda: 1e6)
    r = c.generate("x", allow_ungrounded=True)
    assert r.text == "thường" and not r.grounded and r.fell_back


def test_limit_0_nghi_24h(tmp_path):
    body = b'{"error":{"message":"Quota exceeded ... limit: 0, model: gemini-3.1-pro"}}'
    c, _, _ = mk(tmp_path, {"gemini-3.8-pro": [(429, body)], "gemini-3.7-pro": ok()})
    r = c.generate("x", search=False)
    assert r.model == "gemini-3.7-pro" and c._cool["gemini-3.8-pro"] - 1e6 >= 24 * 3600 - 1


def test_probe_bao_cao(tmp_path):
    fake = _search_blocked_fake()
    c = GeminiClient("K", cache_path=tmp_path / "m.json", transport=fake, clock=lambda: 1e6)
    rep = c.probe()
    assert (rep["key"], rep["plain"], rep["search"]) == ("ok", "ok", "blocked") and rep["models"] == 4

    def bad(method, url, h, b, t):
        return 403, b"denied"
    assert GeminiClient("K", cache_path=tmp_path / "n.json", transport=bad).probe()["key"] == "bad"


def test_gemma_chi_dung_khi_goi_khong_bam_nguon(tmp_path):
    names = ("gemini-3.8-flash", "gemma-4-31b-it")
    models = {"models": [{"name": f"models/{n}", "supportedGenerationMethods": ["generateContent"]} for n in names]}

    class F(Fake):
        def __call__(self, method, url, headers, body, timeout):
            if method == "GET":
                return 200, json.dumps(models).encode()
            self.calls.append((method, url))
            return quota() if b"google_search" in body or ("flash" in url and self.flash_dead) else ok("gemma")
    fake = F({})
    fake.flash_dead = True
    c = GeminiClient("K", cache_path=tmp_path / "m.json", transport=fake, clock=lambda: 1e6)
    r = c.generate("x", search=False)                      # flash 429 → hạ tới tận Gemma
    assert r.model == "gemma-4-31b-it" and r.fell_back
    assert fake.posts() == ["gemini-3.8-flash", "gemma-4-31b-it"]
    fake.calls.clear()
    fake.flash_dead = False
    c2 = GeminiClient("K", cache_path=tmp_path / "n.json", transport=fake, clock=lambda: 1e6)
    from agnet.gemini import GroundingUnavailable
    with pytest.raises(GroundingUnavailable):
        c2.generate("x")                                   # bám nguồn: Gemma bị bỏ qua, không bao giờ được gọi
    assert "gemma-4-31b-it" not in fake.posts()[:-1]


def test_loi_hon_hop_429_503_400_van_ha_het_thang_toi_model_chay_duoc(tmp_path):
    c, fake, _ = mk(tmp_path, {"gemini-3.8-pro": [quota()], "gemini-3.7-pro": [(503, b""), (503, b""), (503, b"")],
                               "gemini-3.8-flash": [(400, b"tool not supported")], "gemini-3.8-flash-lite": ok("cuối")})
    r = c.generate("x")
    assert r.model == "gemini-3.8-flash-lite" and r.fell_back
    assert [a["outcome"] for a in r.attempts] == ["quota_minute", "server_503", "http_400", "ok"]


def test_het_thang_lan_429_503_van_phan_biet_duoc_hang_muc_tim_kiem(tmp_path):
    from agnet.gemini import GroundingUnavailable

    class F(Fake):
        def __call__(self, method, url, headers, body, timeout):
            if method == "GET":
                return super().__call__(method, url, headers, body, timeout)
            self.calls.append((method, url))
            if b"google_search" in body:
                return (503, b"") if "3.7" in url else quota()
            return ok("thường")
    c = GeminiClient("K", cache_path=tmp_path / "m.json", transport=F({}), clock=lambda: 1e6, sleep=lambda s: None)
    with pytest.raises(GroundingUnavailable):
        c.generate("x")
