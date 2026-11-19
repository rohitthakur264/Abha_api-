"""Outbound ABDM client: session auth, headers, bridge URL update, and link token calls."""
import time
import uuid

import httpx
from fastapi import HTTPException

import config
from store import hit_breakpoint, now_iso, sent_requests, token_cache


# ==============================================================================
# GLOBAL SESSION ACCESS TOKEN STATE (Senior Requirement 1)
# Stored in global variables so any Postman/ProDoc call reuses the active token.
# If expired, a fresh accessToken is automatically generated from ABDM Gateway.
# ==============================================================================
GLOBAL_ACCESS_TOKEN: str | None = None
GLOBAL_ACCESS_TOKEN_EXPIRY: float = 0.0  # Unix timestamp when token expires


def get_global_session_status() -> dict:
    """Inspect current GLOBAL_ACCESS_TOKEN status and remaining validity."""
    now = time.time()
    is_valid = bool(GLOBAL_ACCESS_TOKEN and now < GLOBAL_ACCESS_TOKEN_EXPIRY)
    remaining = max(0, int(GLOBAL_ACCESS_TOKEN_EXPIRY - now)) if is_valid else 0
    return {
        "has_token": bool(GLOBAL_ACCESS_TOKEN),
        "is_valid": is_valid,
        "expires_in_seconds": remaining,
        "token_preview": (GLOBAL_ACCESS_TOKEN[:25] + "...") if GLOBAL_ACCESS_TOKEN else None,
    }


def make_headers(
    request_id: str,
    with_hip: bool = False,
    hip_id: str | None = None,
    link_token: str | None = None,
) -> dict:
    """Build mandatory ABDM v3 request headers."""
    headers = {
        "Content-Type": "application/json",
        "REQUEST-ID": request_id,
        "TIMESTAMP": now_iso(),
        "X-CM-ID": config.CM_ID,
    }
    if with_hip:
        headers["X-HIP-ID"] = hip_id or config.HIP_ID
    if link_token:
        headers["X-LINK-TOKEN"] = link_token
    return headers


async def get_access_token(force_refresh: bool = False) -> str:
    """
    Fetch ABDM gateway accessToken or reuse cached token from GLOBAL_ACCESS_TOKEN.
    Senior Requirement 1:
      - Uses GLOBAL_ACCESS_TOKEN if active.
      - If expired or not set, generates new token from ABDM Gateway and updates global variable.
    """
    global GLOBAL_ACCESS_TOKEN, GLOBAL_ACCESS_TOKEN_EXPIRY
    now = time.time()

    # 1. Check if global variable has a valid active token
    if (
        not force_refresh
        and GLOBAL_ACCESS_TOKEN
        and now < (GLOBAL_ACCESS_TOKEN_EXPIRY - config.TOKEN_REFRESH_BUFFER_SECONDS)
    ):
        return GLOBAL_ACCESS_TOKEN

    # 2. Token is missing or expired -> Generate fresh session token from ABDM
    body = {
        "clientId": config.CLIENT_ID,
        "clientSecret": config.CLIENT_SECRET,
        "grantType": "client_credentials",
    }
    async with httpx.AsyncClient(timeout=config.HTTP_TIMEOUT) as client:
        r = await client.post(config.SESSION_URL, json=body, headers=make_headers(str(uuid.uuid4())))
    if r.status_code != 200:
        raise HTTPException(502, f"ABDM session generation failed ({r.status_code}): {r.text}")

    data = r.json()
    expires_in = int(data.get("expiresIn", config.TOKEN_EXPIRY_FALLBACK))
    
    # Update Global Variables
    GLOBAL_ACCESS_TOKEN = data["accessToken"]
    GLOBAL_ACCESS_TOKEN_EXPIRY = now + expires_in

    # Also keep store.py token_cache in sync for backward compatibility
    token_cache["value"] = GLOBAL_ACCESS_TOKEN
    token_cache["exp"] = GLOBAL_ACCESS_TOKEN_EXPIRY

    hit_breakpoint("1", "Got ABDM Session accessToken and stored in GLOBAL_ACCESS_TOKEN", expiresIn=expires_in)
    return GLOBAL_ACCESS_TOKEN


async def send_to_abdm(
    method: str,
    url: str,
    payload: dict,
    label: str,
    with_hip: bool = False,
    hip_id: str | None = None,
    link_token: str | None = None,
) -> dict:
    """Send an authenticated request to ABDM and record its REQUEST-ID for callback matching."""
    token = await get_access_token()
    rid = str(uuid.uuid4())
    headers = make_headers(rid, with_hip=with_hip, hip_id=hip_id, link_token=link_token)
    headers["Authorization"] = f"Bearer {token}"

    sent_requests[rid] = {
        "label": label,
        "method": method,
        "url": url,
        "payload": payload,
        "sent_at": now_iso(),
        "http_status": None,
    }

    # === BREAKPOINT 2: Send request to ABDM with unique REQUEST-ID ===
    hit_breakpoint("2", "Sending request to ABDM", method=method, label=label, request_id=rid)
    async with httpx.AsyncClient(timeout=config.HTTP_TIMEOUT) as client:
        r = await client.request(method, url, json=payload, headers=headers)

    sent_requests[rid]["http_status"] = r.status_code
    sent_requests[rid]["immediate_response"] = r.text[:config.LOG_PREVIEW_LENGTH]

    # === BREAKPOINT 3: Immediate HTTP 202 ACK (linkToken arrives later on webhook) ===
    hit_breakpoint("3", "Received immediate ABDM HTTP reply", status=r.status_code, request_id=rid)
    return {"request_id": rid, "http_status": r.status_code, "immediate_response": r.text}


async def register_bridge_url() -> dict:
    """Register callback URL with ABDM gateway."""
    if not config.WEBHOOK_SITE_URL:
        raise HTTPException(400, "WEBHOOK_SITE_TOKEN / WEBHOOK_SITE_BASE not configured")
    res = await send_to_abdm("PATCH", config.BRIDGE_URL_ENDPOINT, {"url": config.WEBHOOK_SITE_URL}, "register-bridge")
    res["bridge_url"] = config.WEBHOOK_SITE_URL
    return res

