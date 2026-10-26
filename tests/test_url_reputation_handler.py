"""Unit tests for the check_url_reputation Lambda handler.

All network and AWS calls are mocked. No real URLhaus request is made and no
submitted URL is ever opened. The "malicious" sample below is a syntactically valid
but intentionally fake host, used only as a string.
"""
import importlib.util
import os
import sys
from pathlib import Path
from unittest import mock

import pytest
import requests
import responses

# Load the handler module directly from the lambda/ directory.
HANDLER_PATH = (
    Path(__file__).resolve().parents[1]
    / "lambda"
    / "check_url_reputation"
    / "handler.py"
)
spec = importlib.util.spec_from_file_location("urlhaus_handler", HANDLER_PATH)
handler = importlib.util.module_from_spec(spec)
sys.modules["urlhaus_handler"] = handler
spec.loader.exec_module(handler)

# A fake but well-formed "listed" URL used only as a string in mocked responses.
SAMPLE_LISTED_URL = "http://malware-sample.invalid/payload.bin"
SAMPLE_CLEAN_URL = "http://example.com/newsletter"


@pytest.fixture(autouse=True)
def _mock_secret():
    """Supply a fake Auth-Key so the handler reaches the (mocked) HTTP layer."""
    handler._secrets_cache.clear()
    with mock.patch.object(handler, "_get_auth_key", return_value="FAKE-AUTH-KEY"):
        yield


# ---------- normalize_url ----------

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("  http://Example.COM/Path  ", "http://example.com/Path"),
        ("HTTPS://Secure.Example/login", "https://secure.example/login"),
    ],
)
def test_normalize_valid(raw, expected):
    assert handler.normalize_url(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["", "   ", None, 12345, "ftp://example.com/x", "javascript:alert(1)", "notaurl", "http://"],
)
def test_normalize_invalid(raw):
    assert handler.normalize_url(raw) is None


# ---------- handler: four required cases ----------

@responses.activate
def test_threat_match():
    responses.add(
        responses.POST,
        handler.URLHAUS_ENDPOINT,
        json={
            "query_status": "ok",
            "url_status": "online",
            "threat": "malware_download",
            "tags": ["exe", "emotet"],
            "date_added": "2024-01-02 03:04:05 UTC",
            "urlhaus_reference": "https://urlhaus.abuse.ch/url/12345/",
        },
        status=200,
    )
    out = handler.handler({"url": SAMPLE_LISTED_URL})
    assert out["status"] == "threat_match"
    assert out["checked_url"] == SAMPLE_LISTED_URL
    assert out["source"] == "urlhaus"
    assert {"threat": "malware_download"} in out["evidence"]
    assert any("tags" in e for e in out["evidence"])


@responses.activate
def test_no_match():
    responses.add(
        responses.POST,
        handler.URLHAUS_ENDPOINT,
        json={"query_status": "no_results"},
        status=200,
    )
    out = handler.handler({"url": SAMPLE_CLEAN_URL})
    assert out["status"] == "no_match"
    assert out["checked_url"] == SAMPLE_CLEAN_URL
    assert out["evidence"] == []
    assert "not proof" in out["message"].lower()


def test_invalid_input():
    out = handler.handler({"url": "not a url"})
    assert out["status"] == "invalid_input"
    assert out["source"] == "urlhaus"
    assert out["evidence"] == []


def test_invalid_input_missing_key():
    out = handler.handler({})
    assert out["status"] == "invalid_input"


@responses.activate
def test_lookup_failed_timeout():
    responses.add(
        responses.POST,
        handler.URLHAUS_ENDPOINT,
        body=requests.exceptions.ConnectTimeout("simulated timeout"),
    )
    out = handler.handler({"url": SAMPLE_CLEAN_URL})
    assert out["status"] == "lookup_failed"
    assert out["checked_url"] == SAMPLE_CLEAN_URL
    assert "failed" in out["message"].lower()


@responses.activate
def test_lookup_failed_http_5xx():
    responses.add(
        responses.POST,
        handler.URLHAUS_ENDPOINT,
        json={"error": "server"},
        status=502,
    )
    out = handler.handler({"url": SAMPLE_CLEAN_URL})
    assert out["status"] == "lookup_failed"


@responses.activate
def test_unexpected_query_status():
    responses.add(
        responses.POST,
        handler.URLHAUS_ENDPOINT,
        json={"query_status": "invalid_url"},
        status=200,
    )
    out = handler.handler({"url": SAMPLE_CLEAN_URL})
    assert out["status"] == "lookup_failed"


def test_missing_auth_key_returns_lookup_failed():
    # Override the autouse fixture: no key available.
    with mock.patch.object(handler, "_get_auth_key", return_value=None):
        out = handler.handler({"url": SAMPLE_CLEAN_URL})
    assert out["status"] == "lookup_failed"
    assert "auth-key" in out["message"].lower()
