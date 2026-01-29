# CLI Analytics

Privacy-first workflow intelligence for CLI tools. Understand how developers use your CLI, where they fail, and how to improve their experience.

## What It Does

- **Tracks CLI usage** without storing sensitive data
- **Detects workflows** automatically (init → build → deploy)
- **Identifies failure patterns** showing where users struggle
- **A/B testing** to measure CLI changes
- **Recommendations** based on usage patterns
- **Tenant isolation** - each tool's data is private

---

## Quick Start

### 1. Get API Key

```bash
curl -X POST https://cli-analytics-1.onrender.com/keys \
  -H "Content-Type: application/json" \
  -d '{"name": "my-key", "tool_name": "mycli"}'
```

Save the returned `api_key` - it won't be shown again.

### 2. Install SDK

**Python:**
```bash
pip install cli-analytics
```

**Node.js:**
```bash
npm install cli-analytics
```

### 3. Integrate

**Python:**
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

**Node.js:**
```javascript
import * as cliAnalytics from 'cli-analytics';

cliAnalytics.init({
  apiKey: 'cli_xxx',
  toolName: 'mycli',
  toolVersion: '1.0.0'
});

await cliAnalytics.trackCommand(['mycli', 'deploy'], 0, {
  durationMs: 1500,
  flags: ['--force']
});
```

---

## Features

### A/B Testing

Test new CLI flows with automatic variant assignment:

```python
variant = cli_analytics.get_variant("new-deploy-flow")
if variant == "variant_a":
    run_new_deploy()
else:
    run_old_deploy()
```

Create experiments via API:
```bash
curl -X POST https://cli-analytics-1.onrender.com/experiments \
  -H "Content-Type: application/json" \
  -H "X-API-Key: cli_xxx" \
  -d '{"name": "new-deploy-flow", "variants": ["control", "variant_a"]}'
```

### Recommendations

Show helpful tips when commands fail:

```python
if exit_code != 0:
    hint = cli_analytics.get_recommendation("deploy", failed=True)
    if hint:
        print(f"Tip: {hint}")
```

### Dashboard

View analytics at: `https://cli-analytics-1.onrender.com/dashboard`

Enter your API key to see:
- Total events, sessions, workflows
- Success rates by workflow
- Failure hot paths

---

## API Reference

All endpoints require `X-API-Key` header (except `/keys`).

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/keys` | POST | Create API key |
| `/ingest` | POST | Send events |
| `/infer` | POST | Process events into workflows |
| `/reports/summary` | GET | Analytics summary |
| `/reports/workflows/{name}` | GET | Workflow details |
| `/experiments` | GET | List experiments |
| `/experiments` | POST | Create experiment |
| `/experiments/{name}/variant` | GET | Get variant assignment |
| `/experiments/{name}/results` | GET | Experiment results |
| `/recommendations` | GET | Get recommendations |

### Example: Ingest Event

```bash
curl -X POST https://cli-analytics-1.onrender.com/ingest \
  -H "Content-Type: application/json" \
  -H "X-API-Key: cli_xxx" \
  -d '{
    "tool_name": "mycli",
    "command_path": ["mycli", "deploy"],
    "exit_code": 0,
    "duration_ms": 1500,
    "actor_id": "user-123",
    "machine_id": "mac-456",
    "timestamp": "2025-01-27T12:00:00Z",
    "flags_present": ["--force"],
    "ci_detected": false
  }'
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
└── auth.py           # API key auth + tenant isolation

sdk/                  # Python SDK
sdk-node/             # Node.js SDK
dashboard/            # Static HTML dashboard
migrations/           # Alembic
```

---

## Privacy & Security

**Data sanitization:**
- Identifiers hashed (actor_id, machine_id)
- Flag values stripped (only names stored)
- Paths redacted
- Tokens/emails removed

**Tenant isolation:**
- Each API key is scoped to a `tool_name`
- Data is filtered by tool - you only see your own data
- All endpoints require authentication

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
```

---

## Live

- **API**: https://cli-analytics-1.onrender.com
- **Docs**: https://cli-analytics-1.onrender.com/docs
- **Dashboard**: https://cli-analytics-1.onrender.com/dashboard
