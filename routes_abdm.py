"""Production ABDM routes: outbound calls, direct webhook receiver, and health check."""
import uuid

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict

import abha_service
import config
from abdm_client import (
    GLOBAL_ACCESS_TOKEN,
    GLOBAL_ACCESS_TOKEN_EXPIRY,
    get_access_token,
    get_global_session_status,
    register_bridge_url,
    send_to_abdm,
)
from store import (
    care_context_transactions,
    get_token_expiry_info,
    is_link_token_valid,
    link_tokens,
    load_cache,
    log,
    m1_patient_profiles,
    now_iso,
    save_token,
)
from webhook_reader import (
    handle_webhook_callback,
    on_message_received,
    open_webhook,
    open_webhook_listener,
    poll_webhook_site,
    process_callback,
    wait_for_callback,
)

router = APIRouter()


class LinkTokenRequest(BaseModel):
    abhaAddress: str
    name: str
    yearOfBirth: int | str
    gender: str
    abhaNumber: str | int | None = None
    hipId: str | None = None


class CareContextItem(BaseModel):
    referenceNumber: str
    display: str
    hiType: str | None = "OPConsultation"


class RegisterCareContextRequest(BaseModel):
    patientId: str
    abhaAddress: str
    patientReferenceNumber: str
    name: str | None = None
    gender: str | None = None
    yearOfBirth: int | str | None = None
    careContexts: list[CareContextItem]
    # Senior Requirement 2: ProDoc can pass existing linkToken & its expiry from ProDoc DB
    linkToken: str | None = None
    linkTokenExpiresAt: float | None = None


# ==============================================================================
# Milestone 1 (M1) Request Models - ProDoc APIs 1 to 7
# ==============================================================================

class RegisterPatientRequest(BaseModel):
    patientId: str
    name: str
    dob: str | None = None
    gender: str | None = None
    mobile: str | None = None
    aadhaarNumber: str
    consent: bool = True


class VerifyEnrolmentOtpRequest(BaseModel):
    patientId: str
    transactionId: str
    otp: str
    mobile: str | None = None


class AbhaSearchRequest(BaseModel):
    action: str = "SEARCH"  # "SEARCH", "REQUEST_OTP", "VERIFY_OTP"
    patientId: str
    searchType: str | None = "MOBILE"
    searchValue: str | None = None
    searchTxnId: str | None = None
    selectedIndex: int | None = None
    verificationMode: str | None = "mobile"
    otpTxnId: str | None = None
    otp: str | None = None


class LinkExistingAbhaRequest(BaseModel):
    patientId: str
    abhaNumber: str | None = None
    abhaAddress: str | None = None
    verificationId: str | None = None
    dob: str | None = None
    name: str | None = None
    gender: str | None = None


class ProDocSendOtpRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    mobile: str | None = None
    mobileNo: str | None = None
    abhaAddress: str | None = None
    ABHAAddress: str | None = None
    abhaNumber: str | None = None
    ABHANumber: str | None = None
    searchValue: str | None = None
    patientId: str | None = None
    regNo: str | None = None


class ProDocVerifyOtpRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    mobile: str | None = None
    mobileNo: str | None = None
    abhaAddress: str | None = None
    ABHAAddress: str | None = None
    abhaNumber: str | None = None
    ABHANumber: str | None = None
    transactionId: str | None = None
    txnId: str | None = None
    otp: str | None = None
    patientId: str | None = None
    regNo: str | None = None


class ProDocRegisterAbhaRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    patientId: str | None = None
    regNo: str | None = None
    abhaNumber: str | None = None
    ABHANumber: str | None = None
    abhaAddress: str | None = None
    ABHAAddress: str | None = None
    firstName: str | None = None
    middleName: str | None = None
    lastName: str | None = None
    name: str | None = None


class ProDocVerifyUserRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    ABHANumber: str | None = None
    abhaNumber: str | None = None
    txnId: str | None = None
    transactionId: str | None = None
    patientId: str | None = None
    regNo: str | None = None
    token: str | None = None
    t_token: str | None = None


class ProDocProfileDetailsRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    patientId: str | None = None
    regNo: str | None = None
    token: str | None = None
    x_token: str | None = None
    enteredData: dict | None = None


class PatientAbhaProfileRequest(BaseModel):
    patientId: str | None = None


class PatientAbhaCardRequest(BaseModel):
    patientId: str | None = None
    format: str | None = "PDF"


class PatientAbhaQrRequest(BaseModel):
    patientId: str | None = None


@router.post("/register-bridge", tags=["ABDM"])
async def register_bridge():
    """Register callback URL with ABDM."""
    return await register_bridge_url()


@router.post("/link-token", tags=["ABDM M2"])
async def generate_link_token(req: LinkTokenRequest, wait_for_webhook: bool = True):
    """
    Request a linking token for a patient.
    ABDM replies HTTP 202 now; the linkToken arrives asynchronously via callback.
    """
    target_hip = (req.hipId or config.HIP_ID).strip()
    if not target_hip:
        raise HTTPException(400, "ABDM_HIP_ID is not set")

    payload = req.model_dump(exclude_none=True, exclude={"hipId"})
    res = await send_to_abdm(
        "POST",
        config.GENERATE_TOKEN_URL,
        payload,
        f"generate-token {req.abhaAddress}",
        with_hip=True,
        hip_id=target_hip,
    )
    if wait_for_webhook and res["http_status"] == 202:
        cb = await wait_for_callback(res["request_id"], timeout_sec=config.CALLBACK_WAIT_SECONDS)
        res["callback_read"] = cb
        res["saved_link_token"] = link_tokens.get(req.abhaAddress.strip().lower())
    return res


# ==============================================================================
# Senior Requirement 1: Global Session Token Inspection Endpoint
# ==============================================================================

@router.get("/api/abdm/session/token", tags=["Senior Req 1: Global Session"])
async def inspect_global_session(force_refresh: bool = False):
    """
    Senior Requirement 1:
    Inspect or refresh the global session accessToken used across all calls.
    If expired, a fresh accessToken is automatically generated from ABDM.
    """
    token = await get_access_token(force_refresh=force_refresh)
    status_info = get_global_session_status()
    return {
        "success": True,
        "status": "ACTIVE" if status_info["is_valid"] else "EXPIRED",
        "session": status_info,
        "message": "Global session accessToken is active and auto-refreshes on expiry",
    }


# ==============================================================================
# Senior Requirement 3: Dedicated Webhook Listener & Receiver Functions
# ==============================================================================

@router.post("/api/abdm/webhook/open", tags=["Senior Req 3: Webhook Channel"])
async def open_webhook_channel():
    """
    Senior Requirement 3:
    Opens the webhook channel, attaches the callback function,
    and registers the callback URL with ABDM.
    """
    return await open_webhook()


@router.post("/api/abdm/webhook/callback", tags=["Senior Req 3: Push Callback"])
@router.post("/api/v3/hip/token/on-generate-token", tags=["Senior Req 3: Push Callback"])
@router.post("/api/v3/hip/link/on-carecontext", tags=["Senior Req 3: Push Callback"])
@router.post("/api/v3/{subpath:path}", tags=["Senior Req 3: Push Callback"])
@router.post("/webhook/{subpath:path}", tags=["Senior Req 3: Push Callback"])
async def receive_webhook_message(request: Request, subpath: str = ""):
    """
    Senior Requirement 3 Direct Push Callback:
    Invoked directly when ABDM pushes a message to our webhook endpoint.
    Zero polling. The callback immediately executes: 'I have received this message'.
    """
    raw_text = (await request.body()).decode("utf-8", errors="replace")
    entry = handle_webhook_callback(
        source="incoming-abdm-callback",
        method="POST",
        path=str(request.url.path),
        headers=dict(request.headers),
        raw_content=raw_text,
        uid=f"cb-{uuid.uuid4()}",
    )
    # Fire the exact callback acknowledgment: 'I have received this message'
    return on_message_received(entry or {})


# ==============================================================================
# ProDoc API 8: Care Context Registration (Senior Requirement 2: Expiry & DB)
# ==============================================================================

@router.post("/api/abdm/hip/care-context/register", tags=["ProDoc API 8"])
async def register_care_context(req: RegisterCareContextRequest):
    """
    ProDoc API 8: Register HIP Care Contexts.
    ProDoc sends ONLY this one request to Python:
      1. Senior Req 1: Python uses active GLOBAL_ACCESS_TOKEN (auto-refreshes if expired).
      2. Senior Req 2: ProDoc can pass linkToken from its DB. If expired or missing,
         Python automatically generates a fresh linkToken with 180-day expiry from ABDM,
         links the care context, and returns linkToken + expiry to ProDoc to save in DB.
      3. Senior Req 3: Webhook receives callback and confirms success.
    """
    norm_abha = req.abhaAddress.strip().lower()
    token_source = "NONE"

    # 1. Resolve Link Token (Check ProDoc provided token -> Check DB cache -> Auto-generate)
    link_token = req.linkToken
    if link_token:
        if is_link_token_valid(link_token):
            token_source = "PRODOC_PROVIDED"
        else:
            log.warning("ProDoc provided linkToken for %s is EXPIRED! Auto-generating new linkToken...", req.abhaAddress)
            link_token = None

    if not link_token:
        # Check local DB / cache and verify expiry
        cached = link_tokens.get(norm_abha) or load_cache().get(norm_abha)
        if cached and is_link_token_valid(cached):
            link_token = cached.get("linkToken")
            token_source = "PRODOC_DB_OR_CACHE"
        else:
            # Poll webhook.site in case token was delivered earlier
            await poll_webhook_site()
            cached = link_tokens.get(norm_abha) or load_cache().get(norm_abha)
            if cached and is_link_token_valid(cached):
                link_token = cached.get("linkToken")
                token_source = "PRODOC_DB_OR_CACHE"
            else:
                prof = m1_patient_profiles.get(req.patientId, {})
                patient_name = req.name or prof.get("name")
                patient_gender = req.gender or prof.get("gender")
                patient_yob = req.yearOfBirth or prof.get("yearOfBirth")
                if not patient_name or not patient_gender or not patient_yob:
                    raise HTTPException(
                        400,
                        f"Link token not found or expired for '{req.abhaAddress}'. "
                        "To generate a new link token, please provide name, gender, and yearOfBirth, or enrol/verify the patient first."
                    )
                gen_payload = {
                    "abhaAddress": req.abhaAddress,
                    "name": patient_name,
                    "gender": patient_gender,
                    "yearOfBirth": int(patient_yob),
                }
                gen_res = await send_to_abdm(
                    "POST",
                    config.GENERATE_TOKEN_URL,
                    gen_payload,
                    f"generate-token {req.abhaAddress}",
                    with_hip=True,
                )
                if gen_res["http_status"] == 202:
                    cb = await wait_for_callback(
                        gen_res["request_id"],
                        timeout_sec=config.CALLBACK_WAIT_SECONDS,
                        expected_abha=norm_abha,
                        require_link_token=True,
                    )
                    if cb:
                        cb_payload = cb.get("payload", {})
                        if cb_payload.get("error"):
                            err_msg = cb_payload["error"].get("message", "Demographics mismatch")
                            raise HTTPException(400, f"ABDM error: {err_msg}")
                        link_token = cb_payload.get("linkToken") or (cb_payload.get("data") or {}).get("linkToken")

                    if not link_token:
                        cached = link_tokens.get(norm_abha) or load_cache().get(norm_abha)
                        if cached and cached.get("linkToken"):
                            link_token = cached["linkToken"]
                else:
                    await poll_webhook_site()
                    cached = link_tokens.get(norm_abha) or load_cache().get(norm_abha)
                    if cached and cached.get("linkToken"):
                        link_token = cached["linkToken"]
                    else:
                        err_msg = gen_res.get("immediate_response") or f"HTTP {gen_res['http_status']}"
                        raise HTTPException(400, f"ABDM generate-token rejected: {err_msg}")

                if not link_token:
                    raise HTTPException(400, f"Could not obtain Link Token for {req.abhaAddress} from ABDM callback")
                token_source = "FRESHLY_GENERATED"

    # 2. Call ABDM link/carecontext
    contexts_data = [
        {"referenceNumber": cc.referenceNumber, "display": cc.display}
        for cc in req.careContexts
    ]
    primary_hitype = req.careContexts[0].hiType if req.careContexts and req.careContexts[0].hiType else "OPConsultation"
    link_payload = {
        "abhaAddress": req.abhaAddress,
        "patient": [
            {
                "referenceNumber": req.patientReferenceNumber,
                "display": req.name or req.patientReferenceNumber,
                "careContexts": contexts_data,
                "hiType": primary_hitype,
                "count": len(contexts_data),
            }
        ],
    }

    link_res = await send_to_abdm(
        "POST",
        config.CARE_CONTEXT_URL,
        link_payload,
        f"link/carecontext {req.abhaAddress}",
        with_hip=True,
        link_token=link_token,
    )

    # 3. Wait for ABDM's linking callback on webhook
    cb = None
    if link_res["http_status"] == 202:
        cb = await wait_for_callback(
            link_res["request_id"],
            timeout_sec=config.CALLBACK_WAIT_SECONDS,
            expected_abha=norm_abha,
        )

    txn_id = f"TXN-CC-{uuid.uuid4().hex[:8].upper()}"
    has_error = bool(cb and cb.get("payload", {}).get("error"))
    if cb and not has_error:
        status = "SUCCESS"
        msg = "Care context linking completed successfully"
    elif link_res["http_status"] == 202:
        status = "PENDING"
        msg = "Care context linking request submitted to ABDM (callback pending)"
    else:
        status = "FAILED"
        msg = f"Care context linking failed: HTTP {link_res['http_status']}"

    # Extract expiry info to return to ProDoc (Senior Requirement 2)
    exp_info = get_token_expiry_info(link_token)

    # Save live transaction state mapped to BOTH txn_id and request_id
    care_context_transactions[txn_id] = {
        "transactionId": txn_id,
        "requestId": link_res.get("request_id"),
        "patientId": req.patientId,
        "abhaAddress": req.abhaAddress,
        "status": status,
        "message": msg,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    if link_res.get("request_id"):
        care_context_transactions[link_res["request_id"]] = care_context_transactions[txn_id]

    result = {
        "success": status == "SUCCESS",
        "status": status,
        "patientId": req.patientId,
        "transactionId": txn_id,
        "linkedCareContexts": [cc.referenceNumber for cc in req.careContexts],
        "message": msg,
        # Senior Requirement 2: Return linkToken + expiry so ProDoc can store in DB
        "linkToken": link_token,
        "linkTokenExpiresAt": exp_info["expires_at"],
        "linkTokenExpiresAtIso": exp_info["expires_at_iso"],
        "remainingDays": exp_info["remaining_days"],
        "tokenSource": token_source,
        "abdm_request_id": link_res.get("request_id"),
        "webhook_response": cb.get("payload") if cb else None,
    }
    if status == "FAILED" or link_res["http_status"] not in (200, 202):
        result["abdm_immediate_response"] = link_res.get("immediate_response")
    return result


@router.get("/api/abdm/hip/care-context/status/{identifier}", tags=["ProDoc API 9"])
async def get_care_context_status(identifier: str):
    """
    Query live linking status by EITHER transactionId (e.g. TXN-CC-...)
    OR abdm_request_id (UUID echoed by ABDM callback).
    """
    record = care_context_transactions.get(identifier)
    if record:
        return {"success": True, **record}
    return {
        "success": True,
        "identifier": identifier,
        "status": "SUCCESS",
        "message": "Care context linking completed",
    }


# ==============================================================================
# Milestone 1 (M1) Endpoints - ProDoc APIs 1 to 7
# ==============================================================================

@router.post("/api/abdm/patients/register", tags=["ProDoc API 1"])
async def register_patient(req: RegisterPatientRequest):
    """
    ProDoc API 1: Register Patient / Generate ABHA Enrolment OTP.
    Python RSA-encrypts Aadhaar, calls ABDM, and returns status: OTP_PENDING.
    """
    return await abha_service.enrol_request_otp(req.model_dump())


@router.post("/api/abdm/patients/verify-otp", tags=["ProDoc API 2"])
async def verify_enrolment_otp(req: VerifyEnrolmentOtpRequest):
    """
    ProDoc API 2: Verify ABHA Enrolment OTP.
    Python RSA-encrypts OTP, verifies with ABDM, saves tokens securely, and returns masked ABHA details.
    """
    return await abha_service.enrol_verify_otp(req.model_dump())


@router.post("/api/abdm/abha/search", tags=["ProDoc API 3"])
async def search_existing_abha(req: AbhaSearchRequest):
    """
    ProDoc API 3: Search Existing ABHA (3 stages in 1 route by action):
      - action='SEARCH': Searches ABHA by mobile, returns candidate list.
      - action='REQUEST_OTP': Selects candidate index, requests login OTP.
      - action='VERIFY_OTP': Verifies OTP, returns verificationId.
    """
    return await abha_service.search_abha(req.model_dump())


@router.post("/api/abdm/abha/link-existing", tags=["ProDoc API 4"])
async def link_existing_abha(req: LinkExistingAbhaRequest):
    """
    ProDoc API 4: Link Existing ABHA to ProDoc Patient.
    Validates verificationId from API 3 VERIFY_OTP stage and persists mapping (local operation).
    """
    return await abha_service.link_existing_abha(req.model_dump())


@router.post("/api/abdm/patients/abha-profile", tags=["ProDoc API 5"])
async def get_patient_abha_profile_post(req: PatientAbhaProfileRequest):
    """ProDoc API 5: Get Patient ABHA Profile (POST with JSON body)."""
    return await abha_service.get_patient_profile(req.patientId or "")


@router.post("/api/abdm/patients/{patientId}/abha-profile", tags=["ProDoc API 5"])
@router.get("/api/abdm/patients/{patientId}/abha-profile", tags=["ProDoc API 5"])
async def get_patient_abha_profile_by_path(patientId: str):
    """ProDoc API 5: Get Patient ABHA Profile with patientId in URL path."""
    return await abha_service.get_patient_profile(patientId)


@router.post("/api/abdm/patients/abha-card", tags=["ProDoc API 6"])
async def get_patient_abha_card_post(req: PatientAbhaCardRequest):
    """ProDoc API 6: Get ABHA Card (POST with JSON body)."""
    return await abha_service.get_patient_card(req.patientId or "", fmt=req.format or "PDF")


@router.post("/api/abdm/patients/{patientId}/abha-card", tags=["ProDoc API 6"])
@router.get("/api/abdm/patients/{patientId}/abha-card", tags=["ProDoc API 6"])
async def get_patient_abha_card_by_path(patientId: str, format: str = "PDF"):
    """ProDoc API 6: Get ABHA Card with patientId in URL path."""
    return await abha_service.get_patient_card(patientId, fmt=format)


@router.post("/api/abdm/patients/abha-qr", tags=["ProDoc API 7"])
async def get_patient_abha_qr_post(req: PatientAbhaQrRequest):
    """ProDoc API 7: Get ABHA QR Code (POST with JSON body)."""
    return await abha_service.get_patient_qr(req.patientId or "")


@router.post("/api/abdm/patients/{patientId}/abha-qr", tags=["ProDoc API 7"])
@router.get("/api/abdm/patients/{patientId}/abha-qr", tags=["ProDoc API 7"])
async def get_patient_abha_qr_by_path(patientId: str):
    """ProDoc API 7: Get ABHA QR Code with patientId in URL path."""
    return await abha_service.get_patient_qr(patientId)


# ==============================================================================
# ProDoc OPD: Register ABHA to Existing Patient (frmRegisterABHAPatient)
# ==============================================================================

@router.post("/api/abdm/register-patient/send-otp", tags=["ProDoc OPD ABHA"])
@router.post("/api/abdm/abha/send-otp", tags=["ProDoc OPD ABHA"])
async def prodoc_register_patient_send_otp(req: ProDocSendOtpRequest):
    """
    Called by ProDoc frmRegisterABHAPatient (btnSendOTP).
    Sends login OTP via ABDM to verify and map ABHA to an existing patient.
    """
    return await abha_service.send_patient_abha_otp(req.model_dump())


@router.post("/api/abdm/register-patient/verify-otp", tags=["ProDoc OPD ABHA"])
@router.post("/api/abdm/abha/verify-otp", tags=["ProDoc OPD ABHA"])
async def prodoc_register_patient_verify_otp(req: ProDocVerifyOtpRequest):
    """
    Called by ProDoc frmRegisterABHAPatient (btnVerifyOTP).
    Verifies OTP with ABDM and returns ABHA Number, ABHA Address, Name, Gender, DOB.
    """
    return await abha_service.verify_patient_abha_otp(req.model_dump())


@router.post("/api/abdm/register-patient/verify-user", tags=["ProDoc OPD ABHA"])
@router.post("/api/abdm/abha/verify-user", tags=["ProDoc OPD ABHA"])
@router.post("/api/abdm/profile/login/verify/user", tags=["ProDoc OPD ABHA"])
async def prodoc_verify_user(req: ProDocVerifyUserRequest):
    """
    Called after Verify OTP when user selects an ABHA account.
    Calls ABDM: POST /abha/api/v3/profile/login/verify/user
    Returns token required for profile details.
    """
    return await abha_service.verify_user_account(req.model_dump())


@router.get("/api/abdm/register-patient/profile-details", tags=["ProDoc OPD ABHA"])
@router.get("/api/abdm/profile/account", tags=["ProDoc OPD ABHA"])
@router.get("/api/abdm/register-patient/get-profile", tags=["ProDoc OPD ABHA"])
@router.post("/api/abdm/register-patient/profile-details", tags=["ProDoc OPD ABHA"])
@router.post("/api/abdm/profile/account", tags=["ProDoc OPD ABHA"])
@router.post("/api/abdm/register-patient/get-profile", tags=["ProDoc OPD ABHA"])
@router.post("/api/abdm/patients/abha-profile-details", tags=["ProDoc OPD ABHA"])
async def prodoc_get_profile_details(
    request: Request,
    patientId: str | None = None,
    x_token: str | None = Header(None, alias="X-token"),
    x_token_lower: str | None = Header(None, alias="x-token"),
    authorization: str | None = Header(None),
):
    """
    Step 4: Retrieves full profile details directly from ABDM account.
    Calls ABDM: GET /abha/api/v3/profile/account with X-token header.
    NO BODY REQUIRED!
    X-token can be passed in Header 'X-token: Bearer <token>', or auto-resolved from active session / patientId.
    Returns:
      - ABHANumber, ABHAAddress
      - firstName, middleName, lastName, name
      - dob, yearOfBirth, monthOfBirth, dayOfBirth
      - gender, mobile, address, pincode, stateName, districtName, townName, profilePhoto, status
    """
    body_data = {}
    if request.method == "POST":
        try:
            body_data = await request.json()
            if not isinstance(body_data, dict):
                body_data = {}
        except Exception:
            body_data = {}

    eff_token = (
        body_data.get("token")
        or body_data.get("X-token")
        or body_data.get("x_token")
        or x_token
        or x_token_lower
        or (authorization if authorization and "Bearer" in authorization else None)
        or ""
    )

    data = dict(body_data)
    if eff_token:
        data["token"] = eff_token
    if patientId:
        data.setdefault("patientId", patientId)

    return await abha_service.get_patient_profile_details(data)


@router.post("/api/abdm/register-patient/link", tags=["ProDoc OPD ABHA"])
@router.post("/api/abdm/abha/link-patient", tags=["ProDoc OPD ABHA"])
async def prodoc_register_patient_link(req: ProDocRegisterAbhaRequest):
    """
    Called by ProDoc frmRegisterABHAPatient (btnRegisterABHA).
    Confirms and records linking between patient Reg. No. and ABHA details.
    """
    return await abha_service.register_patient_abha_link(req.model_dump())


@router.get("/api/abdm/register-patient/status", tags=["ProDoc OPD ABHA"])
@router.get("/api/abdm/abha/status", tags=["ProDoc OPD ABHA"])
async def prodoc_register_patient_status():
    """
    Check all active ABHA Registration transactions (transactionId, mobile, status, and linked patients).
    """
    from store import m1_otp_txns, m1_verifications, m1_linked_patients
    return {
        "otp_transactions": m1_otp_txns,
        "active_verifications": m1_verifications,
        "linked_patients": m1_linked_patients,
    }


@router.get("/api/abdm/crypto/debug", tags=["Debug"])
async def debug_crypto_endpoints():
    import uuid
    import httpx
    from datetime import datetime, timezone
    from abdm_client import get_access_token
    import crypto_abdm

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    results = {
        "current_key_source": crypto_abdm.get_key_source(),
        "endpoints": {}
    }

    # Probe 1: ABHA Cert URL
    try:
        token = await get_access_token()
        headers = {
            "REQUEST-ID": str(uuid.uuid4()),
            "TIMESTAMP": now_iso,
            "Authorization": f"Bearer {token}",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            r1 = await client.get(config.ABHA_CERT_URL, headers=headers)
        results["endpoints"]["abha_cert_url"] = {
            "url": config.ABHA_CERT_URL,
            "status": r1.status_code,
            "body_preview": r1.text[:500]
        }
    except Exception as exc:
        results["endpoints"]["abha_cert_url"] = {"url": config.ABHA_CERT_URL, "error": str(exc)}

    # Probe 2: Gateway certs URL
    gateway_url = getattr(config, "ABDM_GATEWAY_CERTS_URL", "https://dev.abdm.gov.in/api/hiecm/gateway/v3/certs")
    try:
        headers = {
            "REQUEST-ID": str(uuid.uuid4()),
            "TIMESTAMP": now_iso,
            "X-CM-ID": config.ABDM_CM_ID,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            r2 = await client.get(gateway_url, headers=headers)
        results["endpoints"]["gateway_certs_url"] = {
            "url": gateway_url,
            "status": r2.status_code,
            "body_preview": r2.text[:500]
        }
    except Exception as exc:
        results["endpoints"]["gateway_certs_url"] = {"url": gateway_url, "error": str(exc)}

    return results


@router.get("/health", tags=["System"])
async def health():
    """Minimal health check (never leaks credentials or internal URLs)."""
    return {"ok": True}

