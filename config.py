"""Application configuration loaded strictly from environment variables / .env."""
import os
from dotenv import load_dotenv

load_dotenv()


def require(name: str) -> str:
    """Return a required env variable or fail fast on startup."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required setting: {name}")
    return value


# Feature toggles (disable demo routes & polling in production)
ENABLE_WEBHOOK_POLLING = os.getenv("ENABLE_WEBHOOK_POLLING", "1") == "1"
ENABLE_DEMO_ROUTES = os.getenv("ENABLE_DEMO_ROUTES", "1") == "1"
# Must be 0 when Postman (not Python) sends the ABDM requests (e.g. CEO demo)
ONLY_MATCHED_CALLBACKS = os.getenv("ONLY_MATCHED_CALLBACKS", "0") == "1"
DEBUG_BREAKPOINTS = os.getenv("DEBUG_BREAKPOINTS", "0") == "1"

# Required ABDM credentials & endpoints (no hardcoded defaults)
CLIENT_ID = require("ABDM_CLIENT_ID")
CLIENT_SECRET = require("ABDM_CLIENT_SECRET")
HIP_ID = require("ABDM_HIP_ID")
CM_ID = require("ABDM_CM_ID")

SESSION_URL = require("ABDM_SESSION_URL")
BRIDGE_URL_ENDPOINT = require("ABDM_BRIDGE_URL_ENDPOINT")
GENERATE_TOKEN_URL = require("ABDM_GENERATE_TOKEN_URL")
CARE_CONTEXT_URL = os.getenv("ABDM_CARE_CONTEXT_URL", "https://dev.abdm.gov.in/api/hiecm/hip/v3/link/carecontext")

# Milestone 1 (M1 - ABHA) endpoints & settings
ABHA_BASE_URL = os.getenv("ABHA_BASE_URL", "https://abhasbx.abdm.gov.in")
ABHA_CERT_URL = os.getenv("ABHA_CERT_URL", f"{ABHA_BASE_URL}/abha/api/v3/profile/public/certificate")
ABDM_GATEWAY_CERTS_URL = os.getenv("ABDM_GATEWAY_CERTS_URL", "https://dev.abdm.gov.in/api/hiecm/gateway/v3/certs")
ABDM_PUBLIC_CERT_PEM = os.getenv("ABDM_PUBLIC_CERT_PEM", "")
RSA_PADDING_ALGORITHM = os.getenv("RSA_PADDING_ALGORITHM", "OAEP-SHA1")
ABHA_CONSENT_CODE = os.getenv("ABHA_CONSENT_CODE", "abha-enrollment")
ABHA_CONSENT_VERSION = os.getenv("ABHA_CONSENT_VERSION", "1.4")

ABHA_ENROL_REQUEST_OTP_URL = os.getenv("ABHA_ENROL_REQUEST_OTP_URL", f"{ABHA_BASE_URL}/abha/api/v3/enrollment/request/otp")
ABHA_ENROL_BY_AADHAAR_URL = os.getenv("ABHA_ENROL_BY_AADHAAR_URL", f"{ABHA_BASE_URL}/abha/api/v3/enrollment/enrol/byAadhaar")
ABHA_SEARCH_URL = os.getenv("ABHA_SEARCH_URL", f"{ABHA_BASE_URL}/abha/api/v3/profile/account/abha/search")
ABHA_LOGIN_REQUEST_OTP_URL = os.getenv("ABHA_LOGIN_REQUEST_OTP_URL", f"{ABHA_BASE_URL}/abha/api/v3/profile/login/request/otp")
ABHA_LOGIN_VERIFY_OTP_URL = os.getenv("ABHA_LOGIN_VERIFY_OTP_URL", f"{ABHA_BASE_URL}/abha/api/v3/profile/login/verify")
ABHA_PROFILE_ACCOUNT_URL = os.getenv("ABHA_PROFILE_ACCOUNT_URL", f"{ABHA_BASE_URL}/abha/api/v3/profile/account")
ABHA_CARD_URL = os.getenv("ABHA_CARD_URL", f"{ABHA_BASE_URL}/abha/api/v3/profile/account/abha-card")
ABHA_QR_CODE_URL = os.getenv("ABHA_QR_CODE_URL", f"{ABHA_BASE_URL}/abha/api/v3/profile/account/qrCode")

# Webhook.site settings (required only when demo polling is enabled)
WEBHOOK_SITE_BASE = require("WEBHOOK_SITE_BASE") if ENABLE_WEBHOOK_POLLING else os.getenv("WEBHOOK_SITE_BASE", "")
WEBHOOK_SITE_TOKEN = require("WEBHOOK_SITE_TOKEN") if ENABLE_WEBHOOK_POLLING else os.getenv("WEBHOOK_SITE_TOKEN", "")
WEBHOOK_SITE_URL = f"{WEBHOOK_SITE_BASE}/{WEBHOOK_SITE_TOKEN}" if WEBHOOK_SITE_BASE and WEBHOOK_SITE_TOKEN else ""
WEBHOOK_SITE_API = f"{WEBHOOK_SITE_BASE}/token/{WEBHOOK_SITE_TOKEN}/requests" if WEBHOOK_SITE_BASE and WEBHOOK_SITE_TOKEN else ""

# Operational tuning (configurable via env, no magic numbers in code)
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "35"))
POLL_TIMEOUT = float(os.getenv("POLL_TIMEOUT", "20"))
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "5"))
POLL_STEP_SECONDS = float(os.getenv("POLL_STEP_SECONDS", "2.0"))
CALLBACK_WAIT_SECONDS = float(os.getenv("CALLBACK_WAIT_SECONDS", "35"))
SIMULATE_WAIT_SECONDS = float(os.getenv("SIMULATE_WAIT_SECONDS", "8"))
WEBHOOK_PER_PAGE = int(os.getenv("WEBHOOK_PER_PAGE", "50"))
RATE_LIMIT_BACKOFF_SECONDS = int(os.getenv("RATE_LIMIT_BACKOFF_SECONDS", "3"))
TOKEN_EXPIRY_FALLBACK = int(os.getenv("TOKEN_EXPIRY_FALLBACK", "600"))
TOKEN_REFRESH_BUFFER_SECONDS = int(os.getenv("TOKEN_REFRESH_BUFFER_SECONDS", "30"))
LOG_PREVIEW_LENGTH = int(os.getenv("LOG_PREVIEW_LENGTH", "400"))
TOKEN_PREVIEW_LENGTH = int(os.getenv("TOKEN_PREVIEW_LENGTH", "24"))

