"""Hợp đồng nhiệm vụ giao cho Gemini (mục 18.3). Chỉ là dữ liệu + sinh prompt; nghiệm thu nằm ở acceptance.py."""
from __future__ import annotations

from dataclasses import dataclass, field

RAW_ITEM_FIELDS = ("title", "url", "source", "published_at", "snippet")
OUTPUT_SCHEMA = {
    "type": "array",
    "items": {
        "title": "string, không rỗng",
        "url": "string, URL http(s) THẬT của bài viết gốc, lấy từ kết quả tìm kiếm",
        "source": "string, tên nguồn/trang (vd. Reuters, VnExpress)",
        "published_at": "string, ISO 8601 (vd. 2026-10-02T08:30:00Z)",
        "snippet": "string, 1-3 câu tóm tắt đúng nội dung bài, không thêm số liệu không có trong bài",
    },
}


@dataclass
class TaskContract:
    agent: str
    flow_id: str
    goal: str
    min_items: int = 1
    required_sources: list[str] = field(default_factory=list)
    max_age_hours: float = 48.0
    allow_ungrounded: bool = False          # True: không đòi url nằm trong grounding (chỉ khi grounding bị chặn)
    output_schema: dict = field(default_factory=lambda: OUTPUT_SCHEMA)

    def __post_init__(self) -> None:
        if not self.agent or not self.flow_id or not self.goal:
            raise ValueError("hợp đồng cần agent, flow_id, goal")
        if self.min_items < 1:
            raise ValueError("min_items phải >= 1")
        if self.max_age_hours <= 0:
            raise ValueError("max_age_hours phải > 0")


def build_prompt(c: TaskContract, errors: list[str] | None = None) -> str:
    """Prompt giao việc. `errors` (lần gửi lại) là danh sách lỗi cụ thể của lần nộp trước."""
    lines = [
        f"Bạn là agent `{c.agent}` của luồng `{c.flow_id}`. NHIỆM VỤ: {c.goal}",
        "",
        "HỢP ĐỒNG (sẽ được nghiệm thu bằng code, không bằng cảm tính):",
        f"- Trả về TỐI THIỂU {c.min_items} mục, mỗi mục là một bài báo/tin có thật tìm được bằng Google Search.",
        f"- Chỉ lấy tin đăng trong {c.max_age_hours:g} giờ gần nhất; mục cũ hơn sẽ bị loại.",
    ]
    if c.required_sources:
        lines.append("- BẮT BUỘC quét các nguồn sau (mỗi nguồn ít nhất một lần tìm): " + "; ".join(c.required_sources) + ".")
    lines += [
        "- Đầu ra DUY NHẤT là một mảng JSON, không lời dẫn, mỗi phần tử có đúng các khoá: "
        + ", ".join(RAW_ITEM_FIELDS) + ".",
        "  title: tiêu đề bài; url: địa chỉ http(s) thật của bài; source: tên nguồn; "
        "published_at: ISO 8601; snippet: tóm tắt ngắn đúng nội dung bài.",
        "",
        "CẤM TUYỆT ĐỐI:",
        "- Bịa URL, bịa tiêu đề, bịa ngày đăng hoặc bịa số liệu. URL phải là địa chỉ xuất hiện trong kết quả tìm kiếm.",
        "- Ước lượng hoặc 'làm tròn' cho đủ số lượng. Không đủ tin thật thì trả ít hơn và nói rõ thiếu; mục thiếu bằng chứng sẽ bị loại.",
        "- Thêm con số không có trong bài gốc.",
    ]
    if errors:
        lines += ["", "LẦN NỘP TRƯỚC KHÔNG ĐẠT. Sửa đúng các lỗi sau rồi nộp lại (đây là lần cuối):"]
        lines += [f"  * {e}" for e in errors]
    return "\n".join(lines)
