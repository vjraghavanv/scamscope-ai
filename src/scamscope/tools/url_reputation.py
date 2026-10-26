"""Phase 2 — Strands tool wrapper for the check_url_reputation Lambda.

This is the small Python wrapper that "gives the agent a tool": it exposes the AWS
Lambda function to the Strands agent. The wrapper only INVOKES the Lambda via the AWS
SDK (boto3) and relays the Lambda's structured JSON. It performs no network access to
the submitted URL and does no threat analysis itself.
"""
from __future__ import annotations

import json
from typing import Any, Dict

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import BotoCoreError, ClientError
from strands import tool

from .. import config

# Bounded client timeouts and no automatic retries that would hang the agent.
_BOTO_CONFIG = BotoConfig(
    connect_timeout=3,
    read_timeout=15,
    retries={"max_attempts": 2, "mode": "standard"},
)


def _lambda_client():
    return boto3.client("lambda", region_name=config.REGION, config=_BOTO_CONFIG)


def _error(message: str, checked_url: str = "") -> Dict[str, Any]:
    return {
        "status": "lookup_failed",
        "checked_url": checked_url,
        "source": "urlhaus",
        "evidence": [],
        "message": message,
    }


@tool
def check_url_reputation(url: str) -> Dict[str, Any]:
    """Check whether a URL is a known malicious/malware URL using URLhaus threat
    intelligence, via the check_url_reputation AWS Lambda.

    Use this to gather EVIDENCE about a URL found in a suspicious message. It queries
    a threat-intelligence database only — it never opens or fetches the URL itself,
    so it is safe to call on hostile links. A result does not by itself prove the
    message is or is not phishing; treat it as one signal.

    Args:
        url: The HTTP or HTTPS URL to check. Passed as a string; not fetched.

    Returns:
        A dict with keys:
          status: one of "threat_match", "no_match", "invalid_input", "lookup_failed"
          checked_url: the normalized URL that was checked
          source: the intelligence source ("urlhaus")
          evidence: a list of supporting facts (may be empty)
          message: a short human-readable summary
    """
    if not isinstance(url, str) or not url.strip():
        return {
            "status": "invalid_input",
            "checked_url": "",
            "source": "urlhaus",
            "evidence": [],
            "message": "No URL was provided.",
        }

    client = _lambda_client()
    payload = json.dumps({"url": url}).encode("utf-8")

    try:
        resp = client.invoke(
            FunctionName=config.LAMBDA_NAME,
            InvocationType="RequestResponse",
            Payload=payload,
        )
    except (BotoCoreError, ClientError) as exc:
        return _error(f"Could not invoke the reputation Lambda: {exc}", url)

    # A function-level exception is reported via the FunctionError header.
    func_error = resp.get("FunctionError")
    raw = resp.get("Payload")
    body = raw.read().decode("utf-8") if raw is not None else ""

    try:
        data = json.loads(body) if body else {}
    except json.JSONDecodeError:
        return _error("Reputation Lambda returned a non-JSON response.", url)

    if func_error:
        detail = data.get("errorMessage", "unknown error") if isinstance(data, dict) else "unknown error"
        return _error(f"Reputation Lambda failed: {detail}", url)

    # The handler returns the structured result directly (no API Gateway envelope).
    if isinstance(data, dict) and "status" in data:
        return data

    return _error("Reputation Lambda returned an unexpected payload shape.", url)
