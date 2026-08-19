"""Microsoft Graph API connectivity check (OAuth2 client credentials)."""

from __future__ import annotations

import time
from typing import Any

import httpx

from .base import CheckOutcome

DEFAULT_SCOPE = "https://graph.microsoft.com/.default"
DEFAULT_ENDPOINT = "https://graph.microsoft.com/v1.0/"
TOKEN_URL_TMPL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"


async def check_graph(config: dict[str, Any]) -> CheckOutcome:
    tenant_id = (config.get("tenant_id") or "").strip()
    client_id = (config.get("client_id") or "").strip()
    client_secret = (config.get("client_secret") or "").strip()
    scope = (config.get("scope") or DEFAULT_SCOPE).strip() or DEFAULT_SCOPE
    endpoint = (config.get("endpoint") or DEFAULT_ENDPOINT).strip() or DEFAULT_ENDPOINT
    timeout = float(config.get("timeout", 15))

    if not tenant_id:
        return CheckOutcome("down", "Tenant ID is required")
    if not client_id:
        return CheckOutcome("down", "Client ID is required")
    if not client_secret:
        return CheckOutcome("down", "Client secret is required")

    token_url = TOKEN_URL_TMPL.format(tenant=tenant_id)
    start = time.perf_counter()

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            token_resp = await client.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "scope": scope,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if token_resp.status_code != 200:
                elapsed = (time.perf_counter() - start) * 1000
                detail = _oauth_error(token_resp)
                return CheckOutcome(
                    "down",
                    f"Token request failed (HTTP {token_resp.status_code}): {detail}",
                    elapsed,
                    {"stage": "token", "status_code": token_resp.status_code},
                )

            try:
                access_token = token_resp.json().get("access_token")
            except Exception:
                access_token = None
            if not access_token:
                elapsed = (time.perf_counter() - start) * 1000
                return CheckOutcome(
                    "down",
                    "Token response missing access_token",
                    elapsed,
                    {"stage": "token"},
                )

            graph_resp = await client.get(
                endpoint,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
            )

        elapsed = (time.perf_counter() - start) * 1000

        # Graph root and many endpoints return 200; some return 401/403 for missing perms
        if graph_resp.status_code < 400:
            return CheckOutcome(
                "up",
                f"Graph API OK (HTTP {graph_resp.status_code})",
                elapsed,
                {
                    "stage": "graph",
                    "status_code": graph_resp.status_code,
                    "endpoint": endpoint,
                },
            )

        # Auth worked but Graph rejected — still a connectivity/auth problem for monitoring
        detail = _graph_error(graph_resp)
        return CheckOutcome(
            "down",
            f"Graph call failed (HTTP {graph_resp.status_code}): {detail}",
            elapsed,
            {
                "stage": "graph",
                "status_code": graph_resp.status_code,
                "endpoint": endpoint,
            },
        )
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return CheckOutcome("down", str(exc), elapsed)


def _oauth_error(resp: httpx.Response) -> str:
    try:
        data = resp.json()
        parts = [
            str(data.get("error") or ""),
            str(data.get("error_description") or data.get("error_codes") or ""),
        ]
        msg = " — ".join(p for p in parts if p)
        return msg or resp.text[:300]
    except Exception:
        return (resp.text or "")[:300] or "no body"


def _graph_error(resp: httpx.Response) -> str:
    try:
        data = resp.json()
        err = data.get("error") or {}
        if isinstance(err, dict):
            code = err.get("code") or ""
            message = err.get("message") or ""
            joined = " — ".join(p for p in (code, message) if p)
            if joined:
                return joined
        return str(data)[:300]
    except Exception:
        return (resp.text or "")[:300] or "no body"
