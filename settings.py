"""
settings.py - Centralized operational settings and timeout configuration for ABDM Middleware.

Configures fast acknowledgment timeouts so hospital UI (ProDoc) never freezes.
If ABDM callback arrives after 1-2 seconds (can take up to 10 minutes in sandbox),
Python immediately returns 'PENDING' to ProDoc with transactionId.
ProDoc later checks status via API 9: GET /api/abdm/hip/care-context/status/{transactionId}.
"""
import os
import config

# Fast acknowledgment timeout (Configurable: default 2.0 seconds)
# Reduced from 30-35s down to 1-2s as requested
CALLBACK_WAIT_SECONDS: float = float(os.getenv("CALLBACK_WAIT_SECONDS", "2.0"))
POLL_STEP_SECONDS: float = float(os.getenv("POLL_STEP_SECONDS", "0.5"))

# Re-export all config attributes for convenience
for attr in dir(config):
    if not attr.startswith("__"):
        globals()[attr] = getattr(config, attr)

# Synchronize config module
config.CALLBACK_WAIT_SECONDS = CALLBACK_WAIT_SECONDS
config.POLL_STEP_SECONDS = POLL_STEP_SECONDS
