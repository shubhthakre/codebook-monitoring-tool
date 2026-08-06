import sqlite3
import time
from typing import Any

from .base import CheckOutcome


async def check_sqlite(config: dict[str, Any]) -> CheckOutcome:
    path = config.get("path", "")
    query = config.get("query", "SELECT 1")

    if not path:
        return CheckOutcome("down", "Database path is required")

    start = time.perf_counter()
    try:
        conn = sqlite3.connect(path, timeout=5)
        cursor = conn.cursor()
        cursor.execute(query)
        cursor.fetchone()
        conn.close()
        elapsed = (time.perf_counter() - start) * 1000
        return CheckOutcome("up", "SQLite query succeeded", elapsed)
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return CheckOutcome("down", str(exc), elapsed)
