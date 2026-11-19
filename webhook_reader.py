"""Webhook callback parser (shared by direct endpoint & webhook.site poller)."""
import asyncio
import json
import time
from typing import Any

import httpx

import config
from store import (
    care_context_transactions,
    hit_breakpoint,
    link_tokens,
    log,
    now_iso,
    pending_events,
    received,
    save_token,
    seen_uuids,
    sent_requests,
)

_poll_lock = asyncio.Lock()
_rate_limit_until = 0.0
_callback_listeners: list = []


def register_callback_listener(func) -> None:
    """Register a callback function to be invoked automatically when a message is received on the webhook."""
    if func not in _callback_listeners:
        _callback_listeners.append(func)


def _first(value: Any) -> Any:
    """webhook.site returns header values as lists; normalise to a single string."""
    return value[0] if isinstance(value, list) and value else value


def on_message_received(message: dict) -> dict:
    """
    Senior Requirement 3 Callback Function:
    Invoked automatically the exact millisecond an incoming message arrives.
    Acknowledges: 'I have received this message' and processes the content.
    """
    req_id = message.get("request_id")
    has_token = message.get("has_link_token", False)
    matched = message.get("matched_request")
    log.info("🔔 [WEBHOOK CALLBACK] 'I have received this message!' | request_id=%s | has_link_token=%s | matched=%s", req_id, has_token, matched)
    return {
        "status": "ACK",
        "confirmation": "I have received this message",
        "request_id": req_id,
        "matched_request": matched,
        "has_link_token": has_token,
        "received_at": message.get("received_at") or now_iso(),
    }


async def open_webhook(callback=None) -> dict:
    """
    Senior Requirement 3:
    Opens and activates the webhook channel:
      1. Registers the callback URL with ABDM Gateway.
      2. Attaches the callback function so whenever ABDM sends a message,
         the callback is automatically triggered without manual polling.
    """
    from abdm_client import register_bridge_url
    log.info("[WEBHOOK] Opening webhook channel and registering URL with ABDM...")
    res = await register_bridge_url()
    
    cb_func = callback or on_message_received
    register_callback_listener(cb_func)
    
    log.info("[WEBHOOK] Webhook channel is OPEN. Callback attached: %s", cb_func.__name__)
    return {
        "status": "OPEN",
        "webhook_url": config.WEBHOOK_SITE_URL,
        "mode": "EVENT_DRIVEN_PUSH_CALLBACK",
        "callback_attached": cb_func.__name__,
        "abdm_registration": res,
    }


async def open_webhook_listener() -> dict:
    """Alias for open_webhook() for backward compatibility."""
    return await open_webhook()


def handle_webhook_callback(
    *,
    source: str = "direct-webhook",
    method: str = "POST",
    path: str = "/webhook",
    headers: dict | None = None,
    raw_content: str | dict = "",
    uid: str | None = None,
    received_at: str | None = None,
) -> dict | None:
    """
    Senior Requirement 3:
    Dedicated callback handler invoked when an incoming webhook message is received.
    Parses payload, extracts tokens, executes listeners, and updates local DB/store.
    """
    return process_callback(
        source=source,
        method=method,
        path=path,
        headers=headers,
        raw_content=raw_content,
        uid=uid or f"cb-{uuid.uuid4()}",
        received_at=received_at,
    )


def process_callback(
    *,
    source: str,
    method: str,
    path: str,
    headers: dict | None,
    raw_content: str | dict,
    uid: str,
    received_at: str | None = None,
) -> dict | None:
    """
    Core webhook reader:
      1. Deduplicate by uid
      2. Parse JSON body
      3. Match echoed requestId back to sent_requests
      4. Extract linkToken & abhaAddress
      5. Store entry & signal waiting request
    """
    # === BREAKPOINT 4 (BP-1): Deduplicate so Python never reads the same callback twice ===
    if uid in seen_uuids:
        return None
    seen_uuids.add(uid)

    # Parse raw HTTP body string into Python dict
    if isinstance(raw_content, dict):
        payload = raw_content
    else:
        try:
            payload = json.loads(raw_content or "{}")
        except json.JSONDecodeError:
            payload = {"raw": str(raw_content)}
    body = payload if isinstance(payload, dict) else {}

    # Extract REQUEST-ID echoed by ABDM and check whether Python sent it
    norm_headers = {k.lower(): _first(v) for k, v in (headers or {}).items()}
    request_id = (
        (body.get("response") or {}).get("requestId")
        or (body.get("resp") or {}).get("requestId")
        or norm_headers.get("request-id")
    )
    matched = sent_requests.get(request_id, {}).get("label") if request_id else None

    if config.ONLY_MATCHED_CALLBACKS and (not request_id or request_id not in sent_requests):
        log.info("[SKIP] Ignored callback with unknown/old request_id=%s (%s)", request_id, path)
        return None

    hit_breakpoint("4", "Python fetched new matching webhook", source=source, method=method, path=path)
    # === BREAKPOINT 5 (BP-2): Parsed JSON body ===
    hit_breakpoint("5", "Parsed webhook JSON body", keys=list(body.keys()))
    # === BREAKPOINT 6 (BP-3): Matched echoed REQUEST-ID back to our sent request ===
    hit_breakpoint("6", "Matched response.requestId to sent request", request_id=request_id, matched=matched)

    # === BREAKPOINT 7 (BP-4): Extract linkToken & abhaAddress from JSON and save it ===
    link_token = body.get("linkToken")
    abha_address = body.get("abhaAddress")
    if link_token:
        norm_abha = abha_address.strip().lower() if isinstance(abha_address, str) and abha_address.strip() else None
        key = norm_abha or request_id or uid
        save_token(key, {
            "abhaAddress": abha_address,
            "linkToken": link_token,
            "request_id": request_id,
            "received_at": received_at or now_iso(),
        })
        preview = link_token[:config.TOKEN_PREVIEW_LENGTH] + "..."
        hit_breakpoint("7", "Extracted linkToken & saved for UI", abhaAddress=key, token_preview=preview)
    elif body.get("error"):
        hit_breakpoint("7", "ABDM returned error in callback", error=body["error"])

    entry = {
        "source": source,
        "path": path,
        "method": method,
        "request_id": request_id,
        "matched_request": matched,
        "received_at": received_at or now_iso(),
        "has_link_token": bool(link_token),
        "abhaAddress": abha_address,
        "payload": payload,
    }
    received.append(entry)

    # === BREAKPOINT 8 (BP-5): Callback stored -> dashboard refreshes & caller wakes up ===
    if request_id and request_id in pending_events:
        pending_events[request_id].set()
    hit_breakpoint("8", "Stored callback for dashboard display", total_callbacks=len(received))

    # Update live care context transaction state if matching request_id
    if request_id and request_id in care_context_transactions:
        txn = care_context_transactions[request_id]
        has_err = bool(body.get("error"))
        txn["status"] = "FAILED" if has_err else "SUCCESS"
        txn["message"] = "Care context linking failed via callback" if has_err else "Care context linking completed successfully via webhook callback"
        txn["updated_at"] = now_iso()
        txn["callback_payload"] = payload

    # Senior Requirement 3: Invoke any registered callback listeners
    for listener in _callback_listeners:
        try:
            if asyncio.iscoroutinefunction(listener):
                asyncio.create_task(listener(entry))
            else:
                listener(entry)
        except Exception as e:
            log.warning("Callback listener error: %s", e)

    return entry


async def seed_existing_webhook_items() -> None:
    """Read pre-existing webhook.site items, extract/cache all tokens, and mark as seen."""
    if not config.WEBHOOK_SITE_API:
        return
    try:
        async with httpx.AsyncClient(timeout=config.POLL_TIMEOUT) as client:
            r = await client.get(
                config.WEBHOOK_SITE_API,
                params={"sorting": "newest", "per_page": config.WEBHOOK_PER_PAGE},
            )
        if r.status_code == 200:
            items = r.json().get("data", [])
            for item in reversed(items):
                uid = item.get("uuid")
                if not uid or uid in seen_uuids:
                    continue
                path = (item.get("url", "").split(config.WEBHOOK_SITE_TOKEN, 1)[-1]) or "/"
                process_callback(
                    source="startup-cache",
                    method=item.get("method", "POST"),
                    path=path,
                    headers=item.get("headers") or {},
                    raw_content=item.get("content") or "{}",
                    uid=uid,
                    received_at=item.get("created_at"),
                )
            log.info("[STARTUP] Processed & cached %d webhook items from webhook.site", len(items))
    except Exception as exc:
        log.warning("[STARTUP] Could not seed webhook.site items: %s", exc)


async def poll_webhook_site() -> int:
    """Demo-only transport: poll webhook.site API and pass new callbacks to process_callback()."""
    global _rate_limit_until
    if not config.WEBHOOK_SITE_API or time.time() < _rate_limit_until:
        return 0

    async with _poll_lock:
        if time.time() < _rate_limit_until:
            return 0
        async with httpx.AsyncClient(timeout=config.POLL_TIMEOUT) as client:
            r = await client.get(
                config.WEBHOOK_SITE_API,
                params={"sorting": "newest", "per_page": config.WEBHOOK_PER_PAGE},
            )

        if r.status_code == 429:
            _rate_limit_until = time.time() + config.RATE_LIMIT_BACKOFF_SECONDS
            log.warning("[POLL] webhook.site rate-limited (429); backing off %ss", config.RATE_LIMIT_BACKOFF_SECONDS)
            return 0
        if r.status_code != 200:
            log.warning("[POLL] webhook.site poll failed: %s %s", r.status_code, r.text[:config.LOG_PREVIEW_LENGTH])
            return 0

        new_count = 0
        for item in reversed(r.json().get("data", [])):
            uid = item.get("uuid")
            if not uid or uid in seen_uuids:
                continue
            path = (item.get("url", "").split(config.WEBHOOK_SITE_TOKEN, 1)[-1]) or "/"
            res = process_callback(
                source="webhook.site-poll",
                method=item.get("method", "POST"),
                path=path,
                headers=item.get("headers") or {},
                raw_content=item.get("content") or "{}",
                uid=uid,
                received_at=item.get("created_at"),
            )
            if res:
                new_count += 1
        return new_count


async def wait_for_callback(
    request_id: str,
    timeout_sec: float | None = None,
    expected_abha: str | None = None,
    require_link_token: bool = False,
) -> dict | None:
    """Poll briefly until the callback matching request_id or expected_abha arrives or timeout expires."""
    wait_sec = config.CALLBACK_WAIT_SECONDS if timeout_sec is None else timeout_sec
    norm_expected = expected_abha.strip().lower() if expected_abha else None
    ev = asyncio.Event()
    pending_events[request_id] = ev

    def _matches(cb: dict) -> bool:
        if require_link_token and not cb.get("has_link_token"):
            return False
        if cb.get("request_id") == request_id:
            return True
        if norm_expected and cb.get("abhaAddress") and cb.get("abhaAddress").strip().lower() == norm_expected:
            return True
        return False

    try:
        for cb in reversed(received):
            if _matches(cb):
                return cb
        if norm_expected and norm_expected in link_tokens and (not require_link_token or link_tokens[norm_expected].get("linkToken")):
            return {"payload": link_tokens[norm_expected], "request_id": request_id}

        deadline = time.time() + wait_sec
        while time.time() < deadline:
            await asyncio.sleep(config.POLL_STEP_SECONDS)
            await poll_webhook_site()
            for cb in reversed(received):
                if _matches(cb):
                    return cb
            if norm_expected and norm_expected in link_tokens and (not require_link_token or link_tokens[norm_expected].get("linkToken")):
                return {"payload": link_tokens[norm_expected], "request_id": request_id}
            if ev.is_set():
                match = next((cb for cb in reversed(received) if _matches(cb)), None)
                if match:
                    return match
        return None
    finally:
        pending_events.pop(request_id, None)


async def poll_loop() -> None:
    """Background polling task (demo-only)."""
    log.info("[POLL-LOOP] Background poller started (every %ss)", config.POLL_SECONDS)
    while True:
        await asyncio.sleep(config.POLL_SECONDS)
        # Avoid double-polling webhook.site when an active request is already polling
        if pending_events:
            continue
        try:
            await poll_webhook_site()
        except Exception as exc:
            log.warning("[POLL-LOOP] error: %s", exc)

