"""
Flavour Founders Content Bot
- Runs at 07:05am daily (5 mins after research bot)
- Reads latest research digest from shared storage
- Generates 1 reel idea with 3 A/B hook variations
- Posts to #content Slack channel
"""

import os
import logging
import httpx
import anthropic

from datetime import datetime
from fastapi import FastAPI, BackgroundTasks
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
CONTENT_WEBHOOK_URL = os.environ["CONTENT_WEBHOOK_URL"]
RESEARCH_WEBHOOK_URL = os.environ["RESEARCH_WEBHOOK_URL"]
MANUAL_TRIGGER_TOKEN = os.environ.get("MANUAL_TRIGGER_TOKEN", "")

# ── In-memory store for latest research digest ─────────────────────────────
# Research bot POSTs its digest here via /ingest endpoint
latest_research = {"content": "", "received_at": ""}

# ── Anthropic client ───────────────────────────────────────────────────────
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ── Prompt ─────────────────────────────────────────────────────────────────
BRAND_CONTEXT = """
WHO YOU ARE WRITING FOR:
A UK food entrepreneur who has built TWO 7-figure food businesses (bakery/café, multi-site).
Currently scaling a group with a restaurant launching. Real experience, hard lessons, no theory.

PERSONAL BRAND PILLARS:
1. Food & Drink Business (PRIMARY) — bakery/café growth, profit, margins, labour, systems, scaling
2. Care Less (SECONDARY) — life perspective, freedom, time, YOLO, not overvaluing seriousness

BRAND VOICE: Direct, honest, slightly confrontational, insight-led. NO fluff.

REEL FORMAT:
- 6–9 seconds, text-led, no talking
- Structure: Thumbnail (face) → First 2-3 secs (clean visual + text hook) → Middle (curiosity line) → End (1-2 punchy insight lines)
- Hook style: "Why [positive/neutral]... but [negative reality]"

CONTENT ROTATION:
💰 Money (profit, margins, cash)
🧠 Control (systems, chaos, structure)
⏱ Time (freedom, burnout, stepping away)
🌍 Care Less (occasional)

WHAT WORKS: Contradiction hooks, money topics, specific wording, clean visuals, one clear idea
WHAT DOESN'T: Vague language, repetitive phrasing, talking head intros, long explanations
"""


def build_content_prompt(research_digest: str) -> str:
    today = datetime.now().strftime("%A %d %B %Y")
    return f"""You are the content strategist for Flavour Founders, a UK food entrepreneur personal brand.

{BRAND_CONTEXT}

Today is {today}.

Here is today's research digest:
{research_digest if research_digest else "No research digest available — use your knowledge of UK food business trends."}

Based on the strongest insight from the research digest, generate TODAY'S REEL BRIEF.

Output EXACTLY in this format:

---
🎬 DAILY REEL BRIEF — {datetime.now().strftime("%d %b %Y")}

ANGLE: [💰/🧠/⏱/🌍] [NAME] — [one sentence: what this reel is really about]

---
HOOK A
Line 1: [first text line — 3-5 words max]
Line 2: [second text line — completes the contradiction]
→ Curiosity line: [middle screen text — creates tension]
→ End line 1: [punchy insight]
→ End line 2: [harder-hitting closer]

---
HOOK B
Line 1: [different angle, same contradiction format]
Line 2: [completes it]
→ Curiosity line: [builds tension differently]
→ End line 1: [punchy insight]
→ End line 2: [closer]

---
HOOK C
Line 1: [most provocative version]
Line 2: [sharpest contradiction]
→ Curiosity line: [most tension]
→ End line 1: [punchy insight]
→ End line 2: [strongest closer]

---
📝 CAPTION
Write a full caption following this MANDATORY structure in order:

1. HOOK — strong scroll-stopping first line, repeats reel hook, contradiction format
2. RELATABILITY — personal experience line, feels real ("I did this for YEARS.")
3. SCENARIO BUILD — paint a quick picture, then contrast with "But there's no money left."
4. AUTHORITY — include naturally: "After building not one, but TWO 7-figure food businesses… with another on the way…"
5. CORE INSIGHT — one clear lesson (Revenue ≠ profit / Margins decide everything)
6. BREAKDOWN — 3-4 short bullet points
7. CONSEQUENCE — what happens if not fixed
8. RESOLUTION — the shift ("Once I fixed this…")
9. FINAL LINE — strong and memorable
10. CTA — only sometimes ("Comment 'FOCUS'")

Caption writing rules:
- Short lines, lots of spacing, mobile readable
- CAPITALS for emphasis (not overused)
- Direct, honest, slightly confrontational
- Never robotic or guru-sounding
- Goal: reader thinks 'This is literally me'

#️⃣ HASHTAGS
#bakerybusiness #foodbusiness #entrepreneurmindset #hospitalitybusiness

---
WHY THIS REEL THIS WEEK
[One sentence — what's happening right now that makes this timely]

---

RULES:
- All 3 hooks must follow "Why [positive]... but [negative reality]" contradiction format
- Each hook must be genuinely different — different angle, not just different wording
- Every line must be 5 words or fewer (it's text on screen)
- Must make a bakery owner feel called out
- No vague words: no "struggling", "stressful", "journey", "passion"
- Prioritise money/profit angle unless research strongly suggests another angle"""


# ── Core content generator ─────────────────────────────────────────────────
async def generate_content() -> str:
    research = latest_research.get("content", "")
    if research:
        log.info(f"Using research digest from {latest_research.get('received_at')}")
    else:
        log.warning("No research digest available — generating without it")

    prompt = build_content_prompt(research)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    output = "\n\n".join(
        block.text for block in response.content if block.type == "text"
    )
    log.info(f"Content brief generated ({len(output)} chars)")
    return output


# ── Slack delivery ─────────────────────────────────────────────────────────
async def deliver_content(content: str):
    payload = {
        "text": f"*Flavour Founders Content Bot*\n{content}",
        "content": content,
        "generated_at": datetime.now().isoformat()
    }
    async with httpx.AsyncClient(timeout=30) as http:
        try:
            resp = await http.post(CONTENT_WEBHOOK_URL, json=payload)
            resp.raise_for_status()
            log.info(f"Content delivered to #content → {resp.status_code}")
        except Exception as e:
            log.error(f"Webhook delivery failed: {e}")


# ── Scheduled job ──────────────────────────────────────────────────────────
async def daily_content_job():
    log.info("⏰ Daily content brief triggered")
    content = await generate_content()
    await deliver_content(content)


# ── FastAPI app ────────────────────────────────────────────────────────────
app = FastAPI(title="Flavour Founders Content Bot")
scheduler = AsyncIOScheduler(timezone="Europe/London")


@app.on_event("startup")
async def startup():
    # Runs at 07:05am — 5 mins after research bot
    scheduler.add_job(daily_content_job, CronTrigger(hour=7, minute=5))
    scheduler.start()
    log.info("Content bot scheduler started — daily 07:05 Europe/London")


@app.on_event("shutdown")
async def shutdown():
    scheduler.shutdown()


@app.get("/")
async def health():
    jobs = [
        {"id": job.id, "next_run": str(job.next_run_time)}
        for job in scheduler.get_jobs()
    ]
    return {
        "status": "running",
        "bot": "Flavour Founders Content Bot",
        "scheduled_jobs": jobs,
        "latest_research_received": latest_research.get("received_at", "none")
    }


@app.post("/ingest")
async def ingest_research(payload: dict):
    """Receives research digest from the research bot."""
    latest_research["content"] = payload.get("content", "")
    latest_research["received_at"] = datetime.now().isoformat()
    log.info("Research digest ingested successfully")
    return {"status": "ingested"}


@app.post("/trigger/content")
async def manual_trigger(background_tasks: BackgroundTasks, token: str = ""):
    """Manually trigger a content brief."""
    if MANUAL_TRIGGER_TOKEN and token != MANUAL_TRIGGER_TOKEN:
        return {"error": "Unauthorised"}

    background_tasks.add_task(daily_content_job)
    return {"status": "triggered", "type": "content_brief"}
