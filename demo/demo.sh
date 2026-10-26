#!/usr/bin/env bash
# ScamScope AI — before/after demo (target: under 3 minutes).
#
# BEFORE: the baseline agent reasons about the message wording only.
# AFTER:  the tooled agent additionally checks any URL against URLhaus.
#
# Phase 1 (baseline) needs only Bedrock access. Phase 2 (tooled) needs the
# check_url_reputation Lambda deployed (see infra/DEPLOY.md) and is gated.
#
# Usage:
#   ./demo/demo.sh            # runs BEFORE; runs AFTER only if the Lambda is set
set -euo pipefail

cd "$(dirname "$0")/.."

MSG='URGENT: Your account will be suspended. Verify your password now at http://secure-login-verify.example/reset or lose access in 24 hours.'

echo "============================================================"
echo " SCAMSCOPE AI — BEFORE  (Phase 1: baseline, no tools)"
echo "============================================================"
echo "Message: $MSG"
echo "------------------------------------------------------------"
python -m scamscope.cli baseline "$MSG"
echo

if [[ -n "${SCAMSCOPE_LAMBDA_NAME:-}" ]]; then
  echo "============================================================"
  echo " SCAMSCOPE AI — AFTER  (Phase 2: + check_url_reputation)"
  echo "============================================================"
  echo "Message: $MSG"
  echo "------------------------------------------------------------"
  python -m scamscope.cli tooled "$MSG"
else
  echo "[AFTER skipped] Set SCAMSCOPE_LAMBDA_NAME and deploy the Lambda"
  echo "                (infra/DEPLOY.md) to run the tooled comparison."
fi
