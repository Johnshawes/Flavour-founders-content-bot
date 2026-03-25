# Flavour Founders — Content Bot

Generates 1 daily reel brief with 3 A/B hook variations. Runs 5 mins after the research bot.

## What It Does

- Reads the research bot's daily digest automatically
- Picks the strongest insight
- Generates 1 reel idea × 3 hooks to A/B test
- Posts full brief to #content Slack channel at 07:05am

## Output Per Brief

For each of the 3 hooks:
- Line 1 + Line 2 (screen text, 5 words max each)
- Curiosity line (middle)
- End line 1 + End line 2

Plus: caption, hashtags, why this week

## Environment Variables (Railway)

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Same key as research bot |
| `CONTENT_WEBHOOK_URL` | #content Slack webhook |
| `RESEARCH_WEBHOOK_URL` | Research bot's /ingest endpoint URL |
| `MANUAL_TRIGGER_TOKEN` | Same token as research bot |

## File Structure

```
content-bot/
├── main.py
├── requirements.txt
├── Procfile
└── README.md
```

## Endpoints

- `GET /` — health check + next scheduled run
- `POST /ingest` — receives research digest from research bot
- `POST /trigger/content?token=TOKEN` — manual trigger

## How Research Bot Connects

The research bot POSTs its digest to this bot's `/ingest` endpoint after each run.
Add the content bot's Railway URL as `RESEARCH_WEBHOOK_URL` in the research bot's variables.
