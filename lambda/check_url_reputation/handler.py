"""AWS Lambda: check_url_reputation.

Checks a URL against URLhaus malware-URL intelligence and returns a structured
result. It queries only the URLhaus API with the URL *string*; it NEVER issues a
request to the submitted URL itself, so it is safe to run against hostile links.

Event shape (direct invoke):
    {"url": "http://example.com/path"}

Returns a dict:
    {
      "status": "threat_match" | "no_match" | "invalid_input" | "lookup_failed",
      "checked_url": "<normalized url>",
      "source": "urlhaus",
      "evidence": [ ... ],
      "message": "<human-readable summary>"
    }

The URLhaus Auth-Key is read from AWS Secrets Manager (name in
SCAMSCOPE_URLHAUS_SECRET_NAME); it is never hardcoded. The current URLhaus API
requires an Auth-Key header; see https://urlhaus-api.abuse.ch/ .
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List
from urllib.parse import urlparse, urlunparse

import boto3
import requests

URLHAUS_ENDPOINT = "https://urlhaus-api.abuse.ch/v1/url/"
SECRET_NAME = os.environ.get("SCAMSCOPE_URLHAUS_SECRET_NAME", "scamscope/urlhaus-auth-key")
AUTH_KEY_JSON_FIELD = "auth_key"  # key inside the JSON secret
CONNECT_TIMEOUT = 3.0
READ_TIMEOUT = 8.0

_secrets_cache: Dict[str, str] = {}


def _result(status: str, checked_url: str, evidence: List[Any], message: str) -> Dict[str, Any]:
    return {
        "status": status,
        "checked_url": checked_url,
        "source": "urlhaus",
        "evidence": evidence,
        "message": message,
    }


def normalize_url(raw: Any) -> str | None:
    """Validate and normalize an HTTP/HTTPS URL. Returns None if invalid.

    Normalization: strip whitespace, require http/https scheme and a host, and
    lowercase the scheme and host (path/query preserved — URLhaus is path-sensitive).
    """
    if not isinstance(raw, str):
        return None
    candidate = raw.strip()
    if not candidate:
        return None
    parsed = urlparse(candidate)
    if parsed.scheme.lower() not in ("http", "https"):
        return None
    if not parsed.netloc:
        return None
    normalized = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower(),
    )
    return urlunparse(normalized)


def _get_auth_key() -> str | None:
    """Read the URLhaus Auth-Key from Secrets Manager (cached per container)."""
    if SECRET_NAME in _secrets_cache:
        return _secrets_cache[SECRET_NAME]
    client = boto3.client("secretsmanager")
    resp = client.get_secret_value(SecretId=SECRET_NAME)
    secret_string = resp.get("SecretString")
    if not secret_string:
        return None
    try:
        parsed = json.loads(secret_string)
        key = parsed.get(AUTH_KEY_JSON_FIELD) if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        key = secret_string  # allow a plain-string secret as a fallback
    if key:
        _secrets_cache[SECRET_NAME] = key
    return key


def _query_urlhaus(url: str, auth_key: str) -> Dict[str, Any]:
    """POST the URL string to the URLhaus lookup API. Does not fetch the URL."""
    headers = {"Auth-Key": auth_key}
    resp = requests.post(
        URLHAUS_ENDPOINT,
        data={"url": url},
        headers=headers,
        timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
    )
    resp.raise_for_status()
    return resp.json()


def handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    url_in = event.get("url") if isinstance(event, dict) else None
    normalized = normalize_url(url_in)
    if normalized is None:
        return _result(
            "invalid_input",
            checked_url="" if not isinstance(url_in, str) else url_in.strip(),
            evidence=[],
            message="Input is not a valid HTTP or HTTPS URL.",
        )

    try:
        auth_key = _get_auth_key()
        if not auth_key:
            return _result(
                "lookup_failed",
                checked_url=normalized,
                evidence=[],
                message="URLhaus Auth-Key is not configured in Secrets Manager.",
            )
        data = _query_urlhaus(normalized, auth_key)
    except requests.exceptions.RequestException as exc:
        return _result(
            "lookup_failed",
            checked_url=normalized,
            evidence=[],
            message=f"URLhaus lookup failed: {exc.__class__.__name__}.",
        )
    except Exception as exc:  # noqa: BLE001 — secrets/client errors -> structured failure
        return _result(
            "lookup_failed",
            checked_url=normalized,
            evidence=[],
            message=f"Unexpected lookup error: {exc.__class__.__name__}.",
        )

    query_status = data.get("query_status")

    if query_status == "no_results":
        return _result(
            "no_match",
            checked_url=normalized,
            evidence=[],
            message="URLhaus has no record of this URL. This is not proof it is safe.",
        )

    if query_status == "ok":
        evidence: List[Any] = []
        url_status = data.get("url_status")
        threat = data.get("threat")
        tags = data.get("tags") or []
        date_added = data.get("date_added")
        if url_status:
            evidence.append({"url_status": url_status})
        if threat:
            evidence.append({"threat": threat})
        if tags:
            evidence.append({"tags": tags})
        if date_added:
            evidence.append({"date_added": date_added})
        if data.get("urlhaus_reference"):
            evidence.append({"reference": data["urlhaus_reference"]})
        return _result(
            "threat_match",
            checked_url=normalized,
            evidence=evidence,
            message=(
                f"URLhaus lists this URL (status: {url_status or 'unknown'}, "
                f"threat: {threat or 'unknown'})."
            ),
        )

    # Any other query_status (e.g. invalid_url from URLhaus, http_error) -> failure.
    return _result(
        "lookup_failed",
        checked_url=normalized,
        evidence=[{"query_status": query_status}],
        message=f"URLhaus returned an unexpected status: {query_status!r}.",
    )
