import socket
import time
from typing import Any

import httpx

from .base import CheckOutcome


async def check_http(config: dict[str, Any]) -> CheckOutcome:
    url = config.get("url", "")
    method = config.get("method", "GET").upper()
    expected_status = int(config.get("expected_status", 200))
    timeout = float(config.get("timeout", 10))
    headers = config.get("headers") or {}
    verify_ssl = config.get("verify_ssl", True)
    if isinstance(verify_ssl, str):
        verify_ssl = verify_ssl.strip().lower() not in {"0", "false", "no", "off"}

    if not url:
        return CheckOutcome("down", "URL is required")

    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(follow_redirects=True, verify=verify_ssl) as client:
            response = await client.request(method, url, headers=headers, timeout=timeout)
        elapsed = (time.perf_counter() - start) * 1000

        if response.status_code == expected_status:
            return CheckOutcome(
                "up",
                f"HTTP {response.status_code}",
                elapsed,
                {"status_code": response.status_code},
            )
        return CheckOutcome(
            "down",
            f"Expected {expected_status}, got {response.status_code}",
            elapsed,
            {"status_code": response.status_code},
        )
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return CheckOutcome("down", str(exc), elapsed)


async def check_tcp(config: dict[str, Any]) -> CheckOutcome:
    host = config.get("host", "")
    port = int(config.get("port", 80))
    timeout = float(config.get("timeout", 5))

    if not host:
        return CheckOutcome("down", "Host is required")

    start = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            elapsed = (time.perf_counter() - start) * 1000
            return CheckOutcome("up", f"Connected to {host}:{port}", elapsed)
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return CheckOutcome("down", str(exc), elapsed)
