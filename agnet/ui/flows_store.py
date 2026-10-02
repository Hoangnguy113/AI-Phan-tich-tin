"""Sửa config/flows.yaml từ GUI mà KHÔNG mất comment.

Vì sao không dùng yaml.dump: flows.yaml có comment giải thích (catchup, catchup_until,
run_timeout_min...) và người dùng đọc file này bằng mắt. Ghi lại cả file bằng yaml.dump
sẽ xoá sạch comment và đảo thứ tự khoá. Nên ở đây chỉ thay GIÁ TRỊ của đúng dòng cần sửa.

An toàn khi lưu: dựng nội dung mới trong bộ nhớ → kiểm tra bằng chính models.load_flows
→ chỉ khi hợp lệ mới ghi ra đĩa, kèm bản .bak. Lưu sai không bao giờ phá file đang chạy được.
"""
from __future__ import annotations

import re
import tempfile
from pathlib import Path

import yaml

from ..core.models import load_flows

FLOW_START = re.compile(r"^(\s*)-\s+id:\s*(.+?)\s*(?:#.*)?$")


class InvalidFlows(ValueError):
    """Nội dung sau khi sửa không hợp lệ — đã bỏ, file trên đĩa còn nguyên."""


# ---- số tin trong ngày & bảng thời lượng ---------------------------------
def rescale_mix(mix: dict[str, int], quota: int) -> dict[str, int]:
    """Chia lại duration_mix theo số tin trong ngày, giữ tỉ lệ, tổng ĐÚNG bằng quota.

    models.Flow bắt sum(duration_mix) == daily_quota, nên đổi quota phải chia lại mix.
    Dùng phần dư lớn nhất (largest remainder) để tổng luôn khít, không bị lệch do làm tròn.
    """
    if not mix:
        return {}
    total = sum(mix.values())
    if total <= 0:
        keys = list(mix)
        base, extra = divmod(quota, len(keys))
        return {k: base + (1 if i < extra else 0) for i, k in enumerate(keys)}

    exact = {k: v * quota / total for k, v in mix.items()}
    out = {k: int(v) for k, v in exact.items()}
    # chia phần còn thiếu cho các khoá có phần thập phân lớn nhất
    for k in sorted(exact, key=lambda k: exact[k] - out[k], reverse=True)[: quota - sum(out.values())]:
        out[k] += 1
    return out


# ---- đọc ----------------------------------------------------------------
def flow_ids(path: str | Path) -> list[str]:
    ids = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = FLOW_START.match(line)
        if m:
            ids.append(m.group(2).strip().strip("\"'"))
    return ids


# ---- ghi ----------------------------------------------------------------
def _fmt(value: object) -> str:
    """Giá trị YAML một dòng, dạng gọn (inline) cho khớp văn phong file sẵn có."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return f"{value:g}" if isinstance(value, float) else str(value)
    if isinstance(value, (dict, list)):
        return yaml.safe_dump(value, default_flow_style=True, allow_unicode=True).strip().rstrip("\n")
    return yaml.safe_dump(value, default_flow_style=True, allow_unicode=True).strip().rstrip("\n...").strip()


def _block_bounds(lines: list[str], flow_id: str) -> tuple[int, int, str]:
    """Trả về (dòng đầu, dòng sau cuối, thụt lề của khoá) của khối một luồng."""
    start = indent = None
    for i, line in enumerate(lines):
        m = FLOW_START.match(line)
        if not m:
            continue
        if start is not None:                       # gặp luồng kế tiếp → hết khối
            return start, i, indent
        if m.group(2).strip().strip("\"'") == flow_id:
            start = i
            indent = m.group(1) + "  "              # khoá nằm sâu hơn dấu '-' hai dấu cách
    if start is None:
        raise KeyError(f"không có luồng {flow_id!r} trong file")
    return start, len(lines), indent


def apply_changes(text: str, flow_id: str, changes: dict[str, object]) -> str:
    """Thay giá trị các khoá trong khối của một luồng. Khoá chưa có thì thêm vào cuối khối."""
    lines = text.splitlines()
    start, end, indent = _block_bounds(lines, flow_id)

    for key, value in changes.items():
        pat = re.compile(rf"^(\s*{re.escape(key)}:\s*)(.*?)(\s*#.*)?$")
        for i in range(start, end):
            m = pat.match(lines[i])
            if m:
                lines[i] = f"{m.group(1)}{_fmt(value)}{m.group(3) or ''}"
                break
        else:
            # chèn sau dòng cuối CÓ NỘI DUNG của khối, để không nhảy qua dòng trống/comment cuối
            at = max((j for j in range(start, end) if lines[j].strip()), default=start) + 1
            lines.insert(at, f"{indent}{key}: {_fmt(value)}")
            end += 1
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def set_fields(path: str | Path, flow_id: str, changes: dict[str, object]) -> None:
    """Sửa rồi lưu. Kiểm tra hợp lệ TRƯỚC khi ghi; giữ bản .bak của nội dung cũ."""
    p = Path(path)
    old = p.read_text(encoding="utf-8")
    new = apply_changes(old, flow_id, changes)

    # kiểm tra trên file tạm — không đụng file thật nếu sai
    tmp = Path(tempfile.mkdtemp()) / p.name
    tmp.write_text(new, encoding="utf-8")
    try:
        load_flows(tmp)
    except Exception as e:
        raise InvalidFlows(str(e)) from e
    finally:
        tmp.unlink(missing_ok=True)

    p.with_suffix(p.suffix + ".bak").write_text(old, encoding="utf-8")
    p.write_text(new, encoding="utf-8")


# ---- giờ chạy <-> cron ----------------------------------------------------
_HHMM = re.compile(r"^(\d{1,2}):(\d{2})$")
_DAILY = re.compile(r"^(\d{1,2}) (\d{1,2}) \* \* \*$")


def times_to_cron(times: list[str]) -> list[str]:
    """['05:30', '17:00'] -> ['30 5 * * *', '0 17 * * *'] (hằng ngày; đã sắp xếp, bỏ trùng)."""
    out = set()
    for t in times:
        m = _HHMM.match(str(t).strip())
        if not m or not (0 <= int(m.group(1)) <= 23 and 0 <= int(m.group(2)) <= 59):
            raise ValueError(f"giờ không hợp lệ: {t!r} (cần HH:MM, 00:00–23:59)")
        out.add((int(m.group(1)), int(m.group(2))))
    return [f"{mm} {hh} * * *" for hh, mm in sorted(out)]


def cron_to_times(crons: list[str]) -> list[str] | None:
    """Ngược lại. Trả None nếu có cron KHÔNG phải "hằng ngày vào HH:MM" (theo thứ, theo chu kỳ...).

    None nghĩa là giao diện không được ghi đè lịch đó bằng bộ chọn giờ — sẽ làm mất ý người dùng.
    """
    found = set()
    for c in crons:
        m = _DAILY.match(str(c).strip())
        if not m or not (0 <= int(m.group(2)) <= 23 and 0 <= int(m.group(1)) <= 59):
            return None
        found.add((int(m.group(2)), int(m.group(1))))
    return [f"{hh:02d}:{mm:02d}" for hh, mm in sorted(found)]
