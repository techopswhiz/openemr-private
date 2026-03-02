# AI-generated: Claude Code (claude.ai/code) — observability metrics collector
"""
In-memory metrics collector for the OpenEMR Clinical Agent.

Tracks request latency, LLM inference time, tool call performance,
token usage, error categories, and verification trigger counts.
Thread-safe singleton — no external dependencies (no Prometheus needed).
"""
import json
import sqlite3
import statistics
import threading
import time
from pathlib import Path

from app.config import settings


class MetricsCollector:
    """Collects and summarizes agent performance metrics in-memory."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.request_count: int = 0
        self.request_latencies: list[float] = []
        self.llm_latencies: list[float] = []
        self.tool_latencies: dict[str, list[float]] = {}
        self.tool_call_counts: dict[str, int] = {}
        self.tool_errors: dict[str, int] = {}
        self.error_counts: dict[str, int] = {}
        self.token_usage: list[dict] = []
        self.verification_triggers: dict[str, int] = {}
        self._start_time = time.time()

    def record_request(self, latency: float, tokens_in: int = 0, tokens_out: int = 0) -> None:
        """Record a completed request with its total latency and token usage."""
        with self._lock:
            self.request_count += 1
            self.request_latencies.append(latency)
            if tokens_in > 0 or tokens_out > 0:
                self.token_usage.append({
                    "input": tokens_in,
                    "output": tokens_out,
                    "total": tokens_in + tokens_out,
                    "timestamp": time.time(),
                })

    def record_llm_latency(self, latency: float) -> None:
        """Record LLM inference time for a single call."""
        with self._lock:
            self.llm_latencies.append(latency)

    def record_token_usage(self, tokens_in: int, tokens_out: int) -> None:
        """Record token usage from an LLM call."""
        with self._lock:
            self.token_usage.append({
                "input": tokens_in,
                "output": tokens_out,
                "total": tokens_in + tokens_out,
                "timestamp": time.time(),
            })

    def record_tool_call(self, tool_name: str, latency: float, success: bool = True) -> None:
        """Record a tool invocation with its latency and outcome."""
        with self._lock:
            self.tool_call_counts[tool_name] = self.tool_call_counts.get(tool_name, 0) + 1
            if tool_name not in self.tool_latencies:
                self.tool_latencies[tool_name] = []
            self.tool_latencies[tool_name].append(latency)
            if not success:
                self.tool_errors[tool_name] = self.tool_errors.get(tool_name, 0) + 1

    def record_error(self, category: str, message: str = "") -> None:
        """Record an error by category (e.g., 'openemr_api', 'llm', 'timeout')."""
        with self._lock:
            self.error_counts[category] = self.error_counts.get(category, 0) + 1

    def record_verification(self, check_name: str, triggered: bool) -> None:
        """Record a verification check execution and whether it triggered a warning."""
        with self._lock:
            if triggered:
                self.verification_triggers[check_name] = (
                    self.verification_triggers.get(check_name, 0) + 1
                )

    @staticmethod
    def _percentiles(data: list[float]) -> dict:
        """Compute p50, p95, p99 from a list of values."""
        if not data:
            return {"p50": 0, "p95": 0, "p99": 0}
        sorted_data = sorted(data)
        n = len(sorted_data)
        return {
            "p50": round(sorted_data[int(n * 0.5)] if n > 0 else 0, 4),
            "p95": round(sorted_data[int(n * 0.95)] if n > 1 else sorted_data[-1], 4),
            "p99": round(sorted_data[int(n * 0.99)] if n > 1 else sorted_data[-1], 4),
        }

    def get_summary(self) -> dict:
        """Return a full metrics summary as a JSON-serializable dict."""
        with self._lock:
            uptime = time.time() - self._start_time
            total_errors = sum(self.error_counts.values())
            error_rate = total_errors / self.request_count if self.request_count > 0 else 0

            # Token totals
            total_input_tokens = sum(t["input"] for t in self.token_usage)
            total_output_tokens = sum(t["output"] for t in self.token_usage)
            avg_input = total_input_tokens / len(self.token_usage) if self.token_usage else 0
            avg_output = total_output_tokens / len(self.token_usage) if self.token_usage else 0

            # Per-tool summary
            tool_summary = {}
            for name, count in self.tool_call_counts.items():
                lats = self.tool_latencies.get(name, [])
                tool_summary[name] = {
                    "calls": count,
                    "errors": self.tool_errors.get(name, 0),
                    "latency": self._percentiles(lats),
                    "avg_latency": round(statistics.mean(lats), 4) if lats else 0,
                }

            return {
                "uptime_seconds": round(uptime, 1),
                "requests": {
                    "total": self.request_count,
                    "error_rate": round(error_rate, 4),
                    "latency": self._percentiles(self.request_latencies),
                },
                "llm": {
                    "calls": len(self.llm_latencies),
                    "latency": self._percentiles(self.llm_latencies),
                    "avg_latency": round(
                        statistics.mean(self.llm_latencies), 4
                    ) if self.llm_latencies else 0,
                },
                "tokens": {
                    "total_input": total_input_tokens,
                    "total_output": total_output_tokens,
                    "avg_input_per_call": round(avg_input, 1),
                    "avg_output_per_call": round(avg_output, 1),
                },
                "tools": tool_summary,
                "errors": dict(self.error_counts),
                "verification_triggers": dict(self.verification_triggers),
            }


# --- Eval history (SQLite-backed) ---

def _eval_db_connect() -> sqlite3.Connection:
    """Connect to the eval history database (same directory as sessions DB)."""
    db_path = Path(settings.memory_db_path).parent / "eval_history.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS eval_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            total INTEGER NOT NULL,
            passed INTEGER NOT NULL,
            failed INTEGER NOT NULL,
            results_by_category TEXT NOT NULL,
            pass_rate REAL NOT NULL
        )"""
    )
    conn.commit()
    return conn


def record_eval_run(
    total: int,
    passed: int,
    failed: int,
    results_by_category: dict[str, dict],
) -> dict:
    """Store an eval run result and return regression analysis.

    results_by_category: {"happy_path": {"total": 20, "passed": 18}, ...}
    Returns: {"recorded": True, "regression": bool, "details": str}
    """
    pass_rate = passed / total if total > 0 else 0
    conn = _eval_db_connect()
    try:
        conn.execute(
            "INSERT INTO eval_runs (timestamp, total, passed, failed, results_by_category, pass_rate) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (time.time(), total, passed, failed, json.dumps(results_by_category), pass_rate),
        )
        conn.commit()

        # Regression detection: compare to previous run
        rows = conn.execute(
            "SELECT pass_rate FROM eval_runs ORDER BY id DESC LIMIT 2"
        ).fetchall()

        regression = False
        details = "First recorded run"
        if len(rows) >= 2:
            current_rate = rows[0][0]
            previous_rate = rows[1][0]
            drop = previous_rate - current_rate
            if drop > 0.05:
                regression = True
                details = (
                    f"Pass rate dropped {drop:.1%}: "
                    f"{previous_rate:.1%} -> {current_rate:.1%}"
                )
            else:
                details = f"Pass rate: {current_rate:.1%} (previous: {previous_rate:.1%})"

        return {"recorded": True, "regression": regression, "details": details}
    finally:
        conn.close()


def get_eval_history(limit: int = 20) -> list[dict]:
    """Retrieve recent eval run history."""
    conn = _eval_db_connect()
    try:
        rows = conn.execute(
            "SELECT id, timestamp, total, passed, failed, results_by_category, pass_rate "
            "FROM eval_runs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {
                "id": r[0],
                "timestamp": r[1],
                "total": r[2],
                "passed": r[3],
                "failed": r[4],
                "results_by_category": json.loads(r[5]),
                "pass_rate": round(r[6], 4),
            }
            for r in rows
        ]
    finally:
        conn.close()


# Singleton instance
metrics = MetricsCollector()
# end AI-generated
