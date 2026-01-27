# CLI Analytics

Privacy-first workflow intelligence for CLI tools. Understand how developers use your CLI, where they fail, and how to improve their experience.

## What It Does

- **Tracks CLI usage** without storing sensitive data
- **Detects workflows** automatically (init → build → deploy)
- **Identifies failure patterns** showing where users struggle
- **A/B testing** to measure CLI changes
- **Recommendations** based on usage patterns

---

## SDK Integration

### Install

```bash
pip install cli-analytics
```

### Get API Key

```bash
curl -X POST https://cli-analytics-1.onrender.com/keys \
  -H "Content-Type: application/json" \
  -d '{"name": "my-cli"}'
```

### Basic Usage

```python
import cli_analytics

cli_analytics.init(
    api_key="cli_xxx",
    tool_name="mycli",
    tool_version="1.0.0"
)

# Track commands
cli_analytics.track_command(
    command_path=["mycli", "deploy"],
    exit_code=0,
    duration_ms=1500,
    flags=["--force"]
)
```

### A/B Testing

```python
variant = cli_analytics.get_variant("new-deploy-flow")
if variant == "variant_a":
    run_new_deploy()
else:
    run_old_deploy()
```

### Recommendations

```python
if exit_code != 0:
    hint = cli_analytics.get_recommendation("deploy", failed=True)
    if hint:
        print(f"Tip: {hint}")
```

---

## Architecture

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   CLI + SDK  │─────▶│   FastAPI    │─────▶│   Supabase   │
└──────────────┘      └──────────────┘      └──────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        /ingest        /infer         /reports
        (events)    (workflows)    (analytics)
```

### Stack

| Layer | Tech |
|-------|------|
| API | FastAPI, Uvicorn |
| DB | Supabase PostgreSQL |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| Hosting | Render |

### Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /ingest` | Receive events (API key required) |
| `POST /infer` | Process into sessions/workflows |
| `GET /reports/summary` | Analytics dashboard data |
| `GET /recommendations` | Usage-based suggestions |
| `POST /experiments` | Create A/B test |
| `GET /experiments/{name}/variant` | Get variant |
| `GET /experiments/{name}/results` | Test results |

---

## Project Structure

```
app/
├── main.py           # FastAPI entry
├── ingest.py         # Event ingestion + privacy
├── infer.py          # Session + workflow detection
├── reports.py        # Analytics
├── recommendations.py
├── experiments.py    # A/B testing
├── models.py         # SQLAlchemy
└── auth.py           # API keys

sdk/                  # Python SDK
dashboard/            # Static HTML dashboard
migrations/           # Alembic
```

---

## Local Development

```bash
# Setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Configure .env
DATABASE_URL=postgresql://...
HASH_SALT=your-secret

# Run
alembic upgrade head
uvicorn app.main:app --reload

# Test with sample data
python scripts/generate_sample.py
python scripts/post_events.py events.jsonl --all
```

---

## Privacy

All data sanitized before storage:
- Identifiers hashed
- Flag values stripped
- Paths redacted
- Tokens/emails removed

---

## Live

- **API**: https://cli-analytics-1.onrender.com
- **Docs**: https://cli-analytics-1.onrender.com/docs
- **Dashboard**: https://cli-analytics-1.onrender.com/dashboard
