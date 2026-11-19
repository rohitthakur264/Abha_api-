"""Business logic service for Milestone 1 (M1) ABHA APIs 1 to 7."""
import logging
import uuid
from typing import Any

import httpx
from fastapi import HTTPException
from fastapi.responses import Response

import config
from abdm_client import get_access_token, make_headers
from crypto_abdm import encrypt_abdm, get_key_source
from store import (
    link_tokens,
    m1_enrolments,
    m1_linked_patients,
    m1_otp_txns,
    m1_patient_profiles,
    m1_patient_tokens,
    m1_searches,
    m1_verifications,
    mask_abha_number,
    now_iso,
    parse_jwt_payload,
    save_m1_token,
    save_m1_linked,
    save_m1_profile,
    save_m1_search,
)

log = logging.getLogger("abdm-m1-service")


def _m1_headers(request_id: str, x_token: str | None = None) -> dict[str, str]:
    """Build standard M1 headers with REQUEST-ID and TIMESTAMP."""
    hdrs = {
        "Content-Type": "application/json",
        "REQUEST-ID": request_id,
        "TIMESTAMP": now_iso(),
    }
    if x_token:
        # ABDM requires 'X-token: Bearer <token>' for profile/card/qr APIs
        token_str = x_token if not x_token.startswith("Bearer ") else x_token.replace("Bearer ", "")
        hdrs["X-token"] = f"Bearer {token_str}"
    return hdrs


# ==============================================================================
# API 1: Register Patient / Request Enrolment OTP
# ==============================================================================
async def enrol_request_otp(data: dict) -> dict:
    """
    ProDoc API 1: Starts ABHA enrolment for a new patient.
    Python encrypts Aadhaar with ABDM RSA cert, requests OTP from ABDM, and saves txnId.
    """
    patient_id = data.get("patientId")
    if not patient_id:
        raise HTTPException(400, "patientId is required")

    consent = data.get("consent")
    if consent is not True:
        raise HTTPException(400, "Patient consent is mandatory for ABHA enrolment (consent must be true)")

    plain_aadhaar = str(data.get("aadhaarNumber", "")).strip().replace(" ", "").replace("-", "")
    if len(plain_aadhaar) != 12 or not plain_aadhaar.isdigit():
        raise HTTPException(400, "Valid 12-digit Aadhaar number is required")

    # RSA-encrypt Aadhaar
    enc_aadhaar = await encrypt_abdm(plain_aadhaar)

    # Outbound call to ABDM
    token = await get_access_token()
    req_id = str(uuid.uuid4())
    headers = _m1_headers(req_id)
    headers["Authorization"] = f"Bearer {token}"

    abdm_payload = {
        "txnId": "",
        "scope": ["abha-enrol"],
        "loginHint": "aadhaar",
        "loginId": enc_aadhaar,
        "otpSystem": "aadhaar",
    }

    log.info("[API 1] Requesting ABHA enrolment OTP for patientId=%s", patient_id)
    async with httpx.AsyncClient(timeout=config.HTTP_TIMEOUT) as client:
        r = await client.post(config.ABHA_ENROL_REQUEST_OTP_URL, json=abdm_payload, headers=headers)

    if r.status_code != 200:
        log.warning("[API 1] ABDM enrolment OTP failed (%s): %s", r.status_code, r.text)
        raise HTTPException(r.status_code, f"ABDM enrolment OTP failed: {r.text}")

    res_json = r.json()
    txn_id = res_json.get("txnId")
    if not txn_id:
        raise HTTPException(502, f"ABDM did not return txnId: {r.text}")

    # Store enrolment context
    m1_enrolments[patient_id] = {
        "txnId": txn_id,
        "mobile": data.get("mobile"),
        "name": data.get("name"),
        "dob": data.get("dob"),
        "gender": data.get("gender"),
        "created_at": now_iso(),
    }

    return {
        "success": True,
        "status": "OTP_PENDING",
        "patientId": patient_id,
        "transactionId": txn_id,
        "message": res_json.get("message", "ABHA OTP generated successfully"),
    }


# ==============================================================================
# API 2: Verify Enrolment OTP
# ==============================================================================
async def enrol_verify_otp(data: dict) -> dict:
    """
    ProDoc API 2: Completes enrolment by verifying Aadhaar OTP.
    Python encrypts OTP, verifies with ABDM, securely saves tokens and returns masked identity.
    """
    patient_id = data.get("patientId")
    txn_id = data.get("transactionId")
    otp = str(data.get("otp", "")).strip()

    if not patient_id or not otp:
        raise HTTPException(400, "patientId and otp are required")

    saved_enrol = m1_enrolments.get(patient_id, {})
    # Auto-map transactionId if omitted
    txn_id = (txn_id or "").strip() or saved_enrol.get("txnId")
    if not txn_id:
        raise HTTPException(400, f"No pending enrolment transaction found for patient '{patient_id}'. Call API 1 first or provide transactionId.")
    mobile = data.get("mobile") or saved_enrol.get("mobile", "")

    # RSA-encrypt OTP
    enc_otp = await encrypt_abdm(otp)

    token = await get_access_token()
    req_id = str(uuid.uuid4())
    headers = _m1_headers(req_id)
    headers["Authorization"] = f"Bearer {token}"

    abdm_payload = {
        "authData": {
          "authMethods": ["otp"],
          "otp": {
            "txnId": txn_id,
            "otpValue": enc_otp,
            "mobile": mobile,
          },
        },
        "consent": {
          "code": config.ABHA_CONSENT_CODE,
          "version": config.ABHA_CONSENT_VERSION,
        },
    }

    log.info("[API 2] Verifying enrolment OTP for patientId=%s, txnId=%s", patient_id, txn_id)
    async with httpx.AsyncClient(timeout=config.HTTP_TIMEOUT) as client:
        r = await client.post(config.ABHA_ENROL_BY_AADHAAR_URL, json=abdm_payload, headers=headers)

    if r.status_code != 200:
        log.warning("[API 2] ABDM OTP verification failed (%s): %s", r.status_code, r.text)
        raise HTTPException(r.status_code, f"ABDM OTP verification failed: {r.text}")

    res_json = r.json()
    tokens = res_json.get("tokens", {})
    profile = res_json.get("ABHAProfile", {})

    abha_number = profile.get("ABHANumber") or profile.get("abhaNumber") or ""
    abha_address = profile.get("preferredAbhaAddress") or profile.get("abhaAddress") or ""

    yob = profile.get("yearOfBirth")
    mob = profile.get("monthOfBirth")
    day_ob = profile.get("dayOfBirth")
    if yob and mob and day_ob:
        dob = f"{yob}-{str(mob).zfill(2)}-{str(day_ob).zfill(2)}"
    else:
        dob = str(profile.get("dob") or profile.get("dateOfBirth") or yob or "").strip()
    profile["dob"] = dob

    # Securely store tokens and profile (never return tokens in response or logs)
    if tokens.get("token"):
        save_m1_token(patient_id, {
            "token": tokens["token"],
            "refreshToken": tokens.get("refreshToken"),
            "expiresIn": tokens.get("expiresIn"),
            "saved_at": now_iso(),
        })

    save_m1_profile(patient_id, profile)
    save_m1_linked(patient_id, {
        "patientId": patient_id,
        "abhaNumber": abha_number,
        "abhaAddress": abha_address,
        "dob": dob,
        "linked_at": now_iso(),
    })

    return {
        "success": True,
        "status": "ABHA_CREATED",
        "patientId": patient_id,
        "abhaNumber": mask_abha_number(abha_number),
        "abhaAddress": abha_address,
        "message": res_json.get("message", "ABHA created and linked successfully"),
    }


# ==============================================================================
# API 3: Search Existing ABHA (3 Stages in 1 Route via action)
# ==============================================================================
async def search_abha(data: dict) -> dict:
    """
    ProDoc API 3: Dispatches based on action field:
      - SEARCH: Stage A - Search by mobile, returns matches
      - REQUEST_OTP: Stage B - Select match index, requests login OTP
      - VERIFY_OTP: Stage C - Verifies login OTP, creates verificationId
    """
    action = str(data.get("action") or "SEARCH").upper()
    patient_id = str(data.get("patientId") or data.get("regNo") or "").strip()
    if not patient_id:
        return {
            "success": False,
            "errorCode": "ABHA_NOT_FOUND",
            "message": "patientId is required",
        }

    if action == "SEARCH":
        return await _search_stage_a(patient_id, data)
    elif action == "REQUEST_OTP":
        return await _search_stage_b(patient_id, data)
    elif action == "VERIFY_OTP":
        return await _search_stage_c(patient_id, data)
    else:
        return {
            "success": False,
            "errorCode": "ABHA_NOT_FOUND",
            "message": f"Invalid action '{action}'. Must be SEARCH, REQUEST_OTP, or VERIFY_OTP.",
        }


async def _search_stage_a(patient_id: str, data: dict) -> dict:
    """Stage A: Search ABHA by mobile."""
    search_value = str(data.get("searchValue") or data.get("mobile") or data.get("mobileNo") or "").strip()
    if not search_value:
        return {
            "success": False,
            "errorCode": "ABHA_NOT_FOUND",
            "message": "searchValue is required to search ABHA",
        }

    try:
        enc_val = await encrypt_abdm(search_value)
        token = await get_access_token()
        req_id = str(uuid.uuid4())
        headers = _m1_headers(req_id)
        headers["Authorization"] = f"Bearer {token}"

        abdm_payload = {
            "scope": ["search-abha"],
            "mobile": enc_val,
        }

        log.info("[API 3 - SEARCH] Searching ABHA by %s for patientId=%s", data.get("searchType", "MOBILE"), patient_id)
        async with httpx.AsyncClient(timeout=config.HTTP_TIMEOUT) as client:
            r = await client.post(config.ABHA_SEARCH_URL, json=abdm_payload, headers=headers)

        if r.status_code == 200:
            res_json = r.json()
            search_txn_id = ""
            accounts = []
            if isinstance(res_json, list):
                if res_json:
                    first = res_json[0]
                    if isinstance(first, dict):
                        search_txn_id = first.get("txnId") or ""
                        accounts = first.get("ABHA") or first.get("accounts") or res_json
                    else:
                        accounts = res_json
            elif isinstance(res_json, dict):
                search_txn_id = res_json.get("txnId") or ""
                accounts = res_json.get("ABHA") or res_json.get("accounts") or ([res_json] if "ABHANumber" in res_json or "abhaAddress" in res_json else [])

            matches = []
            for acc in accounts:
                if not isinstance(acc, dict):
                    continue
                num_val = str(acc.get("ABHANumber") or acc.get("abhaNumber") or acc.get("healthIdNumber") or "").strip()
                addr_val = str(acc.get("preferredAbhaAddress") or acc.get("abhaAddress") or acc.get("phrAddress") or "").strip()
                name_val = str(acc.get("name") or "").strip()
                gender_val = str(acc.get("gender") or "").strip()
                dob_val = str(acc.get("dob") or acc.get("yearOfBirth") or acc.get("dateOfBirth") or "").strip()
                index_val = acc.get("index")

                match_item = {
                    "abhaNumber": num_val,
                    "verificationRequired": True,
                }
                if index_val is not None:
                    match_item["index"] = index_val
                if name_val:
                    match_item["name"] = name_val
                if gender_val:
                    match_item["gender"] = gender_val
                if dob_val:
                    match_item["dob"] = dob_val
                if addr_val:
                    match_item["abhaAddress"] = addr_val

                matches.append(match_item)

            if matches:
                search_data = {
                    "patientId": patient_id,
                    "searchTxnId": search_txn_id,
                    "accounts": accounts,
                    "matches": matches,
                    "created_at": now_iso(),
                }
                save_m1_search(search_txn_id or patient_id, search_data)
                save_m1_search(patient_id, search_data)

                resp = {
                    "success": True,
                    "patientId": patient_id,
                    "matches": matches,
                    "message": "ABHA search completed",
                }
                if search_txn_id:
                    resp["searchTxnId"] = search_txn_id
                return resp
            else:
                return {
                    "success": False,
                    "errorCode": "ABHA_NOT_FOUND",
                    "message": "No matching ABHA record found",
                }
        else:
            log.warning("[API 3 - SEARCH] ABDM returned status %s: %s", r.status_code, r.text)
            return {
                "success": False,
                "errorCode": "ABHA_NOT_FOUND",
                "message": "No matching ABHA record found",
            }
    except Exception as exc:
        log.error("[API 3 - SEARCH] Exception: %s", exc)
        return {
            "success": False,
            "errorCode": "ABHA_NOT_FOUND",
            "message": "No matching ABHA record found",
        }


async def _search_stage_b(patient_id: str, data: dict) -> dict:
    """Stage B: Request Login OTP for selected match index."""
    search_txn_id = (data.get("searchTxnId") or "").strip()
    selected_index = data.get("selectedIndex")

    # Auto-map searchTxnId from latest search for this patient if omitted
    if not search_txn_id:
        for s_id, s_meta in reversed(list(m1_searches.items())):
            if s_meta.get("patientId") == patient_id:
                search_txn_id = s_id
                break

    if not search_txn_id or selected_index is None:
        raise HTTPException(400, "searchTxnId (or prior SEARCH call) and selectedIndex are required for REQUEST_OTP action")

    search_meta = m1_searches.get(search_txn_id)
    if not search_meta or search_meta.get("patientId") != patient_id:
        log.warning("[API 3 - REQUEST_OTP] searchTxnId %s not found or patient mismatch", search_txn_id)

    enc_idx = await encrypt_abdm(str(selected_index))
    token = await get_access_token()
    req_id = str(uuid.uuid4())
    headers = _m1_headers(req_id)
    headers["Authorization"] = f"Bearer {token}"

    abdm_payload = {
        "scope": ["abha-login", "search-abha", "mobile-verify"],
        "loginHint": "index",
        "loginId": enc_idx,
        "otpSystem": "abdm",
        "txnId": search_txn_id,
    }

    log.info("[API 3 - REQUEST_OTP] Requesting login OTP for patientId=%s, index=%s", patient_id, selected_index)
    async with httpx.AsyncClient(timeout=config.HTTP_TIMEOUT) as client:
        r = await client.post(config.ABHA_LOGIN_REQUEST_OTP_URL, json=abdm_payload, headers=headers)

    if r.status_code != 200:
        log.warning("[API 3 - REQUEST_OTP] Failed (%s): %s", r.status_code, r.text)
        raise HTTPException(r.status_code, f"ABDM login OTP request failed: {r.text}")

    res_json = r.json()
    otp_txn_id = res_json.get("txnId")

    m1_otp_txns[otp_txn_id] = {
        "patientId": patient_id,
        "searchTxnId": search_txn_id,
        "selectedIndex": selected_index,
        "created_at": now_iso(),
    }

    return {
        "success": True,
        "status": "OTP_SENT",
        "patientId": patient_id,
        "searchTxnId": search_txn_id,
        "otpTxnId": otp_txn_id,
        "message": res_json.get("message", "OTP sent to registered mobile number"),
    }


async def _search_stage_c(patient_id: str, data: dict) -> dict:
    """Stage C: Verify Login OTP and generate verificationId."""
    otp_txn_id = (data.get("otpTxnId") or "").strip()
    otp = str(data.get("otp", "")).strip()

    # Auto-map otpTxnId from latest OTP request for this patient if omitted
    if not otp_txn_id:
        for o_id, o_meta in reversed(list(m1_otp_txns.items())):
            if o_meta.get("patientId") == patient_id:
                otp_txn_id = o_id
                break

    if not otp_txn_id or not otp:
        raise HTTPException(400, "otpTxnId (or prior REQUEST_OTP call) and otp are required for VERIFY_OTP action")

    enc_otp = await encrypt_abdm(otp)
    token = await get_access_token()
    req_id = str(uuid.uuid4())
    headers = _m1_headers(req_id)
    headers["Authorization"] = f"Bearer {token}"

    abdm_payload = {
        "scope": ["abha-login", "mobile-verify"],
        "authData": {
            "authMethods": ["otp"],
            "otp": {
                "txnId": otp_txn_id,
                "otpValue": enc_otp,
            },
        },
    }

    log.info("[API 3 - VERIFY_OTP] Verifying login OTP for patientId=%s, otpTxnId=%s", patient_id, otp_txn_id)
    async with httpx.AsyncClient(timeout=config.HTTP_TIMEOUT) as client:
        r = await client.post(config.ABHA_LOGIN_VERIFY_OTP_URL, json=abdm_payload, headers=headers)

    if r.status_code != 200:
        log.warning("[API 3 - VERIFY_OTP] Verification failed (%s): %s", r.status_code, r.text)
        return {
            "success": False,
            "status": "VERIFICATION_FAILED",
            "message": f"ABDM OTP verification rejected ({r.status_code}): {r.text}",
        }

    res_json = r.json()
    auth_result = str(res_json.get("authResult", "")).lower()
    if auth_result and auth_result != "success":
        return {
            "success": False,
            "status": "VERIFICATION_FAILED",
            "message": res_json.get("message", "OTP verification failed. ABHA has not been verified."),
        }

    # Extract ABHA token
    x_token = res_json.get("token") or (res_json.get("tokens") or {}).get("token")
    if x_token:
        save_m1_token(patient_id, {
            "token": x_token,
            "saved_at": now_iso(),
        })

    # Retrieve match context if available
    otp_meta = m1_otp_txns.get(otp_txn_id, {})
    search_meta = m1_searches.get(otp_meta.get("searchTxnId"), {})
    sel_idx = otp_meta.get("selectedIndex")
    matched_acc = next((m for m in search_meta.get("accounts", []) if m.get("index") == sel_idx), {})

    profile = res_json.get("ABHAProfile") or res_json.get("profile") or {}
    abha_num = profile.get("ABHANumber") or profile.get("abhaNumber") or matched_acc.get("ABHANumber") or matched_acc.get("abhaNumber") or ""
    abha_addr = profile.get("preferredAbhaAddress") or profile.get("abhaAddress") or matched_acc.get("preferredAbhaAddress") or matched_acc.get("abhaAddress") or ""

    if x_token and not abha_addr:
        try:
            access_token = await get_access_token()
            req_id_prof = str(uuid.uuid4())
            h_prof = _m1_headers(req_id_prof, x_token=x_token)
            h_prof["Authorization"] = f"Bearer {access_token}"
            async with httpx.AsyncClient(timeout=config.HTTP_TIMEOUT) as client:
                r_prof = await client.get(config.ABHA_PROFILE_ACCOUNT_URL, headers=h_prof)
            if r_prof.status_code == 200:
                profile = r_prof.json()
                abha_num = profile.get("ABHANumber") or profile.get("abhaNumber") or abha_num
                abha_addr = profile.get("preferredAbhaAddress") or profile.get("abhaAddress") or abha_addr
        except Exception as e_prof:
            log.warning("[API 3 - VERIFY_OTP] Profile fetch attempt: %s", e_prof)

    if profile:
        m1_patient_profiles[patient_id] = profile

    verification_id = f"VERIF-{uuid.uuid4().hex[:8].upper()}"
    m1_verifications[verification_id] = {
        "patientId": patient_id,
        "abhaNumber": abha_num,
        "abhaAddress": abha_addr,
        "token": x_token,
        "profile": profile,
        "verified_at": now_iso(),
    }

    return {
        "success": True,
        "status": "VERIFIED",
        "patientId": patient_id,
        "verificationId": verification_id,
        "abhaNumber": abha_num,
        "abhaAddress": abha_addr,
        "message": "ABHA ownership verified successfully. Call API 4 to link it.",
    }


# ==============================================================================
# API 4: Link Existing ABHA to ProDoc Patient
# ==============================================================================
async def link_existing_abha(data: dict) -> dict:
    """
    ProDoc API 4: Links verified existing ABHA to patient record.
    ProDoc sends: { "patientId": "P10025", "abhaNumber": "12345678901234", "abhaAddress": "rahul.sharma@abdm" }
    """
    patient_id = str(data.get("patientId") or data.get("regNo") or "").strip()
    if not patient_id:
        return {
            "success": False,
            "errorCode": "ABHA_LINK_FAILED",
            "message": "Unable to link ABHA to the ProDoc patient: patientId is required",
        }

    raw_num = str(data.get("abhaNumber") or data.get("ABHANumber") or "").strip()
    clean_num = raw_num.replace("-", "").strip()
    abha_addr = str(data.get("abhaAddress") or data.get("ABHAAddress") or "").strip()
    verification_id = str(data.get("verificationId") or "").strip()

    # Fallback to verification store if available
    if not clean_num or not abha_addr:
        if verification_id and verification_id in m1_verifications:
            verif = m1_verifications[verification_id]
            clean_num = clean_num or str(verif.get("abhaNumber", "")).replace("-", "")
            raw_num = raw_num or verif.get("abhaNumber", "")
            abha_addr = abha_addr or verif.get("abhaAddress", "")

    # Fallback to prior search result if not fully provided
    search_meta = m1_searches.get(patient_id, {})
    if not clean_num and search_meta.get("matches"):
        first_match = search_meta["matches"][0]
        raw_num = raw_num or first_match.get("abhaNumber", "")
        clean_num = raw_num.replace("-", "").strip()
        abha_addr = abha_addr or first_match.get("abhaAddress", "")

    if not clean_num and not abha_addr:
        return {
            "success": False,
            "errorCode": "ABHA_LINK_FAILED",
            "message": "Unable to link ABHA to the ProDoc patient: abhaNumber or abhaAddress is required",
        }

    # Enrich profile with name and gender from prior search if available
    matched_search_acc = {}
    for acc in search_meta.get("accounts", []):
        if not isinstance(acc, dict):
            continue
        acc_num = str(acc.get("ABHANumber") or acc.get("abhaNumber") or "").replace("-", "").strip()
        if acc_num and (acc_num == clean_num or clean_num.endswith(acc_num[-4:] if len(acc_num) >= 4 else acc_num)):
            matched_search_acc = acc
            break
    if not matched_search_acc and search_meta.get("accounts"):
        first_acc = search_meta["accounts"][0]
        if isinstance(first_acc, dict):
            matched_search_acc = first_acc

    current_prof = m1_patient_profiles.get(patient_id, {})
    if matched_search_acc:
        if not current_prof.get("name") and matched_search_acc.get("name"):
            current_prof["name"] = matched_search_acc.get("name")
        if not current_prof.get("gender") and matched_search_acc.get("gender"):
            current_prof["gender"] = matched_search_acc.get("gender")
    if clean_num and not current_prof.get("ABHANumber"):
        current_prof["ABHANumber"] = raw_num or clean_num
    if abha_addr and not current_prof.get("preferredAbhaAddress"):
        current_prof["preferredAbhaAddress"] = abha_addr
    m1_patient_profiles[patient_id] = current_prof

    dob = str(data.get("dob") or data.get("dateOfBirth") or "").strip()
    if dob:
        current_prof["dob"] = dob

    final_num = raw_num or clean_num
    save_m1_profile(patient_id, current_prof)
    linked_rec = {
        "patientId": patient_id,
        "abhaNumber": final_num,
        "abhaAddress": abha_addr,
        "verificationId": verification_id,
        "linked_at": now_iso(),
    }
    if dob:
        linked_rec["dob"] = dob
    save_m1_linked(patient_id, linked_rec)

    log.info("[API 4] Linked patient %s to ABHA number=%s address=%s", patient_id, final_num, abha_addr)
    return {
        "success": True,
        "status": "LINKED",
        "patientId": patient_id,
        "abhaNumber": final_num,
        "abhaAddress": abha_addr,
        "message": "Existing ABHA linked successfully",
    }


# ==============================================================================
# API 5: Get Patient ABHA Profile
# ==============================================================================
async def get_patient_profile(patient_id: str) -> dict:
    """
    ProDoc API 5: Retrieves patient's ABHA profile.
    Uses stored ABHA X-token to query ABDM, with local fallback for linked patients.
    """
    patient_id = str(patient_id or "").strip()
    if not patient_id:
        return {
            "success": False,
            "errorCode": "ABHA_PROFILE_NOT_FOUND",
            "message": "patientId is required",
        }

    token_entry = m1_patient_tokens.get(patient_id)
    if token_entry and token_entry.get("token"):
        try:
            x_token = token_entry["token"]
            access_token = await get_access_token()
            req_id = str(uuid.uuid4())
            headers = _m1_headers(req_id, x_token=x_token)
            headers["Authorization"] = f"Bearer {access_token}"

            log.info("[API 5] Fetching live ABHA profile for patientId=%s", patient_id)
            async with httpx.AsyncClient(timeout=config.HTTP_TIMEOUT) as client:
                r = await client.get(config.ABHA_PROFILE_ACCOUNT_URL, headers=headers)

            if r.status_code == 200:
                profile = r.json()
                m1_patient_profiles[patient_id] = profile

                raw_num = str(profile.get("ABHANumber") or profile.get("abhaNumber") or "").replace("-", "")
                raw_addr = profile.get("preferredAbhaAddress") or profile.get("abhaAddress") or ""
                dob = (
                    f"{profile.get('yearOfBirth')}-{str(profile.get('monthOfBirth', '')).zfill(2)}-{str(profile.get('dayOfBirth', '')).zfill(2)}"
                    if profile.get("yearOfBirth") and profile.get("monthOfBirth") and profile.get("dayOfBirth")
                    else str(profile.get("dob") or profile.get("dateOfBirth") or profile.get("yearOfBirth") or "").strip()
                )

                return {
                    "success": True,
                    "patientId": patient_id,
                    "abhaProfile": {
                        "abhaNumber": raw_num,
                        "abhaAddress": raw_addr,
                        "name": profile.get("name") or "",
                        "gender": profile.get("gender") or "",
                        "dob": dob,
                    },
                    "message": "ABHA profile retrieved successfully",
                }
        except Exception as exc:
            log.warning("[API 5] Live profile fetch failed, falling back to local: %s", exc)

    # Local store fallback (linked patients, cached profiles, or prior search)
    linked = m1_linked_patients.get(patient_id)
    cached = m1_patient_profiles.get(patient_id)
    enrol = m1_enrolments.get(patient_id)
    search_meta = m1_searches.get(patient_id, {})

    if linked or cached or enrol or search_meta.get("matches"):
        p = cached or {}
        search_match = (search_meta.get("matches") or [{}])[0] if search_meta else {}
        raw_num_source = str(
            (linked.get("abhaNumber") if linked else None)
            or p.get("ABHANumber")
            or p.get("abhaNumber")
            or search_match.get("abhaNumber")
            or ""
        ).strip()
        num_val = raw_num_source.replace("-", "") if not raw_num_source.lower().startswith("x") else raw_num_source
        addr_val = (
            (linked.get("abhaAddress") if linked else None)
            or p.get("preferredAbhaAddress")
            or p.get("abhaAddress")
            or search_match.get("abhaAddress")
            or ""
        )
        name = p.get("name") or (enrol.get("name") if enrol else None) or search_match.get("name") or ""
        gender = p.get("gender") or (enrol.get("gender") if enrol else None) or search_match.get("gender") or ""

        # Resolve DOB reliably from all available sources
        dob = ""
        if linked and linked.get("dob"):
            dob = str(linked["dob"]).strip()
        if not dob and p:
            yob = p.get("yearOfBirth")
            mob = p.get("monthOfBirth")
            day_ob = p.get("dayOfBirth")
            if yob and mob and day_ob:
                dob = f"{yob}-{str(mob).zfill(2)}-{str(day_ob).zfill(2)}"
            else:
                dob = str(p.get("dob") or p.get("dateOfBirth") or yob or "").strip()
        if not dob and enrol and enrol.get("dob"):
            dob = str(enrol["dob"]).strip()
        if not dob and search_match and search_match.get("dob"):
            dob = str(search_match["dob"]).strip()

        return {
            "success": True,
            "patientId": patient_id,
            "abhaProfile": {
                "abhaNumber": num_val,
                "abhaAddress": addr_val,
                "name": name,
                "gender": gender,
                "dob": dob,
            },
            "message": "ABHA profile retrieved successfully",
        }

    return {
        "success": False,
        "errorCode": "ABHA_PROFILE_NOT_FOUND",
        "message": "ABHA profile not found for this patient",
    }


# ==============================================================================
# API 6: Get ABHA Card
# ==============================================================================
async def get_patient_card(patient_id: str, fmt: str = "PDF") -> dict:
    """
    ProDoc API 6: Retrieves patient's ABHA card.
    Returns fileBase64 and metadata as expected by ProDoc contract.
    """
    import base64
    patient_id = str(patient_id or "").strip()
    if not patient_id:
        return {
            "success": False,
            "errorCode": "ABHA_CARD_NOT_FOUND",
            "message": "patientId is required",
        }

    token_entry = m1_patient_tokens.get(patient_id)
    if token_entry and token_entry.get("token"):
        try:
            x_token = token_entry["token"]
            access_token = await get_access_token()
            req_id = str(uuid.uuid4())
            headers = _m1_headers(req_id, x_token=x_token)
            headers["Authorization"] = f"Bearer {access_token}"
            headers["Accept"] = "application/pdf"

            log.info("[API 6] Fetching live ABHA card for patientId=%s", patient_id)
            async with httpx.AsyncClient(timeout=config.HTTP_TIMEOUT) as client:
                r = await client.get(config.ABHA_CARD_URL, headers=headers)

            if r.status_code == 200:
                file_b64 = ""
                content_type = r.headers.get("content-type", "application/pdf")
                if "application/json" in content_type:
                    try:
                        j = r.json()
                        file_b64 = j.get("card") or j.get("data") or j.get("fileBase64") or ""
                    except Exception:
                        pass
                if not file_b64:
                    file_b64 = base64.b64encode(r.content).decode("utf-8")

                if file_b64:
                    return {
                        "success": True,
                        "patientId": patient_id,
                        "fileName": f"ABHA_{patient_id}.pdf",
                        "contentType": "application/pdf",
                        "fileBase64": file_b64,
                        "message": "ABHA card retrieved successfully",
                    }
        except Exception as exc:
            log.warning("[API 6] Live card fetch failed, checking local store: %s", exc)

    return {
        "success": False,
        "errorCode": "ABHA_CARD_NOT_FOUND",
        "message": "ABHA card not found for this patient. Ensure patient ABHA is linked or enrolled with active token.",
    }


# ==============================================================================
# API 7: Get ABHA QR Code
# ==============================================================================
async def get_patient_qr(patient_id: str) -> dict:
    """
    ProDoc API 7: Retrieves patient's ABHA QR code.
    Returns qrCodeBase64 as expected by ProDoc contract.
    """
    import base64
    patient_id = str(patient_id or "").strip()
    if not patient_id:
        return {
            "success": False,
            "errorCode": "ABHA_QR_NOT_FOUND",
            "message": "patientId is required",
        }

    linked = m1_linked_patients.get(patient_id, {})
    cached_prof = m1_patient_profiles.get(patient_id, {})
    abha_addr = linked.get("abhaAddress") or cached_prof.get("preferredAbhaAddress") or cached_prof.get("abhaAddress") or ""

    token_entry = m1_patient_tokens.get(patient_id)
    if token_entry and token_entry.get("token"):
        try:
            x_token = token_entry["token"]
            access_token = await get_access_token()
            req_id = str(uuid.uuid4())
            headers = _m1_headers(req_id, x_token=x_token)
            headers["Authorization"] = f"Bearer {access_token}"

            log.info("[API 7] Fetching live ABHA QR code for patientId=%s", patient_id)
            async with httpx.AsyncClient(timeout=config.HTTP_TIMEOUT) as client:
                r = await client.get(config.ABHA_QR_CODE_URL, headers=headers)

            if r.status_code == 200:
                qr_b64 = ""
                content_type = r.headers.get("content-type", "").lower()
                if "json" in content_type:
                    try:
                        j = r.json()
                        qr_b64 = j.get("qrCode") or j.get("data") or j.get("qrCodeBase64") or ""
                        if not abha_addr and j.get("abhaAddress"):
                            abha_addr = j.get("abhaAddress")
                    except Exception:
                        pass
                if not qr_b64:
                    qr_b64 = base64.b64encode(r.content).decode("utf-8")

                if qr_b64:
                    return {
                        "success": True,
                        "patientId": patient_id,
                        "abhaAddress": abha_addr,
                        "qrCodeBase64": qr_b64,
                        "message": "ABHA QR code generated successfully",
                    }
        except Exception as exc:
            log.warning("[API 7] Live QR fetch failed: %s", exc)

    return {
        "success": False,
        "errorCode": "ABHA_QR_NOT_FOUND",
        "message": "ABHA QR code not found for this patient. Ensure patient ABHA is linked or enrolled with active token.",
    }


# ==============================================================================
# ProDoc OPD Flow: Register ABHA to Existing Patient (frmRegisterABHAPatient)
# ==============================================================================

def _extract_abdm_error_details(r: httpx.Response, default_msg: str = "ABDM error") -> tuple[str, str]:
    raw_text = r.text.strip()
    try:
        data = r.json()
        if isinstance(data, dict):
            # 1. Nested "error" object: {"error": {"code": "...", "message": "..."}}
            err_obj = data.get("error")
            if isinstance(err_obj, dict):
                code = err_obj.get("code", "")
                msg = err_obj.get("message", "")
                if msg:
                    return f"{code}: {msg}" if code else msg, raw_text
            # 2. Top-level message or description
            msg = data.get("message") or data.get("description")
            if msg:
                code = data.get("code", "")
                return f"{code}: {msg}" if code else str(msg), raw_text
            # 3. Details list: {"details": [{"code": "...", "message": "..."}]}
            details = data.get("details")
            if isinstance(details, list) and details:
                first = details[0]
                if isinstance(first, dict) and "message" in first:
                    return str(first["message"]), raw_text
        return raw_text or default_msg, raw_text
    except Exception:
        return raw_text or default_msg, raw_text


async def send_patient_abha_otp(data: dict) -> dict:
    """
    Sends Login OTP to patient's mobile for ABHA verification.
    Communicates with ProDoc frmRegisterABHAPatient (btnSendOTP).
    Calls ABDM: POST /abha/api/v3/profile/login/request/otp
    """
    raw_mobile = str(data.get("mobile") or data.get("mobileNo") or data.get("searchValue") or "").strip()
    mobile = "".join(c for c in raw_mobile if c.isdigit())
    if len(mobile) != 10:
        return {
            "success": False,
            "Success": False,
            "transactionId": "",
            "TransactionId": "",
            "message": "Please enter a valid 10-digit mobile number",
            "Message": "Please enter a valid 10-digit mobile number",
        }

    patient_id = str(data.get("patientId") or data.get("regNo") or "").strip()

    try:
        enc_mobile = await encrypt_abdm(mobile)
        token = await get_access_token()
        req_id = str(uuid.uuid4())
        headers = _m1_headers(req_id)
        headers["Authorization"] = f"Bearer {token}"

        abdm_payload = {
            "scope": ["abha-login", "mobile-verify"],
            "loginHint": "mobile",
            "loginId": enc_mobile,
            "otpSystem": "abdm",
        }

        log.info("[PRODOC ABHA SEND-OTP] Requesting ABDM login OTP for mobile=******%s", mobile[-4:])
        async with httpx.AsyncClient(timeout=config.HTTP_TIMEOUT) as client:
            r = await client.post(config.ABHA_LOGIN_REQUEST_OTP_URL, json=abdm_payload, headers=headers)

        if r.status_code == 200:
            res_json = r.json()
            txn_id = res_json.get("txnId") or ""
            msg = res_json.get("message") or f"OTP sent to mobile number ending with ******{mobile[-4:]}"

            # Store runtime state
            m1_otp_txns[txn_id] = {
                "mobile": mobile,
                "patientId": patient_id,
                "created_at": now_iso(),
            }

            return {
                "success": True,
                "transactionId": txn_id,
                "message": msg,
            }
        else:
            err_msg, raw_err = _extract_abdm_error_details(r, "Failed to send OTP from ABDM")
            log.warning("[PRODOC ABHA SEND-OTP] ABDM returned status %s: %s", r.status_code, raw_err)

            return {
                "success": False,
                "transactionId": "",
                "message": err_msg,
                "abdm_status": r.status_code,
                "abdm_raw": raw_err,
                "key_source": get_key_source(),
            }
    except Exception as exc:
        log.error("[PRODOC ABHA SEND-OTP] Exception: %s", exc)
        return {
            "success": False,
            "transactionId": "",
            "message": f"Server error: {str(exc)}",
        }


async def verify_patient_abha_otp(data: dict) -> dict:
    """
    Verifies Login OTP entered by patient and retrieves ABHA details.
    Communicates with ProDoc frmRegisterABHAPatient (btnVerifyOTP).
    Calls ABDM: POST /abha/api/v3/profile/login/verify
    Returns normalized ABHA account details (name, abhaNumber, preferredAbhaAddress, gender, dob, accounts).
    """
    txn_id = str(data.get("transactionId") or data.get("txnId") or "").strip()
    raw_otp = str(data.get("otp") or "").strip()
    otp = "".join(c for c in raw_otp if c.isdigit())

    # Auto-resolve transactionId from mobile or patientId or latest active transaction if omitted
    if not txn_id:
        mobile_val = "".join(c for c in str(data.get("mobile") or data.get("mobileNo") or "") if c.isdigit())
        patient_val = str(data.get("patientId") or data.get("regNo") or "").strip()

        for t_id, meta in reversed(list(m1_otp_txns.items())):
            if (mobile_val and meta.get("mobile") == mobile_val) or (patient_val and meta.get("patientId") == patient_val):
                txn_id = t_id
                log.info("[PRODOC ABHA VERIFY-OTP] Auto-matched transactionId=%s for mobile=%s / patient=%s", txn_id, mobile_val, patient_val)
                break

        if not txn_id and m1_otp_txns:
            txn_id = list(m1_otp_txns.keys())[-1]
            log.info("[PRODOC ABHA VERIFY-OTP] Auto-selected latest active transactionId=%s", txn_id)

    if not txn_id:
        return {
            "success": False,
            "message": "No active OTP request found. Please Send OTP first.",
        }

    if len(otp) != 6:
        return {
            "success": False,
            "message": "Please enter a valid 6-digit OTP",
        }

    try:
        enc_otp = await encrypt_abdm(otp)
        token = await get_access_token()
        req_id = str(uuid.uuid4())
        headers = _m1_headers(req_id)
        headers["Authorization"] = f"Bearer {token}"

        abdm_payload = {
            "scope": ["abha-login", "mobile-verify"],
            "authData": {
                "authMethods": ["otp"],
                "otp": {
                    "txnId": txn_id,
                    "otpValue": enc_otp,
                },
            },
        }

        log.info("[PRODOC ABHA VERIFY-OTP] Verifying OTP for txnId=%s", txn_id)
        async with httpx.AsyncClient(timeout=config.HTTP_TIMEOUT) as client:
            r = await client.post(config.ABHA_LOGIN_VERIFY_OTP_URL, json=abdm_payload, headers=headers)

        if r.status_code == 200:
            res_json = r.json()
            auth_result = str(res_json.get("authResult", "success")).lower()
            if auth_result == "failed":
                fail_msg = res_json.get("message") or "OTP did not match or is expired"
                return {
                    "success": False,
                    "message": fail_msg,
                    "transactionId": txn_id,
                }

            # Extract account details from accounts array or root
            accounts_raw = res_json.get("accounts") or []
            primary_account = accounts_raw[0] if accounts_raw else {}

            jwt_claims = parse_jwt_payload(res_json.get("token"))

            abha_number = (
                primary_account.get("ABHANumber")
                or primary_account.get("abhaNumber")
                or res_json.get("ABHANumber")
                or res_json.get("abhaNumber")
                or jwt_claims.get("abhaNumber")
                or ""
            )
            abha_address = (
                primary_account.get("preferredAbhaAddress")
                or primary_account.get("abhaAddress")
                or res_json.get("preferredAbhaAddress")
                or res_json.get("abhaAddress")
                or jwt_claims.get("preferredAbhaAddress")
                or ""
            )
            patient_name = (
                primary_account.get("name")
                or primary_account.get("patientName")
                or res_json.get("name")
                or jwt_claims.get("name")
                or ""
            )
            gender = primary_account.get("gender") or res_json.get("gender") or jwt_claims.get("gender") or ""
            dob = primary_account.get("dob") or res_json.get("dob") or jwt_claims.get("dob") or ""
            status = primary_account.get("status") or res_json.get("status") or "ACTIVE"
            verified_status = primary_account.get("verifiedStatus") or res_json.get("verifiedStatus") or "VERIFIED"

            # Normalize accounts list for multi-account selection in ProDoc
            normalized_accounts = []
            for acc in accounts_raw:
                normalized_accounts.append({
                    "abhaNumber": acc.get("ABHANumber") or acc.get("abhaNumber"),
                    "preferredAbhaAddress": acc.get("preferredAbhaAddress") or acc.get("abhaAddress"),
                    "name": acc.get("name"),
                    "gender": acc.get("gender"),
                    "dob": acc.get("dob"),
                    "status": acc.get("status", "ACTIVE"),
                })

            patient_id = data.get("patientId") or data.get("regNo")
            if patient_id and res_json.get("token"):
                save_m1_token(patient_id, {
                    "token": res_json["token"],
                    "abhaNumber": abha_number,
                    "abhaAddress": abha_address,
                    "saved_at": now_iso(),
                })

            return {
                "success": True,
                "message": "OTP Verified Successfully",
                "transactionId": txn_id,
                "abhaNumber": abha_number,
                "abhaAddress": abha_address,
                "patientName": patient_name,
                "gender": gender,
                "dob": dob,
                "status": status,
                "verifiedStatus": verified_status,
                "accounts": normalized_accounts,
            }
        else:
            err_msg, raw_err = _extract_abdm_error_details(r, "OTP verification failed")
            log.warning("[PRODOC ABHA VERIFY-OTP] ABDM returned status %s: %s", r.status_code, raw_err)
            return {
                "success": False,
                "message": err_msg,
                "transactionId": txn_id,
                "abdm_status": r.status_code,
                "abdm_raw": raw_err,
            }
    except Exception as exc:
        log.error("[PRODOC ABHA VERIFY-OTP] Exception: %s", exc)
        return {
            "success": False,
            "message": f"Server error: {str(exc)}",
        }


async def register_patient_abha_link(data: dict) -> dict:
    """
    Saves/links verified ABHA Number & Address with ProDoc RegNo/Patient record.
    Communicates with ProDoc frmRegisterABHAPatient (btnRegisterABHA).
    """
    reg_no = str(data.get("regNo") or data.get("patientId") or "").strip()
    abha_number = str(data.get("abhaNumber") or data.get("ABHANumber") or "").strip()
    abha_address = str(data.get("abhaAddress") or data.get("ABHAAddress") or "").strip()

    if not reg_no:
        return {"success": False, "message": "Patient Reg. No. is required"}
    if not abha_number or not abha_address:
        return {"success": False, "message": "Both ABHA Number and ABHA Address are required to register"}

    m1_linked_patients[reg_no] = {
        "regNo": reg_no,
        "abhaNumber": abha_number,
        "abhaAddress": abha_address,
        "linked_at": now_iso(),
    }

    return {
        "success": True,
        "message": f"ABHA details successfully registered for patient {reg_no}",
        "regNo": reg_no,
        "abhaNumber": abha_number,
        "abhaAddress": abha_address,
    }

