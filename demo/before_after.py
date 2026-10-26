"""Before/After demo for the AWS Builder Center 'Give Your Agent a Tool' challenge.

BEFORE: the baseline ScamScope agent analyses a suspicious message using only the
        language model's reasoning — it has no way to verify any URL.
AFTER:  the SAME agent, now given ONE new tool (check_url_reputation, backed by an
        AWS Lambda that queries URLhaus threat intelligence), verifies the link and
        cites real evidence.

Run:
    PYTHONPATH=src python demo/before_after.py "<malicious_url>"

The malicious URL is passed in so the script itself hard-codes no live threat.
"""
from __future__ import annotations

import sys

from scamscope.agent_baseline import analyse as analyse_baseline
from scamscope.agent_tooled import analyse as analyse_tooled

BANNER = "=" * 78


def _phishing_message(mal_url: str) -> str:
    return (
        "URGENT: Your account has been temporarily suspended due to unusual "
        "sign-in activity. To avoid permanent closure within 24 hours, verify "
        "your identity immediately here:\n"
        f"{mal_url}\n"
        "Failure to confirm will result in loss of access. — Security Team"
    )


def main() -> int:
    mal_url = sys.argv[1] if len(sys.argv) > 1 else "http://example.com/login"
    message = _phishing_message(mal_url)

    print(BANNER)
    print("SUSPICIOUS MESSAGE UNDER ANALYSIS")
    print(BANNER)
    print(message)
    print()

    print(BANNER)
    print("BEFORE  —  baseline agent (NO tool, reasoning only)")
    print(BANNER)
    print(analyse_baseline(message))
    print()

    print(BANNER)
    print("AFTER   —  tooled agent (NEW tool: check_url_reputation via AWS Lambda)")
    print(BANNER)
    print(analyse_tooled(message))
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
