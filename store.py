"""In-memory store & logging/breakpoint helpers (replace with database in production)."""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("abdm-linktoken")

import json
import base64
import time
from pathlib import Path

# Persistent token cache files
CACHE_FILE = Path(__file__).parent / "link_tokens_cache.json"
M1_CACHE_FILE = Path(__file__).parent / "m1_tokens_cache.json"
M1_LINKED_FILE = Path(__file__).parent / "m1_linked_cache.json"
M1_PROFILES_FILE = Path(__file__).parent / "m1_profiles_cache.json"
M1_SEARCHES_FILE = Path(__file__).parent / "m1_searches_cache.json"


def parse_jwt_expiry(token: str | None) -> float | None:
    """Decode JWT payload without verifying signature to extract the 'exp' timestamp."""
    payload = parse_jwt_payload(token)
    if "exp" in payload:
        try:
            return float(payload["exp"])
        except Exception:
            pass
    return None


def parse_jwt_payload(token: str | None) -> dict:
    """Decode JWT payload dictionary without verifying signature."""
    if not token or not isinstance(token, str):
        return {}
    try:
        parts = token.split(".")
        if len(parts) >= 2:
            payload_b64 = parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4)
            payload_json = base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode("utf-8")
            return json.loads(payload_json)
    except Exception:
        pass
    return {}


def is_link_token_valid(token_or_data: dict | str | None) -> bool:
    """
    Check if linkToken exists and has not expired.
    Senior Requirement 2: Detect token expiry so fresh token can be generated.
    """
    if not token_or_data:
        return False
    now = time.time()
    if isinstance(token_or_data, str):
        exp = parse_jwt_expiry(token_or_data)
        return exp is not None and now < exp
    if isinstance(token_or_data, dict):
        raw_tok = token_or_data.get("linkToken")
        if not raw_tok:
            return False
        exp = token_or_data.get("expires_at") or parse_jwt_expiry(raw_tok)
        if exp is not None:
            return now < float(exp)
        return True
    return False


def get_token_expiry_info(token_or_data: dict | str | None) -> dict:
    """Return structured expiry details for a linkToken."""
    raw_token = token_or_data if isinstance(token_or_data, str) else (token_or_data or {}).get("linkToken")
    if not raw_token:
        return {"has_token": False, "is_valid": False, "expires_at": None, "expires_at_iso": None, "remaining_days": 0}
    
    exp = None
    if isinstance(token_or_data, dict) and token_or_data.get("expires_at"):
        exp = float(token_or_data["expires_at"])
    else:
        exp = parse_jwt_expiry(raw_token)
    
    # Fallback if unparsable: 180 days (6 months) from now
    if not exp:
        exp = time.time() + (180 * 86400)

    now = time.time()
    is_valid = now < exp
    remaining_secs = max(0.0, exp - now)
    remaining_days = int(remaining_secs // 86400)
    iso_str = datetime.fromtimestamp(exp, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "has_token": True,
        "is_valid": is_valid,
        "expires_at": exp,
        "expires_at_iso": iso_str,
        "remaining_days": remaining_days,
        "remaining_seconds": int(remaining_secs),
    }


def _load_cache() -> dict[str, dict]:
    if CACHE_FILE.exists():
        try:
            data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            # Auto-enrich cached tokens with expiry if missing
            for item in data.values():
                if isinstance(item, dict) and item.get("linkToken") and not item.get("expires_at"):
                    info = get_token_expiry_info(item["linkToken"])
                    item["expires_at"] = info["expires_at"]
                    item["expires_at_iso"] = info["expires_at_iso"]
            return data
        except Exception as e:
            log.warning("Could not load token cache: %s", e)
    return {}

load_cache = _load_cache

def save_token(key: str, data: dict) -> None:
    # Ensure expiry timestamp and ISO format are populated
    raw_token = data.get("linkToken")
    if raw_token and not data.get("expires_at"):
        info = get_token_expiry_info(raw_token)
        data["expires_at"] = info["expires_at"]
        data["expires_at_iso"] = info["expires_at_iso"]

    link_tokens[key] = data
    try:
        current = _load_cache()
        current[key] = data
        CACHE_FILE.write_text(json.dumps(current, indent=2), encoding="utf-8")
    except Exception as e:
        log.warning("Could not persist token: %s", e)

def _load_m1_cache() -> dict[str, dict]:
    if M1_CACHE_FILE.exists():
        try:
            return json.loads(M1_CACHE_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning("Could not load M1 token cache: %s", e)
    return {}

def save_m1_token(patient_id: str, data: Any, abha_number: str = "", abha_address: str = "") -> None:
    if isinstance(data, str):
        data = {
            "token": data,
            "abhaNumber": abha_number,
            "abhaAddress": abha_address,
            "saved_at": now_iso(),
        }
    elif isinstance(data, dict):
        if abha_number and "abhaNumber" not in data:
            data["abhaNumber"] = abha_number
        if abha_address and "abhaAddress" not in data:
            data["abhaAddress"] = abha_address
    m1_patient_tokens[patient_id] = data
    try:
        current = _load_m1_cache()
        current[patient_id] = data
        M1_CACHE_FILE.write_text(json.dumps(current, indent=2), encoding="utf-8")
    except Exception as e:
        log.warning("Could not persist M1 token: %s", e)

def mask_abha_number(val: str | None) -> str:
    """Mask 14-digit ABHA number as XX-XXXX-XXXX-XXXX."""
    if not val:
        return ""
    digits = "".join(ch for ch in str(val) if ch.isdigit())
    if len(digits) == 14:
        return f"{digits[:2]}-XXXX-XXXX-{digits[-4:]}"
    if len(val) >= 8:
        return f"{val[:2]}-XXXX-{val[-4:]}"
    return val

# Memory & State (M2)
sent_requests: dict[str, dict] = {}
received: list[dict] = []
link_tokens: dict[str, dict] = _load_cache()
seen_uuids: set[str] = set()
pending_events: dict[str, asyncio.Event] = {}
token_cache: dict[str, Any] = {"value": None, "exp": 0.0}
care_context_transactions: dict[str, dict] = {}  # Maps txnId & requestId -> live transaction state

def _load_m1_linked() -> dict[str, dict]:
    if M1_LINKED_FILE.exists():
        try:
            return json.loads(M1_LINKED_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning("Could not load M1 linked cache: %s", e)
    return {}

def save_m1_linked(patient_id: str, data: dict) -> None:
    m1_linked_patients[patient_id] = data
    try:
        current = _load_m1_linked()
        current[patient_id] = data
        M1_LINKED_FILE.write_text(json.dumps(current, indent=2), encoding="utf-8")
    except Exception as e:
        log.warning("Could not persist M1 linked patient: %s", e)

def _load_m1_profiles() -> dict[str, dict]:
    if M1_PROFILES_FILE.exists():
        try:
            return json.loads(M1_PROFILES_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning("Could not load M1 profiles cache: %s", e)
    return {}

def save_m1_profile(patient_id: str, data: dict) -> None:
    m1_patient_profiles[patient_id] = data
    try:
        current = _load_m1_profiles()
        current[patient_id] = data
        M1_PROFILES_FILE.write_text(json.dumps(current, indent=2), encoding="utf-8")
    except Exception as e:
        log.warning("Could not persist M1 profile: %s", e)

def _load_m1_searches() -> dict[str, dict]:
    if M1_SEARCHES_FILE.exists():
        try:
            return json.loads(M1_SEARCHES_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning("Could not load M1 searches cache: %s", e)
    return {}

def save_m1_search(key: str, data: dict) -> None:
    m1_searches[key] = data
    try:
        current = _load_m1_searches()
        current[key] = data
        M1_SEARCHES_FILE.write_text(json.dumps(current, indent=2), encoding="utf-8")
    except Exception as e:
        log.warning("Could not persist M1 search: %s", e)

def get_m1_linked(patient_id: str) -> dict:
    disk = _load_m1_linked()
    if patient_id in disk:
        m1_linked_patients[patient_id] = disk[patient_id]
        return disk[patient_id]
    return m1_linked_patients.get(patient_id, {})

def get_m1_profile(patient_id: str) -> dict:
    disk = _load_m1_profiles()
    if patient_id in disk:
        m1_patient_profiles[patient_id] = disk[patient_id]
        return disk[patient_id]
    return m1_patient_profiles.get(patient_id, {})

# Memory & State (M1 - ABHA APIs 1-7)
m1_patient_tokens: dict[str, dict] = _load_m1_cache()
m1_enrolments: dict[str, dict] = {}       # patientId -> {txnId, mobile, name, dob, gender}
m1_searches: dict[str, dict] = _load_m1_searches()
m1_otp_txns: dict[str, dict] = {}         # otpTxnId -> {patientId, searchTxnId, selectedIndex, selectedMatch}
m1_verifications: dict[str, dict] = {}    # verificationId -> {patientId, abhaNumber, abhaAddress, verifiedAt}
m1_linked_patients: dict[str, dict] = _load_m1_linked()
m1_patient_profiles: dict[str, dict] = _load_m1_profiles()


def now_iso() -> str:
    """Return UTC timestamp in ABDM ISO-8601 millisecond format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def hit_breakpoint(bp_id: str, title: str, **context: Any) -> None:
    """
    Log demo breakpoint in terminal and optionally pause in pdb.
    Click a red-dot IDE breakpoint on the `if config.DEBUG_BREAKPOINTS:` line
    or set DEBUG_BREAKPOINTS=1 in .env.
    """
    summary = ", ".join(f"{k}={v}" for k, v in context.items())
    log.info("[BREAKPOINT %s] %s | %s", bp_id, title, summary)
    if config.DEBUG_BREAKPOINTS:  # <-- CLICK RED DOT BREAKPOINT HERE in IDE
        breakpoint()


def clear_demo_store() -> None:
    """Clear tracked outbound/inbound demo records while keeping seen_uuids for dedup."""
    sent_requests.clear()
    received.clear()
    link_tokens.clear()

