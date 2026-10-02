"""Đổi ngôn ngữ giao diện Việt <-> Anh mà KHÔNG phải sửa từng trang.

Cách làm: duyệt cây widget, ghi nhớ chữ gốc (tiếng Việt) của từng ô vào thuộc tính động, rồi đặt lại
bằng bản dịch trong EN khi chọn "en" và trả về chữ gốc khi chọn "vi". Nhờ vậy trang mới chỉ cần thêm
vào từ điển, và đổi qua lại nhiều lần không làm hỏng chữ gốc.

Giới hạn (nói thẳng): thông báo trạng thái dựng bằng f-string lúc chạy (ví dụ "Đã lưu. Luồng ... xử lý N tin")
chưa có bản dịch và vẫn hiện tiếng Việt.
"""
from __future__ import annotations

from PySide6.QtWidgets import (QAbstractButton, QAbstractSpinBox, QComboBox, QGroupBox, QLabel,
                               QLineEdit, QListWidget, QMainWindow, QPlainTextEdit, QTabWidget, QTableWidget,
                               QWidget)

EN: dict[str, str] = {
    # cửa sổ & tab
    "Agnet — quản lý luồng viết kịch bản": "Agnet — script flow manager",
    "Bảng điều khiển": "Dashboard",
    "Cài đặt luồng": "Flow settings",
    "Kho kịch bản": "Script library",
    "Duyệt": "Approve",
    "Cần viết lại…": "Needs rewrite…",
    "Loại": "Reject",
    "Mở thư mục": "Open folder",
    "Kịch bản": "Script",
    "Lời thoại": "Voiceover",
    "Đóng gói": "Packaging",
    "Nguồn": "Sources",
    "Nhân vật KOC": "KOC character",
    "Báo cáo ngày": "Daily report",
    "Cài đặt chung": "General settings",
    "Tài khoản Claude": "Claude account",
    "Quản lý luồng kịch bản": "Script flow management",
    "Ctrl+1…9: chuyển mục": "Ctrl+1…9: switch section",
    "Đội agent": "Agent team",
    "Hợp đồng & tỉ lệ đạt": "Contracts & pass rate",
    # chung
    "Lưu": "Save",
    "Bỏ thay đổi": "Discard changes",
    "Làm mới": "Refresh",
    "Dừng": "Stop",
    "Thêm": "Add",
    "Xóa": "Remove",
    # tài khoản
    "Đăng nhập": "Sign in",
    "Đăng xuất": "Sign out",
    "Kiểm tra lại": "Check again",
    "Kiểm tra hệ thống (doctor)": "System check (doctor)",
    "Kết quả kiểm tra hệ thống hiện ở đây.": "System check results appear here.",
    # bảng điều khiển
    "<b>Các luồng</b>": "<b>Flows</b>",
    "<b>Lần chạy gần đây</b>": "<b>Recent runs</b>",
    "Chạy ngay luồng đang chọn": "Run selected flow now",
    "Kết quả lần chạy hiện ở đây.": "Run output appears here.",
    "Luồng": "Flow",
    "Số tin/ngày": "Items/day",
    "Hôm nay": "Today",
    "Đã chi hôm nay": "Spent today",
    "Trần/ngày": "Daily cap",
    "Lịch": "Schedule",
    "Ngày": "Date",
    "Trạng thái": "Status",
    "Chi phí": "Cost",
    # cài đặt luồng
    "Luồng:": "Flows:",
    "Sản lượng mỗi ngày": "Daily output",
    "Số tin (kịch bản) hệ thống xử lý trong một ngày:": "Number of items (scripts) processed per day:",
    "  kịch bản/ngày": "  scripts/day",
    "Chia theo thời lượng — tổng phải bằng số trên:": "Split by duration — the total must equal the number above:",
    "Khoảng thời lượng (phút)": "Duration range (min)",
    "Số kịch bản": "Scripts",
    "Chia lại tự động theo số tin/ngày": "Re-split automatically by items/day",
    "Lịch & ngân sách": "Schedule & budget",
    "Bật luồng này": "Enable this flow",
    "Giờ chạy (hằng ngày):": "Run times (daily):",
    "Múi giờ:": "Time zone:",
    "Trần chi phí:": "Cost cap:",
    " / ngày": " / day",
    # cài đặt chung
    "Giao diện": "Appearance",
    "Ngôn ngữ giao diện:": "Interface language:",
    "Chủ đề:": "Theme:",
    "Theo hệ thống": "Follow system",
    "Sáng": "Light",
    "Tối": "Dark",
    "Chạy song song": "Parallel execution",
    "Số agent chạy song song:": "Parallel agents:",
    "Nhiều agent cùng dùng một lần đăng nhập Claude có thể đua nhau làm mới token "
    "(đã gặp khi chạy thật 02/10/2026). Mặc định 3 là mức thận trọng.":
        "Several agents sharing one Claude login can race to refresh the token "
        "(seen in a real run on 02/10/2026). The default of 3 is the cautious setting.",
    "  agent": "  agents",
    "Khảo sát thị trường & tìm kiếm mạng (Gemini)": "Market research & web search (Gemini)",
    "Nhà cung cấp:": "Provider:",
    "Tắt (chỉ dùng Claude)": "Off (Claude only)",
    "Gemini API (khóa Google AI Studio)": "Gemini API (Google AI Studio key)",
    "Gemini CLI (đăng nhập Google)": "Gemini CLI (Google sign-in)",
    "Khóa Gemini API:": "Gemini API key:",
    "Dán khóa mới (để trống = giữ khóa hiện tại)": "Paste a new key (leave empty to keep the current one)",
    "Xóa khóa": "Remove key",
    "BẮT BUỘC bám nguồn tìm kiếm (không bám được thì bỏ nguồn, không để Claude làm thay)": "REQUIRE search grounding (if it fails, drop the source; Claude does not take over)",
    # trang Gemini
    "Khóa và trạng thái": "Key & status",
    "Kiểm tra khóa": "Check key",
    "Bấm “Kiểm tra khóa” để thử khóa Gemini.": "Press “Check key” to test the Gemini key.",
    "Chưa có khóa — nhập ở trang Cài đặt chung.": "No key — enter it on the General settings page.",
    "Thang model": "Model ladder",
    "Thứ tự": "Order",
    "Bậc": "Tier",
    "Phiên bản": "Version",
    "Tải lại danh sách model": "Reload model list",
    "Chính sách": "Policy",
    "Bậc ưu tiên:": "Preferred tier:",
    "Pro (mạnh nhất)": "Pro (most capable)",
    "Flash (cân bằng)": "Flash (balanced)",
    "Flash-Lite (rẻ, nhanh)": "Flash-Lite (cheap, fast)",
    "Tự cập nhật danh sách model từ Google": "Auto-update the model list from Google",
    "Hạ xuống model thấp hơn khi hết định mức": "Fall back to a lower model when quota runs out",
    "Tải lại danh sách mỗi:": "Reload list every:",
    "  giờ": "  hours",
    "Lưu chính sách": "Save policy",
    # trang Đội agent / Hợp đồng
    "Số": "No.", "Tên": "Name", "Tầng": "Tier", "Công cụ": "Tools",
    "Lưu thay đổi": "Save changes", "Hoàn tác": "Undo",
    "Chỉ đổi được engine và model. Công cụ (tools) chỉ đọc; agent không có quyền Write/Edit. "
    "Chỉ 7 agent khảo sát mới được chọn gemini.":
        "Only engine and model can be changed. Tools are read-only; agents never get Write/Edit. "
        "Only the 7 research agents may use gemini.",
    "Số lượt": "Runs", "Đạt": "Passed", "Không đạt": "Failed", "Đạt ngay lần 1": "First-try passes",
    "Tỉ lệ đạt": "Pass rate", "Chưa có lượt chạy Gemini nào.": "No Gemini runs yet.",
    "N lượt gần nhất: ": "Last N runs: ", "tất cả": "all",
}


from . import page_cost as _pc, page_koc as _pk          # noqa: E402  bản dịch do từng trang khai báo
EN.update(_pk.EN)
EN.update(_pc.EN)
EN[_pk.TITLE_VI] = _pk.TITLE_EN
EN[_pc.TITLE_VI] = _pc.TITLE_EN
EN.update({"<b>Chi phí theo luồng</b>": "<b>Cost per flow</b>",
           "<b>Model Gemini đang nghỉ</b>": "<b>Gemini models on cooldown</b>"})
for _k in [k for k, v in EN.items() if k == v]:      # bản dịch trùng chữ gốc là vô nghĩa (và test cấm)
    del EN[_k]


def _tr(w: QWidget, slot: str, cur: str, lang: str) -> str:
    """Chữ cần hiển thị cho một ô. Chữ gốc được nhớ trên chính widget."""
    vi = w.property(f"_vi_{slot}")
    shown = w.property(f"_en_{slot}")
    if vi is None or (cur != vi and cur != shown):     # chữ do ứng dụng vừa đặt lại → là gốc mới
        vi = cur
    target = EN.get(vi, vi) if lang == "en" else vi
    w.setProperty(f"_vi_{slot}", vi)
    w.setProperty(f"_en_{slot}", target)
    return target


def apply(root: QWidget, lang: str) -> None:
    lang = "en" if lang == "en" else "vi"
    for w in [root, *root.findChildren(QWidget)]:
        if isinstance(w, QMainWindow) or w is root and w.windowTitle():
            w.setWindowTitle(_tr(w, "title", w.windowTitle(), lang))
        if isinstance(w, (QLabel, QAbstractButton)) and w.text():
            w.setText(_tr(w, "text", w.text(), lang))
        elif isinstance(w, QGroupBox):
            w.setTitle(_tr(w, "title", w.title(), lang))
        elif isinstance(w, (QLineEdit, QPlainTextEdit)) and w.placeholderText():
            w.setPlaceholderText(_tr(w, "ph", w.placeholderText(), lang))
        elif isinstance(w, QTabWidget):
            for i in range(w.count()):
                w.setTabText(i, _tr(w, f"tab{i}", w.tabText(i), lang))
        elif isinstance(w, QListWidget):
            for i in range(w.count()):
                w.item(i).setText(_tr(w, f"row{i}", w.item(i).text(), lang))
        elif isinstance(w, QComboBox):
            for i in range(w.count()):
                w.setItemText(i, _tr(w, f"item{i}", w.itemText(i), lang))
        elif isinstance(w, QTableWidget):
            for c in range(w.columnCount()):
                it = w.horizontalHeaderItem(c)
                if it is not None:
                    it.setText(_tr(w, f"h{c}", it.text(), lang))
        if isinstance(w, QAbstractSpinBox) and hasattr(w, "suffix"):
            if w.suffix():
                w.setSuffix(_tr(w, "suffix", w.suffix(), lang))
