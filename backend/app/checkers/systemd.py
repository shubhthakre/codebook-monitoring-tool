import asyncio
import platform
import shutil
import time
from typing import Any

from .base import CheckOutcome

_JOURNALCTL = "/usr/bin/journalctl"
_SYSTEMCTL = "/usr/bin/systemctl"


def _resolve_bin(preferred: str, name: str) -> str | None:
    """Prefer absolute path (reliable under systemd), then PATH lookup."""
    if shutil.which(preferred):
        return preferred
    return shutil.which(name)


async def fetch_journal_logs(
    unit: str,
    *,
    lines: int = 100,
    since: str | None = None,
    until: str | None = None,
    grep: str | None = None,
) -> dict[str, Any]:
    """Fetch journalctl logs for a unit. Raises ValueError on config errors."""
    if not unit:
        raise ValueError("Systemd unit name is required (e.g. nginx.service)")

    if platform.system() != "Linux":
        raise RuntimeError(
            f"Systemd logs are only available on Linux hosts (got {platform.system()})"
        )

    journalctl = _resolve_bin(_JOURNALCTL, "journalctl")
    if not journalctl:
        raise RuntimeError("journalctl not found on this system")

    pattern = (grep or "").strip() or None

    cmd = [
        journalctl,
        "-u",
        unit,
        "-n",
        str(lines),
        "--no-pager",
        "-o",
        "short-iso",
    ]
    if since:
        cmd.extend(["--since", since])
    if until:
        cmd.extend(["--until", until])
    if pattern:
        # journalctl --grep uses PCRE; passed as argv (no shell)
        cmd.extend(["--grep", pattern])

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)

    err = stderr.decode(errors="replace").strip()
    if proc.returncode != 0:
        # --grep with no matches often exits 1 with empty stderr
        if pattern and proc.returncode == 1 and (
            not err or "no entries" in err.lower()
        ):
            log_lines: list[str] = []
        else:
            raise RuntimeError(err or "journalctl failed")
    else:
        log_lines = stdout.decode(errors="replace").strip().splitlines()
        if log_lines == [""]:
            log_lines = []

    is_active = await _check_unit_active(unit)

    return {
        "unit": unit,
        "lines": log_lines[-lines:],
        "active": is_active,
        "since": since,
        "until": until,
        "grep": pattern,
        "count": len(log_lines[-lines:]),
    }


async def check_systemd(config: dict[str, Any]) -> CheckOutcome:
    unit = config.get("unit", "")
    lines = int(config.get("lines", 50))
    since = config.get("since", "1 hour ago")
    grep = config.get("grep") or None

    if not unit:
        return CheckOutcome("down", "Systemd unit name is required (e.g. nginx.service)")

    start = time.perf_counter()
    try:
        result = await fetch_journal_logs(unit, lines=lines, since=since, grep=grep)
        elapsed = (time.perf_counter() - start) * 1000
        is_active = result["active"]
        log_lines = result["lines"]

        status = "up" if is_active else "down"
        message = (
            f"Unit {'active' if is_active else 'inactive'} — "
            f"{len(log_lines)} log lines fetched"
        )

        return CheckOutcome(
            status,
            message,
            elapsed,
            {"unit": unit, "lines": log_lines, "active": is_active},
        )
    except asyncio.TimeoutError:
        elapsed = (time.perf_counter() - start) * 1000
        return CheckOutcome("down", "journalctl timed out", elapsed)
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return CheckOutcome("down", str(exc), elapsed)


async def _check_unit_active(unit: str) -> bool:
    systemctl = _resolve_bin(_SYSTEMCTL, "systemctl")
    if not systemctl:
        return True

    proc = await asyncio.create_subprocess_exec(
        systemctl,
        "is-active",
        unit,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    return stdout.decode().strip() == "active"

