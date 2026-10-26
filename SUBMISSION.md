# ScamScope — Builder Center Submission

**Challenge:** Give Your Agent a Tool
**Account:** `<your-account-id>` · **Region:** us-east-1

---

## Project title
**ScamScope: giving a phishing-analysis agent a malware-URL fact-checker**

## Short tagline
A phishing-analysis agent that used to *guess* whether a link was dangerous now
*verifies* it against live URLhaus threat intelligence through an AWS Lambda tool.

---

## 1. The agent I started with, and what it could already do

ScamScope is a cybersecurity assistant built on the **Strands Agents SDK**, running
on **Amazon Bedrock with Amazon Nova Pro** (`us.amazon.nova-pro-v1:0`). Given a
suspicious message, it explains the social-engineering warning signs: urgency,
threats of account loss, credential/OTP/payment requests, sender mismatch,
look-alike domains, and link-text-vs-target tricks.

**Its gap:** when a message contained a URL, the agent could only *reason about how
the link looked*. It had no way to check whether the link was actually known-bad. It
would hedge — "this link does not appear to be associated with..." — because
guessing is all a language model can do about a live URL.

## 2. The one new tool I added, and why I picked it

**`check_url_reputation(url)`** — a tool that checks a URL against
[URLhaus](https://urlhaus.abuse.ch/) malware-URL threat intelligence and returns a
structured verdict (`threat_match` / `no_match` / `invalid_input` / `lookup_failed`)
with evidence.

I picked URL reputation because it closes the agent's single biggest blind spot with
*ground truth*: a phishing verdict is far stronger when it cites a real
threat-intelligence match than when it rests on wording alone. It is also the most
reusable pattern in the whole domain — any agent that handles untrusted text
(email triage, chat moderation, SOC assistants) can bolt on the same tool.

**Safety-by-design:** the tool **never fetches the submitted URL** — it only sends
the URL *string* to the URLhaus lookup API, so it is safe to run against hostile
links.

## 3. AWS services used

- **AWS Lambda** — hosts `check_url_reputation` (Python 3.12, 15s timeout, 256 MB).
  The Strands tool wrapper invokes it with `boto3`; the agent never talks to URLhaus
  directly.
- **Amazon Bedrock (Amazon Nova Pro)** — the agent's reasoning model.
- **AWS Secrets Manager** — stores the URLhaus Auth-Key. It is read inside the Lambda
  at runtime and is never in code, env files, or the repo.
- **Amazon CloudWatch Logs** — execution evidence.
- **AWS IAM** — a dedicated least-privilege execution role: read exactly one secret,
  write its own logs, nothing else.

**Architecture (request path):**
```
suspicious message
      │
      ▼
Strands Agent (Amazon Bedrock · Nova Pro)
      │  decides to verify a URL
      ▼
@tool check_url_reputation  ──boto3 invoke──▶  AWS Lambda
                                                 │ reads Auth-Key ─▶ Secrets Manager
                                                 │ lookup (string only) ─▶ URLhaus API
                                                 ▼
                                         structured verdict + evidence
      ▲                                          │
      └───────────── cited in the answer ◀───────┘
```

## 4. Before / after — demonstrated live

Same phishing message, containing a **real, currently-online malware URL** pulled
from the URLhaus feed (`http://115.49.192.100:38223/i`, Mozi botnet, ELF/MIPS
malware download).

**BEFORE (no tool):** Nova Pro flags urgency/threats/verify-identity correctly, but
on the URL it can only speculate — "does not appear to be associated..." — with no
verification. (Full transcript in `demo/evidence/before_after_transcript.txt`.)

**AFTER (with the tool):** the agent reasons, then calls
`Tool #1: check_url_reputation`. The Lambda reads the key from Secrets Manager,
queries URLhaus, and returns a verdict. The agent now states the URL is
**"confirmed as malicious by URLhaus, with evidence of malware download"** and gives
a decisive "Do not click the link," followed by independent safe next steps.

CloudWatch confirms the real invocations (sub-2s warm calls; cold-start init logged).

---

## How this maps to the judging criteria

- **Technical innovation & originality (25%)** — turns an LLM's *opinion* about a
  link into a *verified fact* via live threat intel, with a safe-by-design tool that
  never touches the hostile URL.
- **Craft & execution (25%)** — Strands `@tool` → boto3 → Lambda → Secrets Manager,
  least-privilege IAM, bounded timeouts, structured error states, 23 passing tests,
  live CloudWatch evidence.
- **Usefulness & impact (25%)** — URL reputation is a drop-in upgrade for any
  agent that reads untrusted text; the Lambda + secret + IAM pattern is copy-paste
  reusable.
- **Creativity & storytelling (25%)** — a crisp before/after on one real message:
  "guesses about the link" → "confirmed malicious by URLhaus."

---

## Demo video script (< 3 minutes)

**0:00–0:20 — Hook.** "This is ScamScope, a phishing-analysis agent on Amazon Bedrock
Nova Pro. It reads suspicious messages. But until this weekend it could only *guess*
whether a link was dangerous. I gave it one tool to *verify* instead."

**0:20–0:50 — Before.** Run the baseline on the phishing message. Point at the
hedge: *"does not appear to be associated..."* — "No verification. Just a guess."

**0:50–1:40 — The tool.** Show `agent_tooled.py` (the `@tool` wrapper), the Lambda
handler (note: it never opens the URL), and the AWS console: the Lambda function,
the Secrets Manager secret, the least-privilege IAM role.

**1:40–2:30 — After.** Run the tooled agent on the *same* message. Show
`Tool #1: check_url_reputation` firing and the agent's new verdict: **"confirmed as
malicious by URLhaus, with evidence of malware download. Do not click."** Flash the
CloudWatch log line proving the Lambda ran.

**2:30–2:55 — Why it matters.** "One tool turned a plausible guess into a verified
threat call — and the same Lambda + Secrets Manager + IAM pattern drops into any
agent that handles untrusted text."

---

## Repo / submission checklist
- [ ] Push the repo to a public GitHub (strip `.venv`, `lambda/.../build`,
      `function.zip`, and any `.env` — all are gitignorable build/local artifacts).
- [ ] Record the < 3-min video (script above) and upload to YouTube **unlisted/public**.
- [ ] Paste the video link into the submission's **demo** field.
- [ ] Paste sections 1–4 above into the write-up.
- [ ] Confirm the project is **previously unpublished**.
