# CLI Analytics SDK

Privacy-first analytics for CLI tools.

## Installation

```bash
pip install cli-analytics
```

## Usage

```python
import cli_analytics

# Initialize once at startup
cli_analytics.init(
    api_key="your-api-key",
    tool_name="mytool",
    tool_version="1.0.0"
)

# Track commands
cli_analytics.track_command(
    command_path=["mytool", "deploy"],
    exit_code=0,
    duration_ms=1500,
    flags=["--force", "--env"]
)
```

## Get an API Key

```bash
curl -X POST https://cli-analytics.onrender.com/keys \
  -H "Content-Type: application/json" \
  -d '{"name": "my-cli-tool"}'
```
