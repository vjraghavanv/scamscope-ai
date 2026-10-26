"""Unit tests for the Strands tool wrapper (scamscope.tools.url_reputation).

The wrapper only invokes the Lambda via boto3 and relays its structured JSON. We mock
the boto3 Lambda client so no AWS call is made. If the real `strands` SDK is not
installed, we stub a minimal `strands.tool` passthrough decorator so the module under
test still imports — the wrapper's logic is independent of the SDK.
"""
import io
import json
import sys
import types
from unittest import mock

import pytest

# --- Stub `strands` if it is not installed, so the wrapper imports cleanly. ---
if "strands" not in sys.modules:
    try:
        import strands  # noqa: F401
    except ImportError:
        stub = types.ModuleType("strands")

        def _tool(fn=None, **_kwargs):
            # Support both @tool and @tool(...) usage; return the function unchanged.
            if fn is None:
                return lambda f: f
            return fn

        stub.tool = _tool
        sys.modules["strands"] = stub

from scamscope.tools import url_reputation  # noqa: E402


def _invoke_response(payload_dict, function_error=None):
    body = json.dumps(payload_dict).encode("utf-8")
    resp = {"Payload": io.BytesIO(body)}
    if function_error:
        resp["FunctionError"] = function_error
    return resp


def _call(url):
    """Call the wrapper, tolerating either a bare function or a Strands-wrapped tool."""
    fn = url_reputation.check_url_reputation
    target = getattr(fn, "__wrapped__", None) or (fn if callable(fn) else None)
    try:
        return target(url)
    except TypeError:
        # Strands tool object — call via its underlying function if exposed.
        return fn(url)


def test_passes_through_threat_match():
    fake = {
        "status": "threat_match",
        "checked_url": "http://malware-sample.invalid/x",
        "source": "urlhaus",
        "evidence": [{"threat": "malware_download"}],
        "message": "listed",
    }
    client = mock.Mock()
    client.invoke.return_value = _invoke_response(fake)
    with mock.patch.object(url_reputation, "_lambda_client", return_value=client):
        out = _call("http://malware-sample.invalid/x")
    assert out == fake
    # Confirm the wrapper sent the URL and used RequestResponse (never fetched it).
    kwargs = client.invoke.call_args.kwargs
    assert kwargs["InvocationType"] == "RequestResponse"
    assert json.loads(kwargs["Payload"]) == {"url": "http://malware-sample.invalid/x"}


def test_empty_url_is_invalid_input_without_invoking():
    client = mock.Mock()
    with mock.patch.object(url_reputation, "_lambda_client", return_value=client):
        out = _call("   ")
    assert out["status"] == "invalid_input"
    client.invoke.assert_not_called()


def test_function_error_becomes_lookup_failed():
    client = mock.Mock()
    client.invoke.return_value = _invoke_response(
        {"errorMessage": "boom"}, function_error="Unhandled"
    )
    with mock.patch.object(url_reputation, "_lambda_client", return_value=client):
        out = _call("http://example.com/x")
    assert out["status"] == "lookup_failed"
    assert "boom" in out["message"]


def test_invoke_exception_becomes_lookup_failed():
    from botocore.exceptions import ClientError

    client = mock.Mock()
    client.invoke.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "no"}}, "Invoke"
    )
    with mock.patch.object(url_reputation, "_lambda_client", return_value=client):
        out = _call("http://example.com/x")
    assert out["status"] == "lookup_failed"


def test_non_json_payload_becomes_lookup_failed():
    client = mock.Mock()
    client.invoke.return_value = {"Payload": io.BytesIO(b"not json")}
    with mock.patch.object(url_reputation, "_lambda_client", return_value=client):
        out = _call("http://example.com/x")
    assert out["status"] == "lookup_failed"
