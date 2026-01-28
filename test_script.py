import cli_analytics

cli_analytics.init(
    api_key="cli__yT9ZNlxYHpkNghlGWVv7mXbMQ7CmUaC9nuLyzYn3Qw",
    tool_name="mycli",
    endpoint="http://localhost:8000"
)

# Track some commands
cli_analytics.track_command(["mycli", "build"], exit_code=0, duration_ms=1200)
cli_analytics.track_command(["mycli", "deploy"], exit_code=1, duration_ms=800)
print("Events tracked!")

# Test recommendations (simulating a failed deploy)
hint = cli_analytics.get_recommendation("deploy", failed=True)
if hint:
    print(f"Tip: {hint}")
else:
    print("No recommendations yet")

# A/B testing
variant = cli_analytics.get_variant("new-onboarding")
print(f"Variant: {variant}")
