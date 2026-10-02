"""SQLite (MVP, mục 11.1): bộ nhớ đề tài chống trùng + sổ chi phí + lịch sử chạy.

Chống trùng dùng độ giống token (Jaccard) trên văn bản đã bỏ dấu. Giai đoạn 2 thay bằng
embedding + pgvector qua cùng giao diện `TopicStore`.
"""
from __future__ import annotations

import re
import sqlite3
import unicodedata
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

DEDUP_WINDOW_DAYS = 30  # mục 4: loại đề tài đã làm 30 ngày qua
DEDUP_THRESHOLD = 0.6

SCHEMA = """
CREATE TABLE IF NOT EXISTS topics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  flow_id TEXT NOT NULL,
  day TEXT NOT NULL,
  title TEXT NOT NULL,
  norm TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_topics_day ON topics(day);
CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  flow_id TEXT NOT NULL,
  day TEXT NOT NULL,
  status TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT
);
CREATE TABLE IF NOT EXISTS cost_ledger (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT,
  flow_id TEXT NOT NULL,
  day TEXT NOT NULL,
  usd REAL NOT NULL,
  tokens INTEGER NOT NULL DEFAULT 0,
  note TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cost_day ON cost_ledger(flow_id, day);
"""

_STOP = {"va", "la", "cua", "cho", "the", "nhung", "mot", "cac", "duoc", "trong", "voi", "khi", "de",
         "der", "die", "das", "und", "the", "of", "and", "to", "in", "a"}


def normalize(text: str) -> frozenset[str]:
    t = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    toks = re.findall(r"[a-z0-9]+", t)
    return frozenset(w for w in toks if w not in _STOP and len(w) > 1)


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class BudgetExceeded(RuntimeError):
    def __init__(self, flow_id: str, spent: float, cap: float):
        super().__init__(f"luồng {flow_id} đã chi ${spent:.2f} ≥ giới hạn ${cap:.2f}/ngày — dừng an toàn")
        self.flow_id, self.spent, self.cap = flow_id, spent, cap


class Store:
    def __init__(self, path: str | Path = "agnet.db"):
        self.path = str(path)
        with self._conn() as c:
            c.executescript(SCHEMA)

    @contextmanager
    def _conn(self):
        c = sqlite3.connect(self.path)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        finally:
            c.close()

    # ---- đề tài / chống trùng --------------------------------------------
    def find_duplicate(self, title: str, *, today: date, threshold: float = DEDUP_THRESHOLD) -> tuple[str, float] | None:
        """Trả về (tiêu đề đã có, độ giống) nếu trùng đề tài trong 30 ngày — dùng chung mọi luồng."""
        cutoff = (today - timedelta(days=DEDUP_WINDOW_DAYS)).isoformat()
        n = normalize(title)
        best: tuple[str, float] | None = None
        with self._conn() as c:
            for r in c.execute("SELECT title, norm FROM topics WHERE day >= ?", (cutoff,)):
                s = jaccard(n, frozenset(r["norm"].split()))
                if s >= threshold and (best is None or s > best[1]):
                    best = (r["title"], round(s, 2))
        return best

    def claim_topic(self, flow_id: str, title: str, *, today: date) -> bool:
        """Khoá đề tài. False nếu đã có đề tài giống (không ghi). Nguyên tử trong một giao dịch."""
        with self._conn() as c:
            c.execute("BEGIN IMMEDIATE")
            cutoff = (today - timedelta(days=DEDUP_WINDOW_DAYS)).isoformat()
            n = normalize(title)
            for r in c.execute("SELECT norm FROM topics WHERE day >= ?", (cutoff,)):
                if jaccard(n, frozenset(r["norm"].split())) >= DEDUP_THRESHOLD:
                    return False
            c.execute(
                "INSERT INTO topics(flow_id, day, title, norm, created_at) VALUES (?,?,?,?,?)",
                (flow_id, today.isoformat(), title, " ".join(sorted(n)), _now()),
            )
            return True

    def release_topic(self, flow_id: str, title: str, *, today: date) -> None:
        """Nhả khoá khi kịch bản bị QA loại để đề tài còn được dùng lại."""
        with self._conn() as c:
            c.execute("DELETE FROM topics WHERE flow_id=? AND day=? AND title=?", (flow_id, today.isoformat(), title))

    # ---- chi phí ---------------------------------------------------------
    def spent_today(self, flow_id: str, today: date) -> float:
        with self._conn() as c:
            r = c.execute("SELECT COALESCE(SUM(usd),0) s FROM cost_ledger WHERE flow_id=? AND day=?", (flow_id, today.isoformat())).fetchone()
        return float(r["s"])

    def charge(self, flow_id: str, usd: float, *, cap: float, today: date, run_id: str | None = None, tokens: int = 0, note: str = "") -> float:
        """Ghi chi phí; ném BudgetExceeded NGAY SAU KHI ghi nếu chạm trần (mục 13: giới hạn cứng)."""
        with self._conn() as c:
            c.execute(
                "INSERT INTO cost_ledger(run_id, flow_id, day, usd, tokens, note, created_at) VALUES (?,?,?,?,?,?,?)",
                (run_id, flow_id, today.isoformat(), usd, tokens, note, _now()),
            )
        spent = self.spent_today(flow_id, today)
        if spent >= cap:
            raise BudgetExceeded(flow_id, spent, cap)
        return spent

    def remaining(self, flow_id: str, cap: float, today: date) -> float:
        return max(0.0, cap - self.spent_today(flow_id, today))

    # ---- lịch sử chạy ----------------------------------------------------
    def start_run(self, run_id: str, flow_id: str, today: date) -> None:
        with self._conn() as c:
            c.execute("INSERT OR REPLACE INTO runs(run_id, flow_id, day, status, started_at) VALUES (?,?,?,?,?)",
                      (run_id, flow_id, today.isoformat(), "running", _now()))

    def finish_run(self, run_id: str, status: str) -> None:
        with self._conn() as c:
            c.execute("UPDATE runs SET status=?, finished_at=? WHERE run_id=?", (status, _now(), run_id))

    # ---- phục vụ chạy tự động hằng ngày ---------------------------------
    def mark_stale_running(self, older_than_hours: float = 6.0) -> int:
        """Lần chạy 'running' bỏ dở (máy tắt/ngắt điện) → 'interrupted', để lần sau còn chạy bù."""
        cut = (datetime.now(timezone.utc) - timedelta(hours=older_than_hours)).isoformat(timespec="seconds")
        with self._conn() as c:
            cur = c.execute("UPDATE runs SET status='interrupted', finished_at=? "
                            "WHERE status='running' AND started_at <= ?", (_now(), cut))
            return cur.rowcount

    def ran_today(self, flow_id: str, today: date) -> bool:
        """True nếu hôm nay đã có lần chạy KẾT THÚC (dù thiếu sản lượng) — tránh chạy lại tốn tiền."""
        with self._conn() as c:
            r = c.execute("SELECT COUNT(*) n FROM runs WHERE flow_id=? AND day=? "
                          "AND status NOT IN ('running','interrupted')", (flow_id, today.isoformat())).fetchone()
        return bool(r["n"])

    def is_running(self, flow_id: str) -> bool:
        with self._conn() as c:
            r = c.execute("SELECT COUNT(*) n FROM runs WHERE flow_id=? AND status='running'", (flow_id,)).fetchone()
        return bool(r["n"])

    def recent_runs(self, limit: int = 20, flow_id: str | None = None) -> list[dict]:
        q = "SELECT r.*, (SELECT COALESCE(SUM(usd),0) FROM cost_ledger l WHERE l.run_id=r.run_id) usd FROM runs r"
        args: tuple = ()
        if flow_id:
            q += " WHERE r.flow_id=?"
            args = (flow_id,)
        q += " ORDER BY r.started_at DESC LIMIT ?"
        with self._conn() as c:
            return [dict(r) for r in c.execute(q, args + (limit,))]

    def cost_by_day(self, days: int = 7) -> list[dict]:
        cut = (date.today() - timedelta(days=days)).isoformat()
        with self._conn() as c:
            return [dict(r) for r in c.execute(
                "SELECT day, flow_id, ROUND(SUM(usd),3) usd, SUM(tokens) tokens, COUNT(*) calls "
                "FROM cost_ledger WHERE day >= ? GROUP BY day, flow_id ORDER BY day DESC", (cut,))]

    def finish_running(self, flow_id: str, status: str) -> int:
        """Kết thúc cứng mọi lần chạy đang treo của một luồng (dùng khi quá trần thời gian)."""
        with self._conn() as c:
            cur = c.execute("UPDATE runs SET status=?, finished_at=? WHERE flow_id=? AND status='running'",
                            (status, _now(), flow_id))
            return cur.rowcount
