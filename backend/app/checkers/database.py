import asyncio
import time
from typing import Any

from .base import CheckOutcome


async def check_postgres(config: dict[str, Any]) -> CheckOutcome:
    host = config.get("host", "localhost")
    port = int(config.get("port", 5432))
    database = config.get("database", "postgres")
    user = config.get("user", "postgres")
    password = config.get("password", "")
    query = config.get("query", "SELECT 1")

    start = time.perf_counter()
    try:
        import psycopg2

        def _connect():
            conn = psycopg2.connect(
                host=host,
                port=port,
                dbname=database,
                user=user,
                password=password,
                connect_timeout=5,
            )
            cursor = conn.cursor()
            cursor.execute(query)
            cursor.fetchone()
            conn.close()

        await asyncio.to_thread(_connect)
        elapsed = (time.perf_counter() - start) * 1000
        return CheckOutcome("up", "PostgreSQL connection OK", elapsed)
    except ImportError:
        return CheckOutcome(
            "down",
            "psycopg2 not installed. Run: pip install psycopg2-binary",
        )
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return CheckOutcome("down", str(exc), elapsed)


async def check_mysql(config: dict[str, Any]) -> CheckOutcome:
    host = config.get("host", "localhost")
    port = int(config.get("port", 3306))
    database = config.get("database", "")
    user = config.get("user", "root")
    password = config.get("password", "")
    query = config.get("query", "SELECT 1")

    start = time.perf_counter()
    try:
        import pymysql

        def _connect():
            conn = pymysql.connect(
                host=host,
                port=port,
                database=database or None,
                user=user,
                password=password,
                connect_timeout=5,
            )
            cursor = conn.cursor()
            cursor.execute(query)
            cursor.fetchone()
            conn.close()

        await asyncio.to_thread(_connect)
        elapsed = (time.perf_counter() - start) * 1000
        return CheckOutcome("up", "MySQL connection OK", elapsed)
    except ImportError:
        return CheckOutcome(
            "down",
            "pymysql not installed. Run: pip install pymysql",
        )
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return CheckOutcome("down", str(exc), elapsed)


_oracle_client_initialized = False


def _ensure_oracle_client() -> str:
    """Enable thick mode when Instant Client path is configured. Returns mode label."""
    global _oracle_client_initialized
    import oracledb
    from ..config import get_settings

    if not oracledb.is_thin_mode():
        _oracle_client_initialized = True
        return "thick"

    if _oracle_client_initialized:
        return "thin"

    lib_dir = (get_settings().oracle_client_lib_dir or "").strip()
    if not lib_dir:
        return "thin"

    oracledb.init_oracle_client(lib_dir=lib_dir)
    _oracle_client_initialized = True
    return "thick" if not oracledb.is_thin_mode() else "thin"


def _oracle_error_hint(exc: Exception) -> str:
    text = str(exc)
    if "DPY-3010" in text:
        return (
            "Oracle DB is 11g or older; python-oracledb thin mode cannot connect. "
            "Install Oracle Instant Client, set ORACLE_CLIENT_LIB_DIR in backend/.env "
            "to the Instant Client folder, then restart the backend."
        )
    if "DPY-6001" in text or "ORA-12514" in text:
        return (
            "Service name is wrong (listener does not know it). "
            "Use the real SERVICE_NAME/SID (often ORCL), or set DSN like host:1521/ORCL."
        )
    return text


async def check_oracle(config: dict[str, Any]) -> CheckOutcome:
    host = config.get("host", "localhost")
    port = int(config.get("port", 1521))
    service_name = config.get("service_name", "ORCL")
    user = config.get("user", "")
    password = config.get("password", "")
    query = config.get("query", "SELECT 1 FROM DUAL")
    dsn = config.get("dsn")

    if not user:
        return CheckOutcome("down", "Oracle user is required")

    start = time.perf_counter()
    try:
        import oracledb

        mode = _ensure_oracle_client()
        connect_dsn = dsn or f"{host}:{port}/{service_name}"

        def _connect():
            conn = oracledb.connect(user=user, password=password, dsn=connect_dsn)
            cursor = conn.cursor()
            cursor.execute(query)
            cursor.fetchone()
            conn.close()

        await asyncio.to_thread(_connect)
        elapsed = (time.perf_counter() - start) * 1000
        return CheckOutcome("up", f"Oracle connection OK ({mode} mode)", elapsed)
    except ImportError:
        return CheckOutcome(
            "down",
            "oracledb not installed. Run: pip install oracledb",
        )
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        hint = _oracle_error_hint(exc)
        raw = str(exc).splitlines()[0]
        message = hint if hint != str(exc) else raw
        if hint != str(exc) and "DPY-3010" in str(exc):
            # Keep actionable hint, but note thin/thick for debugging.
            try:
                import oracledb

                mode = "thin" if oracledb.is_thin_mode() else "thick"
                message = f"{hint} (mode={mode})"
            except Exception:
                message = hint
        return CheckOutcome("down", message, elapsed)
