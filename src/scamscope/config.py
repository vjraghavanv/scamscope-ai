"""Central configuration, read from environment variables.

Nothing secret lives here — only names, ids, and regions. The URLhaus Auth-Key
value is read from Secrets Manager inside the Lambda at runtime.
"""
from __future__ import annotations

import os

# Bedrock model used by the Strands agent. Override with SCAMSCOPE_MODEL_ID.
# Amazon Nova only, per project constraint (no non-Nova models).
MODEL_ID: str = os.environ.get(
    "SCAMSCOPE_MODEL_ID",
    "us.amazon.nova-pro-v1:0",
)

# AWS region for both Bedrock and Lambda. Falls back to the standard AWS vars.
# Pinned to us-east-1 per project constraint.
REGION: str = (
    os.environ.get("SCAMSCOPE_REGION")
    or os.environ.get("AWS_REGION")
    or os.environ.get("AWS_DEFAULT_REGION")
    or "us-east-1"
)

# Phase 2: name of the deployed Lambda function.
LAMBDA_NAME: str = os.environ.get("SCAMSCOPE_LAMBDA_NAME", "check_url_reputation")

# Phase 2: name of the Secrets Manager secret holding the URLhaus Auth-Key.
URLHAUS_SECRET_NAME: str = os.environ.get(
    "SCAMSCOPE_URLHAUS_SECRET_NAME", "scamscope/urlhaus-auth-key"
)
