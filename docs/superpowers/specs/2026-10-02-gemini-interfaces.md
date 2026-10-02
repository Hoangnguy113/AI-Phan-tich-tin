# Hợp đồng giao diện — Gemini, Chỉ huy, Định tuyến (02/10/2026)

Tài liệu này KHÓA tên hàm, chữ ký và hành vi để các luồng B1–B5 viết song song mà ghép được với nhau.
Ai cần đổi hợp đồng phải DỪNG và báo lại, không tự đổi.

Quy ước chung: Python ≥ 3.10, `from __future__ import annotations`, không thêm phụ thuộc mới ngoài `google-genai`
(đã cài, 2.17.0). Mọi test dùng transport/đồng hồ/`sleep` GIẢ — **không gọi mạng, không dùng khóa thật**. Văn phong và comment
tiếng Việt như phần mã hiện có. Không bao giờ in/log/ghi khóa API.

## Phân chia tệp (mỗi luồng CHỈ ghi vào tệp của mình)

| Luồng | Được ghi |
|---|---|
| B1 | `agnet/gemini/*.py`, `tests/test_gemini_*.py` |
| B2 | `agnet/commander/*.py`, `tests/test_commander_*.py` |
| B3 | `.claude/agents/01-*.md 02-* 03-* 04-* 05-* 08-* 09-*`, `tests/test_agents_engine.py` |
| B4 | `agnet/pipeline/router.py`, `agnet/pipeline/agents.py`, `agnet/runner.py`, `tests/test_router_*.py`, `tests/test_sdk_retry.py` |
| B5 | `agnet/ui/page_settings.py`, `agnet/ui/i18n.py`, `tests/test_ui_gemini_settings.py` |

Tệp đã có, KHÔNG sửa trừ khi là chủ: `agnet/core/settings.py` (đã có đủ trường Gemini), `agnet/ui/library.py`, mọi tệp khác.

## B1 — `agnet/gemini/`

### `errors.py`
```python
class GeminiError(Exception): ...
class AuthError(GeminiError): ...                 # 401/403, khóa sai/thu hồi — KHÔNG thử model khác
class ModelNotFound(GeminiError): ...             # 404 — model biến mất/đổi tên
class TransientError(GeminiError): ...            # 5xx, mất mạng, timeout
class QuotaExhausted(GeminiError):                # 429 RESOURCE_EXHAUSTED
    scope: str            # "minute" | "day" | "unknown"   (đoán từ nội dung lỗi: PerMinute/PerDay)
    retry_after_sec: float | None
class AllModelsExhausted(GeminiError):
    tried: list[str]
```

### `types.py`
```python
@dataclass(frozen=True)
class ModelInfo:
    name: str                 # "gemini-3.8-pro" — KHÔNG có tiền tố "models/"
    family: str               # "gemini"
    version: tuple[int, ...]  # (3, 8)
    tier: str                 # "pro" | "flash" | "flash-lite" | "other"
    preview: bool             # tên chứa preview / exp / experimental
    supports_generate: bool   # có "generateContent" trong supportedGenerationMethods

@dataclass
class GeminiResult:
    text: str
    sources: list[dict]       # [{"url": str, "title": str}] từ siêu dữ liệu bám nguồn; rỗng nếu không có
    model: str                # model THỰC SỰ đã trả lời
    input_tokens: int = 0
    output_tokens: int = 0
```

### `transport.py`
```python
class Transport(Protocol):
    async def list_models(self) -> list[dict]: ...   # dict thô: {"name": "models/gemini-...", "supportedGenerationMethods": [...]}
    async def generate(self, model: str, prompt: str, *, system: str | None = None,
                       grounding: bool = True, timeout: float = 120.0) -> GeminiResult: ...

class GoogleGenAITransport:                          # bản thật, dùng google-genai
    def __init__(self, api_key: str, client=None): ...   # client để tiêm giả khi test
```
`GoogleGenAITransport` chuyển lỗi SDK thành các lỗi ở `errors.py` (429→`QuotaExhausted` với `scope` đoán từ chuỗi lỗi
"PerDay"/"per day" → `"day"`, "PerMinute"/"per minute" → `"minute"`, còn lại `"unknown"`; 404→`ModelNotFound`; 401/403→`AuthError`;
5xx/kết nối/timeout→`TransientError`). `grounding=True` bật công cụ tìm kiếm Google của SDK và đọc nguồn từ siêu dữ liệu bám nguồn.
**Chưa kiểm chứng:** chưa gọi thật lần nào, và chưa biết bám nguồn có dùng chung được với đầu ra JSON ép schema hay không — vì vậy
`generate` KHÔNG ép `response_schema`; chỉ yêu cầu JSON trong prompt, bên Chỉ huy tự phân tích.

### `fake.py`
```python
class FakeTransport:
    def __init__(self, models: list[str] | list[dict] | None = None, script: dict[str, list] | None = None): ...
    calls: list[dict]                                 # mỗi lượt generate: {"model", "prompt", "system", "grounding"}
    list_calls: int
```
`script[model]` là hàng đợi các phần tử: `GeminiResult` (trả về) hoặc một `Exception` (ném ra), lấy lần lượt; hết hàng đợi thì
trả `GeminiResult(text="{}", sources=[], model=model)`. `models` là tên (có/không tiền tố `models/`) hoặc dict thô; mặc định mọi model
có `supportedGenerationMethods=["generateContent"]`.

### `catalog.py`
```python
def parse_model_name(name: str, methods: list[str] | None = None) -> ModelInfo
```
Chịu được tên lạ (không bao giờ ném lỗi). Gỡ tiền tố `models/`. Họ = đoạn chữ đầu (`gemini`); phiên bản = các số liền sau họ
(`gemini-3.8-pro` → `(3, 8)`, `gemini-2.5-flash-lite` → `(2, 5)`, `gemini-3-pro` → `(3,)`); bậc = `flash-lite` | `flash` | `pro`
(kiểm `flash-lite` trước `flash`), còn lại `other`. `preview` = có `preview`/`exp`/`experimental` trong tên. Tên có
`embedding`, `imagen`, `veo`, `tts`, `live`, `audio`, `image`, `aqa` hoặc thiếu `generateContent` → `supports_generate=False`.
```python
def build_ladder(models: list[ModelInfo], tier: str = "pro", allow_preview: bool = False) -> list[str]
```
Thang từ cao xuống thấp, chỉ gồm model `supports_generate` và bậc ≠ `other`. Bắt đầu từ `tier` rồi chỉ đi XUỐNG
(`pro` → `flash` → `flash-lite`; `tier="flash"` thì không có `pro`). Trong mỗi bậc: phiên bản giảm dần, bản ổn định trước bản
preview cùng phiên bản. `allow_preview=False` thì bỏ hẳn preview, TRỪ khi bỏ xong mà thang rỗng thì dùng lại preview.
Ví dụ với `[3.8-pro, 3.7-pro, 3.8-flash, 3.7-flash, 3.8-flash-lite]`, `tier="pro"`:
`3.8-pro, 3.7-pro, 3.8-flash, 3.7-flash, 3.8-flash-lite`.
```python
class ModelCatalog:
    def __init__(self, cache_path: str | Path, clock: Callable[[], float] = time.time): ...
    models: list[ModelInfo]          # từ bộ nhớ đệm
    fetched_at: float | None
    last_error: str | None
    def load(self) -> None            # đọc cache; hỏng/thiếu → rỗng, không ném
    def save(self) -> None            # ghi nguyên tử
    def is_stale(self, max_age_hours: float) -> bool
    async def refresh(self, transport: Transport) -> list[ModelInfo]   # lỗi mạng → giữ cache cũ, đặt last_error, KHÔNG ném
    async def refresh_if_stale(self, transport: Transport, max_age_hours: float) -> bool   # True nếu có làm mới
    def ladder(self, tier: str = "pro", allow_preview: bool = False) -> list[str]
```
Cache mặc định: `config/gemini_models.json` (chỉ chứa tên model/phiên bản/bậc/thời điểm, KHÔNG chứa khóa).

### `fallback.py`
```python
class GeminiRunner:
    def __init__(self, transport: Transport, catalog: ModelCatalog, *, tier: str = "pro", fallback: bool = True,
                 pinned_model: str | None = None, auto_update: bool = True, refresh_hours: float = 24,
                 clock=time.time, sleep=asyncio.sleep, allow_preview: bool = False): ...
    last_used_model: str | None
    usage_log: list[dict]            # [{"model", "ok": bool, "error": str|None}]
    async def generate(self, prompt: str, *, system: str | None = None, grounding: bool = True,
                       timeout: float = 120.0) -> GeminiResult
```
Hành vi:
1. `auto_update` và catalog cũ → `catalog.refresh_if_stale` trước (lỗi làm mới không chặn).
2. Thang = `catalog.ladder(tier)`; nếu `auto_update=False` hoặc thang rỗng và có `pinned_model` → `[pinned_model]`. Không có gì → `AllModelsExhausted(tried=[])`.
3. Bỏ qua model đang "nghỉ". Với từng model theo thứ tự:
   - `QuotaExhausted`: nếu `fallback=False` → ném lại. Ngược lại cho model nghỉ rồi thử model kế —
     `scope=="minute"`: nghỉ `retry_after_sec` (mặc định 60s); `scope=="day"`/`"unknown"`: nghỉ tới nửa đêm kế tiếp theo giờ
     `America/Los_Angeles` (lúc Google đặt lại hạn mức ngày; **chưa kiểm chứng**); thang này tính theo `clock`.
   - `ModelNotFound`: loại model khỏi lượt này, làm mới catalog một lần, thử model kế.
   - `TransientError`: thử lại CÙNG model tối đa 2 lần (chờ 1s rồi 3s qua `sleep`), vẫn lỗi thì thử model kế.
   - `AuthError`: ném ngay, không thử model khác.
4. Hết thang → `AllModelsExhausted(tried)` kèm danh sách đã thử.
5. Mỗi thành công cập nhật `last_used_model`; mỗi lượt (ok hay không) thêm vào `usage_log`.

## B2 — `agnet/commander/` (code thuần, không gọi mạng)

```python
# contract.py
@dataclass
class TaskContract:
    agent: str
    goal: str
    item_fields: list[str]            # trường BẮT BUỘC mỗi mục, ví dụ ["title","url","source","published_at","snippet"]
    min_items: int
    max_age_hours: float | None = None
    required_sources: list[str] = field(default_factory=list)   # nguồn phải quét (chỉ để nhắc trong prompt)
    numeric_fields: list[str] = field(default_factory=list)     # trường số liệu phải kèm "source" ngay cạnh
    def to_prompt(self, flow: dict) -> str     # prompt giao việc: mục tiêu, luồng, trường bắt buộc, tối thiểu, ĐẦU RA CHỈ MỘT JSON
    def to_retry_prompt(self, flow: dict, verdict: "Verdict") -> str   # nêu LỖI CỤ THỂ + số mục còn thiếu

def contract_for(agent: str, flow: dict) -> TaskContract    # bảng hợp đồng cho 7 agent Gemini; agent lạ → KeyError
```
7 agent: `trend-scout`, `video-platform-scout`, `news-scout`, `community-scout`, `domain-internal-scout`, `keyword-miner`,
`competitor-gap-analyst`.
```python
# acceptance.py
@dataclass
class Rejected: item: dict; reasons: list[str]
@dataclass
class Verdict:
    accepted: list[dict]; rejected: list[Rejected]; shortfall: int; errors: list[str]
    @property
    def ok(self) -> bool            # shortfall == 0 and not errors

def validate(contract: TaskContract, items: object, *, grounding_sources: list[dict] | None = None,
             now: datetime | None = None) -> Verdict
```
Quy tắc từng mục (đều bằng code, không dùng LLM): đủ `item_fields` và không rỗng · `url` là http(s) hợp lệ · nếu có
`grounding_sources` thì tên miền của `url` phải trùng một nguồn bám (mục bịa URL bị loại) · `published_at` đọc được (ISO) và không
quá `max_age_hours` · trùng URL/tiêu đề (dùng `agnet.storage.db.normalize`/`jaccard`) trong cùng lượt thì giữ mục đầu · mỗi
`numeric_fields` có giá trị số phải đi kèm `<trường>_source` không rỗng — **thiếu nguồn thì loại cả mục, không "ước lượng cho đủ"**.
`items` không phải list → `Verdict(accepted=[], errors=["đầu ra không phải danh sách"], shortfall=min_items)`.
```python
# ledger.py
class ComplianceLedger:
    def __init__(self, path: str | Path): ...
    def record(self, agent: str, verdict: Verdict, attempt: int, model: str | None = None) -> None   # ghi 1 dòng JSON
    def rate(self, agent: str, last_n: int = 20) -> float | None      # tỉ lệ lượt đạt hợp đồng, None nếu chưa có dữ liệu
    def summary(self) -> dict[str, dict]                              # {agent: {"runs", "pass", "rate"}}
# commander.py
@dataclass
class AssignResult: accepted: list[dict]; verdict: Verdict; attempts: int; compliant: bool; model: str | None
async def assign(contract: TaskContract, flow: dict, generate: Callable[..., Awaitable[GeminiResult]],
                 *, ledger: ComplianceLedger | None = None, retries: int = 1) -> AssignResult
```
`assign`: gọi `generate(prompt)` → phân tích JSON từ `result.text` (dùng `agnet.pipeline.agents.extract_json`; lỗi → coi như thiếu) →
`validate` (truyền `result.sources`) → chưa đạt thì gửi lại `retries` lần với `to_retry_prompt` (giữ các mục đã chấp nhận, chỉ xin phần thiếu) →
ghi sổ mỗi lượt. Hết lượt vẫn thiếu: trả phần đã chấp nhận, `compliant=False`. **Không bao giờ tự bịa mục.**

## B3 — Agent Gemini

Bảy tệp `01,02,03,04,05,08,09` thêm dòng frontmatter `engine: gemini` (giữ nguyên `name`, `model`, `tools`, `skills`; với agent
engine=gemini thì `tools` chỉ mang tính ghi chú). Viết lại thân prompt theo mô hình "nhận hợp đồng → tìm kiếm có nguồn → trả MỘT JSON
đúng trường": mỗi mục có `title`, `url`, `source`, `published_at` (ISO), `snippet`, `lang`; số liệu đi kèm `<trường>_source`; cấm bịa số/URL;
thiếu bằng chứng thì bỏ mục. Hai agent `11-deep-researcher` và `12-fact-checker` GIỮ `engine: claude` (bản lai Gemini+Claude làm sau).
Agent không có `engine` hiểu là `claude`. Test: `tests/test_agents_engine.py` đọc frontmatter bằng `yaml` trực tiếp (không phụ thuộc
`AgentSpec`).

## B4 — Định tuyến

- `agnet/pipeline/agents.py`: `AgentSpec` thêm `engine: str = "claude"` (đọc `meta.get("engine", "claude")`). `SdkRunner.run` thử lại
  lùi dần khi lỗi tạm thời `Failed to refresh OAuth token` / `another Claude Code process` (tối đa 3 lần, chờ 2s, 5s; `sleep` tiêm được);
  lỗi khác không thử lại.
- `agnet/pipeline/router.py`:
```python
class RoutingRunner:                 # triển khai AgentRunner
    def __init__(self, claude: AgentRunner, gemini: GeminiRunner | None, flow_dict_provider=None,
                 ledger: ComplianceLedger | None = None): ...
    async def run(self, agent: AgentSpec, prompt: str, *, max_budget_usd: float) -> AgentResult
```
  `agent.engine == "gemini"` và có `gemini` → `commander.assign(contract_for(agent.name, flow), flow, gemini.generate)`, trả
  `AgentResult(text=<JSON của mục đã chấp nhận>, cost_usd=0.0)`; còn lại → `claude.run`. Gemini lỗi (`AllModelsExhausted`, `AuthError`)
  thì **dự phòng sang Claude** cho lượt đó và ghi cảnh báo — pipeline không dừng.
- `agnet/runner.py`: `run_flow` dựng `RoutingRunner` khi `settings.gemini_provider == "gemini_api"` và có `GEMINI_API_KEY`; không thì như cũ
  (toàn Claude). Giữ `concurrency` như hiện tại.

## B5 — Giao diện cài đặt Gemini

`page_settings.py` thêm vào nhóm Gemini: ô tick "Tự cập nhật danh sách model từ Google" (`gemini_auto_update`), "Hết định mức thì
xuống model thấp hơn" (`gemini_fallback`), chọn bậc ưu tiên (`gemini_tier`: pro/flash/flash-lite), số giờ làm mới
(`gemini_refresh_hours`), nút "Cập nhật danh sách model ngay", nhãn hiện thang model (`A → B → C`) và thời điểm cập nhật lần cuối.
`SettingsPage.__init__` thêm tham số tùy chọn `transport_factory: Callable[[str], Transport] | None` và `catalog_path` để test tiêm
FakeTransport; mặc định dùng `GoogleGenAITransport(key)` và `config/gemini_models.json`. Nút làm mới chạy ở luồng nền (không khóa
giao diện), thiếu khóa thì báo rõ, lỗi mạng thì giữ danh sách cũ và hiện lỗi. Bản dịch tiếng Anh thêm vào `i18n.EN`; bài quét
`test_khong_sot_chu_viet_co_dinh_khi_chuyen_english` phải tiếp tục xanh.
