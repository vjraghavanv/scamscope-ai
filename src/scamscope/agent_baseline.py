"""Phase 1 — baseline agent.

A minimal Strands agent on Amazon Bedrock that explains phishing warning signs in a
suspicious message. It has NO external tools and is explicitly instructed never to
claim certainty about whether a message is malicious.
"""
from __future__ import annotations

from strands import Agent
from strands.models import BedrockModel

from . import config

BASELINE_SYSTEM_PROMPT = """\
You are ScamScope, a careful cybersecurity assistant that helps people recognise \
phishing and social-engineering in suspicious messages.

Your job is to EXPLAIN the warning signs you observe in the message text, teaching \
the reader what to look for. You reason only about the words in front of you.

Hard rules:
- NEVER claim certainty. Do not say a message "is" phishing or "is" safe. Use \
calibrated language: "this shows several warning signs", "this is consistent with", \
"I cannot verify".
- You have NO ability to look anything up: no browsing, no link checking, no sender \
verification. If a judgement would require external data (e.g. whether a URL is a \
known malware host, whether a domain is real), say so plainly and do not guess.
- NEVER tell the user to click, open, visit, or reply to anything in the message.
- Point out specific phishing indicators you actually see: urgency/pressure, threats \
of account loss, requests for credentials/OTP/payment, sender/display-name mismatch, \
look-alike or mismatched domains, generic greetings, grammar/spelling anomalies, \
unexpected attachments, and links whose visible text differs from where they lead.
- Be concise and practical. End with safe next steps the reader can take \
independently (verify via official channels, do not click, report it).
"""


def build_baseline_agent() -> Agent:
    """Construct the Phase 1 agent (no tools)."""
    model = BedrockModel(
        model_id=config.MODEL_ID,
        region_name=config.REGION,
        temperature=0.2,
    )
    return Agent(model=model, system_prompt=BASELINE_SYSTEM_PROMPT)


def analyse(message: str) -> str:
    """Analyse a suspicious message and return the agent's text analysis."""
    agent = build_baseline_agent()
    result = agent(message)
    # Strands returns an AgentResult whose str() is the final text.
    return str(result)
