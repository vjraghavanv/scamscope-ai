# ScamScope AI

A cybersecurity agent that analyses suspicious messages for phishing warning signs,
built for the AWS Builder Center **"Give Your Agent a Tool"** challenge.

The project is delivered in two phases:

- **Phase 1 — Baseline agent.** A minimal [Strands Agents](https://strandsagents.com)
  agent on Amazon Bedrock that explains phishing warning signs from the text of a
  message alone. It has **no external tools** and never claims certainty.
- **Phase 2 — New AWS tool.** The agent gains one new capability: an AWS Lambda
  function, `check_url_reputation`, that checks a URL against
  [URLhaus](https://urlhaus.abuse.ch) malware-URL intelligence. The Lambda is
  exposed to the agent through a small Strands tool wrapper that invokes it with the
  AWS SDK. **The agent never fetches the submitted URL** — it only queries the
  threat-intelligence API.

> **Before / after.** Phase 1 reasons about *wording*. Phase 2 adds *evidence*: the
> agent can now say whether a URL in the message is a known-bad malware host, not
> just whether the message *reads* like phishing.

---

## Project structure

```
scamscope-ai/
├── README.md                     # this file
├── requirements.txt              # runtime deps (Strands + boto3)
├── requirements-dev.txt          # test deps (pytest, responses)
├── .env.example                  # env vars for local runs
├── src/
│   └── scamscope/
│       ├── __init__.py
│       ├── config.py             # model id / region / lambda name from env
│       ├── agent_baseline.py     # Phase 1 agent (no tools)
│       ├── agent_tooled.py       # Phase 2 agent (+ reputation tool)
│       ├── cli.py                # CLI entrypoint (baseline | tooled)
│       └── tools/
│           ├── __init__.py
│           └── url_reputation.py # Strands @tool wrapper -> invokes Lambda
├── lambda/
│   └── check_url_reputation/
│       ├── handler.py            # Lambda handler: validate + query URLhaus
│       └── requirements.txt      # Lambda deps (requests)
├── infra/
│   ├── iam_policy.json           # least-privilege execution-role policy
│   └── DEPLOY.md                 # deployment instructions (NOT run until approved)
├── demo/
│   └── demo.sh                   # <3 min before/after demo script
└── tests/
    ├── test_url_reputation_handler.py  # Lambda handler unit tests
    └── test_tool_wrapper.py            # Strands tool wrapper unit tests
```

---

## Prerequisites

- Python 3.10–3.13 (the Strands SDK supports 3.10+; see note below if you are on 3.14/3.15)
- An AWS account with **Amazon Bedrock model access enabled** for **Amazon Nova**
  (default: `us.amazon.nova-pro-v1:0` in `us-east-1`)
- AWS CLI v2 for credentials

---

## 1. Configure AWS credentials

Strands uses the standard AWS credential chain via boto3. Configure credentials in
your terminal **before** running the agent:

```bash
# Option A — SSO (recommended)
aws sso login --profile my-profile
export AWS_PROFILE=my-profile

# Option B — static/long-lived keys
aws configure            # enter access key, secret, region
```

Set the region to one where you have Bedrock model access (the default here is
`us-east-1`):

```bash
export AWS_REGION=us-east-1
```

Confirm the identity resolves:

```bash
aws sts get-caller-identity
```

---

## 2. Install

```bash
cd scamscope-ai
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

> **Python 3.14/3.15 note.** At the time of writing, some Strands/boto dependencies
> do not yet publish wheels for the very newest CPython. If `pip install` fails to
> build a dependency, create the venv with a 3.12 interpreter
> (`python3.12 -m venv .venv`) — e.g. via `pyenv install 3.12` or Homebrew
> `python@3.12`. The Lambda handler and its unit tests run on **any** Python 3.10+
> and do not need the Strands SDK at all.

---

## 3. Run the baseline agent (Phase 1)

```bash
# default model/region from config.py; override with env vars
python -m scamscope.cli baseline "Your account is locked. Verify now: http://secure-login.example/reset"
```

Or read the message from stdin:

```bash
echo "Dear customer, confirm your password at http://badsite.example" | python -m scamscope.cli baseline -
```

The baseline prints the agent's analysis of phishing warning signs. It reasons only
about the message text — it does **not** look anything up.

---

## 4. Run the tooled agent (Phase 2) — requires deployed Lambda

Phase 2 requires the `check_url_reputation` Lambda to be deployed and a URLhaus
Auth-Key stored in Secrets Manager. **Deployment is gated** — see
[`infra/DEPLOY.md`](infra/DEPLOY.md). Nothing in this repo deploys AWS resources
automatically.

Once deployed:

```bash
export SCAMSCOPE_LAMBDA_NAME=check_url_reputation
python -m scamscope.cli tooled "Is http://some-url.example/login safe?"
```

---

## Tests

Unit tests run fully offline — the URLhaus API and the Lambda invocation are mocked,
so **no network calls and no malicious URLs are ever opened**.

```bash
pip install -r requirements-dev.txt
pytest -q
```

Coverage:

- Known URLhaus-listed sample → `threat_match`
- Unlisted URL → `no_match`
- Invalid input → `invalid_input`
- Simulated API failure (timeout / 5xx) → `lookup_failed`
- Tool wrapper parses Lambda responses and surfaces errors

---

## Security notes

- **No URL fetching.** The handler sends only the *URL string* to URLhaus; it never
  issues a request to the submitted URL itself.
- **Secrets.** The URLhaus Auth-Key lives in AWS Secrets Manager and is read at
  runtime. It is never hardcoded or committed. `.env.example` documents names only.
- **Least privilege.** The Lambda execution role is limited to reading the one
  secret and writing its own CloudWatch logs (see `infra/iam_policy.json`). The
  agent's caller needs only `lambda:InvokeFunction` on the one function.
- **Timeouts.** The outbound URLhaus request has an explicit connect/read timeout,
  and the Lambda has a short function timeout, so a slow API cannot hang the agent.
