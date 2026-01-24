# CLI Analytics

Workflow/Outcome Intelligence for CLI Tools - a privacy-first analytics system that helps you understand how developers use your CLI.

## Features

- **Privacy-First**: Never stores raw arguments, file paths, emails, tokens, or env vars
- **Sessionization**: Automatically groups events into user sessions (30-min timeout)
- **Workflow Detection**: Identifies workflows like "deploy", "test", "build"
- **Outcome Tracking**: Tracks SUCCESS, FAILED, and ABANDONED workflows
- **Failure Hot Paths**: Identifies common failing command sequences

## Quick Start (Local Development)

### Prerequisites

- Python 3.11+
- PostgreSQL (or use Supabase)

### 1. Clone and Setup

```bash
git clone https://github.com/YOUR_USERNAME/cli-analytics.git
cd cli-analytics
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Database

Create a `.env` file:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/cli_analytics
HASH_SALT=your-secret-salt-here
LOG_LEVEL=INFO
```

For Supabase, use the connection string from your project settings:
```env
DATABASE_URL=postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
```

### 3. Run Migrations

```bash
alembic upgrade head
```

### 4. Start the Server

```bash
uvicorn app.main:app --reload
```

The API is now running at http://localhost:8000

### 5. Generate Sample Data

```bash
python scripts/generate_sample.py
```

This creates `events.jsonl` with realistic CLI event data.

### 6. Ingest Events

```bash
python scripts/post_events.py events.jsonl --all
```

The `--all` flag will:
1. Post events to `/ingest`
2. Run `/infer` to process events
3. Display the summary report

### 7. View Reports

Open http://localhost:8000/docs for the interactive API documentation.

Or use curl:

```bash
# Health check
curl http://localhost:8000/health

# Summary report
curl http://localhost:8000/reports/summary

# Specific workflow details
curl http://localhost:8000/reports/workflows/apply_workflow
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/ingest` | POST | Ingest single or batch events |
| `/infer` | POST | Run sessionization and workflow inference |
| `/reports/summary` | GET | Get overall summary report |
| `/reports/workflows/{name}` | GET | Get details for a specific workflow |

## Event Schema

```json
{
  "timestamp": "2025-01-24T10:00:00Z",
  "tool_name": "terraform",
  "tool_version": "1.7.0",
  "command_path": ["terraform", "apply"],
  "flags_present": ["--auto-approve"],
  "exit_code": 0,
  "duration_ms": 45000,
  "error_type": null,
  "actor_id": "user-abc123",
  "machine_id": "machine-xyz789",
  "session_hint": null,
  "ci_detected": false
}
```

## Deploy to Render

### 1. Create Supabase Project

1. Go to [supabase.com](https://supabase.com) and create a new project
2. Go to Settings → Database → Connection string
3. Copy the URI (it starts with `postgresql://`)

### 2. Deploy to Render

1. Push your code to GitHub
2. Go to [render.com](https://render.com) and create a new Web Service
3. Connect your GitHub repository
4. Set the following:
   - **Build Command**: `pip install -r requirements.txt && alembic upgrade head`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables:
   - `DATABASE_URL`: Your Supabase connection string
   - `HASH_SALT`: A random secret string
   - `LOG_LEVEL`: `INFO`

Or use the `render.yaml` for automatic configuration:

```bash
# The render.yaml file is already configured
# Just connect your repo and Render will auto-detect it
```

## Running Tests

```bash
pytest tests/ -v
```

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ CLI Events  │────▶│  /ingest    │────▶│ raw_events  │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                                               ▼
                    ┌─────────────┐     ┌─────────────┐
                    │   /infer    │────▶│  sessions   │
                    └─────────────┘     │  workflows  │
                                        └─────────────┘
                                               │
                                               ▼
                    ┌─────────────┐     ┌─────────────┐
                    │  /reports   │◀────│  Aggregated │
                    └─────────────┘     │    Data     │
                                        └─────────────┘
```

## Privacy

The system is designed with privacy as a core principle:

- **Identifier Hashing**: `actor_id` and `machine_id` are hashed before storage
- **Flag Sanitization**: Only flag names are stored, never values
- **Command Path Filtering**: Only alphanumeric command names are allowed
- **Error Redaction**: File paths, emails, and tokens are stripped from error messages
- **Blocklist**: Flags containing "token", "password", "secret", etc. are automatically removed

## License

MIT
