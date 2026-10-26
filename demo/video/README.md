# ScamScope demo video — package

## Files
- `scamscope_demo.webm` — the finished **44-second**, 1280×720 animated before/after video.
  YouTube accepts `.webm` on upload, so you can upload it as-is.
- `frames/s1.png … s6.png` — one still per scene (thumbnails / article figures).
- `demo_player.html` — the source animation (open in any browser to replay/re-record).

## How this video was made (provenance, be honest in your submission)
The before/after **text is from a real live run** on 2026-10-26: Amazon Bedrock Nova Pro
through the Strands agent, calling the deployed AWS Lambda `check_url_reputation`, which
read the URLhaus Auth-Key from Secrets Manager and queried URLhaus. The malicious URL
`http://221.15.172.85:48113/bin.sh` was a currently-online malware-download URL from the
URLhaus feed. The video is an **animated presentation of that real run** (a screen capture
of the live terminal is an equally valid alternative — see "Option: real terminal capture").

## Adding narration (the video is currently silent)
Pick ONE:
1. **Easiest — narrate on upload:** upload `scamscope_demo.webm` to YouTube, then use
   YouTube's built-in tools, or simply record a screen-capture of it playing while you talk
   (macOS ⌘⇧5 → record selected portion with microphone on).
2. **Record yourself presenting the HTML:** open `demo_player.html` full-screen, press ⌘⇧5,
   enable the mic, click record, then run the page (it auto-plays when you call the start
   hook — or just screen-record the 44s webm playing in a browser) and read the script below.

## Narration script (timed to the 44s animation, ~110 words — comfortably under 3 min)

- **[0:00–0:05] Intro:** "This is ScamScope, a phishing-analysis agent on Amazon Bedrock
  Nova Pro. It reads suspicious messages — but it could only *guess* whether a link was
  actually dangerous."
- **[0:05–0:11] The message:** "Here's a classic phishing message: urgency, a 24-hour
  threat, and a link to verify your identity."
- **[0:11–0:18] BEFORE:** "Before, the agent spotted the social-engineering cues, but on
  the link itself it could only speculate — and Bedrock's filter even cut it off. No
  verification."
- **[0:18–0:26] The tool:** "So I gave it one new tool: check_url_reputation. The agent
  calls an AWS Lambda, which reads a key from Secrets Manager and checks URLhaus threat
  intelligence — sending only the URL string, never opening the hostile link."
- **[0:26–0:34] AFTER:** "Now the same message gets a verified answer: URLhaus confirms the
  link is malicious, associated with a malware download. A guess became a fact."
- **[0:34–0:44] Close:** "One tool — Lambda, Secrets Manager, IAM, CloudWatch — turned a
  plausible guess into a verified threat call. And the same pattern drops into any agent
  that reads untrusted text."

## Option: real terminal capture (strongest "craft" evidence)
If you'd rather show the actual run instead of the animation, screen-record this on macOS
(⌘⇧5, mic on) from the project root:
```bash
cd "/Users/vijayaraghavanvashudevan/Documents/aws ug mdu/scamscope-ai"
export AWS_REGION=us-east-1 SCAMSCOPE_REGION=us-east-1
# grab a fresh online malware URL from URLhaus, then run before/after:
PYTHONPATH=src ./.venv/bin/python demo/before_after.py "http://221.15.172.85:48113/bin.sh"
```
(Use a fresh URL if that one has gone offline.) Best of both: show the terminal run, then
cut to this animation for the architecture + summary.
