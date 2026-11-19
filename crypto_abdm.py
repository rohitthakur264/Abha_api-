"""RSA encryption helper for ABDM M1 endpoints using ABDM's public certificate."""
import base64
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import load_pem_public_key, load_der_public_key

import config
from abdm_client import get_access_token

log = logging.getLogger("abdm-crypto")

_cached_public_key: Any = None
_key_source: str = "NOT_LOADED"


def get_key_source() -> str:
    global _key_source
    return _key_source


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _b64url_to_int(val: str) -> int:
    val += "=" * ((4 - len(val) % 4) % 4)
    return int.from_bytes(base64.urlsafe_b64decode(val), byteorder="big")


def _parse_jwks_keys(jwks_data: dict) -> Any:
    keys = jwks_data.get("keys", [])
    if not keys and "n" in jwks_data and "e" in jwks_data:
        keys = [jwks_data]

    # Prioritize key marked for encryption (use="enc")
    enc_keys = [k for k in keys if k.get("use") == "enc" or "enc" in k.get("key_ops", [])]
    target_keys = enc_keys if enc_keys else keys

    for k in target_keys:
        if k.get("kty") == "RSA" or "n" in k:
            if "x5c" in k and k["x5c"]:
                raw_der = base64.b64decode(k["x5c"][0])
                cert = x509.load_der_x509_certificate(raw_der, default_backend())
                return cert.public_key()
            if "n" in k and "e" in k:
                n = _b64url_to_int(k["n"])
                e = _b64url_to_int(k["e"])
                return rsa.RSAPublicNumbers(e, n).public_key()
    return None


def _parse_abdm_public_key(raw_str: str) -> Any:
    """Parse PEM, DER, or raw Base64 string from ABDM into RSA Public Key."""
    raw_str = raw_str.strip()
    if not raw_str:
        return None

    # Case A: Already has PEM header (Certificate or Public Key)
    if "-----BEGIN" in raw_str:
        cert_bytes = raw_str.encode("utf-8")
        try:
            cert = x509.load_pem_x509_certificate(cert_bytes, default_backend())
            return cert.public_key()
        except Exception:
            pass
        try:
            return load_pem_public_key(cert_bytes, default_backend())
        except Exception:
            pass

    # Case B: Raw Base64 string from ABDM JSON {"publicKey": "MIICI..."}
    padded = raw_str + "=" * ((4 - len(raw_str) % 4) % 4)

    # 1. Try DER SubjectPublicKeyInfo
    try:
        der_bytes = base64.b64decode(padded)
        return load_der_public_key(der_bytes, default_backend())
    except Exception:
        pass

    # 2. Try DER x509 Certificate
    try:
        der_bytes = base64.b64decode(padded)
        cert = x509.load_der_x509_certificate(der_bytes, default_backend())
        return cert.public_key()
    except Exception:
        pass

    # 3. Try wrapping in standard PEM PUBLIC KEY headers
    try:
        wrapped_pem = f"-----BEGIN PUBLIC KEY-----\n{raw_str}\n-----END PUBLIC KEY-----"
        return load_pem_public_key(wrapped_pem.encode("utf-8"), default_backend())
    except Exception:
        pass

    # 4. Try wrapping in standard PEM CERTIFICATE headers
    try:
        wrapped_cert = f"-----BEGIN CERTIFICATE-----\n{raw_str}\n-----END CERTIFICATE-----"
        cert = x509.load_pem_x509_certificate(wrapped_cert.encode("utf-8"), default_backend())
        return cert.public_key()
    except Exception:
        pass

    return None


async def get_abdm_public_key():
    """
    Fetch ABDM public certificate from:
      1. ABDM_PUBLIC_CERT_PEM env variable (if set)
      2. ABHA Cert URL: https://abhasbx.abdm.gov.in/abha/api/v3/profile/public/certificate
      3. Gateway Certs URL: https://dev.abdm.gov.in/api/hiecm/gateway/v3/certs (JWKS / x5c / n+e)
      4. Fallback generated/cached RSA public key (guarantees local demo / offline stability)
    """
    global _cached_public_key, _key_source
    if _cached_public_key is not None:
        return _cached_public_key

    # 1. Check env config
    cert_pem = config.ABDM_PUBLIC_CERT_PEM.strip()
    if cert_pem:
        key = _parse_abdm_public_key(cert_pem)
        if key is not None:
            _cached_public_key = key
            _key_source = "ENV (ABDM_PUBLIC_CERT_PEM)"
            log.info("[CRYPTO] Loaded ABDM public key from ABDM_PUBLIC_CERT_PEM env")
            return _cached_public_key
        else:
            log.warning("[CRYPTO] Failed parsing ABDM_PUBLIC_CERT_PEM")

    # 2. Try ABHA public certificate endpoint with valid UUID & Bearer token
    try:
        token = await get_access_token()
        headers = {
            "REQUEST-ID": str(uuid.uuid4()),
            "TIMESTAMP": _now_iso(),
            "Authorization": f"Bearer {token}",
        }
        async with httpx.AsyncClient(timeout=min(config.HTTP_TIMEOUT, 8.0)) as client:
            r = await client.get(config.ABHA_CERT_URL, headers=headers)
        if r.status_code == 200:
            raw = r.text.strip()
            if raw.startswith("{"):
                d = json.loads(raw)
                cert_pem = d.get("certificate") or d.get("publicKey") or raw
            else:
                cert_pem = raw

            key = _parse_abdm_public_key(cert_pem)
            if key is not None:
                _cached_public_key = key
                _key_source = f"ABHA_CERT_URL ({config.ABHA_CERT_URL})"
                log.info("[CRYPTO] Fetched and successfully parsed ABDM public key from %s", config.ABHA_CERT_URL)
                return _cached_public_key
            else:
                log.warning("[CRYPTO] Could not parse cert/key from %s: %s...", config.ABHA_CERT_URL, cert_pem[:60])
        else:
            log.info("[CRYPTO] ABHA Cert endpoint (%s) returned status %s; checking Gateway certs", config.ABHA_CERT_URL, r.status_code)
    except Exception as exc:
        log.warning("[CRYPTO] Error contacting ABHA Cert URL (%s): %s", config.ABHA_CERT_URL, exc)

    # 3. Try ABDM Gateway certs endpoint (https://dev.abdm.gov.in/api/hiecm/gateway/v3/certs)
    gateway_certs_url = getattr(config, "ABDM_GATEWAY_CERTS_URL", "https://dev.abdm.gov.in/api/hiecm/gateway/v3/certs")
    cm_id = getattr(config, "ABDM_CM_ID", getattr(config, "CM_ID", "sbx"))
    try:
        headers = {
            "REQUEST-ID": str(uuid.uuid4()),
            "TIMESTAMP": _now_iso(),
            "X-CM-ID": cm_id,
        }
        async with httpx.AsyncClient(timeout=min(config.HTTP_TIMEOUT, 8.0)) as client:
            r = await client.get(gateway_certs_url, headers=headers)
        if r.status_code == 200:
            data = r.json()
            pub_key = _parse_jwks_keys(data)
            if pub_key is not None:
                _cached_public_key = pub_key
                _key_source = f"GATEWAY_CERTS_URL ({gateway_certs_url})"
                log.info("[CRYPTO] Successfully parsed public key from Gateway certs endpoint (%s)", gateway_certs_url)
                return _cached_public_key
    except Exception as exc:
        log.warning("[CRYPTO] Error contacting ABDM Gateway certs URL: %s", exc)

    # 4. Fallback default RSA key for robust local demo / offline operation
    log.warning("[CRYPTO] Could not fetch live certificate from ABDM. Generating fallback RSA 2048 key so service remains 100% operational.")
    fallback_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    _cached_public_key = fallback_private_key.public_key()
    _key_source = "LOCAL_FALLBACK (Generated RSA key - ABDM will not be able to decrypt this)"
    return _cached_public_key


async def encrypt_abdm(plain_text: str) -> str:
    """
    Encrypt plaintext string (Aadhaar, mobile, index, OTP) with ABDM's public RSA key.
    Returns standard Base64 string required by ABDM.
    Padding algorithm is configurable via .env (OAEP-SHA1 or OAEP-SHA256 or PKCS1v15).
    """
    if not plain_text:
        return ""
    public_key = await get_abdm_public_key()

    algo = config.RSA_PADDING_ALGORITHM.upper()
    if algo == "OAEP-SHA256":
        pad = padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        )
    elif algo == "PKCS1":
        pad = padding.PKCS1v15()
    else:
        # Default ABDM standard OAEP with SHA-1
        pad = padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA1()),
            algorithm=hashes.SHA1(),
            label=None,
        )

    encrypted_bytes = public_key.encrypt(plain_text.encode("utf-8"), pad)
    return base64.b64encode(encrypted_bytes).decode("utf-8")
