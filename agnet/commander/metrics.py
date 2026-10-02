"""Tỉ lệ đạt hợp đồng theo agent (mục 18.3 điểm 5). Bảng riêng trong cùng file SQLite với db.py; không sửa db.py."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS commander_compliance (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  agent TEXT NOT NULL,
  flow_id TEXT NOT NULL,
  compliance TEXT NOT NULL,
  attempts INTEGER NOT NULL,
  accepted INTEGER NOT NULL DEFAULT 0,
  rejected INTEGER NOT NULL DEFAULT 0,
  note TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cc_agent ON commander_compliance(agent, created_at);
"""


class ComplianceStore:
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

    def record(self, contract, outcome, *, now: datetime | None = None) -> None:
        rep = outcome.report
        n_acc = len(outcome.items) or (len(rep.accepted) if rep else 0)
        n_rej = len(rep.rejected) if rep else 0
        with self._conn() as c:
            c.execute(
                "INSERT INTO commander_compliance(agent, flow_id, compliance, attempts, accepted, rejected, note, created_at)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (contract.agent, contract.flow_id, outcome.compliance, outcome.attempts, n_acc, n_rej,
                 "; ".join(outcome.errors)[:500], (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")))

    def rates(self, *, last_n: int | None = None) -> dict[str, dict]:
        """{agent: {runs, passed, failed, first_try, rate}} — rate = passed/runs; chưa có lượt nào thì không có khoá."""
        out: dict[str, dict] = {}
        with self._conn() as c:
            agents = [r["agent"] for r in c.execute("SELECT DISTINCT agent FROM commander_compliance ORDER BY agent")]
            for a in agents:
                q = "SELECT compliance, attempts FROM commander_compliance WHERE agent=? ORDER BY id DESC"
                args: tuple = (a,)
                if last_n:
                    q += " LIMIT ?"
                    args = (a, last_n)
                rows = c.execute(q, args).fetchall()
                p = sum(1 for r in rows if r["compliance"] == "pass")
                out[a] = {"runs": len(rows), "passed": p, "failed": len(rows) - p,
                          "first_try": sum(1 for r in rows if r["compliance"] == "pass" and r["attempts"] == 1),
                          "rate": p / len(rows)}
        return out

    def rate(self, agent: str, *, last_n: int | None = None) -> float | None:
        r = self.rates(last_n=last_n).get(agent)
        return r["rate"] if r else None
